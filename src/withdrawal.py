"""FIRE後の取り崩し戦略計算モジュール。

サポートする戦略:
  fixed      - 固定額（現状維持）: 毎月一定額を取り崩す
  percentage - 定率: 残高 × 年率 / 12 を取り崩す（4%ルール等）
  guardrail  - ガードレール戦略: 資産がFIRE時の比率を下回ると支出削減
"""

from typing import Any, Dict


def calc_withdrawal_adjustment(
    current_assets: float,
    fire_assets: float,
    base_expense_monthly: float,
    config: Dict[str, Any],
) -> float:
    """取り崩し戦略に基づいて base_expense_monthly への月次調整額を返す。

    Args:
        current_assets: 現時点の総資産額（円）
        fire_assets: FIRE達成時の総資産額（基準値・円）
        base_expense_monthly: 月次基本生活費（住宅ローン・教育費を除く・円）
        config: シミュレーション設定辞書

    Returns:
        base_expense_monthly への加算値（負 = 削減、正 = 増加）。
        固定戦略または fire_assets <= 0 の場合は 0 を返す。
    """
    strategy = config['simulation'].get('withdrawal_strategy', 'fixed')

    if strategy == 'fixed' or fire_assets <= 0 or base_expense_monthly <= 0:
        return 0.0

    if strategy == 'percentage':
        rate = float(config['simulation'].get('withdrawal_rate', 0.04))
        new_base = current_assets * rate / 12
        return new_base - base_expense_monthly

    if strategy == 'guardrail':
        lower = float(config['simulation'].get('guardrail_lower', 0.80))
        upper = float(config['simulation'].get('guardrail_upper', 1.20))
        reduction = float(config['simulation'].get('guardrail_reduction', 0.10))
        ratio = current_assets / fire_assets
        if ratio < lower:
            # 資産が下限を割り込み → 生活費を削減
            return base_expense_monthly * (-reduction)
        elif ratio > upper:
            # 資産が上限を超過 → 生活費をわずかに増加
            return base_expense_monthly * 0.05
        return 0.0

    return 0.0
