#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FIRE後計算パスの整合性検証テスト

全シミュレーションパス（ベースライン、MC事前計算、MCイテレーション、FIRE判定）が
共通関数を介して同一の支出・収入を算出することを検証する。
"""

import sys
from pathlib import Path
from datetime import datetime

import pytest
import numpy as np

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from config import load_config
from simulator import (
    _compute_post_fire_monthly_expenses,
    _compute_post_fire_monthly_income,
    _compute_austerity_period,
    _compute_austerity_reduction,
    _get_discretionary_ratio,
    _get_life_stage_for_year,
    _calculate_monthly_expenses,
    _calculate_monthly_income,
    _precompute_monthly_cashflows,
    _set_reference_date,
    calculate_base_expense,
)

FIXED_REF_DATE = datetime(2025, 3, 1)


@pytest.fixture(autouse=True)
def set_reference_date():
    _set_reference_date(FIXED_REF_DATE)


@pytest.fixture
def config():
    return load_config('config.yaml')


class TestExpenseConsistency:
    """共通関数 _compute_post_fire_monthly_expenses と各パスの支出が一致することを検証"""

    def test_shared_vs_calculate_monthly_expenses(self, config):
        """_calculate_monthly_expenses が FIRE後に共通関数へ委譲していることを検証"""
        years = 10.0
        prev_gains = 500_000.0
        years_since_fire = 5.0

        shared = _compute_post_fire_monthly_expenses(
            years, config,
            prev_year_capital_gains=prev_gains,
            years_since_fire=years_since_fire,
        )

        via_calc = _calculate_monthly_expenses(
            years, config,
            monthly_expense=300_000,
            expense_growth_rate=0.02,
            fire_achieved=True,
            prev_year_capital_gains=prev_gains,
            years_since_fire=years_since_fire,
        )

        assert abs(shared['total'] - via_calc['total']) < 1.0, (
            f"Shared={shared['total']:.0f} vs CalcMonthly={via_calc['total']:.0f}"
        )
        for key in ['base_expense', 'education_expense', 'mortgage_payment',
                     'maintenance_cost', 'workation_cost', 'pension_premium',
                     'health_insurance_premium']:
            assert abs(shared[key] - via_calc[key]) < 1.0, (
                f"{key}: shared={shared[key]:.0f} vs calc={via_calc[key]:.0f}"
            )

    def test_shared_vs_precompute(self, config):
        """_precompute_monthly_cashflows の支出が共通関数（健康保険除外）と一致"""
        years_offset = 4.0
        total_months = 24

        expenses, income, base_exp, life_stages, workation_costs = _precompute_monthly_cashflows(
            years_offset, total_months, config,
        )

        for month_idx in range(total_months):
            years = years_offset + month_idx / 12
            shared = _compute_post_fire_monthly_expenses(
                years, config, include_health_insurance=False,
            )
            assert abs(expenses[month_idx] - shared['total']) < 1.0, (
                f"Month {month_idx}: precompute={expenses[month_idx]:.0f} "
                f"vs shared={shared['total']:.0f}"
            )
            assert abs(base_exp[month_idx] - shared['annual_base_expense']) < 1.0
            assert abs(workation_costs[month_idx] - shared['workation_cost']) < 1.0

    def test_health_insurance_excluded_when_disabled(self, config):
        """include_health_insurance=False で健康保険料が0になることを検証"""
        years = 10.0
        with_hi = _compute_post_fire_monthly_expenses(
            years, config, include_health_insurance=True,
        )
        without_hi = _compute_post_fire_monthly_expenses(
            years, config, include_health_insurance=False,
        )
        assert without_hi['health_insurance_premium'] == 0.0
        assert with_hi['total'] >= without_hi['total']


class TestIncomeConsistency:
    """共通関数 _compute_post_fire_monthly_income と各パスの収入が一致することを検証"""

    def test_shared_vs_calculate_monthly_income(self, config):
        """_calculate_monthly_income が FIRE後に共通関数へ委譲していることを検証"""
        years = 15.0
        fire_month = 48
        current_assets = 50_000_000.0
        override_ages = {'夫': 74, '妻': 73}

        via_calc = _calculate_monthly_income(
            years, FIXED_REF_DATE,
            fire_achieved=True, fire_month=fire_month,
            husband_income_base=0, wife_income_base=0,
            monthly_income=0, husband_ratio=0.5,
            income_growth_rate=0.03, config=config,
            current_assets=current_assets,
            override_start_ages=override_ages,
        )

        shared = _compute_post_fire_monthly_income(
            years, config,
            fire_year_offset=fire_month / 12,
            current_assets=current_assets,
            override_start_ages=override_ages,
        )

        assert abs(via_calc['total_income'] - shared['total']) < 1.0, (
            f"CalcIncome={via_calc['total_income']:.0f} vs Shared={shared['total']:.0f}"
        )
        assert abs(via_calc['pension_income'] - shared['pension_income']) < 1.0
        assert abs(via_calc['child_allowance'] - shared['child_allowance']) < 1.0

    def test_shared_vs_precompute_income(self, config):
        """_precompute_monthly_cashflows の収入が共通関数と一致"""
        years_offset = 4.0
        total_months = 24
        override_ages = {'夫': 74, '妻': 73}

        _, income_arr, _, _, _ = _precompute_monthly_cashflows(
            years_offset, total_months, config,
            override_start_ages=override_ages,
        )

        for month_idx in range(total_months):
            years = years_offset + month_idx / 12
            shared = _compute_post_fire_monthly_income(
                years, config,
                fire_year_offset=years_offset,
                current_assets=None,
                override_start_ages=override_ages,
            )
            assert abs(income_arr[month_idx] - shared['total']) < 1.0, (
                f"Month {month_idx}: precompute={income_arr[month_idx]:.0f} "
                f"vs shared={shared['total']:.0f}"
            )


class TestAusterityConsistency:
    """緊縮削減の共通関数が全パスで正しく機能することを検証"""

    def test_austerity_period_calculation(self, config):
        """_compute_austerity_period が正しい期間を計算"""
        override_ages = {'夫': 74, '妻': 73}
        fire_years_offset = 4.0

        start, end, rate = _compute_austerity_period(
            config, fire_years_offset, override_ages,
        )

        if rate > 0:
            assert start is not None
            assert end is not None
            assert start < end
            assert start >= 0
            earliest_age = min(override_ages.values())
            start_age = config['simulation']['start_age']
            expected_end = int((earliest_age - start_age - fire_years_offset) * 12)
            assert end == expected_end

    def test_austerity_zero_outside_period(self, config):
        """緊縮期間外で削減額が0になることを検証"""
        years = 5.0
        reduction = _compute_austerity_reduction(
            months_since_fire=0, years=years, config=config,
            reduction_rate=0.3, reduction_start_month=100, reduction_end_month=200,
        )
        assert reduction == 0.0

    def test_austerity_positive_inside_period(self, config):
        """緊縮期間内で削減額が正になることを検証"""
        years = 30.0
        reduction = _compute_austerity_reduction(
            months_since_fire=150, years=years, config=config,
            reduction_rate=0.3, reduction_start_month=100, reduction_end_month=200,
        )
        assert reduction > 0.0

    def test_austerity_uses_discretionary_ratio(self, config):
        """緊縮削減が _get_discretionary_ratio を使用していることを検証"""
        years = 30.0
        disc_ratio = _get_discretionary_ratio(years, config)
        annual_base = calculate_base_expense(years, config, 0)
        expected = annual_base * disc_ratio / 12.0 * 0.3

        actual = _compute_austerity_reduction(
            months_since_fire=150, years=years, config=config,
            reduction_rate=0.3, reduction_start_month=100, reduction_end_month=200,
        )
        assert abs(actual - expected) < 1.0

    def test_no_austerity_when_rate_zero(self, config):
        """削減率0で削減額が0"""
        reduction = _compute_austerity_reduction(
            months_since_fire=150, years=30.0, config=config,
            reduction_rate=0.0, reduction_start_month=100, reduction_end_month=200,
        )
        assert reduction == 0.0


class TestLifeStageHelpers:
    """ライフステージ関連ヘルパーの整合性検証"""

    def test_life_stage_for_year_consistency(self, config):
        """_get_life_stage_for_year と _get_discretionary_ratio が整合"""
        for years in [5.0, 15.0, 25.0, 35.0, 45.0]:
            stage = _get_life_stage_for_year(years, config)
            ratio = _get_discretionary_ratio(years, config)
            expected_ratio = config['fire']['discretionary_ratio_by_stage'].get(stage, 0.30)
            assert ratio == expected_ratio, (
                f"years={years}: stage={stage}, ratio={ratio}, expected={expected_ratio}"
            )

    def test_precompute_life_stages_match(self, config):
        """_precompute_monthly_cashflows のライフステージが共通ヘルパーと一致"""
        years_offset = 4.0
        total_months = 24

        _, _, _, life_stages, _ = _precompute_monthly_cashflows(
            years_offset, total_months, config,
        )

        for month_idx in range(total_months):
            years = years_offset + month_idx / 12
            expected_stage = _get_life_stage_for_year(years, config)
            assert life_stages[month_idx] == expected_stage, (
                f"Month {month_idx}: precompute={life_stages[month_idx]} "
                f"vs helper={expected_stage}"
            )
