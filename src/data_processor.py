"""
データプロセッサーモジュール
データクリーニング、正規化、集計を担当
"""

import pandas as pd
import numpy as np
from typing import Dict, Any


def clean_asset_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    資産データのクリーニングと処理

    Args:
        df: 資産推移データフレーム

    Returns:
        クリーニング済みデータフレーム
    """
    print("Cleaning asset data...")

    df = df.copy()

    # 欠損値処理（前方埋め）
    df = df.ffill()

    # 純資産の計算
    # total_assets = 現金・預金 + 投資信託（負債データなし）
    df['net_assets'] = df['total_assets']

    # 負債カラムを追加（データにないため0とする）
    df['debt'] = 0

    # 移動平均の計算
    df['net_assets_ma3'] = df['net_assets'].rolling(window=3, min_periods=1).mean()
    df['net_assets_ma12'] = df['net_assets'].rolling(window=12, min_periods=1).mean()
    df['total_assets_ma3'] = df['total_assets'].rolling(window=3, min_periods=1).mean()

    # 資産内訳の移動平均
    df['cash_deposits_ma3'] = df['cash_deposits'].rolling(window=3, min_periods=1).mean()
    df['investment_trusts_ma3'] = df['investment_trusts'].rolling(window=3, min_periods=1).mean()

    # 月次集約（月末値を使用）
    df['year_month'] = df['date'].dt.to_period('M')

    print(f"  Processed {len(df)} daily records")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

    return df


def get_monthly_asset_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    日次データから月次データを取得（月末値）

    Args:
        df: 資産推移データフレーム

    Returns:
        月次集約データフレーム
    """
    # 月末値を取得
    monthly_df = df.groupby('year_month').last().reset_index()
    monthly_df['month'] = monthly_df['year_month'].dt.to_timestamp()

    print(f"  Monthly data: {len(monthly_df)} months")

    return monthly_df


def clean_transaction_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    収支データのクリーニングと処理

    Args:
        df: 収支詳細データフレーム

    Returns:
        クリーニング済みデータフレーム
    """
    print("Cleaning transaction data...")

    df = df.copy()

    # 計算対象外（振替）を除外
    # is_expense = 1 のみが計算対象
    df = df[df['is_expense'] == 1].copy()
    print(f"  Using only target transactions (is_expense=1). Remaining: {len(df)}")

    # 収入・支出の分離（金額の符号で判断）
    # 正の値 = 収入、負の値 = 支出
    df['income'] = np.where(df['amount'] > 0, df['amount'], 0)
    df['expense'] = np.where(df['amount'] < 0, -df['amount'], 0)  # 負の値を正に変換

    # カテゴリーの正規化（NaNを'その他'に）
    df['category_major'] = df['category_major'].fillna('その他')
    df['category_minor'] = df['category_minor'].fillna('その他')

    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Total income: JPY{df['income'].sum():,.0f}")
    print(f"  Total expense: JPY{df['expense'].sum():,.0f}")

    return df


def calculate_monthly_cashflow(df: pd.DataFrame) -> pd.DataFrame:
    """
    月次収支の集計

    Args:
        df: 収支詳細データフレーム

    Returns:
        月次収支データフレーム
    """
    print("Calculating monthly cashflow...")

    # 月次で集計
    df['year_month'] = df['date'].dt.to_period('M')

    monthly_cf = df.groupby('year_month').agg({
        'income': 'sum',
        'expense': 'sum'
    }).reset_index()

    monthly_cf['month'] = monthly_cf['year_month'].dt.to_timestamp()
    monthly_cf['net_cashflow'] = monthly_cf['income'] - monthly_cf['expense']

    # 移動平均（3ヶ月、6ヶ月）
    monthly_cf['income_ma3'] = monthly_cf['income'].rolling(window=3, min_periods=1).mean()
    monthly_cf['expense_ma3'] = monthly_cf['expense'].rolling(window=3, min_periods=1).mean()
    monthly_cf['income_ma6'] = monthly_cf['income'].rolling(window=6, min_periods=1).mean()
    monthly_cf['expense_ma6'] = monthly_cf['expense'].rolling(window=6, min_periods=1).mean()

    print(f"  Monthly cashflow calculated for {len(monthly_cf)} months")
    print(f"  Average monthly income: JPY{monthly_cf['income'].mean():,.0f}")
    print(f"  Average monthly expense: JPY{monthly_cf['expense'].mean():,.0f}")
    print(f"  Average savings: JPY{monthly_cf['net_cashflow'].mean():,.0f}")

    return monthly_cf


def calculate_category_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    カテゴリー別支出の集計

    Args:
        df: 収支詳細データフレーム

    Returns:
        カテゴリー別集計データフレーム
    """
    print("Calculating category breakdown...")

    # 支出のみ抽出
    expense_df = df[df['is_expense'] == 1].copy()

    # 大区分別集計
    category_summary = expense_df.groupby('category_major').agg({
        'expense': 'sum'
    }).reset_index()

    category_summary = category_summary.sort_values('expense', ascending=False)
    category_summary['percentage'] = category_summary['expense'] / category_summary['expense'].sum() * 100

    print(f"  Top 5 expense categories:")
    for _, row in category_summary.head().iterrows():
        print(f"    {row['category_major']}: JPY{row['expense']:,.0f} ({row['percentage']:.1f}%)")

    return category_summary


def calculate_category_monthly_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    カテゴリー別の月次支出推移

    Args:
        df: 収支詳細データフレーム

    Returns:
        カテゴリー別月次集計データフレーム
    """
    # 支出のみ抽出
    expense_df = df[df['is_expense'] == 1].copy()
    expense_df['year_month'] = expense_df['date'].dt.to_period('M')

    # 月次×カテゴリーでピボット
    monthly_category = expense_df.pivot_table(
        index='year_month',
        columns='category_major',
        values='expense',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    monthly_category['month'] = monthly_category['year_month'].dt.to_timestamp()

    print(f"  Category monthly breakdown: {len(monthly_category)} months")

    return monthly_category
