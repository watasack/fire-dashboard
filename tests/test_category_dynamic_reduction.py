#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
カテゴリ別動的削減機能のテスト

カテゴリ別予算と動的削減が連携して動作することを確認
"""

import pytest
import yaml
from pathlib import Path
from src.simulator import (
    calculate_base_expense_by_category,
    apply_dynamic_expense_reduction
)


@pytest.fixture
def config():
    """テスト用の設定を読み込み"""
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class TestCategoryDynamicReduction:
    """カテゴリ別動的削減のテスト"""

    def test_reduction_only_affects_discretionary_categories(self, config):
        """裁量的カテゴリのみが削減され、基礎生活費は削減されない"""
        # カテゴリ別予算を有効化
        config_enabled = config.copy()
        config_enabled['fire']['expense_categories']['enabled'] = True

        # カテゴリ別内訳を取得
        total, category_breakdown = calculate_base_expense_by_category(
            year_offset=0.0,
            config=config_enabled,
            fallback_expense=2500000
        )

        # レベル1（警戒）で20%削減を適用
        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense=total,
            stage='young_child',
            drawdown_level=1,
            config=config_enabled,
            category_breakdown=category_breakdown
        )

        assert breakdown['essential'] == 1896000

        expected_discretionary = 700000 * (1 - 0.20)
        assert abs(breakdown['discretionary'] - expected_discretionary) < 1000

        expected_total = 1896000 + expected_discretionary
        assert abs(actual - expected_total) < 1000

        assert breakdown['reduction_rate'] == 0.20

        assert abs(breakdown['amount_saved'] - 140000) < 1000

    def test_category_breakdown_in_result(self, config):
        """削減後のカテゴリ別内訳が結果に含まれることを確認"""
        config_enabled = config.copy()
        config_enabled['fire']['expense_categories']['enabled'] = True

        total, category_breakdown = calculate_base_expense_by_category(
            year_offset=0.0,
            config=config_enabled,
            fallback_expense=2500000
        )

        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense=total,
            stage='young_child',
            drawdown_level=2,  # レベル2: 50%削減
            config=config_enabled,
            category_breakdown=category_breakdown
        )

        assert 'categories_after' in breakdown

        categories_after = breakdown['categories_after']

        assert categories_after['food_home'] == 600000
        assert categories_after['utilities_electricity'] == 120000

        original_food_out = 240000
        expected_food_out = original_food_out * (1 - 0.50)
        assert abs(categories_after['food_out'] - expected_food_out) < 1000

    def test_100_percent_reduction_eliminates_discretionary(self, config):
        """100%削減で裁量的支出がゼロになることを確認"""
        config_enabled = config.copy()
        config_enabled['fire']['expense_categories']['enabled'] = True

        total, category_breakdown = calculate_base_expense_by_category(
            year_offset=0.0,
            config=config_enabled,
            fallback_expense=2500000
        )

        # レベル3（危機）で70%削減
        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense=total,
            stage='young_child',
            drawdown_level=3,
            config=config_enabled,
            category_breakdown=category_breakdown
        )

        expected_discretionary = 700000 * (1 - 0.70)
        assert abs(breakdown['discretionary'] - expected_discretionary) < 1000

        assert breakdown['reduction_rate'] == 0.70

        expected_total = 1896000 + expected_discretionary
        assert abs(actual - expected_total) < 1000

        assert abs(breakdown['amount_saved'] - 490000) < 1000

        categories_after = breakdown['categories_after']
        assert abs(categories_after['food_out'] - 240000 * 0.30) < 1000
        assert abs(categories_after['travel_domestic'] - 60000 * 0.30) < 1000

    def test_traditional_reduction_without_category_breakdown(self, config):
        """カテゴリ内訳なしの場合、従来の比率ベース削減が動作する"""
        config['fire']['expense_categories']['enabled'] = False

        base_expense = 2800000
        stage = 'young_child'

        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense=base_expense,
            stage=stage,
            drawdown_level=1,  # レベル1: 20%削減
            config=config,
            category_breakdown=None
        )

        expected_essential = 2800000 * 0.75
        expected_discretionary = 2800000 * 0.25 * (1 - 0.20)
        expected_total = expected_essential + expected_discretionary

        assert abs(actual - expected_total) < 1000
        assert abs(breakdown['essential'] - expected_essential) < 1000
        assert abs(breakdown['discretionary'] - expected_discretionary) < 1000
        assert breakdown['reduction_rate'] == 0.20

        assert 'categories_after' not in breakdown

    def test_no_reduction_at_level_0_with_categories(self, config):
        """レベル0（正常）ではカテゴリ別でも削減なし"""
        config_enabled = config.copy()
        config_enabled['fire']['expense_categories']['enabled'] = True

        total, category_breakdown = calculate_base_expense_by_category(
            year_offset=0.0,
            config=config_enabled,
            fallback_expense=2500000
        )

        # レベル0（正常）で削減なし
        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense=total,
            stage='young_child',
            drawdown_level=0,
            config=config_enabled,
            category_breakdown=category_breakdown
        )

        # 削減なし
        assert actual == total
        assert breakdown['reduction_rate'] == 0.0
        assert breakdown['amount_saved'] == 0.0

        assert breakdown['discretionary'] == 700000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
