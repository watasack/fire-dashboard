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

        # レベル1（警戒）で50%削減を適用
        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense=total,
            stage='young_child',
            drawdown_level=1,
            config=config_enabled,
            category_breakdown=category_breakdown
        )

        # 基礎生活費は削減されない
        assert breakdown['essential'] == 2100000  # young_childの基礎生活費

        # 裁量的支出は50%削減
        expected_discretionary = 700000 * 0.5  # 700,000の50% = 350,000
        assert abs(breakdown['discretionary'] - expected_discretionary) < 1000

        # 合計は基礎 + 削減後裁量
        expected_total = 2100000 + expected_discretionary
        assert abs(actual - expected_total) < 1000

        # 削減率は50%
        assert breakdown['reduction_rate'] == 0.50

        # 削減額は35万円
        assert abs(breakdown['amount_saved'] - 350000) < 1000

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
            drawdown_level=2,  # レベル2: 80%削減
            config=config_enabled,
            category_breakdown=category_breakdown
        )

        # カテゴリ別削減後の金額が含まれる
        assert 'categories_after' in breakdown

        categories_after = breakdown['categories_after']

        # 基礎生活費カテゴリは削減されない
        assert categories_after['food_home'] == 600000  # 自炊は削減されない
        assert categories_after['utilities_electricity'] == 120000  # 電気代も削減されない

        # 裁量的支出カテゴリは80%削減
        original_food_out = 240000
        expected_food_out = original_food_out * (1 - 0.80)  # 48,000
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

        # レベル3（危機）で100%削減
        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense=total,
            stage='young_child',
            drawdown_level=3,
            config=config_enabled,
            category_breakdown=category_breakdown
        )

        # 裁量的支出はゼロ
        assert breakdown['discretionary'] == 0.0

        # 削減率は100%
        assert breakdown['reduction_rate'] == 1.00

        # 合計は基礎生活費のみ
        assert actual == 2100000

        # 削減額は裁量的支出の全額
        assert abs(breakdown['amount_saved'] - 700000) < 1000

        # すべての裁量的カテゴリがゼロ
        categories_after = breakdown['categories_after']
        assert categories_after['food_out'] == 0.0
        assert categories_after['travel_domestic'] == 0.0
        assert categories_after['travel_international'] == 0.0

    def test_traditional_reduction_without_category_breakdown(self, config):
        """カテゴリ内訳なしの場合、従来の比率ベース削減が動作する"""
        # カテゴリ別予算は無効（従来方式）
        config['fire']['expense_categories']['enabled'] = False

        base_expense = 2800000
        stage = 'young_child'

        # カテゴリ内訳なしで呼び出す
        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense=base_expense,
            stage=stage,
            drawdown_level=1,  # レベル1: 50%削減
            config=config,
            category_breakdown=None  # カテゴリ内訳なし
        )

        # 従来方式: 裁量的25% = 70万円 → 50%削減 = 35万円
        expected_essential = 2800000 * 0.75  # 210万円
        expected_discretionary = 2800000 * 0.25 * (1 - 0.50)  # 35万円
        expected_total = expected_essential + expected_discretionary

        assert abs(actual - expected_total) < 1000
        assert abs(breakdown['essential'] - expected_essential) < 1000
        assert abs(breakdown['discretionary'] - expected_discretionary) < 1000
        assert breakdown['reduction_rate'] == 0.50

        # カテゴリ別内訳は含まれない
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

        # 裁量的支出は元のまま
        assert breakdown['discretionary'] == 700000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
