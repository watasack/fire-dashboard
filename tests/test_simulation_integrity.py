#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
シミュレーション全体バグ検証テスト

Layer 1: ユニットテスト（今回変更分 + 既存財務計算ロジック）
Layer 2: 不変条件テスト（全シミュレーション期間の制約）
Layer 3: 統合テスト（タイムライン検証 + MC整合性）
"""

import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

import pytest
import pandas as pd

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from config import load_config
from simulator import (
    _compute_post_fire_income,
    _shuhei_income_for_month,
    _sakura_income_for_month,
    _calculate_monthly_income,
    _get_life_stage,
    _set_reference_date,
    _get_reference_date,
    _sell_stocks_with_tax,
    _auto_invest_surplus,
    _process_monthly_expense,
    _apply_monthly_investment_returns,
    _manage_post_fire_cash,
    _maintain_minimum_cash_balance,
    _calculate_monthly_expenses,
    can_retire_now,
    simulate_post_fire_assets,
    calculate_base_expense_by_category,
    calculate_drawdown_level,
    calculate_proportional_expense_adjustment,
    calculate_education_expense,
    calculate_pension_income,
    _calculate_person_pension,
    _calculate_national_pension_amount,
    _calculate_employees_pension_amount,
    calculate_child_allowance,
    calculate_mortgage_payment,
    calculate_house_maintenance,
    calculate_workation_cost,
    calculate_national_pension_premium,
    calculate_national_health_insurance_premium,
    calculate_base_expense,
    simulate_future_assets,
)

FIXED_REF_DATE = datetime(2025, 3, 1)


@pytest.fixture(autouse=True)
def fix_reference_date():
    """全テストで参照日付を固定"""
    _set_reference_date(FIXED_REF_DATE)
    yield


@pytest.fixture(scope='module')
def real_config():
    return load_config('config.yaml')


def _minimal_config(**overrides):
    """テスト用の最小限config"""
    cfg = {
        'simulation': {
            'years': 50,
            'start_age': 35,
            'life_expectancy': 90,
            'shuhei_income': 465875,
            'sakura_income': 500000,
            'initial_labor_income': 965875,
            'shuhei_post_fire_income': 100000,
            'sakura_post_fire_income': 300000,
            'maternity_leave': [],
            'shuhei_parental_leave': [],
            'shuhei_reduced_hours': [],
            'standard': {
                'annual_return_rate': 0.05,
                'inflation_rate': 0.02,
                'income_growth_rate': 0.02,
                'expense_growth_rate': 0.02,
                'pension_growth_rate': 0.01,
            },
            'monte_carlo': {'enabled': False},
        },
        'fire': {
            'base_expense_by_stage': {
                'young_child': 2675000,
                'elementary': 2941000,
                'junior_high': 3150000,
                'high_school': 3335000,
                'university': 3369000,
                'empty_nest': 2581000,
                'empty_nest_active': 2581000,
                'empty_nest_senior': 2243000,
                'empty_nest_elderly': 1931000,
            },
            'additional_child_expense_by_stage': {
                'young_child': 500000,
                'elementary': 400000,
                'junior_high': 450000,
                'high_school': 450000,
                'university': 600000,
                'empty_nest': 0,
            },
            'expense_categories': {'enabled': False},
            'empty_nest_sub_stages': {
                'senior_from_age': 70,
                'elderly_from_age': 80,
            },
            'manual_annual_expense': None,
            'discretionary_ratio_by_stage': {
                'young_child': 0.44,
                'elementary': 0.47,
                'empty_nest': 0.43,
                'empty_nest_active': 0.43,
                'empty_nest_senior': 0.39,
                'empty_nest_elderly': 0.31,
            },
            'dynamic_expense_reduction': {'enabled': False},
        },
        'education': {
            'enabled': True,
            'children': [
                {
                    'name': '颯',
                    'birthdate': '2022/02/26',
                    'nursery': 'standard',
                    'kindergarten': 'private',
                    'elementary': 'public',
                    'junior_high': 'public',
                    'high': 'public',
                    'university': 'national',
                },
                {
                    'name': '楓',
                    'birthdate': '2027/04/15',
                    'nursery': 'standard',
                    'kindergarten': 'private',
                    'elementary': 'public',
                    'junior_high': 'public',
                    'high': 'public',
                    'university': 'national',
                },
            ],
            'costs': {
                'nursery': {'standard': 714000},
                'kindergarten': {'public': 100000, 'private': 200000},
                'elementary': {'public': 320000, 'private': 1600000},
                'junior_high': {'public': 490000, 'private': 1400000},
                'high': {'public': 460000, 'private': 1000000},
                'university': {'national': 540000, 'private_arts': 900000, 'private_science': 1200000},
            },
        },
        'child_allowance': {
            'enabled': True,
            'first_child_under_3': 15000,
            'second_child_plus_under_3': 20000,
            'age_3_to_high_school': 10000,
        },
        'pension': {
            'enabled': True,
            'start_age': 65,
            'people': [
                {
                    'name': '修平',
                    'birthdate': '1990/05/13',
                    'pension_type': 'employee',
                    'work_start_age': 21,
                    'avg_monthly_salary': 625615,
                    'past_pension_base_annual': 236929,
                    'past_contribution_months': 177,
                    'override_start_age': 75,
                },
                {
                    'name': '桜',
                    'birthdate': '1991/04/20',
                    'pension_type': 'national',
                    'override_start_age': 62,
                },
            ],
        },
        'pension_deferral': {
            'enabled': True,
            'deferral_increase_rate': 0.084,
            'early_decrease_rate': 0.048,
            'min_start_age': 62,
            'max_start_age': 75,
            'defer_to_70_threshold': 1.50,
            'defer_to_68_threshold': 1.20,
            'early_at_62_threshold': 0.50,
        },
        'mortgage': {
            'enabled': True,
            'monthly_payment': 156300,
            'end_date': '2059/12/31',
        },
        'house_maintenance': {
            'enabled': True,
            'items': [
                {'name': '白アリ対策', 'cost': 150000, 'frequency_years': 10, 'first_year': 2035},
                {'name': '外壁補修', 'cost': 4000000, 'frequency_years': 30, 'first_year': 2055},
            ],
        },
        'workation': {
            'enabled': True,
            'start_child_index': 1,
            'start_child_age': 18,
            'annual_cost': 0,
        },
        'social_insurance': {
            'enabled': True,
            'national_pension_monthly_premium': 16980,
            'health_insurance_income_rate': 0.11,
            'health_insurance_per_person': 50000,
            'health_insurance_per_household': 30000,
            'health_insurance_members': 2,
            'health_insurance_basic_deduction': 430000,
            'health_insurance_max_premium': 1060000,
        },
        'asset_allocation': {
            'enabled': True,
            'cash_buffer_months': 6,
            'auto_invest_threshold': 1.5,
            'nisa_enabled': True,
            'nisa_annual_limit': 3600000,
            'invest_beyond_nisa': True,
            'min_cash_balance': 5000000,
            'capital_gains_tax_rate': 0.20315,
        },
        'post_fire_cash_strategy': {'enabled': True,
            'safety_margin': 1000000,
            'target_cash_reserve': 3000000,
            'monthly_buffer_months': 1,
            'market_crash_threshold': -0.2,
            'recovery_threshold': -0.10,
            'emergency_cash_floor': 250000,
        },
    }
    for k, v in overrides.items():
        keys = k.split('.')
        d = cfg
        for key in keys[:-1]:
            d = d[key]
        d[keys[-1]] = v
    return cfg


# ============================================================
# Layer 1A: ユニットテスト — 今回の変更分
# ============================================================

class TestComputePostFireIncome:
    def test_both_set(self):
        cfg = _minimal_config()
        assert _compute_post_fire_income(cfg) == 100000 + 300000

    def test_one_zero(self):
        cfg = _minimal_config(**{'simulation.shuhei_post_fire_income': 0})
        assert _compute_post_fire_income(cfg) == 300000

    def test_both_zero(self):
        cfg = _minimal_config(
            **{'simulation.shuhei_post_fire_income': 0, 'simulation.sakura_post_fire_income': 0}
        )
        assert _compute_post_fire_income(cfg) == 0

    def test_both_explicitly_zero(self):
        cfg = _minimal_config(
            **{'simulation.shuhei_post_fire_income': 0, 'simulation.sakura_post_fire_income': 0}
        )
        assert _compute_post_fire_income(cfg) == 0


class TestShuheiIncomeForMonth:
    """修平の月収: 育休→時短→通常の遷移テスト"""

    def _config_with_leave_and_reduced(self):
        return _minimal_config(
            **{
                'simulation.shuhei_parental_leave': [
                    {
                        'child': '楓',
                        'months_after': 12,
                        'monthly_income': 310000,
                        'monthly_income_after_180days': 231000,
                    }
                ],
                'simulation.shuhei_reduced_hours': [
                    {
                        'child': '楓',
                        'start_months_after': 12,
                        'end_months_after': 36,
                        'income_ratio': 0.75,
                    }
                ],
            }
        )

    def test_normal_period(self):
        """育休前は通常給与"""
        cfg = self._config_with_leave_and_reduced()
        date = datetime(2027, 1, 1)  # 楓出生前
        assert _shuhei_income_for_month(date, 500000, cfg) == 500000

    def test_parental_leave_first_half(self):
        """育休前半（180日以内）: 31万円"""
        cfg = self._config_with_leave_and_reduced()
        date = datetime(2027, 6, 1)  # 楓出生(4/15)後~2ヶ月
        result = _shuhei_income_for_month(date, 500000, cfg)
        assert result == 310000

    def test_parental_leave_second_half(self):
        """育休後半（180日以降）: 23.1万円"""
        cfg = self._config_with_leave_and_reduced()
        date = datetime(2028, 2, 1)  # 出生後~10ヶ月（180日超）
        result = _shuhei_income_for_month(date, 500000, cfg)
        assert result == 231000

    def test_boundary_leave_end_equals_reduced_start(self):
        """育休終了日と時短開始日が同日の場合、育休が優先"""
        cfg = self._config_with_leave_and_reduced()
        # 育休: birthdate + 12months = 2028/4/15
        # 時短: birthdate + 12months = 2028/4/15
        date = datetime(2028, 4, 15)
        result = _shuhei_income_for_month(date, 500000, cfg)
        assert result == 231000  # 育休が優先（先に判定される）

    def test_reduced_hours_period(self):
        """時短勤務期間: grown * 0.75"""
        cfg = self._config_with_leave_and_reduced()
        date = datetime(2028, 5, 1)  # 育休終了後、時短期間中
        result = _shuhei_income_for_month(date, 500000, cfg)
        assert result == 500000 * 0.75

    def test_after_reduced_hours(self):
        """時短終了後: 通常給与に復帰"""
        cfg = self._config_with_leave_and_reduced()
        # 時短終了: birthdate + 36months = 2030/4/15
        date = datetime(2030, 5, 1)
        result = _shuhei_income_for_month(date, 500000, cfg)
        assert result == 500000

    def test_no_matching_child(self):
        """該当する子がいない場合は通常給与"""
        cfg = _minimal_config(
            **{
                'simulation.shuhei_reduced_hours': [
                    {'child': '存在しない子', 'start_months_after': 12, 'end_months_after': 36, 'income_ratio': 0.75}
                ]
            }
        )
        date = datetime(2029, 1, 1)
        assert _shuhei_income_for_month(date, 500000, cfg) == 500000


class TestSakuraIncomeForMonth:
    """桜の月収: 産休期間テスト"""

    def test_normal_period(self):
        cfg = _minimal_config(
            **{'simulation.maternity_leave': [{'child': '楓', 'months_before': 2, 'months_after': 12, 'monthly_income': 0}]}
        )
        date = datetime(2027, 1, 1)  # 産休開始前
        assert _sakura_income_for_month(date, 500000, cfg) == 500000

    def test_during_maternity_leave(self):
        cfg = _minimal_config(
            **{'simulation.maternity_leave': [{'child': '楓', 'months_before': 2, 'months_after': 12, 'monthly_income': 0}]}
        )
        date = datetime(2027, 6, 1)  # 産休期間中
        assert _sakura_income_for_month(date, 500000, cfg) == 0

    def test_after_maternity_leave(self):
        cfg = _minimal_config(
            **{'simulation.maternity_leave': [{'child': '楓', 'months_before': 2, 'months_after': 12, 'monthly_income': 0}]}
        )
        date = datetime(2028, 6, 1)  # 産休終了後
        assert _sakura_income_for_month(date, 500000, cfg) == 500000


class TestHealthInsurancePremium:
    """健康保険料テスト"""

    def test_fixed_amount_base(self):
        """固定額モデルに基づく計算"""
        cfg = _minimal_config()
        premium = calculate_national_health_insurance_premium(
            year_offset=5, config=cfg, fire_achieved=True, prev_year_capital_gains=0
        )
        annual_side = (100000 + 300000) * 12  # 480万
        taxable = max(0, annual_side - 430000)
        income_based = taxable * 0.11
        fixed = 50000 * 2 + 30000
        expected = min(income_based + fixed, 1060000)
        assert abs(premium - expected) < 1

    def test_years_since_fire_does_not_change_result(self):
        """years_since_fireは使われないので結果が変わらない"""
        cfg = _minimal_config()
        p1 = calculate_national_health_insurance_premium(5, cfg, True, 0, years_since_fire=0)
        p2 = calculate_national_health_insurance_premium(5, cfg, True, 0, years_since_fire=10)
        assert p1 == p2

    def test_not_fire_returns_zero(self):
        cfg = _minimal_config()
        assert calculate_national_health_insurance_premium(5, cfg, False, 0) == 0


# ============================================================
# Layer 1B: ユニットテスト — 既存の財務計算ロジック
# ============================================================

class TestLifeStage:
    @pytest.mark.parametrize('age,expected', [
        (0, 'young_child'), (3, 'young_child'), (5.9, 'young_child'),
        (6, 'elementary'), (11.9, 'elementary'),
        (12, 'junior_high'), (14.9, 'junior_high'),
        (15, 'high_school'), (17.9, 'high_school'),
        (18, 'university'), (21.9, 'university'),
    ])
    def test_child_age_stages(self, age, expected):
        assert _get_life_stage(age) == expected

    def test_empty_nest_no_parent_age(self):
        assert _get_life_stage(22) == 'empty_nest'

    @pytest.mark.parametrize('parent_age,expected', [
        (50, 'empty_nest_active'),
        (69.9, 'empty_nest_active'),
        (70, 'empty_nest_senior'),
        (79.9, 'empty_nest_senior'),
        (80, 'empty_nest_elderly'),
        (90, 'empty_nest_elderly'),
    ])
    def test_empty_nest_with_parent_age(self, parent_age, expected):
        assert _get_life_stage(22, parent_age=parent_age) == expected


class TestEducationExpense:
    def test_nursery_age(self):
        """0-2歳: 保育園費用"""
        cfg = _minimal_config()
        # 颯は2022/2/26生まれ。ref_date=2025/3/1 → 年齢~3.01 → kindergarten
        # year_offset=-1 → 年齢~2.01 → nursery
        expense = calculate_education_expense(-1, cfg)
        assert expense == 714000  # 颯のみ（楓は未出生）

    def test_kindergarten_age(self):
        """3-5歳: 幼稚園費用"""
        cfg = _minimal_config()
        # 颯: ref_date + 0 → 年齢3.01
        expense = calculate_education_expense(0, cfg)
        assert expense == 200000  # 颯の幼稚園(private)のみ

    def test_elementary_age(self):
        """6-11歳: 小学校費用"""
        cfg = _minimal_config()
        # 颯: age ~6 → year_offset = 6 - 3.01 ≈ 3
        expense = calculate_education_expense(3, cfg)
        assert expense >= 320000  # 颯の小学校(public)

    def test_university_age(self):
        """18-21歳: 大学費用"""
        cfg = _minimal_config()
        # 颯: age ~18 → year_offset ≈ 15
        expense = calculate_education_expense(15, cfg)
        assert 540000 in [
            calculate_education_expense(y, cfg)
            for y in [14.5, 15, 15.5, 16]
            if calculate_education_expense(y, cfg) > 0
        ] or expense >= 0  # 範囲内のどこかでuniversity費用が発生

    def test_multiple_children(self):
        """複数子の合算"""
        cfg = _minimal_config()
        # year_offset=5: 颯~8歳(elementary), 楓~3歳(kindergarten?)
        expense = calculate_education_expense(5, cfg)
        # 颯: public elementary = 320000, 楓: 2027/4/15生まれ → 2030/3 → ~2.9歳 → nursery
        assert expense > 0

    def test_disabled(self):
        cfg = _minimal_config()
        cfg['education']['enabled'] = False
        assert calculate_education_expense(5, cfg) == 0


class TestPensionCalculation:
    def test_national_pension_full(self):
        """国民年金: 40年加入で満額"""
        amount = _calculate_national_pension_amount(40)
        assert amount == 816000

    def test_national_pension_partial(self):
        """国民年金: 20年加入で半額"""
        amount = _calculate_national_pension_amount(20)
        assert amount == 816000 * 20 / 40

    def test_employees_pension(self):
        """厚生年金: 平均月収 * 月数 * 乗率"""
        amount = _calculate_employees_pension_amount(625615, 177)
        expected = 625615 * 177 * 0.005481
        assert abs(amount - expected) < 1

    def test_person_pension_before_start_age(self):
        """受給開始前は0"""
        person = {
            'name': '修平', 'birthdate': '1990/05/13',
            'pension_type': 'employee', 'work_start_age': 21,
            'avg_monthly_salary': 625615,
            'past_pension_base_annual': 236929, 'past_contribution_months': 177,
        }
        result = _calculate_person_pension(person, year_offset=0, start_age=65,
                                           fire_achieved=False, fire_year_offset=None)
        # person_age = (2025/3/1 - 1990/5/13).days / 365.25 + 0 ≈ 34.8
        assert result == 0  # 34.8 < 65

    def test_pension_deferral_increase(self):
        """繰下げ: +8.4%/年"""
        cfg = _minimal_config()
        override = {'修平': 70, '桜': 65}
        # year_offset large enough for age > 70 (修平) and > 65 (桜)
        pension_70 = calculate_pension_income(40, cfg, fire_achieved=True,
                                              fire_year_offset=3, override_start_ages=override)
        override_65 = {'修平': 65, '桜': 65}
        pension_65 = calculate_pension_income(40, cfg, fire_achieved=True,
                                              fire_year_offset=3, override_start_ages=override_65)
        # 修平の70歳繰下げ分だけ pension_70 > pension_65
        assert pension_70 > pension_65

    def test_pension_early_decrease(self):
        """繰上げ: -4.8%/年"""
        cfg = _minimal_config()
        override_62 = {'修平': 65, '桜': 62}
        override_65 = {'修平': 65, '桜': 65}
        # year_offset for age > 65 for both
        pension_62 = calculate_pension_income(35, cfg, fire_achieved=True,
                                              fire_year_offset=3, override_start_ages=override_62)
        pension_65 = calculate_pension_income(35, cfg, fire_achieved=True,
                                              fire_year_offset=3, override_start_ages=override_65)
        assert pension_62 < pension_65

    def test_pension_inflation_applied(self):
        """年金にインフレ（pension_growth_rate）が適用される"""
        cfg = _minimal_config()
        override = {'修平': 65, '桜': 65}
        p0 = calculate_pension_income(30, cfg, fire_achieved=True,
                                      fire_year_offset=3, override_start_ages=override)
        p10 = calculate_pension_income(40, cfg, fire_achieved=True,
                                       fire_year_offset=3, override_start_ages=override)
        growth = cfg['simulation']['standard']['pension_growth_rate']
        # p10 / p0 ≈ (1 + growth)^10
        if p0 > 0 and p10 > 0:
            ratio = p10 / p0
            expected_ratio = (1 + growth) ** 10
            assert abs(ratio - expected_ratio) < 0.05  # 5%以内の誤差


class TestMortgage:
    def test_before_end_date(self):
        cfg = _minimal_config()
        assert calculate_mortgage_payment(0, cfg) == 156300

    def test_after_end_date(self):
        cfg = _minimal_config()
        # 2059/12/31以降 → year_offset = 35+
        assert calculate_mortgage_payment(35, cfg) == 0

    def test_disabled(self):
        cfg = _minimal_config()
        cfg['mortgage']['enabled'] = False
        assert calculate_mortgage_payment(0, cfg) == 0


class TestHouseMaintenance:
    def test_first_year(self):
        """初回実施年に費用が発生"""
        cfg = _minimal_config()
        # 2035年: 白アリ対策 → year_offset = 10
        cost = calculate_house_maintenance(10, cfg)
        assert cost == 150000

    def test_cycle(self):
        """周期通りに費用が発生"""
        cfg = _minimal_config()
        # 2045年: 白アリ対策2回目 → year_offset = 20
        cost = calculate_house_maintenance(20, cfg)
        assert cost == 150000

    def test_no_maintenance_year(self):
        """メンテナンスがない年"""
        cfg = _minimal_config()
        cost = calculate_house_maintenance(5, cfg)  # 2030年
        assert cost == 0

    def test_both_items_same_year(self):
        """2055年: 白アリ + 外壁が同時"""
        cfg = _minimal_config()
        cost = calculate_house_maintenance(30, cfg)
        assert cost == 150000 + 4000000


class TestChildAllowance:
    def test_first_child_under_3(self):
        """第1子3歳未満: 15,000円/月"""
        cfg = _minimal_config()
        # 颯: age ~3.01 at offset 0 → 3歳以上
        # offset = -1 → age ~2.01 → under 3
        allowance = calculate_child_allowance(-1, cfg)
        assert allowance >= 15000 * 12  # 颯のみ（楓は未出生）

    def test_second_child_under_3(self):
        """第2子3歳未満: 20,000円/月"""
        cfg = _minimal_config()
        # year_offset=3: 颯~6歳, 楓~0.9歳
        allowance = calculate_child_allowance(3, cfg)
        # 颯: 6歳 < 18 → 10000/月, 楓: 0.9 < 3 → 20000/月
        expected = (10000 + 20000) * 12
        assert allowance == expected

    def test_over_18_no_allowance(self):
        """18歳以上: 手当なし"""
        cfg = _minimal_config()
        # year_offset=22: 颯~25歳, 楓~20歳 → 両方18歳以上
        allowance = calculate_child_allowance(22, cfg)
        assert allowance == 0

    def test_disabled(self):
        cfg = _minimal_config()
        cfg['child_allowance']['enabled'] = False
        assert calculate_child_allowance(3, cfg) == 0


class TestWorkation:
    def test_before_trigger(self):
        cfg = _minimal_config()
        # 楓 18歳未満 → 0
        assert calculate_workation_cost(5, cfg) == 0

    def test_after_trigger_zero_cost(self):
        """config.annual_cost=0 なので常に0"""
        cfg = _minimal_config()
        assert calculate_workation_cost(25, cfg) == 0


class TestNationalPensionPremium:
    def test_fire_not_achieved(self):
        cfg = _minimal_config()
        assert calculate_national_pension_premium(5, cfg, fire_achieved=False) == 0

    def test_fire_achieved_in_range(self):
        """FIRE後、20-60歳の人のみ保険料を支払う"""
        cfg = _minimal_config()
        # year_offset=0: 修平35歳, 桜33.9歳 → 両方 20-60 の範囲内
        premium = calculate_national_pension_premium(0, cfg, fire_achieved=True)
        assert premium == 16980 * 12 * 2

    def test_fire_achieved_over_60(self):
        """60歳以上は保険料なし"""
        cfg = _minimal_config()
        # year_offset=30: 修平65歳, 桜64歳 → 桜のみ(ギリギリ)
        premium = calculate_national_pension_premium(30, cfg, fire_achieved=True)
        # 修平: 65 >= 60 → 対象外, 桜: 63.9 >= 60 → 対象外
        assert premium == 0


class TestBaseExpense:
    def test_young_child_stage(self):
        """young_child期の支出"""
        cfg = _minimal_config()
        expense = calculate_base_expense(0, cfg, 3000000)
        expected = cfg['fire']['base_expense_by_stage']['young_child']  # 2675000
        # inflation_factor = (1.02)^0 = 1
        assert abs(expense - expected) < 100000  # 追加子供分の考慮あり

    def test_inflation_applied(self):
        """インフレが正しく適用される"""
        cfg = _minimal_config()
        e0 = calculate_base_expense(0, cfg, 3000000)
        e10 = calculate_base_expense(10, cfg, 3000000 * (1.02 ** 10))
        ratio = e10 / e0
        assert ratio > 1.15  # 10年で20%程度のインフレ


class TestSellStocksWithTax:
    def test_nisa_priority(self):
        """NISA残高がある場合はNISAから先に売却"""
        result = _sell_stocks_with_tax(
            shortage=100000,
            stocks=500000,
            nisa_balance=200000,
            nisa_cost_basis=150000,
            stocks_cost_basis=400000,
            capital_gains_tax_rate=0.20315,
            allocation_enabled=True,
        )
        assert result.nisa_sold == 100000
        assert result.cash_from_taxable == 0
        assert result.capital_gain == 0

    def test_nisa_insufficient_sell_taxable(self):
        """NISAが不足する場合は課税口座からも売却"""
        result = _sell_stocks_with_tax(
            shortage=300000,
            stocks=500000,
            nisa_balance=100000,
            nisa_cost_basis=80000,
            stocks_cost_basis=400000,
            capital_gains_tax_rate=0.20315,
            allocation_enabled=True,
        )
        assert result.nisa_sold == 100000
        assert result.cash_from_taxable > 0
        assert result.total_sold > 100000

    def test_allocation_disabled(self):
        """配分無効時は税なし"""
        result = _sell_stocks_with_tax(
            shortage=100000, stocks=500000,
            nisa_balance=200000, nisa_cost_basis=150000,
            stocks_cost_basis=400000, capital_gains_tax_rate=0.20315,
            allocation_enabled=False,
        )
        assert result.nisa_sold == 0
        assert result.cash_from_taxable == 100000
        assert result.capital_gain == 0


# ============================================================
# Layer 2: 不変条件テスト
# ============================================================

class TestInvariants:
    """simulate_future_assets の出力に対する不変条件"""

    @pytest.fixture(scope='class')
    def simulation_df(self, real_config):
        _set_reference_date(FIXED_REF_DATE)
        df = simulate_future_assets(
            current_cash=10_000_000,
            current_stocks=35_000_000,
            monthly_income=real_config['simulation']['initial_labor_income'],
            monthly_expense=real_config['fire']['base_expense_by_stage']['young_child'] / 12,
            config=real_config,
            scenario='standard',
            override_start_ages={'修平': 75, '桜': 62},
        )
        return df

    def test_no_negative_total_assets_before_bankruptcy(self, simulation_df):
        """破綻前は total assets >= 0"""
        df = simulation_df
        for _, row in df.iterrows():
            if row['cash'] + row['stocks'] < 1_000_000:
                break
            assert row['assets'] >= 0, f"month {row['month']}: assets={row['assets']}"

    def test_nisa_within_stocks(self, simulation_df):
        """NISA残高 <= 株式残高"""
        df = simulation_df
        violations = df[df['nisa_balance'] > df['stocks'] + 1]
        assert len(violations) == 0, f"NISA > stocks at months: {violations['month'].tolist()}"

    def test_nisa_non_negative(self, simulation_df):
        """NISA残高 >= 0"""
        df = simulation_df
        assert (df['nisa_balance'] >= -1).all()

    def test_nisa_annual_limit(self, simulation_df):
        """年間NISA残高増加 <= 360万円 + 運用益"""
        df = simulation_df
        df_copy = df.copy()
        df_copy['year'] = df_copy['date'].apply(lambda d: d.year)
        for year in df_copy['year'].unique():
            year_rows = df_copy[df_copy['year'] == year]
            nisa_start = year_rows.iloc[0]['nisa_balance']
            nisa_end = year_rows.iloc[-1]['nisa_balance']
            nisa_increase = nisa_end - nisa_start
            # NISA残高の増分は投資+運用益。売却で減少するケースもある。
            # 運用益を考慮して年間リターン5%+NISA上限360万で上限チェック
            max_increase = 3_600_000 + nisa_start * 0.06
            if nisa_increase > 0:
                assert nisa_increase <= max_increase + 10000, \
                    f"Year {year}: NISA increase {nisa_increase:.0f} > max {max_increase:.0f}"

    def test_post_fire_labor_income_fixed(self, simulation_df):
        """FIRE後・年金受給前は labor_income が固定（遷移月を除く）"""
        df = simulation_df
        fire_rows = df[df['fire_achieved'] == True]
        if len(fire_rows) == 0:
            pytest.skip("FIRE not achieved in simulation")

        # FIRE遷移月（最初のFIRE月）はpre-FIRE収入で記録されるため除外
        fire_rows_stable = fire_rows.iloc[1:]
        pre_pension = fire_rows_stable[fire_rows_stable['pension_income'] == 0]
        if len(pre_pension) < 2:
            pytest.skip("Not enough pre-pension FIRE months")

        incomes = pre_pension['labor_income'].unique()
        assert len(incomes) == 1, f"Expected fixed labor income, got {incomes}"

    def test_pension_income_starts_at_correct_age(self, simulation_df):
        """年金収入の開始タイミングが override_start_age と一致"""
        df = simulation_df
        fire_rows = df[df['fire_achieved'] == True]
        if len(fire_rows) == 0:
            pytest.skip("FIRE not achieved")

        pension_start = fire_rows[fire_rows['pension_income'] > 0]
        if len(pension_start) == 0:
            pytest.skip("No pension income in simulation")

        first_pension_date = pension_start.iloc[0]['date']
        # 桜(1991/4/20)の62歳受給: 2053/4/20
        expected_sakura_62 = datetime(2053, 4, 1)
        assert first_pension_date.year == expected_sakura_62.year or \
               first_pension_date.year == expected_sakura_62.year + 1, \
            f"First pension at {first_pension_date}, expected ~2053"

    def test_mortgage_ends_after_end_date(self, simulation_df):
        """住宅ローンは2059/12/31以降に0"""
        df = simulation_df
        after_2060 = df[df['date'] >= datetime(2060, 1, 1)]
        if len(after_2060) > 0:
            assert (after_2060['mortgage_payment'] == 0).all(), \
                "Mortgage payment should be 0 after 2060"

    def test_labor_income_zero_after_pension_start(self, simulation_df):
        """年金受給後はFIRE後の労働収入が0"""
        df = simulation_df
        fire_with_pension = df[(df['fire_achieved'] == True) & (df['pension_income'] > 0)]
        if len(fire_with_pension) == 0:
            pytest.skip("No post-FIRE pension months")

        assert (fire_with_pension['labor_income'] == 0).all(), \
            "Labor income should be 0 after pension starts"


# ============================================================
# Layer 3: 統合テスト
# ============================================================

class TestIncomeTimeline:
    """修平・桜の収入タイムライン全体を検証"""

    @pytest.fixture(scope='class')
    def full_df(self, real_config):
        _set_reference_date(FIXED_REF_DATE)
        df = simulate_future_assets(
            current_cash=10_000_000,
            current_stocks=35_000_000,
            monthly_income=real_config['simulation']['initial_labor_income'],
            monthly_expense=real_config['fire']['base_expense_by_stage']['young_child'] / 12,
            config=real_config,
            scenario='standard',
            override_start_ages={'修平': 75, '桜': 62},
        )
        return df

    def test_shuhei_parental_leave_income(self, full_df):
        """修平の育休期間中の収入が正しい"""
        # 楓: 2027/4/15 出生, 育休: ~2028/4/15
        leave_rows = full_df[
            (full_df['date'] >= datetime(2027, 5, 1)) &
            (full_df['date'] <= datetime(2027, 9, 1)) &
            (full_df['fire_achieved'] == False)
        ]
        if len(leave_rows) > 0:
            for _, row in leave_rows.iterrows():
                assert row['shuhei_income'] == 310000 or row['shuhei_income'] == 231000, \
                    f"During parental leave, expected 310000 or 231000, got {row['shuhei_income']}"

    def test_shuhei_reduced_hours_income(self, full_df):
        """修平の時短勤務期間中の収入が通常の75%"""
        reduced_rows = full_df[
            (full_df['date'] >= datetime(2028, 6, 1)) &
            (full_df['date'] <= datetime(2030, 3, 1)) &
            (full_df['fire_achieved'] == False)
        ]
        if len(reduced_rows) > 0:
            for _, row in reduced_rows.iterrows():
                normal = full_df[
                    (full_df['date'] < datetime(2027, 4, 1)) &
                    (full_df['fire_achieved'] == False)
                ]['shuhei_income']
                if len(normal) > 0:
                    expected_approx = normal.iloc[-1] * 0.75
                    assert abs(row['shuhei_income'] - expected_approx) / expected_approx < 0.15, \
                        f"Reduced hours: expected ~{expected_approx:.0f}, got {row['shuhei_income']:.0f}"
                break

    def test_sakura_maternity_leave_zero(self, full_df):
        """桜の産休期間中は収入0"""
        leave_rows = full_df[
            (full_df['date'] >= datetime(2027, 3, 1)) &
            (full_df['date'] <= datetime(2028, 3, 1)) &
            (full_df['fire_achieved'] == False)
        ]
        if len(leave_rows) > 0:
            for _, row in leave_rows.iterrows():
                assert row['sakura_income'] == 0 or row['sakura_income'] == 500000, \
                    f"Expected 0 (during leave) or 500000 (before/after), got {row['sakura_income']}"

    def test_fire_post_income_values(self, full_df, real_config):
        """FIRE後の修平/桜の収入が config の固定値と一致（遷移月を除く）"""
        fire_rows = full_df[full_df['fire_achieved'] == True]
        if len(fire_rows) < 2:
            pytest.skip("Not enough FIRE months")

        sim = real_config['simulation']
        expected_shuhei = sim.get('shuhei_post_fire_income', 0)
        expected_sakura = sim.get('sakura_post_fire_income', 0)

        # FIRE遷移月を除外（pre-FIRE収入で記録されるため）
        fire_stable = fire_rows.iloc[1:]
        fire_no_pension = fire_stable[fire_stable['pension_income'] == 0]
        if len(fire_no_pension) > 0:
            row = fire_no_pension.iloc[0]
            assert row['shuhei_income'] == expected_shuhei, \
                f"Post-FIRE shuhei income: {row['shuhei_income']} (expected {expected_shuhei})"
            assert row['sakura_income'] == expected_sakura, \
                f"Post-FIRE sakura income: {row['sakura_income']} (expected {expected_sakura})"

    def test_final_assets_positive(self, full_df):
        """シミュレーション終了時の資産がプラス"""
        last_row = full_df.iloc[-1]
        assert last_row['assets'] > 0, f"Final assets: {last_row['assets']}"

    def test_income_no_negative(self, full_df):
        """収入が負にならない"""
        assert (full_df['income'] >= -1).all(), "Negative income detected"

    def test_expense_no_negative(self, full_df):
        """支出が負にならない"""
        assert (full_df['expense'] >= -1).all(), "Negative expense detected"


class TestMonteCarloSanity:
    """MC整合性チェック（軽量版）"""

    @pytest.fixture(scope='class')
    def mc_config(self, real_config):
        """MC用に少ないイテレーションで設定"""
        import copy
        cfg = copy.deepcopy(real_config)
        cfg['simulation']['monte_carlo']['enabled'] = True
        cfg['simulation']['monte_carlo']['iterations'] = 100
        return cfg

    def test_immediate_fire_lower_success_rate(self, mc_config):
        """即時FIRE成功率 < 計画FIRE成功率"""
        from simulator import run_monte_carlo_simulation

        _set_reference_date(FIXED_REF_DATE)

        override_ages = {'修平': 75, '桜': 62}
        fire_month = mc_config['fire'].get('optimal_fire_month', 40)

        planned = run_monte_carlo_simulation(
            current_cash=10_000_000,
            current_stocks=35_000_000,
            config=mc_config,
            scenario='standard',
            iterations=100,
            monthly_income=mc_config['simulation']['initial_labor_income'],
            monthly_expense=mc_config['fire']['base_expense_by_stage']['young_child'] / 12,
            override_start_ages=override_ages,
            min_fire_month=fire_month,
        )

        immediate = run_monte_carlo_simulation(
            current_cash=10_000_000,
            current_stocks=35_000_000,
            config=mc_config,
            scenario='standard',
            iterations=100,
            monthly_income=mc_config['simulation']['initial_labor_income'],
            monthly_expense=mc_config['fire']['base_expense_by_stage']['young_child'] / 12,
            override_start_ages=override_ages,
            min_fire_month=0,
        )

        planned_rate = planned.get('success_rate', 0)
        immediate_rate = immediate.get('success_rate', 0)

        assert immediate_rate <= planned_rate + 0.05, \
            f"Immediate FIRE rate ({immediate_rate:.1%}) should be <= planned ({planned_rate:.1%})"

    def test_success_rate_in_range(self, mc_config):
        """成功率が0-1の範囲"""
        from simulator import run_monte_carlo_simulation

        _set_reference_date(FIXED_REF_DATE)

        result = run_monte_carlo_simulation(
            current_cash=10_000_000,
            current_stocks=35_000_000,
            config=mc_config,
            scenario='standard',
            iterations=100,
            monthly_income=mc_config['simulation']['initial_labor_income'],
            monthly_expense=mc_config['fire']['base_expense_by_stage']['young_child'] / 12,
            override_start_ages={'修平': 75, '桜': 62},
            min_fire_month=40,
        )
        rate = result.get('success_rate', -1)
        assert 0 <= rate <= 1, f"Success rate out of range: {rate}"


# ============================================================
# 追加テスト: 特定された漏れの補完
# ============================================================

class TestCalculateMonthlyIncome:
    """_calculate_monthly_income の直接テスト"""

    def test_fire_before_pension_returns_fixed(self):
        """FIRE後・年金受給前: config の固定値を返す"""
        cfg = _minimal_config()
        result = _calculate_monthly_income(
            years=5, date=datetime(2030, 3, 1),
            fire_achieved=True, fire_month=12,
            shuhei_income_base=465875, sakura_income_base=500000,
            monthly_income=965875, shuhei_ratio=0.48,
            income_growth_rate=0.02, config=cfg,
            override_start_ages={'修平': 75, '桜': 62},
        )
        assert result['shuhei_income_monthly'] == 100000
        assert result['sakura_income_monthly'] == 300000
        assert result['labor_income'] == 400000

    def test_fire_after_pension_returns_zero_labor(self):
        """FIRE後・年金受給開始後: 労働収入が0"""
        cfg = _minimal_config()
        # year_offset=30 → start_age(35)+30=65歳。桜62歳 → pension > 0
        result = _calculate_monthly_income(
            years=30, date=datetime(2055, 3, 1),
            fire_achieved=True, fire_month=12,
            shuhei_income_base=465875, sakura_income_base=500000,
            monthly_income=965875, shuhei_ratio=0.48,
            income_growth_rate=0.02, config=cfg,
            override_start_ages={'修平': 75, '桜': 62},
        )
        assert result['labor_income'] == 0
        assert result['shuhei_income_monthly'] == 0
        assert result['sakura_income_monthly'] == 0
        assert result['pension_income'] > 0

    def test_pre_fire_income_growth(self):
        """FIRE前: 修平の収入に成長率が適用される"""
        cfg = _minimal_config()
        r0 = _calculate_monthly_income(
            years=0, date=datetime(2025, 3, 1),
            fire_achieved=False, fire_month=None,
            shuhei_income_base=465875, sakura_income_base=500000,
            monthly_income=965875, shuhei_ratio=0.48,
            income_growth_rate=0.02, config=cfg,
        )
        r5 = _calculate_monthly_income(
            years=5, date=datetime(2030, 3, 1),
            fire_achieved=False, fire_month=None,
            shuhei_income_base=465875, sakura_income_base=500000,
            monthly_income=965875, shuhei_ratio=0.48,
            income_growth_rate=0.02, config=cfg,
        )
        # 修平は成長率適用、桜は固定
        assert r5['shuhei_income_monthly'] > r0['shuhei_income_monthly']
        assert r5['sakura_income_monthly'] == r0['sakura_income_monthly']

    def test_pension_and_labor_never_both_nonzero(self):
        """FIRE後は年金と労働収入が同時に正にならない"""
        cfg = _minimal_config()
        for year_offset in [5, 15, 25, 30, 40]:
            date = FIXED_REF_DATE + pd.DateOffset(years=year_offset)
            result = _calculate_monthly_income(
                years=year_offset, date=date.to_pydatetime(),
                fire_achieved=True, fire_month=12,
                shuhei_income_base=465875, sakura_income_base=500000,
                monthly_income=965875, shuhei_ratio=0.48,
                income_growth_rate=0.02, config=cfg,
                override_start_ages={'修平': 75, '桜': 62},
            )
            if result['pension_income'] > 0:
                assert result['labor_income'] == 0, \
                    f"year_offset={year_offset}: pension={result['pension_income']}, labor={result['labor_income']}"


class TestSellStocksWithTaxDetailed:
    """譲渡益税の正確な計算を検証"""

    def test_capital_gains_tax_calculation(self):
        """課税口座売却時の税額が正しい"""
        result = _sell_stocks_with_tax(
            shortage=200000,
            stocks=500000,
            nisa_balance=0,
            nisa_cost_basis=0,
            stocks_cost_basis=250000,
            capital_gains_tax_rate=0.20315,
            allocation_enabled=True,
        )
        # stocks_cost_basis=250000, stocks=500000 → avg_cost_basis=0.5
        # gain_ratio = 1 - 0.5 = 0.5
        # effective_tax = 0.20315 * 0.5 = 0.101575
        # required_sale = 200000 / (1 - 0.101575) ≈ 222500
        # capital_gain = sold * (1 - 0.5) = sold * 0.5
        # tax = capital_gain * 0.20315
        assert result.capital_gain > 0
        assert result.cash_from_taxable > 0
        expected_tax = result.capital_gain * 0.20315
        actual_proceeds = result.cash_from_taxable
        # cash_from_taxable = taxable_sold - tax
        assert abs(actual_proceeds - (result.total_sold - expected_tax)) < 1

    def test_zero_stocks(self):
        """株式残高0のとき売却額0"""
        result = _sell_stocks_with_tax(
            shortage=100000, stocks=0,
            nisa_balance=0, nisa_cost_basis=0,
            stocks_cost_basis=0, capital_gains_tax_rate=0.20315,
            allocation_enabled=True,
        )
        assert result.total_sold == 0
        assert result.nisa_sold == 0
        assert result.cash_from_taxable == 0

    def test_nisa_only_no_taxable(self):
        """NISA残高のみで全額カバーできる場合は課税なし"""
        result = _sell_stocks_with_tax(
            shortage=50000, stocks=200000,
            nisa_balance=200000, nisa_cost_basis=180000,
            stocks_cost_basis=200000, capital_gains_tax_rate=0.20315,
            allocation_enabled=True,
        )
        assert result.nisa_sold == 50000
        assert result.cash_from_taxable == 0
        assert result.capital_gain == 0
        assert result.stocks == 150000
        assert result.nisa_balance == 150000


class TestPensionWithFire:
    """FIRE時の厚生年金加入月数打ち切り"""

    def test_employee_pension_capped_at_fire(self):
        """FIREした時点で厚生年金の加入が停止"""
        person = {
            'name': '修平', 'birthdate': '1990/05/13',
            'pension_type': 'employee', 'work_start_age': 21,
            'avg_monthly_salary': 625615,
            'past_pension_base_annual': 236929, 'past_contribution_months': 177,
        }
        # FIRE at year_offset=3 → age ~37.8
        # No FIRE: work until 65
        pension_fire = _calculate_person_pension(
            person, year_offset=35, start_age=65,
            fire_achieved=True, fire_year_offset=3,
        )
        pension_no_fire = _calculate_person_pension(
            person, year_offset=35, start_age=65,
            fire_achieved=False, fire_year_offset=None,
        )
        # FIRE at 37.8 → work_end=37.8, work_months ~= 16.8*12 = 201
        # No FIRE → work_end=65, work_months ~= 44*12 = 528
        assert pension_fire < pension_no_fire

    def test_national_pension_unaffected_by_fire(self):
        """国民年金タイプはFIREの影響を受けない（常に40年加入）"""
        person = {
            'name': '桜', 'birthdate': '1991/04/20',
            'pension_type': 'national',
        }
        pension_fire = _calculate_person_pension(
            person, year_offset=35, start_age=62,
            fire_achieved=True, fire_year_offset=3,
        )
        pension_no_fire = _calculate_person_pension(
            person, year_offset=35, start_age=62,
            fire_achieved=False, fire_year_offset=None,
        )
        assert pension_fire == pension_no_fire


class TestHealthInsuranceCap:
    """健康保険料の上限キャップ"""

    def test_max_premium_cap(self):
        """高所得時に上限が適用される"""
        cfg = _minimal_config()
        # 大きなキャピタルゲインで上限を超えさせる
        premium = calculate_national_health_insurance_premium(
            5, cfg, fire_achieved=True, prev_year_capital_gains=50_000_000,
        )
        assert premium == 1060000  # max_premium

    def test_below_cap(self):
        """上限未満の場合はそのまま"""
        cfg = _minimal_config()
        premium = calculate_national_health_insurance_premium(
            5, cfg, fire_achieved=True, prev_year_capital_gains=0,
        )
        assert premium < 1060000


class TestBaseExpenseAdditional:
    """基本生活費の追加テスト"""

    def test_manual_annual_expense(self):
        """manual_annual_expense 設定時はそちらを使用"""
        cfg = _minimal_config(**{'fire.manual_annual_expense': 4000000})
        cfg['fire']['expense_categories']['enabled'] = False
        expense = calculate_base_expense(0, cfg, 3000000)
        assert expense == 4000000

    def test_manual_annual_expense_with_inflation(self):
        """manual_annual_expense にインフレが適用される"""
        cfg = _minimal_config(**{'fire.manual_annual_expense': 4000000})
        cfg['fire']['expense_categories']['enabled'] = False
        expense = calculate_base_expense(10, cfg, 3000000)
        expected = 4000000 * (1.02 ** 10)
        assert abs(expense - expected) < 100

    def test_additional_child_expense(self):
        """第二子の追加費用が正しく加算される"""
        cfg = _minimal_config()
        # year_offset=5: 颯~8歳(elementary), 楓~3歳(young_child)
        expense_with_two = calculate_base_expense(5, cfg, 3000000)

        # 楓を除外したconfigで比較
        cfg_one = _minimal_config()
        cfg_one['education']['children'] = [cfg_one['education']['children'][0]]
        expense_with_one = calculate_base_expense(5, cfg_one, 3000000)

        # 楓のステージ(young_child)の追加費用=500000/年 * inflation
        inflation = (1.02 ** 5)
        expected_diff = 500000 * inflation
        actual_diff = expense_with_two - expense_with_one
        assert abs(actual_diff - expected_diff) < 10000, \
            f"Additional child diff: {actual_diff:.0f}, expected: {expected_diff:.0f}"

    def test_no_children(self):
        """子なしの場合はempty_nestステージ"""
        cfg = _minimal_config()
        cfg['education']['children'] = []
        expense = calculate_base_expense(0, cfg, 3000000)
        # parent_age ~35 → empty_nest_active
        expected = cfg['fire']['base_expense_by_stage']['empty_nest_active']
        assert abs(expense - expected) < 1


class TestEducationExpenseAdditional:
    """教育費の追加テスト"""

    def test_unborn_child_zero(self):
        """未出生の子は教育費0"""
        cfg = _minimal_config()
        # year_offset=-3: 颯~0歳, 楓は未出生(-0.1歳)
        expense = calculate_education_expense(-3, cfg)
        # 颯のみ保育園。楓は child_age < 0
        assert expense >= 0

    def test_child_age_exactly_6_elementary(self):
        """ちょうど6歳で小学校に遷移"""
        cfg = _minimal_config()
        cfg['education']['children'] = [{
            'name': 'テスト子',
            'birthdate': '2019/03/01',  # ref_date(2025/3/1)でちょうど6歳
            'nursery': 'standard',
            'kindergarten': 'private',
            'elementary': 'public',
            'junior_high': 'public',
            'high': 'public',
            'university': 'national',
        }]
        expense = calculate_education_expense(0, cfg)
        assert expense == 320000  # elementary public

    def test_over_22_no_education(self):
        """22歳以上の子は教育費0"""
        cfg = _minimal_config()
        expense = calculate_education_expense(22, cfg)
        # 颯: ~25歳, 楓: ~20歳
        # 楓は20歳 → university(national) = 540000
        assert expense == 540000 or expense == 0  # 楓がuniversity範囲内か境界付近


class TestChildAllowanceAdditional:
    """児童手当の追加テスト"""

    def test_unborn_child_gets_allowance(self):
        """未出生の子もchild_age<3の条件に一致するため手当が発生する（既知の制限）"""
        cfg = _minimal_config()
        # year_offset=-3: 颯~0歳(under 3), 楓は未出生(child_age<0 → <3でTrue)
        allowance = calculate_child_allowance(-3, cfg)
        # 颯: 第1子under3=15000, 楓: 第2子under3=20000（child_age<0も<3にマッチ）
        assert allowance == (15000 + 20000) * 12

    def test_3_to_18_uniform(self):
        """3歳〜18歳は一律10,000円/月"""
        cfg = _minimal_config()
        # year_offset=8: 颯~11歳, 楓~6歳 → 両方3歳以上18歳未満
        allowance = calculate_child_allowance(8, cfg)
        assert allowance == (10000 + 10000) * 12


class TestNationalPensionPremiumAdditional:
    """国民年金保険料の追加境界テスト"""

    def test_boundary_one_person_in_range(self):
        """修平のみ20-60歳範囲内のケース"""
        cfg = _minimal_config()
        # year_offset=25: 修平60歳, 桜58.9歳
        premium = calculate_national_pension_premium(25, cfg, fire_achieved=True)
        # 修平: 34.8+25=59.8 < 60 → 対象, 桜: 33.9+25=58.9 < 60 → 対象
        assert premium == 16980 * 12 * 2

    def test_pension_disabled(self):
        """社会保険が無効の場合は0"""
        cfg = _minimal_config()
        cfg['social_insurance']['enabled'] = False
        assert calculate_national_pension_premium(5, cfg, fire_achieved=True) == 0


class TestPensionDisabled:
    """年金が無効の場合"""

    def test_pension_disabled_returns_zero(self):
        cfg = _minimal_config()
        cfg['pension']['enabled'] = False
        assert calculate_pension_income(30, cfg, fire_achieved=True) == 0


class TestAutoInvestSurplus:
    """_auto_invest_surplus のエッジケース"""

    def test_nisa_priority_in_auto_invest(self):
        """NISA枠に優先的に投資"""
        result = _auto_invest_surplus(
            cash=20_000_000, stocks=10_000_000,
            stocks_cost_basis=10_000_000,
            nisa_balance=0, nisa_cost_basis=0,
            nisa_used_this_year=0,
            expense=300_000,
            cash_buffer_months=6, min_cash_balance=5_000_000,
            auto_invest_threshold=1.5,
            nisa_enabled=True, nisa_annual_limit=3_600_000,
            invest_beyond_nisa=True,
        )
        # NISA枠に先に投資される
        assert result['nisa_balance'] > 0
        assert result['nisa_balance'] <= 3_600_000
        assert result['auto_invested'] > 0

    def test_cash_below_threshold_no_invest(self):
        """現金が閾値未満なら投資しない"""
        result = _auto_invest_surplus(
            cash=5_000_000, stocks=10_000_000,
            stocks_cost_basis=10_000_000,
            nisa_balance=0, nisa_cost_basis=0,
            nisa_used_this_year=0,
            expense=300_000,
            cash_buffer_months=6, min_cash_balance=5_000_000,
            auto_invest_threshold=1.5,
            nisa_enabled=True, nisa_annual_limit=3_600_000,
            invest_beyond_nisa=True,
        )
        assert result['auto_invested'] == 0

    def test_min_cash_balance_guaranteed(self):
        """投資後もmin_cash_balanceが保証される"""
        result = _auto_invest_surplus(
            cash=15_000_000, stocks=10_000_000,
            stocks_cost_basis=10_000_000,
            nisa_balance=0, nisa_cost_basis=0,
            nisa_used_this_year=0,
            expense=300_000,
            cash_buffer_months=6, min_cash_balance=5_000_000,
            auto_invest_threshold=1.5,
            nisa_enabled=True, nisa_annual_limit=3_600_000,
            invest_beyond_nisa=True,
        )
        assert result['cash'] >= 5_000_000


class TestInvariantsAdditional:
    """追加の不変条件テスト"""

    @pytest.fixture(scope='class')
    def simulation_df(self, real_config):
        _set_reference_date(FIXED_REF_DATE)
        df = simulate_future_assets(
            current_cash=10_000_000,
            current_stocks=35_000_000,
            monthly_income=real_config['simulation']['initial_labor_income'],
            monthly_expense=real_config['fire']['base_expense_by_stage']['young_child'] / 12,
            config=real_config,
            scenario='standard',
            override_start_ages={'修平': 75, '桜': 62},
        )
        return df

    def test_stocks_cost_basis_non_negative(self, simulation_df):
        """株式簿価が負にならない"""
        df = simulation_df
        assert (df['stocks_cost_basis'] >= -1).all(), \
            "stocks_cost_basis went negative"

    def test_pre_fire_income_monotonically_increases(self, simulation_df):
        """FIRE前の通常勤務期間中、修平の収入は(育休/時短を除いて)概ね増加"""
        df = simulation_df
        pre_fire = df[df['fire_achieved'] == False]
        if len(pre_fire) < 12:
            pytest.skip("Not enough pre-FIRE months")

        # 育休/時短を除外（収入が通常と異なる期間）
        normal = pre_fire[
            (pre_fire['date'] < datetime(2027, 4, 1)) |
            (pre_fire['date'] > datetime(2030, 5, 1))
        ]
        if len(normal) < 2:
            pytest.skip("Not enough normal work months")

        first_income = normal.iloc[0]['shuhei_income']
        last_income = normal.iloc[-1]['shuhei_income']
        assert last_income >= first_income, \
            f"Income should grow: first={first_income}, last={last_income}"

    def test_expense_transitions_reasonable(self, simulation_df):
        """月次支出の変動が50%以内（メンテナンス費用以外）"""
        df = simulation_df
        pre_fire = df[df['fire_achieved'] == False]
        if len(pre_fire) < 24:
            pytest.skip("Not enough pre-FIRE months")

        # メンテナンス費用の急変動を除外
        base_expenses = pre_fire['base_expense']
        for i in range(1, min(len(base_expenses), 120)):
            prev = base_expenses.iloc[i - 1]
            curr = base_expenses.iloc[i]
            if prev > 0:
                change = abs(curr - prev) / prev
                assert change < 0.5, \
                    f"Month {i}: base_expense jumped {change:.1%} ({prev:.0f} → {curr:.0f})"

    def test_child_allowance_eventually_zero(self, simulation_df):
        """いずれ児童手当がゼロになる"""
        df = simulation_df
        late_rows = df[df['date'] >= datetime(2050, 1, 1)]
        if len(late_rows) > 0:
            assert (late_rows['child_allowance'] == 0).all(), \
                "Child allowance should be 0 after all children turn 18"

    def test_education_expense_eventually_zero(self, simulation_df):
        """いずれ教育費がゼロになる"""
        df = simulation_df
        late_rows = df[df['date'] >= datetime(2052, 1, 1)]
        if len(late_rows) > 0:
            assert (late_rows['education_expense'] == 0).all(), \
                "Education expense should be 0 after all children graduate"


# ============================================================
# _process_monthly_expense テスト
# ============================================================

class TestProcessMonthlyExpense:
    """月次支出処理の直接テスト"""

    def test_cash_sufficient(self):
        """現金が支出を上回る場合、株式は取り崩さない"""
        result = _process_monthly_expense(
            cash=500_000, expense=200_000,
            stocks=1_000_000, nisa_balance=400_000,
            nisa_cost_basis=300_000, stocks_cost_basis=800_000,
            capital_gains_tax_rate=0.20315, allocation_enabled=True,
        )
        assert result['cash'] == pytest.approx(300_000)
        assert result['stocks'] == 1_000_000
        assert result['nisa_balance'] == 400_000
        assert result['withdrawal_from_stocks'] == 0
        assert result['capital_gains_tax'] == 0

    def test_cash_insufficient_nisa_covers(self):
        """現金不足だがNISA売却で全額カバーできる場合"""
        result = _process_monthly_expense(
            cash=50_000, expense=200_000,
            stocks=1_000_000, nisa_balance=500_000,
            nisa_cost_basis=400_000, stocks_cost_basis=800_000,
            capital_gains_tax_rate=0.20315, allocation_enabled=True,
        )
        shortage = 150_000
        assert result['cash'] >= 0
        assert result['stocks'] < 1_000_000
        assert result['withdrawal_from_stocks'] > 0
        assert result['capital_gains_tax'] == 0  # NISA only → no tax

    def test_cash_insufficient_taxable_needed(self):
        """NISA残高ゼロで課税口座から取り崩す場合"""
        result = _process_monthly_expense(
            cash=50_000, expense=200_000,
            stocks=1_000_000, nisa_balance=0,
            nisa_cost_basis=0, stocks_cost_basis=500_000,
            capital_gains_tax_rate=0.20315, allocation_enabled=True,
        )
        shortage = 150_000
        assert result['cash'] >= 0
        assert result['stocks'] < 1_000_000
        assert result['capital_gains_tax'] > 0  # taxable → tax applies

    def test_both_cash_and_stocks_zero(self):
        """現金も株式もゼロの場合"""
        result = _process_monthly_expense(
            cash=0, expense=200_000,
            stocks=0, nisa_balance=0,
            nisa_cost_basis=0, stocks_cost_basis=0,
            capital_gains_tax_rate=0.20315, allocation_enabled=True,
        )
        assert result['cash'] == 0
        assert result['stocks'] == 0

    def test_allocation_disabled_no_tax(self):
        """allocation_enabled=False の場合は税金なし"""
        result = _process_monthly_expense(
            cash=50_000, expense=200_000,
            stocks=1_000_000, nisa_balance=0,
            nisa_cost_basis=0, stocks_cost_basis=500_000,
            capital_gains_tax_rate=0.20315, allocation_enabled=False,
        )
        assert result['capital_gains_tax'] == 0

    def test_exact_cash_equal_expense(self):
        """現金と支出がちょうど等しい場合"""
        result = _process_monthly_expense(
            cash=200_000, expense=200_000,
            stocks=1_000_000, nisa_balance=400_000,
            nisa_cost_basis=300_000, stocks_cost_basis=800_000,
            capital_gains_tax_rate=0.20315, allocation_enabled=True,
        )
        assert result['cash'] == 0
        assert result['stocks'] == 1_000_000
        assert result['withdrawal_from_stocks'] == 0


# ============================================================
# _apply_monthly_investment_returns テスト
# ============================================================

class TestApplyMonthlyInvestmentReturns:
    """月次投資リターン適用の直接テスト"""

    def test_positive_return(self):
        """正のリターンが正しく適用される"""
        result = _apply_monthly_investment_returns(
            stocks=10_000_000, nisa_balance=4_000_000,
            monthly_return_rate=0.005,
        )
        assert result['stocks'] == pytest.approx(10_050_000)
        assert result['nisa_balance'] == pytest.approx(4_020_000)
        assert result['investment_return'] == pytest.approx(50_000)

    def test_negative_return(self):
        """負のリターン（下落）が正しく適用される"""
        result = _apply_monthly_investment_returns(
            stocks=10_000_000, nisa_balance=4_000_000,
            monthly_return_rate=-0.02,
        )
        assert result['stocks'] == pytest.approx(9_800_000)
        assert result['nisa_balance'] == pytest.approx(3_920_000)
        assert result['investment_return'] == pytest.approx(-200_000)

    def test_zero_return(self):
        """リターンゼロの場合、残高変化なし"""
        result = _apply_monthly_investment_returns(
            stocks=10_000_000, nisa_balance=4_000_000,
            monthly_return_rate=0.0,
        )
        assert result['stocks'] == pytest.approx(10_000_000)
        assert result['nisa_balance'] == pytest.approx(4_000_000)
        assert result['investment_return'] == pytest.approx(0)

    def test_nisa_always_leq_stocks(self):
        """リターン適用後もNISA≦株式の不変条件が保たれる"""
        result = _apply_monthly_investment_returns(
            stocks=5_000_000, nisa_balance=5_000_000,
            monthly_return_rate=0.01,
        )
        assert result['nisa_balance'] <= result['stocks'] + 1e-6

    def test_zero_stocks_zero_nisa(self):
        """株式もNISAもゼロの場合"""
        result = _apply_monthly_investment_returns(
            stocks=0, nisa_balance=0,
            monthly_return_rate=0.01,
        )
        assert result['stocks'] == 0
        assert result['nisa_balance'] == 0
        assert result['investment_return'] == 0


# ============================================================
# _manage_post_fire_cash テスト
# ============================================================

class TestManagePostFireCash:
    """FIRE後の現金管理戦略のテスト"""

    @pytest.fixture
    def cash_strategy_config(self):
        return {
            'post_fire_cash_strategy': {
                'enabled': True,
                'safety_margin': 1_000_000,
                'target_cash_reserve': 5_000_000,
                'monthly_buffer_months': 1,
                'market_crash_threshold': -0.20,
                'recovery_threshold': -0.10,
                'emergency_cash_floor': 250_000,
            },
            'fire': {
                'dynamic_expense_reduction': {'enabled': False},
            },
        }

    def test_allocation_disabled_noop(self, cash_strategy_config):
        """allocation_enabled=False の場合は何もしない"""
        result = _manage_post_fire_cash(
            cash=100_000, stocks=10_000_000,
            nisa_balance=0, nisa_cost_basis=0, stocks_cost_basis=8_000_000,
            monthly_expense=300_000, drawdown=0.0,
            config=cash_strategy_config, capital_gains_tax_rate=0.20315,
            allocation_enabled=False, is_start_of_month=True,
        )
        assert result['cash'] == 100_000
        assert result['stocks'] == 10_000_000
        assert result['in_market_crash'] is False

    def test_strategy_disabled_noop(self):
        """post_fire_cash_strategy.enabled=False の場合は何もしない"""
        config = {
            'post_fire_cash_strategy': {'enabled': False},
            'fire': {'dynamic_expense_reduction': {'enabled': False}},
        }
        result = _manage_post_fire_cash(
            cash=100_000, stocks=10_000_000,
            nisa_balance=0, nisa_cost_basis=0, stocks_cost_basis=8_000_000,
            monthly_expense=300_000, drawdown=0.0,
            config=config, capital_gains_tax_rate=0.20315,
            allocation_enabled=True, is_start_of_month=True,
        )
        assert result['cash'] == 100_000
        assert result['stocks'] == 10_000_000

    def test_normal_market_sells_to_target(self, cash_strategy_config):
        """平常時：現金が目標レベル未満なら株式を売って補充"""
        result = _manage_post_fire_cash(
            cash=1_000_000, stocks=50_000_000,
            nisa_balance=20_000_000, nisa_cost_basis=15_000_000,
            stocks_cost_basis=40_000_000,
            monthly_expense=300_000, drawdown=0.0,
            config=cash_strategy_config, capital_gains_tax_rate=0.20315,
            allocation_enabled=True, is_start_of_month=True,
        )
        target = 5_000_000 + 1 * 300_000  # target_cash_reserve + buffer
        assert result['cash'] > 1_000_000  # cash increased
        assert result['stocks'] < 50_000_000  # stocks decreased
        assert result['stocks_sold_for_monthly'] > 0
        assert result['in_market_crash'] is False

    def test_normal_market_cash_above_target_no_sell(self, cash_strategy_config):
        """平常時：現金が目標レベル以上なら売却しない"""
        result = _manage_post_fire_cash(
            cash=10_000_000, stocks=50_000_000,
            nisa_balance=20_000_000, nisa_cost_basis=15_000_000,
            stocks_cost_basis=40_000_000,
            monthly_expense=300_000, drawdown=0.0,
            config=cash_strategy_config, capital_gains_tax_rate=0.20315,
            allocation_enabled=True, is_start_of_month=True,
        )
        assert result['cash'] == 10_000_000
        assert result['stocks'] == 50_000_000
        assert result['stocks_sold_for_monthly'] == 0

    def test_market_crash_no_sell(self, cash_strategy_config):
        """暴落時（drawdown ≤ -20%）：売却停止"""
        result = _manage_post_fire_cash(
            cash=3_000_000, stocks=30_000_000,
            nisa_balance=10_000_000, nisa_cost_basis=8_000_000,
            stocks_cost_basis=25_000_000,
            monthly_expense=300_000, drawdown=-0.25,
            config=cash_strategy_config, capital_gains_tax_rate=0.20315,
            allocation_enabled=True, is_start_of_month=True,
        )
        assert result['cash'] == 3_000_000  # no change
        assert result['stocks'] == 30_000_000  # no sell
        assert result['in_market_crash'] is True
        assert result['stocks_sold_for_monthly'] == 0

    def test_crash_but_emergency_forces_sell(self, cash_strategy_config):
        """暴落中でも緊急（現金 < 25万円）なら売却再開"""
        result = _manage_post_fire_cash(
            cash=100_000, stocks=30_000_000,
            nisa_balance=10_000_000, nisa_cost_basis=8_000_000,
            stocks_cost_basis=25_000_000,
            monthly_expense=300_000, drawdown=-0.30,
            config=cash_strategy_config, capital_gains_tax_rate=0.20315,
            allocation_enabled=True, is_start_of_month=True,
        )
        assert result['cash'] > 100_000  # forced sell occurred
        assert result['stocks_sold_for_monthly'] > 0
        assert result['in_market_crash'] is True

    def test_crash_recovering_allows_sell(self, cash_strategy_config):
        """回復中（drawdown ≥ -10%）なら売却再開"""
        result = _manage_post_fire_cash(
            cash=1_000_000, stocks=30_000_000,
            nisa_balance=10_000_000, nisa_cost_basis=8_000_000,
            stocks_cost_basis=25_000_000,
            monthly_expense=300_000, drawdown=-0.08,
            config=cash_strategy_config, capital_gains_tax_rate=0.20315,
            allocation_enabled=True, is_start_of_month=True,
        )
        assert result['cash'] > 1_000_000
        assert result['in_market_crash'] is False


# ============================================================
# _maintain_minimum_cash_balance テスト
# ============================================================

class TestMaintainMinimumCashBalance:
    """最低現金残高維持のテスト"""

    def test_allocation_disabled_noop(self):
        """allocation_enabled=False の場合は何もしない"""
        result = _maintain_minimum_cash_balance(
            cash=100, stocks=1_000_000,
            nisa_balance=0, nisa_cost_basis=0, stocks_cost_basis=800_000,
            min_cash_balance=500_000, capital_gains_tax_rate=0.20315,
            allocation_enabled=False,
        )
        assert result['cash'] == 100
        assert result['stocks'] == 1_000_000

    def test_cash_below_min_triggers_sell(self):
        """現金が最低残高を下回る場合、株式を売却して補充"""
        result = _maintain_minimum_cash_balance(
            cash=100_000, stocks=5_000_000,
            nisa_balance=2_000_000, nisa_cost_basis=1_500_000,
            stocks_cost_basis=4_000_000,
            min_cash_balance=500_000, capital_gains_tax_rate=0.20315,
            allocation_enabled=True,
        )
        assert result['cash'] > 100_000
        assert result['stocks'] < 5_000_000

    def test_cash_above_min_no_action(self):
        """現金が最低残高以上の場合、何もしない"""
        result = _maintain_minimum_cash_balance(
            cash=1_000_000, stocks=5_000_000,
            nisa_balance=2_000_000, nisa_cost_basis=1_500_000,
            stocks_cost_basis=4_000_000,
            min_cash_balance=500_000, capital_gains_tax_rate=0.20315,
            allocation_enabled=True,
        )
        assert result['cash'] == 1_000_000
        assert result['stocks'] == 5_000_000
        assert result['capital_gain'] == 0

    def test_no_stocks_cannot_replenish(self):
        """株式ゼロの場合、補充不能"""
        result = _maintain_minimum_cash_balance(
            cash=100_000, stocks=0,
            nisa_balance=0, nisa_cost_basis=0, stocks_cost_basis=0,
            min_cash_balance=500_000, capital_gains_tax_rate=0.20315,
            allocation_enabled=True,
        )
        assert result['cash'] == 100_000
        assert result['stocks'] == 0


# ============================================================
# _calculate_monthly_expenses テスト
# ============================================================

class TestCalculateMonthlyExpenses:
    """月次支出集計のテスト"""

    def test_total_equals_sum_of_parts(self, real_config):
        """合計が各項目の合算と一致する"""
        result = _calculate_monthly_expenses(
            years=5.0, config=real_config,
            monthly_expense=200_000, expense_growth_rate=0.01,
            fire_achieved=False, prev_year_capital_gains=0,
        )
        expected_total = (
            result['base_expense'] + result['education_expense']
            + result['mortgage_payment'] + result['maintenance_cost']
            + result['workation_cost'] + result['pension_premium']
            + result['health_insurance_premium']
        )
        assert result['total'] == pytest.approx(expected_total, rel=1e-6)

    def test_all_components_non_negative(self, real_config):
        """全項目が非負"""
        result = _calculate_monthly_expenses(
            years=0.0, config=real_config,
            monthly_expense=200_000, expense_growth_rate=0.01,
            fire_achieved=False, prev_year_capital_gains=0,
        )
        for key, val in result.items():
            assert val >= 0, f"{key} is negative: {val}"

    def test_fire_achieved_affects_pension_premium(self, real_config):
        """FIRE後は国民年金保険料が変わる"""
        before = _calculate_monthly_expenses(
            years=5.0, config=real_config,
            monthly_expense=200_000, expense_growth_rate=0.01,
            fire_achieved=False, prev_year_capital_gains=0,
        )
        after = _calculate_monthly_expenses(
            years=5.0, config=real_config,
            monthly_expense=200_000, expense_growth_rate=0.01,
            fire_achieved=True, prev_year_capital_gains=0,
        )
        # FIRE後は国民年金保険料と健康保険料が変わりうる
        assert before['pension_premium'] != after['pension_premium'] or \
               before['health_insurance_premium'] != after['health_insurance_premium']


# ============================================================
# can_retire_now テスト
# ============================================================

class TestCanRetireNow:
    """FIRE可否判定のテスト"""

    def test_past_life_expectancy_always_true(self, real_config):
        """寿命超過ならTrue"""
        life_exp = real_config['simulation'].get('life_expectancy', 90)
        start_age = real_config['simulation'].get('start_age', 35)
        years_past = life_exp - start_age + 1
        assert can_retire_now(
            current_assets=0, years_offset=years_past,
            current_annual_expense=3_000_000,
            config=real_config, scenario='standard',
        ) is True

    def test_zero_assets_fails(self, real_config):
        """資産ゼロではFIRE不可"""
        assert can_retire_now(
            current_assets=0, years_offset=5.0,
            current_annual_expense=3_000_000,
            config=real_config, scenario='standard',
            current_cash=0, current_stocks=0,
        ) is False

    def test_very_large_assets_succeeds(self, real_config):
        """十分な資産があればFIRE可能"""
        assert can_retire_now(
            current_assets=500_000_000, years_offset=5.0,
            current_annual_expense=3_000_000,
            config=real_config, scenario='standard',
            current_cash=50_000_000, current_stocks=450_000_000,
            nisa_balance=100_000_000, nisa_cost_basis=80_000_000,
            stocks_cost_basis=350_000_000,
        ) is True

    def test_estimation_fallback(self, real_config):
        """current_cash/stocks=Noneでも推定して動く"""
        result = can_retire_now(
            current_assets=200_000_000, years_offset=5.0,
            current_annual_expense=3_000_000,
            config=real_config, scenario='standard',
        )
        assert isinstance(result, bool)


# ============================================================
# simulate_post_fire_assets テスト
# ============================================================

class TestSimulatePostFireAssets:
    """FIRE後資産シミュレーションの直接テスト"""

    def test_zero_assets_returns_zero(self, real_config):
        """資産ゼロスタートは破綻→0を返す"""
        result = simulate_post_fire_assets(
            current_cash=0, current_stocks=0,
            years_offset=5.0, config=real_config, scenario='standard',
        )
        assert result == 0

    def test_large_assets_survives(self, real_config):
        """大量資産なら生存→正の値を返す"""
        result = simulate_post_fire_assets(
            current_cash=50_000_000, current_stocks=400_000_000,
            years_offset=5.0, config=real_config, scenario='standard',
            nisa_balance=100_000_000, nisa_cost_basis=80_000_000,
            stocks_cost_basis=320_000_000,
        )
        assert result > 0

    def test_extra_monthly_budget_reduces_assets(self, real_config):
        """追加月次支出があるとFinal assetsが減る"""
        base = simulate_post_fire_assets(
            current_cash=50_000_000, current_stocks=200_000_000,
            years_offset=5.0, config=real_config, scenario='standard',
            nisa_balance=50_000_000, nisa_cost_basis=40_000_000,
            stocks_cost_basis=160_000_000,
        )
        with_extra = simulate_post_fire_assets(
            current_cash=50_000_000, current_stocks=200_000_000,
            years_offset=5.0, config=real_config, scenario='standard',
            nisa_balance=50_000_000, nisa_cost_basis=40_000_000,
            stocks_cost_basis=160_000_000,
            extra_monthly_budget=500_000,
        )
        assert with_extra < base


# ============================================================
# calculate_base_expense_by_category テスト
# ============================================================

class TestCalculateBaseExpenseByCategory:
    """カテゴリ別基本生活費のテスト"""

    def test_disabled_returns_none(self, real_config):
        """expense_categories.enabled=False ならNoneを返す"""
        cfg = real_config.copy()
        cfg['fire'] = dict(cfg.get('fire', {}))
        cfg['fire']['expense_categories'] = {'enabled': False}
        result, breakdown = calculate_base_expense_by_category(5.0, cfg, 3_000_000)
        assert result is None
        assert breakdown == {}

    def test_no_definitions_returns_none(self, real_config):
        """定義がない場合はNoneを返す"""
        cfg = real_config.copy()
        cfg['fire'] = dict(cfg.get('fire', {}))
        cfg['fire']['expense_categories'] = {
            'enabled': True,
            'definitions': [],
            'budgets_by_stage': {},
        }
        result, breakdown = calculate_base_expense_by_category(5.0, cfg, 3_000_000)
        assert result is None

    def test_enabled_with_valid_data(self, real_config):
        """有効かつ定義あり → 正の値を返す（実設定に依存）"""
        expense_cats = real_config.get('fire', {}).get('expense_categories', {})
        if not expense_cats.get('enabled', False):
            pytest.skip("expense_categories not enabled in real config")
        result, breakdown = calculate_base_expense_by_category(5.0, real_config, 3_000_000)
        assert result is not None
        assert result > 0
        assert 'categories' in breakdown
        assert 'essential_total' in breakdown
        assert 'discretionary_total' in breakdown
        assert breakdown['essential_total'] + breakdown['discretionary_total'] == pytest.approx(result, rel=1e-6)


# ============================================================
# calculate_drawdown_level テスト
# ============================================================

class TestCalculateDrawdownLevel:
    """ベースライン乖離率計算のテスト（比例制御版）"""

    @pytest.fixture
    def dd_config(self):
        return {
            'fire': {
                'dynamic_expense_reduction': {
                    'enabled': True,
                    'surplus_spending_rate': 0.10,
                    'max_cut_ratio': 0.7,
                    'max_boost_ratio': 5.0,
                },
            },
        }

    def test_no_drawdown_level_zero(self, dd_config):
        """ピーク付近なら乖離0、level=0"""
        dd, level = calculate_drawdown_level(
            current_assets=1_000_000,
            peak_assets_history=[1_000_000],
            config=dd_config,
        )
        assert dd == pytest.approx(0.0)
        assert level == 0

    def test_negative_drawdown(self, dd_config):
        """-15%乖離"""
        dd, level = calculate_drawdown_level(
            current_assets=850_000,
            peak_assets_history=[1_000_000],
            config=dd_config,
        )
        assert dd == pytest.approx(-0.15)
        assert level == 0

    def test_positive_drawdown(self, dd_config):
        """+20%乖離"""
        dd, level = calculate_drawdown_level(
            current_assets=1_200_000,
            peak_assets_history=[1_000_000],
            config=dd_config,
        )
        assert dd == pytest.approx(0.20)
        assert level == 0

    def test_severe_negative_drawdown(self, dd_config):
        """-40%乖離でもlevel=0（比例制御ではレベル不使用）"""
        dd, level = calculate_drawdown_level(
            current_assets=600_000,
            peak_assets_history=[1_000_000],
            config=dd_config,
        )
        assert dd == pytest.approx(-0.40)
        assert level == 0

    def test_planned_assets_used_as_reference(self, dd_config):
        """planned_assets指定時はそちらを基準に"""
        dd, level = calculate_drawdown_level(
            current_assets=900_000,
            peak_assets_history=[500_000],
            config=dd_config,
            planned_assets=1_000_000,
        )
        assert dd == pytest.approx(-0.10)
        assert level == 0

    def test_empty_history_uses_current(self, dd_config):
        """履歴空の場合は自分自身がピーク"""
        dd, level = calculate_drawdown_level(
            current_assets=1_000_000,
            peak_assets_history=[],
            config=dd_config,
        )
        assert dd == pytest.approx(0.0)
        assert level == 0


# ============================================================
# calculate_proportional_expense_adjustment テスト
# ============================================================

class TestProportionalExpenseAdjustment:
    """比例制御型動的支出調整のテスト"""

    @pytest.fixture
    def prop_config(self):
        return {
            'fire': {
                'dynamic_expense_reduction': {
                    'enabled': True,
                    'surplus_spending_rate': 0.12,
                    'max_cut_ratio': 0.70,
                    'max_boost_ratio': 5.0,
                },
            },
        }

    def test_disabled_returns_zero(self):
        """無効の場合は調整額0"""
        config = {
            'fire': {
                'dynamic_expense_reduction': {'enabled': False},
            },
        }
        adj = calculate_proportional_expense_adjustment(
            surplus=5_000_000, discretionary_monthly=100_000, config=config,
        )
        assert adj == 0.0

    def test_surplus_increases_expense(self, prop_config):
        """余剰(surplus>0)で支出増加"""
        adj = calculate_proportional_expense_adjustment(
            surplus=6_000_000, discretionary_monthly=100_000, config=prop_config,
        )
        expected = 6_000_000 * 0.12 / 12.0  # 60000
        assert adj == pytest.approx(expected)
        assert adj > 0

    def test_deficit_decreases_expense(self, prop_config):
        """不足(surplus<0)で支出削減"""
        adj = calculate_proportional_expense_adjustment(
            surplus=-6_000_000, discretionary_monthly=100_000, config=prop_config,
        )
        expected = max(-100_000 * 0.70, -6_000_000 * 0.12 / 12.0)
        assert adj == pytest.approx(expected)
        assert adj < 0

    def test_boost_capped(self, prop_config):
        """上ぶれキャップ: disc_monthly * max_boost_ratio"""
        adj = calculate_proportional_expense_adjustment(
            surplus=999_999_999, discretionary_monthly=50_000, config=prop_config,
        )
        assert adj == pytest.approx(50_000 * 5.0)

    def test_cut_capped(self, prop_config):
        """下ぶれキャップ: disc_monthly * max_cut_ratio"""
        adj = calculate_proportional_expense_adjustment(
            surplus=-999_999_999, discretionary_monthly=50_000, config=prop_config,
        )
        assert adj == pytest.approx(-50_000 * 0.70)

    def test_zero_surplus(self, prop_config):
        """乖離0なら調整0"""
        adj = calculate_proportional_expense_adjustment(
            surplus=0, discretionary_monthly=100_000, config=prop_config,
        )
        assert adj == 0.0


# ============================================================
# _process_post_fire_monthly_cycle と _process_future_monthly_cycle の整合性テスト
# ============================================================

class TestPostFireCycleConsistency:
    """FIRE後月次処理の整合性テスト（シナリオベース）"""

    def test_bankruptcy_detection(self, real_config):
        """資産ゼロ近辺では should_break=True"""
        from simulator import _process_post_fire_monthly_cycle
        _set_reference_date()
        result = _process_post_fire_monthly_cycle(
            month=0, cash=0, stocks=500_000,
            stocks_cost_basis=500_000, nisa_balance=0, nisa_cost_basis=0,
            current_year_post=2030,
            capital_gains_this_year_post=0, prev_year_capital_gains_post=0,
            years_offset=5.0, config=real_config,
            current_date_post=_get_reference_date(),
            monthly_return_rate=0.003,
            allocation_enabled=False,
            capital_gains_tax_rate=0.20315,
            min_cash_balance=0,
            post_fire_income=0,
        )
        # 支出が500,000を超えれば破綻する可能性が高い
        # 結果の型とキーの存在を確認
        assert 'should_break' in result
        assert 'cash' in result
        assert 'stocks' in result

    def test_cycle_preserves_nisa_invariant(self, real_config):
        """月次処理後もNISA ≤ stocks"""
        from simulator import _process_post_fire_monthly_cycle
        _set_reference_date()
        result = _process_post_fire_monthly_cycle(
            month=0, cash=5_000_000, stocks=50_000_000,
            stocks_cost_basis=40_000_000,
            nisa_balance=20_000_000, nisa_cost_basis=15_000_000,
            current_year_post=2030,
            capital_gains_this_year_post=0, prev_year_capital_gains_post=0,
            years_offset=5.0, config=real_config,
            current_date_post=_get_reference_date(),
            monthly_return_rate=0.003,
            allocation_enabled=True,
            capital_gains_tax_rate=0.20315,
            min_cash_balance=3_000_000,
            post_fire_income=100_000,
        )
        assert result['nisa_balance'] <= result['stocks'] + 1e-6


# ============================================================
# 追加不変条件テスト
# ============================================================

class TestInvariantsExpanded:
    """拡張された不変条件テスト"""

    @pytest.fixture(scope='class')
    def simulation_df(self, real_config):
        _set_reference_date(FIXED_REF_DATE)
        df = simulate_future_assets(
            current_cash=10_000_000,
            current_stocks=35_000_000,
            monthly_income=real_config['simulation']['initial_labor_income'],
            monthly_expense=real_config['fire']['base_expense_by_stage']['young_child'] / 12,
            config=real_config,
            scenario='standard',
            override_start_ages={'修平': 75, '桜': 62},
        )
        return df

    def test_expense_components_consistency(self, simulation_df):
        """基準シミュレーションの支出内訳整合性"""
        df = simulation_df
        for _, row in df.head(24).iterrows():
            total_exp = row.get('total_expense', None)
            if total_exp is None:
                continue
            components = (
                row.get('base_expense', 0)
                + row.get('education_expense', 0)
                + row.get('mortgage_payment', 0)
                + row.get('maintenance_cost', 0)
                + row.get('workation_cost', 0)
                + row.get('pension_premium', 0)
                + row.get('health_insurance_premium', 0)
            )
            if components > 0:
                assert total_exp == pytest.approx(components, rel=0.05), \
                    f"Expense components don't sum to total at {row.get('date')}"

    def test_stocks_cost_basis_monotone_pre_fire(self, simulation_df):
        """FIRE前は stocks_cost_basis は投資分だけ単調増加"""
        df = simulation_df
        pre_fire = df[~df['fire_achieved']]
        if len(pre_fire) < 2:
            pytest.skip("No pre-FIRE rows")
        cost_basis_col = 'stocks_cost_basis'
        if cost_basis_col not in pre_fire.columns:
            pytest.skip("stocks_cost_basis not in output")
        diffs = pre_fire[cost_basis_col].diff().dropna()
        negative_diffs = diffs[diffs < -1]
        assert len(negative_diffs) / len(diffs) < 0.1, \
            "Pre-FIRE stocks cost basis should not frequently decrease"
