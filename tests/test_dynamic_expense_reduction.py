#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
比例制御型動的支出調整のテスト

ベースラインとの乖離に比例した支出調整ロジックが正しく機能することを確認
"""

import pytest
import yaml
from pathlib import Path
from src.simulator import (
    calculate_drawdown_level,
    calculate_proportional_expense_adjustment,
)


@pytest.fixture
def config():
    """テスト用の設定を読み込み"""
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class TestDrawdownCalculation:
    """ベースライン乖離率計算のテスト"""

    def test_no_drawdown(self, config):
        """乖離なし"""
        peak_history = [10000000, 9500000, 9800000, 10200000]
        current = 10200000

        drawdown, level = calculate_drawdown_level(current, peak_history, config)

        assert drawdown == 0.0
        assert level == 0

    def test_negative_drawdown(self, config):
        """下ぶれ（-5%）"""
        peak_history = [10000000, 9500000, 9800000, 10200000]
        current = 9690000  # -5%

        drawdown, level = calculate_drawdown_level(current, peak_history, config)

        expected_drawdown = (9690000 / 10200000) - 1.0
        assert abs(drawdown - expected_drawdown) < 0.001
        assert level == 0

    def test_positive_drawdown(self, config):
        """上ぶれ（+20%）"""
        drawdown, level = calculate_drawdown_level(
            current_assets=12000000,
            peak_assets_history=[],
            config=config,
            planned_assets=10000000,
        )

        assert abs(drawdown - 0.20) < 0.001
        assert level == 0

    def test_empty_history_uses_current(self, config):
        """履歴が空の場合、現在資産を基準とする"""
        drawdown, level = calculate_drawdown_level(5000000, [], config)

        assert drawdown == 0.0
        assert level == 0

    def test_planned_assets_takes_priority(self, config):
        """planned_assets が指定された場合、そちらを基準にする"""
        drawdown, level = calculate_drawdown_level(
            current_assets=8000000,
            peak_assets_history=[10000000],
            config=config,
            planned_assets=10000000,
        )
        assert abs(drawdown - (-0.20)) < 0.001
        assert level == 0


class TestProportionalExpenseAdjustment:
    """比例制御型支出調整のテスト"""

    def test_no_adjustment_when_disabled(self, config):
        """動的調整が無効の場合、調整額0"""
        config_disabled = config.copy()
        config_disabled['fire'] = dict(config['fire'])
        config_disabled['fire']['dynamic_expense_reduction'] = dict(config['fire']['dynamic_expense_reduction'])
        config_disabled['fire']['dynamic_expense_reduction']['enabled'] = False

        adj = calculate_proportional_expense_adjustment(
            surplus=5000000, discretionary_monthly=100000, config=config_disabled
        )
        assert adj == 0.0

    def test_surplus_increases_expense(self, config):
        """余剰（surplus > 0）→ 支出増加（正の調整額）"""
        adj = calculate_proportional_expense_adjustment(
            surplus=10000000, discretionary_monthly=100000, config=config
        )
        assert adj > 0

    def test_deficit_decreases_expense(self, config):
        """不足（surplus < 0）→ 支出削減（負の調整額）"""
        adj = calculate_proportional_expense_adjustment(
            surplus=-10000000, discretionary_monthly=100000, config=config
        )
        assert adj < 0

    def test_proportional_to_surplus(self, config):
        """調整額は余剰に比例する"""
        adj1 = calculate_proportional_expense_adjustment(
            surplus=5000000, discretionary_monthly=1000000, config=config
        )
        adj2 = calculate_proportional_expense_adjustment(
            surplus=10000000, discretionary_monthly=1000000, config=config
        )
        assert abs(adj2 / adj1 - 2.0) < 0.01

    def test_boost_capped_by_max_boost_ratio(self, config):
        """上ぶれ時の支出増加は裁量支出 × max_boost_ratio でキャップ"""
        disc_monthly = 100000
        max_boost_ratio = config['fire']['dynamic_expense_reduction']['max_boost_ratio']
        max_boost = disc_monthly * max_boost_ratio

        adj = calculate_proportional_expense_adjustment(
            surplus=999_999_999, discretionary_monthly=disc_monthly, config=config
        )
        assert abs(adj - max_boost) < 1.0

    def test_cut_capped_by_max_cut_ratio(self, config):
        """下ぶれ時の支出削減は裁量支出 × max_cut_ratio でキャップ"""
        disc_monthly = 100000
        max_cut_ratio = config['fire']['dynamic_expense_reduction']['max_cut_ratio']
        max_cut = disc_monthly * max_cut_ratio

        adj = calculate_proportional_expense_adjustment(
            surplus=-999_999_999, discretionary_monthly=disc_monthly, config=config
        )
        assert abs(adj - (-max_cut)) < 1.0

    def test_zero_surplus_no_adjustment(self, config):
        """乖離0の場合、調整なし"""
        adj = calculate_proportional_expense_adjustment(
            surplus=0, discretionary_monthly=100000, config=config
        )
        assert adj == 0.0

    def test_exact_adjustment_value(self, config):
        """具体的な計算値を検証: surplus × α / 12"""
        alpha = config['fire']['dynamic_expense_reduction']['surplus_spending_rate']
        surplus = 6000000

        adj = calculate_proportional_expense_adjustment(
            surplus=surplus, discretionary_monthly=1000000, config=config
        )
        expected = surplus * alpha / 12.0
        assert abs(adj - expected) < 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
