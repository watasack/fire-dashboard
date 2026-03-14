"""
tests/test_guardrail_logic.py

比例制御型ガードレール戦略（動的支出調整）のユニットテスト。
calculate_proportional_expense_adjustment のキャップ動作と比例係数を検証する。
"""

import pytest
from src.simulator import calculate_proportional_expense_adjustment


def _make_config(enabled: bool = True, alpha: float = 0.40, max_cut: float = 0.70, max_boost: float = 5.0) -> dict:
    return {
        'fire': {
            'dynamic_expense_reduction': {
                'enabled': enabled,
                'surplus_spending_rate': alpha,
                'max_cut_ratio': max_cut,
                'max_boost_ratio': max_boost,
            }
        }
    }


class TestCalculateProportionalExpenseAdjustment:

    def test_disabled_returns_zero(self):
        config = _make_config(enabled=False)
        result = calculate_proportional_expense_adjustment(
            surplus=1_000_000, discretionary_monthly=100_000, config=config
        )
        assert result == 0.0

    def test_no_surplus_no_adjustment(self):
        config = _make_config(alpha=0.40)
        result = calculate_proportional_expense_adjustment(
            surplus=0, discretionary_monthly=100_000, config=config
        )
        assert result == 0.0

    def test_positive_surplus_increases_expense(self):
        config = _make_config(alpha=0.40, max_boost=5.0)
        # 余剰 120万円 → 年率40% → 年48万 → 月4万
        result = calculate_proportional_expense_adjustment(
            surplus=1_200_000, discretionary_monthly=100_000, config=config
        )
        assert result == pytest.approx(1_200_000 * 0.40 / 12, rel=1e-6)

    def test_negative_surplus_decreases_expense(self):
        config = _make_config(alpha=0.40)
        # 不足 120万円 → 年率40% → 年-48万 → 月-4万
        result = calculate_proportional_expense_adjustment(
            surplus=-1_200_000, discretionary_monthly=100_000, config=config
        )
        assert result == pytest.approx(-1_200_000 * 0.40 / 12, rel=1e-6)

    def test_max_cut_cap_applied(self):
        config = _make_config(alpha=0.40, max_cut=0.70)
        disc_monthly = 100_000
        # 大きな不足 → キャップに当たる
        result = calculate_proportional_expense_adjustment(
            surplus=-100_000_000, discretionary_monthly=disc_monthly, config=config
        )
        assert result == pytest.approx(-(disc_monthly * 0.70), rel=1e-6)

    def test_max_boost_cap_applied(self):
        config = _make_config(alpha=0.40, max_boost=5.0)
        disc_monthly = 100_000
        # 大きな余剰 → キャップに当たる
        result = calculate_proportional_expense_adjustment(
            surplus=100_000_000, discretionary_monthly=disc_monthly, config=config
        )
        assert result == pytest.approx(disc_monthly * 5.0, rel=1e-6)

    def test_proportional_to_alpha(self):
        disc_monthly = 50_000
        surplus = 600_000
        for alpha in [0.1, 0.3, 0.5]:
            config = _make_config(alpha=alpha, max_boost=10.0)
            expected = surplus * alpha / 12.0
            result = calculate_proportional_expense_adjustment(
                surplus=surplus, discretionary_monthly=disc_monthly, config=config
            )
            assert result == pytest.approx(expected, rel=1e-6), f"alpha={alpha}"

    def test_zero_discretionary_monthly(self):
        config = _make_config(alpha=0.40)
        # 裁量支出0の場合、キャップが0なので調整も0
        result = calculate_proportional_expense_adjustment(
            surplus=1_000_000, discretionary_monthly=0, config=config
        )
        assert result == 0.0
