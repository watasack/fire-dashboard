"""
分析モジュール
現状の資産状況と収支トレンドの分析を担当
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from scipy import stats


def analyze_current_status(asset_df: pd.DataFrame) -> Dict[str, Any]:
    """
    現在の資産状況を分析

    Args:
        asset_df: 資産推移データフレーム

    Returns:
        現状分析結果の辞書
    """
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
        'cash_deposits': latest['cash_deposits'],
        'investment_trusts': latest['investment_trusts'],
        'growth_rate_1m': growth_1m,
        'growth_rate_3m': growth_3m,
        'growth_rate_12m': growth_12m,
    }

    return result


def analyze_income_expense_trends(
    cashflow_df: pd.DataFrame,
    transaction_df: pd.DataFrame = None,
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    収支のトレンドを分析

    Args:
        cashflow_df: 月次収支データフレーム
        transaction_df: 取引明細データフレーム（予測用収入計算に使用、オプション）
        config: 設定辞書（予測用収入フィルタに使用、オプション）

    Returns:
        収支トレンド分析結果の辞書
    """
    if len(cashflow_df) == 0:
        return {
            'monthly_avg_income': 0,
            'monthly_avg_income_forecast': 0,
            'monthly_avg_expense': 0,
            'monthly_avg_savings': 0,
            'savings_rate': 0,
            'annual_income': 0,
            'annual_expense': 0,
        }

    # 月次平均（実際の全収入）
    monthly_avg_income = cashflow_df['income'].mean()
    monthly_avg_expense = cashflow_df['expense'].mean()
    monthly_avg_savings = cashflow_df['net_cashflow'].mean()

    # 将来予測用の収入を計算（定期収入のみ）
    monthly_avg_income_forecast = monthly_avg_income  # デフォルトは全収入

    if transaction_df is not None and config is not None:
        forecast_config = config['data']['income_forecast']
        if forecast_config:
            income_df = transaction_df[transaction_df['amount'] > 0].copy()

            include_keywords = forecast_config['include_keywords']
            exclude_keywords = forecast_config['exclude_keywords']

            # 除外キーワードでフィルタ
            for keyword in exclude_keywords:
                income_df = income_df[~income_df['description'].str.contains(keyword, na=False)]

            # 含めるキーワードでフィルタ（指定がある場合のみ）
            if include_keywords:
                mask = pd.Series(False, index=income_df.index)
                for keyword in include_keywords:
                    mask |= income_df['description'].str.contains(keyword, na=False)
                income_df = income_df[mask]

            # 予測用収入の月次平均を計算
            if len(income_df) > 0:
                income_df['year_month'] = income_df['date'].dt.to_period('M')
                monthly_forecast = income_df.groupby('year_month')['amount'].sum()
                monthly_avg_income_forecast = monthly_forecast.mean()

    # 貯蓄率（実際の全収入ベース）
    savings_rate = monthly_avg_savings / monthly_avg_income if monthly_avg_income > 0 else 0

    # 年間換算
    annual_income = monthly_avg_income * 12
    annual_expense = monthly_avg_expense * 12

    # 手動設定の年間支出があれば優先（データが不足している場合）
    if config is not None:
        manual_expense = config.get('fire', {}).get('manual_annual_expense')
        if manual_expense is not None and manual_expense > 0:
            annual_expense = manual_expense
            monthly_avg_expense = annual_expense / 12
            # 貯蓄額を再計算
            monthly_avg_savings = monthly_avg_income_forecast - monthly_avg_expense
            savings_rate = monthly_avg_savings / monthly_avg_income if monthly_avg_income > 0 else 0

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
        'monthly_avg_income_forecast': monthly_avg_income_forecast,  # 予測用収入
        'monthly_avg_expense': monthly_avg_expense,
        'monthly_avg_savings': monthly_avg_savings,
        'savings_rate': savings_rate,
        'annual_income': annual_income,
        'annual_expense': annual_expense,
        'income_trend': income_trend,
        'expense_trend': expense_trend,
    }

    return result


def analyze_expense_by_category(transaction_df: pd.DataFrame) -> Dict[str, Any]:
    """
    カテゴリー別支出を分析

    Args:
        transaction_df: 収支詳細データフレーム

    Returns:
        カテゴリー別分析結果の辞書
    """
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

    return result


def generate_action_items(
    fire_target: Dict[str, Any],
    fire_achievement: Dict[str, Any],
    trends: Dict[str, Any],
    expense_breakdown: Dict[str, Any],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    FIREのためのアクションアイテムを生成

    Args:
        fire_target: FIRE目標額情報
        fire_achievement: FIRE達成予想情報
        trends: 収支トレンド
        expense_breakdown: カテゴリー別支出
        config: 設定辞書

    Returns:
        アクションアイテムのリスト
    """
    action_items = []
    monthly_avg_expense = trends['monthly_avg_expense']
    monthly_avg_savings = trends['monthly_avg_savings']
    annual_return_rate = config['simulation']['standard']['annual_return_rate']

    # 達成済みの場合
    if fire_achievement and fire_achievement.get('achieved'):
        action_items.append({
            'icon': '✓',
            'text': 'FIRE目標を達成済みです！資産の維持に注力しましょう',
            'type': 'success'
        })
        return action_items

    # 達成不可能な場合（貯蓄率がマイナス）
    if monthly_avg_savings <= 0:
        action_items.append({
            'icon': '⚠',
            'text': f'支出が収入を超過しています。月{abs(monthly_avg_savings)/10000:.1f}万円の赤字を改善する必要があります',
            'type': 'critical'
        })
        return action_items

    # 1. 支出削減の提案
    if len(expense_breakdown['top_categories']) > 0:
        top_category = expense_breakdown['top_categories'][0]
        top_category_amount = top_category['amount'] / 12  # 月額に換算
        action_items.append({
            'icon': '💡',
            'text': f'{top_category["category"]}（月{top_category_amount/10000:.1f}万円）の見直しで貯蓄を増やせる可能性があります',
            'type': 'suggestion'
        })

    # 2. 貯蓄率の改善余地
    savings_rate = trends['savings_rate']
    if savings_rate < 0.3:  # 30%未満
        target_rate = 0.3
        additional_savings_needed = trends['monthly_avg_income'] * target_rate - monthly_avg_savings
        action_items.append({
            'icon': '📊',
            'text': f'貯蓄率を30%に引き上げるには、月{additional_savings_needed/10000:.1f}万円の追加貯蓄が必要です',
            'type': 'info'
        })

    # 3. 投資リターンの重要性
    if fire_achievement:
        months_to_fire = fire_achievement['months_to_fire']
        years_to_fire = months_to_fire // 12

        if years_to_fire >= 10:
            action_items.append({
                'icon': '📈',
                'text': f'年率{annual_return_rate:.1%}のリターンを維持することで、{years_to_fire}年後にFIRE達成予定です',
                'type': 'info'
            })
        else:
            action_items.append({
                'icon': '🎯',
                'text': f'あと{years_to_fire}年でFIRE達成です！現在の貯蓄ペースを維持しましょう',
                'type': 'success'
            })

    # 最大3つまでに制限
    return action_items[:3]
