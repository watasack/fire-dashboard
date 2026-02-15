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

    return df


def clean_transaction_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    収支データのクリーニングと処理

    Args:
        df: 収支詳細データフレーム

    Returns:
        クリーニング済みデータフレーム
    """
    df = df.copy()

    # 計算対象外（振替）を除外
    # is_expense = 1 のみが計算対象
    df = df[df['is_expense'] == 1].copy()

    # 収入・支出の分離（金額の符号で判断）
    # 正の値 = 収入、負の値 = 支出
    df['income'] = np.where(df['amount'] > 0, df['amount'], 0)
    df['expense'] = np.where(df['amount'] < 0, -df['amount'], 0)  # 負の値を正に変換

    # カテゴリーの正規化（NaNを'その他'に）
    df['category_major'] = df['category_major'].fillna('その他')
    df['category_minor'] = df['category_minor'].fillna('その他')

    return df


def calculate_monthly_cashflow(df: pd.DataFrame) -> pd.DataFrame:
    """
    月次収支の集計

    Args:
        df: 収支詳細データフレーム

    Returns:
        月次収支データフレーム
    """
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

    return monthly_cf


