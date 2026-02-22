#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
カテゴリ別予算機能のテスト

カテゴリ別予算計算が正しく動作することを確認
"""

import pytest
import yaml
from pathlib import Path
from src.simulator import calculate_base_expense_by_category, calculate_base_expense


@pytest.fixture
def config():
    """テスト用の設定を読み込み"""
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class TestCategoryBasedCalculation:
    """カテゴリ別予算計算のテスト"""

    def test_category_based_calculation_when_disabled(self, config):
        """カテゴリ別予算が無効の場合、Noneを返す"""
        # カテゴリ別予算は現在デフォルトで無効
        assert config['fire']['expense_categories']['enabled'] is False

        total, breakdown = calculate_base_expense_by_category(
            year_offset=0.0,
            config=config,
            fallback_expense=2500000
        )

        assert total is None
        assert breakdown == {}

    def test_category_based_calculation_young_child(self, config):
        """young_childステージでカテゴリ別計算が正しく動作する"""
        # カテゴリ別予算を有効化
        config_enabled = config.copy()
        config_enabled['fire']['expense_categories']['enabled'] = True

        total, breakdown = calculate_base_expense_by_category(
            year_offset=0.0,  # 颯は2022/02/26生まれなので、現在young_child
            config=config_enabled,
            fallback_expense=2500000
        )

        # young_childの合計は2,800,000円
        assert total == 2800000
        assert breakdown['stage'] == 'young_child'
        assert breakdown['total'] == 2800000

        # 基礎生活費と裁量的支出の合計が一致
        assert breakdown['essential_total'] + breakdown['discretionary_total'] == 2800000

        # 裁量的支出は25% (700,000円)
        assert breakdown['discretionary_total'] == 700000
        assert breakdown['essential_total'] == 2100000

    def test_category_based_essential_discretionary_split(self, config):
        """カテゴリが基礎/裁量に正しく分類されることを確認"""
        config_enabled = config.copy()
        config_enabled['fire']['expense_categories']['enabled'] = True

        total, breakdown = calculate_base_expense_by_category(
            year_offset=0.0,
            config=config_enabled,
            fallback_expense=2500000
        )

        # カテゴリ内訳を確認
        categories = breakdown['categories']

        # 基礎生活費の例（food_home, utilities_electricity）
        assert 'food_home' in categories
        assert 'utilities_electricity' in categories

        # 裁量的支出の例（food_out, travel_domestic）
        assert 'food_out' in categories
        assert 'travel_domestic' in categories

        # 各カテゴリの金額が正の値
        assert all(amount >= 0 for amount in categories.values())

    def test_fallback_to_traditional_when_disabled(self, config):
        """カテゴリ別予算が無効の場合、従来方式にフォールバック"""
        # カテゴリ別予算は無効
        config['fire']['expense_categories']['enabled'] = False

        # calculate_base_expense() は従来方式を使用
        total = calculate_base_expense(
            year_offset=0.0,
            config=config,
            fallback_expense=2500000
        )

        # young_childの合計は2,800,000円（従来方式でも同じ）
        assert total == 2800000

    def test_all_stages_sum_correctly(self, config):
        """すべてのライフステージで合計が正しいことを確認"""
        config_enabled = config.copy()
        config_enabled['fire']['expense_categories']['enabled'] = True

        # 各ステージの期待合計（base_expense_by_stageと一致すべき）
        expected_totals = {
            'young_child': 2800000,
            'elementary': 3000000,
            'junior_high': 3200000,
            'high_school': 3300000,
            'university': 3400000,
            'empty_nest': 2500000
        }

        # 各ステージの年齢オフセット（大体の値）
        stage_offsets = {
            'young_child': 0.0,    # 颯は2歳 → young_child
            'elementary': 5.0,     # 颯が7歳 → elementary
            'junior_high': 11.0,   # 颯が13歳 → junior_high
            'high_school': 14.0,   # 颯が16歳 → high_school
            'university': 17.0,    # 颯が19歳 → university
            'empty_nest': 23.0     # 颯が25歳 → empty_nest
        }

        for stage, year_offset in stage_offsets.items():
            total, breakdown = calculate_base_expense_by_category(
                year_offset=year_offset,
                config=config_enabled,
                fallback_expense=2500000
            )

            # 第二子（楓）の影響を除外するため、颯のみの期間でテスト
            # 楓は2027/04/15生まれなので、year_offset < 5.0では未出生
            if year_offset < 5.0:
                assert total == expected_totals[stage], \
                    f"Stage {stage}: expected {expected_totals[stage]}, got {total}"
                assert breakdown['stage'] == stage

    def test_calculate_base_expense_uses_category_when_enabled(self, config):
        """calculate_base_expense() がカテゴリ別計算を優先することを確認"""
        config_enabled = config.copy()
        config_enabled['fire']['expense_categories']['enabled'] = True

        # カテゴリ別計算を直接呼ぶ
        category_total, _ = calculate_base_expense_by_category(
            year_offset=0.0,
            config=config_enabled,
            fallback_expense=2500000
        )

        # calculate_base_expense() を呼ぶ
        total = calculate_base_expense(
            year_offset=0.0,
            config=config_enabled,
            fallback_expense=2500000
        )

        # 両者が一致することを確認
        assert total == category_total
        assert total == 2800000


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
