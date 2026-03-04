#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
比例制御型動的支出調整のカテゴリ関連テスト

比例制御メカニズムにおけるカテゴリ別裁量支出比率の取得が
正しく動作することを確認
"""

import pytest
import yaml
from pathlib import Path
from src.simulator import (
    calculate_base_expense_by_category,
    calculate_proportional_expense_adjustment,
)


@pytest.fixture
def config():
    """テスト用の設定を読み込み"""
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class TestCategoryProportionalReduction:
    """カテゴリ別裁量支出比率と比例制御の連携テスト"""

    def test_discretionary_ratio_affects_cap(self, config):
        """裁量支出が大きいほどキャップ値も大きい"""
        surplus = 999_999_999

        disc_small = 50_000
        disc_large = 100_000

        adj_small = calculate_proportional_expense_adjustment(
            surplus=surplus, discretionary_monthly=disc_small, config=config
        )
        adj_large = calculate_proportional_expense_adjustment(
            surplus=surplus, discretionary_monthly=disc_large, config=config
        )

        max_boost_ratio = config['fire']['dynamic_expense_reduction']['max_boost_ratio']
        assert abs(adj_small - disc_small * max_boost_ratio) < 1.0
        assert abs(adj_large - disc_large * max_boost_ratio) < 1.0
        assert adj_large > adj_small

    def test_zero_discretionary_zero_adjustment(self, config):
        """裁量支出0の場合、調整額も0"""
        adj = calculate_proportional_expense_adjustment(
            surplus=10_000_000, discretionary_monthly=0, config=config
        )
        assert adj == 0.0

    def test_category_breakdown_provides_discretionary_info(self, config):
        """カテゴリ別内訳から裁量支出情報が取得できることを確認"""
        config_enabled = config.copy()
        config_enabled['fire']['expense_categories']['enabled'] = True

        total, category_breakdown = calculate_base_expense_by_category(
            year_offset=0.0,
            config=config_enabled,
            fallback_expense=2500000
        )

        definitions = config_enabled['fire']['expense_categories']['definitions']
        disc_map = {cat['id']: cat['discretionary'] for cat in definitions}

        disc_total = sum(
            amt for cat_id, amt in category_breakdown['categories'].items()
            if disc_map.get(cat_id, False)
        )

        assert disc_total > 0
        assert disc_total < total


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
