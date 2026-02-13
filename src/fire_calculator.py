"""
FIRE計算モジュール
FIRE目標額の逆算ロジック（二分探索）
"""

from typing import Dict, Any
from .simulator import simulate_with_withdrawal


def calculate_fire_target(
    annual_expense: float,
    current_net_assets: float,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    FIRE目標額を計算

    二分探索で「シミュレーション期間終了後も資産がゼロにならない最低額」を逆算し、
    3つのシナリオで検証して最も悲観的なシナリオでも破綻しない額を推奨する

    Args:
        annual_expense: 年間支出
        current_net_assets: 現在の純資産
        config: 設定辞書

    Returns:
        FIRE目標額と関連情報の辞書
    """
    print("Calculating FIRE target using binary search...")

    # 設定取得
    life_expectancy_years = config['simulation'].get('life_expectancy', 90)
    start_age = config['simulation'].get('start_age', 35)
    retirement_years = life_expectancy_years - start_age
    safety_buffer = config['fire'].get('safety_buffer', 1.2)
    tolerance = config['fire'].get('tolerance', 100000)

    # 各シナリオで最低必要額を計算
    scenarios = ['standard', 'optimistic', 'pessimistic']
    scenario_targets = {}

    for scenario in scenarios:
        scenario_config = config['simulation'][scenario]
        return_rate = scenario_config['annual_return_rate']
        inflation_rate = scenario_config['inflation_rate']

        print(f"\n  Calculating for {scenario} scenario...")
        print(f"    Return rate: {return_rate:.1%}, Inflation: {inflation_rate:.1%}")

        # 二分探索
        min_assets = annual_expense * 10  # 下限
        max_assets = annual_expense * 100  # 上限
        iterations = 0
        max_iterations = 100

        while max_assets - min_assets > tolerance and iterations < max_iterations:
            mid_assets = (min_assets + max_assets) / 2

            # シミュレーション実行
            final_assets = simulate_with_withdrawal(
                initial_assets=mid_assets,
                annual_expense=annual_expense,
                years=retirement_years,
                return_rate=return_rate,
                inflation_rate=inflation_rate
            )

            if final_assets > 0:
                # まだ資産が残っている → もっと少なくても良い
                max_assets = mid_assets
            else:
                # 資産が尽きた → もっと必要
                min_assets = mid_assets

            iterations += 1

        minimum_required = max_assets

        print(f"    Minimum required: JPY{minimum_required:,.0f} (iterations: {iterations})")

        scenario_targets[scenario] = {
            'minimum_required': minimum_required,
            'return_rate': return_rate,
            'inflation_rate': inflation_rate,
        }

    # 最も悲観的なシナリオの値を採用
    pessimistic_minimum = scenario_targets['pessimistic']['minimum_required']
    recommended_target = pessimistic_minimum * safety_buffer

    # 4%ルールとの比較
    rule_of_4_percent = annual_expense / 0.04

    # 現在の達成率
    progress_rate = current_net_assets / recommended_target if recommended_target > 0 else 0

    # 不足額
    shortfall = max(0, recommended_target - current_net_assets)

    print(f"\n  === FIRE Target Summary ===")
    print(f"  Annual expense: JPY{annual_expense:,.0f}")
    print(f"  Retirement period: {retirement_years} years")
    print(f"  Pessimistic minimum: JPY{pessimistic_minimum:,.0f}")
    print(f"  Safety buffer: {safety_buffer:.1%}")
    print(f"  Recommended target: JPY{recommended_target:,.0f}")
    print(f"  4% rule (reference): JPY{rule_of_4_percent:,.0f}")
    print(f"  Current assets: JPY{current_net_assets:,.0f}")
    print(f"  Progress: {progress_rate:.1%}")
    print(f"  Shortfall: JPY{shortfall:,.0f}")

    return {
        'recommended_target': recommended_target,
        'pessimistic_minimum': pessimistic_minimum,
        'standard_minimum': scenario_targets['standard']['minimum_required'],
        'optimistic_minimum': scenario_targets['optimistic']['minimum_required'],
        'safety_buffer': safety_buffer,
        'rule_of_4_percent': rule_of_4_percent,
        'current_net_assets': current_net_assets,
        'progress_rate': progress_rate,
        'shortfall': shortfall,
        'annual_expense': annual_expense,
        'retirement_years': retirement_years,
        'scenario_details': scenario_targets,
    }


def calculate_withdrawal_rate(target_assets: float, annual_expense: float) -> float:
    """
    資産額に対する引き出し率を計算

    Args:
        target_assets: 目標資産額
        annual_expense: 年間支出

    Returns:
        引き出し率（0-1）
    """
    if target_assets <= 0:
        return 0

    return annual_expense / target_assets


def calculate_years_to_depletion(
    assets: float,
    annual_expense: float,
    return_rate: float = 0.05,
    inflation_rate: float = 0.02
) -> float:
    """
    資産が枯渇するまでの年数を計算

    Args:
        assets: 現在の資産
        annual_expense: 年間支出
        return_rate: 年率リターン
        inflation_rate: インフレ率

    Returns:
        枯渇までの年数（枯渇しない場合は-1）
    """
    current_assets = assets
    monthly_expense = annual_expense / 12
    monthly_return = (1 + return_rate) ** (1/12) - 1
    max_years = 200

    for month in range(max_years * 12):
        years_elapsed = month / 12
        adjusted_expense = monthly_expense * (1 + inflation_rate) ** years_elapsed
        investment_return = current_assets * monthly_return

        current_assets = current_assets - adjusted_expense + investment_return

        if current_assets <= 0:
            return years_elapsed

    return -1  # 枯渇しない（200年以上持つ）
