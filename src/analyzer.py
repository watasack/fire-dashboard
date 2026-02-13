"""
分析モジュール
現状の資産状況と収支トレンドの分析を担当
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from scipy import stats


def analyze_current_status(asset_df: pd.DataFrame) -> Dict[str, Any]:
    """
    現在の資産状況を分析

    Args:
        asset_df: 資産推移データフレーム

    Returns:
        現状分析結果の辞書
    """
    print("Analyzing current status...")

    # 最新データを取得
    latest = asset_df.iloc[-1]

    # 1ヶ月前、3ヶ月前、1年前のデータ（存在する場合）
    months_ago_1 = asset_df.iloc[-min(30, len(asset_df))]
    months_ago_3 = asset_df.iloc[-min(90, len(asset_df))]
    months_ago_12 = asset_df.iloc[-min(365, len(asset_df))]

    # 成長率の計算
    growth_1m = (latest['net_assets'] / months_ago_1['net_assets'] - 1) * 100 if months_ago_1['net_assets'] > 0 else 0
    growth_3m = (latest['net_assets'] / months_ago_3['net_assets'] - 1) * 100 if months_ago_3['net_assets'] > 0 else 0
    growth_12m = (latest['net_assets'] / months_ago_12['net_assets'] - 1) * 100 if months_ago_12['net_assets'] > 0 else 0

    result = {
        'date': latest['date'],
        'total_assets': latest['total_assets'],
        'net_assets': latest['net_assets'],
        'debt': latest['debt'],
        'cash_investments': latest['cash_investments'],
        'growth_rate_1m': growth_1m,
        'growth_rate_3m': growth_3m,
        'growth_rate_12m': growth_12m,
    }

    print(f"  Current net assets: JPY{result['net_assets']:,.0f}")
    print(f"  Growth (1M): {result['growth_rate_1m']:.2f}%")
    print(f"  Growth (3M): {result['growth_rate_3m']:.2f}%")
    print(f"  Growth (12M): {result['growth_rate_12m']:.2f}%")

    return result


def analyze_income_expense_trends(cashflow_df: pd.DataFrame) -> Dict[str, Any]:
    """
    収支のトレンドを分析

    Args:
        cashflow_df: 月次収支データフレーム

    Returns:
        収支トレンド分析結果の辞書
    """
    print("Analyzing income/expense trends...")

    if len(cashflow_df) == 0:
        return {
            'monthly_avg_income': 0,
            'monthly_avg_expense': 0,
            'monthly_avg_savings': 0,
            'savings_rate': 0,
            'annual_income': 0,
            'annual_expense': 0,
        }

    # 月次平均
    monthly_avg_income = cashflow_df['income'].mean()
    monthly_avg_expense = cashflow_df['expense'].mean()
    monthly_avg_savings = cashflow_df['net_cashflow'].mean()

    # 貯蓄率
    savings_rate = monthly_avg_savings / monthly_avg_income if monthly_avg_income > 0 else 0

    # 年間換算
    annual_income = monthly_avg_income * 12
    annual_expense = monthly_avg_expense * 12

    # トレンド分析（線形回帰）
    if len(cashflow_df) >= 3:
        x = np.arange(len(cashflow_df))

        # 収入のトレンド
        income_slope, income_intercept, _, _, _ = stats.linregress(x, cashflow_df['income'])

        # 支出のトレンド
        expense_slope, expense_intercept, _, _, _ = stats.linregress(x, cashflow_df['expense'])

        income_trend = 'increasing' if income_slope > 0 else 'decreasing' if income_slope < 0 else 'stable'
        expense_trend = 'increasing' if expense_slope > 0 else 'decreasing' if expense_slope < 0 else 'stable'
    else:
        income_trend = 'insufficient_data'
        expense_trend = 'insufficient_data'

    result = {
        'monthly_avg_income': monthly_avg_income,
        'monthly_avg_expense': monthly_avg_expense,
        'monthly_avg_savings': monthly_avg_savings,
        'savings_rate': savings_rate,
        'annual_income': annual_income,
        'annual_expense': annual_expense,
        'income_trend': income_trend,
        'expense_trend': expense_trend,
    }

    print(f"  Monthly avg income: JPY{result['monthly_avg_income']:,.0f}")
    print(f"  Monthly avg expense: JPY{result['monthly_avg_expense']:,.0f}")
    print(f"  Savings rate: {result['savings_rate']:.1%}")
    print(f"  Income trend: {result['income_trend']}")
    print(f"  Expense trend: {result['expense_trend']}")

    return result


def analyze_expense_by_category(transaction_df: pd.DataFrame) -> Dict[str, Any]:
    """
    カテゴリー別支出を分析

    Args:
        transaction_df: 収支詳細データフレーム

    Returns:
        カテゴリー別分析結果の辞書
    """
    print("Analyzing expense by category...")

    # 支出のみ抽出
    expense_df = transaction_df[transaction_df['is_expense'] == 1].copy()

    if len(expense_df) == 0:
        return {
            'total_expense': 0,
            'category_breakdown': {},
            'top_categories': [],
        }

    # 大区分別集計
    category_summary = expense_df.groupby('category_major')['expense'].sum().sort_values(ascending=False)

    # 割合計算
    total_expense = category_summary.sum()
    category_percentages = (category_summary / total_expense * 100).to_dict()

    # トップ5カテゴリー
    top_categories = [
        {'category': cat, 'amount': amt, 'percentage': category_percentages[cat]}
        for cat, amt in category_summary.head().items()
    ]

    result = {
        'total_expense': total_expense,
        'category_breakdown': category_summary.to_dict(),
        'category_percentages': category_percentages,
        'top_categories': top_categories,
    }

    print(f"  Total expense: JPY{result['total_expense']:,.0f}")
    print(f"  Top category: {top_categories[0]['category']} (JPY{top_categories[0]['amount']:,.0f}, {top_categories[0]['percentage']:.1f}%)")

    return result


def calculate_savings_rate_history(cashflow_df: pd.DataFrame) -> pd.DataFrame:
    """
    貯蓄率の推移を計算

    Args:
        cashflow_df: 月次収支データフレーム

    Returns:
        貯蓄率推移データフレーム
    """
    df = cashflow_df.copy()

    # 貯蓄率
    df['savings_rate'] = np.where(
        df['income'] > 0,
        df['net_cashflow'] / df['income'],
        0
    )

    # 3ヶ月移動平均
    df['savings_rate_ma3'] = df['savings_rate'].rolling(window=3, min_periods=1).mean()

    return df
