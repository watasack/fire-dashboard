#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
動的支出削減機能のテスト

暴落時の裁量的支出削減ロジックが正しく機能することを確認
"""

import pytest
import yaml
from pathlib import Path
from src.simulator import (
    calculate_drawdown_level,
    apply_dynamic_expense_reduction
)


@pytest.fixture
def config():
    """テスト用の設定を読み込み"""
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class TestDrawdownCalculation:
    """ドローダウン計算のテスト"""

    def test_no_drawdown_normal_level(self, config):
        """ドローダウンなし（正常レベル）"""
        peak_history = [10000000, 9500000, 9800000, 10200000]
        current = 10200000  # ピーク

        drawdown, level = calculate_drawdown_level(current, peak_history, config)

        assert drawdown == 0.0
        assert level == 0  # 正常

    def test_small_drawdown_normal_level(self, config):
        """小さなドローダウン（-10%、正常レベル）"""
        peak_history = [10000000, 9500000, 9800000, 10200000]
        current = 9180000  # -10%

        drawdown, level = calculate_drawdown_level(current, peak_history, config)

        expected_drawdown = (9180000 / 10200000) - 1.0  # -10%
        assert abs(drawdown - expected_drawdown) < 0.001
        assert level == 0  # -15%未満なので正常

    def test_warning_level_drawdown(self, config):
        """警戒レベルのドローダウン（-20%）"""
        peak_history = [10000000, 9500000, 9800000, 10200000]
        current = 8160000  # -20%

        drawdown, level = calculate_drawdown_level(current, peak_history, config)

        expected_drawdown = (8160000 / 10200000) - 1.0  # -20%
        assert abs(drawdown - expected_drawdown) < 0.001
        assert level == 1  # 警戒レベル（-15% 〜 -30%）

    def test_concern_level_drawdown(self, config):
        """深刻レベルのドローダウン（-40%）"""
        peak_history = [10000000, 9500000, 9800000, 10200000]
        current = 6120000  # -40%

        drawdown, level = calculate_drawdown_level(current, peak_history, config)

        expected_drawdown = (6120000 / 10200000) - 1.0  # -40%
        assert abs(drawdown - expected_drawdown) < 0.001
        assert level == 2  # 深刻レベル（-30% 〜 -50%）

    def test_crisis_level_drawdown(self, config):
        """危機レベルのドローダウン（-60%）"""
        peak_history = [10000000, 9500000, 9800000, 10200000]
        current = 4080000  # -60%

        drawdown, level = calculate_drawdown_level(current, peak_history, config)

        expected_drawdown = (4080000 / 10200000) - 1.0  # -60%
        assert abs(drawdown - expected_drawdown) < 0.001
        assert level == 3  # 危機レベル（-50%以下）

    def test_empty_history_uses_current_as_peak(self, config):
        """履歴が空の場合、現在資産をピークとする"""
        peak_history = []
        current = 5000000

        drawdown, level = calculate_drawdown_level(current, peak_history, config)

        assert drawdown == 0.0  # 現在=ピークなので0%
        assert level == 0  # 正常


class TestDynamicExpenseReduction:
    """動的支出削減のテスト"""

    def test_no_reduction_when_disabled(self, config):
        """動的削減が無効の場合、削減なし"""
        # 設定を一時的に無効化
        config_disabled = config.copy()
        config_disabled['fire']['dynamic_expense_reduction']['enabled'] = False

        base_expense = 2800000  # 280万円/年
        stage = 'young_child'

        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense, stage, drawdown_level=1, config=config_disabled
        )

        assert actual == 2800000  # 削減なし
        assert breakdown['reduction_rate'] == 0.0

    def test_no_reduction_at_level_0(self, config):
        """レベル0（正常）では削減なし"""
        base_expense = 2800000  # 280万円/年
        stage = 'young_child'

        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense, stage, drawdown_level=0, config=config
        )

        assert actual == 2800000  # 削減なし
        assert breakdown['discretionary_original'] == 700000  # 25%が裁量的
        assert breakdown['discretionary'] == 700000  # 削減なし
        assert breakdown['reduction_rate'] == 0.0

    def test_30_percent_reduction_at_level_1(self, config):
        """レベル1（警戒）で30%削減"""
        base_expense = 2800000  # 280万円/年
        stage = 'young_child'

        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense, stage, drawdown_level=1, config=config
        )

        # 裁量的25% = 70万円 → 30%削減 = 49万円
        # 実際の支出 = 210万円（基礎） + 49万円（裁量） = 259万円
        expected_essential = 2800000 * 0.75  # 210万円
        expected_discretionary = 2800000 * 0.25 * (1 - 0.30)  # 49万円
        expected_total = expected_essential + expected_discretionary

        assert abs(actual - expected_total) < 1000
        assert abs(breakdown['essential'] - expected_essential) < 1000
        assert abs(breakdown['discretionary'] - expected_discretionary) < 1000
        assert breakdown['reduction_rate'] == 0.30
        assert abs(breakdown['amount_saved'] - 210000) < 1000  # 21万円削減

    def test_60_percent_reduction_at_level_2(self, config):
        """レベル2（深刻）で60%削減"""
        base_expense = 2800000  # 280万円/年
        stage = 'young_child'

        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense, stage, drawdown_level=2, config=config
        )

        # 裁量的25% = 70万円 → 60%削減 = 28万円
        # 実際の支出 = 210万円（基礎） + 28万円（裁量） = 238万円
        expected_essential = 2800000 * 0.75  # 210万円
        expected_discretionary = 2800000 * 0.25 * (1 - 0.60)  # 28万円
        expected_total = expected_essential + expected_discretionary

        assert abs(actual - expected_total) < 1000
        assert breakdown['reduction_rate'] == 0.60
        assert abs(breakdown['amount_saved'] - 420000) < 1000  # 42万円削減

    def test_90_percent_reduction_at_level_3(self, config):
        """レベル3（危機）で90%削減"""
        base_expense = 2800000  # 280万円/年
        stage = 'young_child'

        actual, breakdown = apply_dynamic_expense_reduction(
            base_expense, stage, drawdown_level=3, config=config
        )

        # 裁量的25% = 70万円 → 90%削減 = 7万円
        # 実際の支出 = 210万円（基礎） + 7万円（裁量） = 217万円
        expected_essential = 2800000 * 0.75  # 210万円
        expected_discretionary = 2800000 * 0.25 * (1 - 0.90)  # 7万円
        expected_total = expected_essential + expected_discretionary

        assert abs(actual - expected_total) < 1000
        assert breakdown['reduction_rate'] == 0.90
        assert abs(breakdown['amount_saved'] - 630000) < 1000  # 63万円削減

    def test_different_stage_ratios(self, config):
        """異なるライフステージで裁量的支出比率が変わることを確認"""
        base_expense = 2500000  # 250万円/年

        # young_child: 25%裁量的
        actual_yc, breakdown_yc = apply_dynamic_expense_reduction(
            base_expense, 'young_child', drawdown_level=1, config=config
        )
        assert abs(breakdown_yc['discretionary_original'] - 625000) < 1000  # 25%

        # empty_nest: 40%裁量的
        actual_en, breakdown_en = apply_dynamic_expense_reduction(
            base_expense, 'empty_nest', drawdown_level=1, config=config
        )
        assert abs(breakdown_en['discretionary_original'] - 1000000) < 1000  # 40%

        # empty_nestの方が削減額が大きい
        assert breakdown_en['amount_saved'] > breakdown_yc['amount_saved']

    def test_essential_expense_never_reduced(self, config):
        """基礎生活費は削減されないことを確認"""
        base_expense = 2800000  # 280万円/年
        stage = 'young_child'

        # すべてのレベルで基礎生活費は一定
        expected_essential = 2800000 * 0.75  # 210万円

        for level in [0, 1, 2, 3]:
            actual, breakdown = apply_dynamic_expense_reduction(
                base_expense, stage, drawdown_level=level, config=config
            )
            assert abs(breakdown['essential'] - expected_essential) < 1000


class TestIntegration:
    """統合テスト"""

    def test_drawdown_triggers_appropriate_reduction(self, config):
        """ドローダウンに応じて適切な削減が適用されることを確認"""
        base_expense = 2800000
        stage = 'young_child'

        # シナリオ1: -10%ドローダウン → レベル0 → 削減なし
        drawdown1, level1 = calculate_drawdown_level(
            current_assets=9000000,
            peak_assets_history=[10000000],
            config=config
        )
        actual1, breakdown1 = apply_dynamic_expense_reduction(
            base_expense, stage, level1, config
        )
        assert level1 == 0
        assert breakdown1['reduction_rate'] == 0.0

        # シナリオ2: -20%ドローダウン → レベル1 → 30%削減
        drawdown2, level2 = calculate_drawdown_level(
            current_assets=8000000,
            peak_assets_history=[10000000],
            config=config
        )
        actual2, breakdown2 = apply_dynamic_expense_reduction(
            base_expense, stage, level2, config
        )
        assert level2 == 1
        assert breakdown2['reduction_rate'] == 0.30

        # シナリオ3: -40%ドローダウン → レベル2 → 60%削減
        drawdown3, level3 = calculate_drawdown_level(
            current_assets=6000000,
            peak_assets_history=[10000000],
            config=config
        )
        actual3, breakdown3 = apply_dynamic_expense_reduction(
            base_expense, stage, level3, config
        )
        assert level3 == 2
        assert breakdown3['reduction_rate'] == 0.60


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
