"""
tests/test_visualizer_multi.py
比較シナリオ（プランA）表示のテスト
"""
import pandas as pd
import numpy as np
from datetime import datetime
from src.visualizer import create_fire_timeline_chart


def _make_dummy_df(n_months: int = 120, fire_at: int = 60) -> pd.DataFrame:
    """テスト用のベースシミュレーション DataFrame を生成"""
    dates = pd.date_range(start='2025-01-01', periods=n_months, freq='MS')
    df = pd.DataFrame({
        'date': dates,
        'month': range(n_months),
        'cash': np.linspace(5_000_000, 3_000_000, n_months),
        'stocks': np.linspace(10_000_000, 30_000_000, n_months),
        'assets': np.linspace(15_000_000, 33_000_000, n_months),
        'stocks_cost_basis': np.linspace(10_000_000, 25_000_000, n_months),
        'fire_achieved': [i >= fire_at for i in range(n_months)],
        'husband_income': [400_000] * fire_at + [0] * (n_months - fire_at),
        'wife_income': [300_000] * fire_at + [0] * (n_months - fire_at),
        'labor_income': [700_000] * fire_at + [0] * (n_months - fire_at),
        'pension_income': [0] * fire_at + [200_000] * (n_months - fire_at),
        'child_allowance': [0] * n_months,
        'base_expense': [300_000] * n_months,
        'education_expense': [0] * n_months,
        'mortgage_payment': [0] * n_months,
        'maintenance_cost': [0] * n_months,
        'workation_cost': [0] * n_months,
        'pension_premium': [0] * n_months,
        'health_insurance_premium': [0] * n_months,
        'investment_return': [0] * n_months,
        'auto_invested': [0] * n_months,
        'capital_gains_tax': [0] * n_months,
    })
    return df


def _dummy_config() -> dict:
    return {
        'family': {'husband_age': 35, 'wife_age': 33},
        'fire': {'target_success_rate': 0.95},
        'simulation': {'life_expectancy': 95, 'start_age': 35},
        'visualization': {'font_family': 'sans-serif'},
        'education': {'children': []},
        'mortgage': {'end_date': None},
        'house_maintenance': {'items': []},
        'pension': {'people': [], 'start_age': 65},
    }


def test_no_comparison_traces():
    """比較データなしの場合、プランAのトレースが含まれないこと"""
    df = _make_dummy_df()
    fire_row = df[df['fire_achieved']].iloc[0]
    fig = create_fire_timeline_chart(
        current_status={'net_assets': 15_000_000, 'cash_deposits': 5_000_000, 'investment_trusts': 10_000_000},
        fire_target={'recommended_target': 30_000_000, 'annual_expense': 3_600_000},
        fire_achievement={'achieved': False, 'achievement_date': fire_row['date'], 'months_to_fire': int(fire_row['month'])},
        simulations={'standard': df},
        config=_dummy_config(),
        comparison_data=None,
    )
    trace_names = [t.name for t in fig.data if t.name]
    assert 'プランA' not in trace_names


def test_comparison_trace_added():
    """比較データありの場合、プランAのトレースが1本追加されること"""
    df_current = _make_dummy_df(fire_at=60)
    df_plan_a = _make_dummy_df(fire_at=48)  # プランA: より早くFIRE
    fire_row = df_current[df_current['fire_achieved']].iloc[0]

    fig_no_comp = create_fire_timeline_chart(
        current_status={'net_assets': 15_000_000, 'cash_deposits': 5_000_000, 'investment_trusts': 10_000_000},
        fire_target={'recommended_target': 30_000_000, 'annual_expense': 3_600_000},
        fire_achievement={'achieved': False, 'achievement_date': fire_row['date'], 'months_to_fire': int(fire_row['month'])},
        simulations={'standard': df_current},
        config=_dummy_config(),
        comparison_data=None,
    )

    fig_with_comp = create_fire_timeline_chart(
        current_status={'net_assets': 15_000_000, 'cash_deposits': 5_000_000, 'investment_trusts': 10_000_000},
        fire_target={'recommended_target': 30_000_000, 'annual_expense': 3_600_000},
        fire_achievement={'achieved': False, 'achievement_date': fire_row['date'], 'months_to_fire': int(fire_row['month'])},
        simulations={'standard': df_current},
        config=_dummy_config(),
        comparison_data={'df': df_plan_a, 'label': 'プランA'},
    )

    # 比較データありの場合はトレースが1本多いこと
    assert len(fig_with_comp.data) == len(fig_no_comp.data) + 1

    # プランAのトレースが含まれること
    trace_names = [t.name for t in fig_with_comp.data if t.name]
    assert 'プランA' in trace_names
