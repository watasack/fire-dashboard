"""
シミュレーターモジュール
将来の資産推移を予測
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from dateutil.relativedelta import relativedelta


def simulate_future_assets(
    current_assets: float,
    monthly_income: float,
    monthly_expense: float,
    config: Dict[str, Any],
    scenario: str = 'standard'
) -> pd.DataFrame:
    """
    将来の資産推移をシミュレーション

    Args:
        current_assets: 現在の純資産
        monthly_income: 月次収入
        monthly_expense: 月次支出
        config: 設定辞書
        scenario: シナリオ名 ('standard', 'optimistic', 'pessimistic')

    Returns:
        シミュレーション結果のデータフレーム
    """
    print(f"Simulating future assets ({scenario} scenario)...")

    # シナリオ設定取得
    scenario_config = config['simulation'][scenario]
    annual_return_rate = scenario_config['annual_return_rate']
    inflation_rate = scenario_config['inflation_rate']
    income_growth_rate = scenario_config['income_growth_rate']
    expense_growth_rate = scenario_config['expense_growth_rate']

    # シミュレーション期間
    simulation_years = config['simulation']['years']
    simulation_months = simulation_years * 12

    # 月次リターン率（複利計算）
    monthly_return_rate = (1 + annual_return_rate) ** (1/12) - 1

    # シミュレーション結果を格納
    results = []

    # 初期値
    assets = current_assets
    income = monthly_income
    expense = monthly_expense

    # 開始日
    from datetime import datetime
    current_date = datetime.now()

    # 月次シミュレーション
    for month in range(simulation_months + 1):
        # 現在月の日付
        date = current_date + relativedelta(months=month)

        # 年数（成長率計算用）
        years = month / 12

        # 収入・支出の成長（複利）
        income = monthly_income * (1 + income_growth_rate) ** years
        expense = monthly_expense * (1 + expense_growth_rate) ** years

        # 運用リターン
        investment_return = assets * monthly_return_rate

        # 資産更新（収入 - 支出 + 運用リターン）
        assets = assets + income - expense + investment_return

        # 記録
        results.append({
            'date': date,
            'month': month,
            'assets': max(0, assets),  # 負債は0で下限
            'income': income,
            'expense': expense,
            'net_cashflow': income - expense,
            'investment_return': investment_return,
            'cumulative_income': income * (month + 1),
            'cumulative_expense': expense * (month + 1),
        })

        # 資産がゼロになったら終了
        if assets <= 0:
            print(f"  Assets depleted at month {month} ({years:.1f} years)")
            break

    df = pd.DataFrame(results)

    print(f"  Simulated {len(df)} months ({len(df)/12:.1f} years)")
    print(f"  Final assets: JPY{df.iloc[-1]['assets']:,.0f}")

    return df


def simulate_with_withdrawal(
    initial_assets: float,
    annual_expense: float,
    years: int,
    return_rate: float,
    inflation_rate: float
) -> float:
    """
    定額引き出しシミュレーション（FIRE計算用）

    Args:
        initial_assets: 初期資産
        annual_expense: 年間支出
        years: シミュレーション期間（年）
        return_rate: 年率リターン
        inflation_rate: インフレ率

    Returns:
        最終資産額
    """
    assets = initial_assets
    monthly_expense = annual_expense / 12
    monthly_return_rate = (1 + return_rate) ** (1/12) - 1

    for month in range(years * 12):
        # 年数
        years_elapsed = month / 12

        # インフレ調整後の支出
        adjusted_expense = monthly_expense * (1 + inflation_rate) ** years_elapsed

        # 運用リターン
        investment_return = assets * monthly_return_rate

        # 資産更新
        assets = assets - adjusted_expense + investment_return

        # 資産がゼロ以下になったら終了
        if assets <= 0:
            return 0

    return assets


def calculate_years_to_target(
    current_assets: float,
    target_assets: float,
    monthly_income: float,
    monthly_expense: float,
    annual_return_rate: float,
    max_years: int = 100
) -> float:
    """
    目標資産額到達までの年数を計算

    Args:
        current_assets: 現在の資産
        target_assets: 目標資産額
        monthly_income: 月次収入
        monthly_expense: 月次支出
        annual_return_rate: 年率リターン
        max_years: 最大計算年数

    Returns:
        到達年数（到達不可能な場合は-1）
    """
    if current_assets >= target_assets:
        return 0

    assets = current_assets
    monthly_return_rate = (1 + annual_return_rate) ** (1/12) - 1
    monthly_savings = monthly_income - monthly_expense

    if monthly_savings <= 0 and monthly_return_rate <= 0:
        return -1  # 到達不可能

    for month in range(max_years * 12):
        investment_return = assets * monthly_return_rate
        assets = assets + monthly_savings + investment_return

        if assets >= target_assets:
            return month / 12

    return -1  # max_years以内に到達不可能
