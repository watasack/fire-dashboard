#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
年金計算のデバッグ
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from config import load_config
from simulator import (
    calculate_pension_income,
    _determine_optimal_pension_start_age
)


def debug_pension_calculation():
    """
    年金計算の詳細をデバッグ
    """
    config = load_config('config.yaml')

    base_expense = config['fire']['base_expense_by_stage']['empty_nest']
    fire_target = base_expense / 0.04

    print("=" * 80)
    print("年金計算デバッグ")
    print("=" * 80)
    print()

    # ケース1: 65歳、資産=目標（通常受給）
    print("【ケース1】65歳、資産=目標（通常受給）")
    print(f"  year_offset: 30 (35 + 30 = 65歳)")
    print(f"  current_assets: {fire_target:,.0f}円")
    print(f"  fire_target_assets: {fire_target:,.0f}円")

    optimal_age_1 = _determine_optimal_pension_start_age(
        current_assets=fire_target,
        config=config,
        fire_target_assets=fire_target
    )
    print(f"  → optimal_start_age: {optimal_age_1}歳")

    pension_1 = calculate_pension_income(
        year_offset=30,
        config=config,
        fire_achieved=True,
        fire_year_offset=4,
        current_assets=fire_target,
        fire_target_assets=fire_target
    )
    print(f"  → 年金額: {pension_1:,.0f}円/年")
    print()

    # ケース2: 70歳、資産=目標の160%（繰り下げ受給）
    print("【ケース2】70歳、資産=目標の160%（繰り下げ想定）")
    print(f"  year_offset: 35 (35 + 35 = 70歳)")
    print(f"  current_assets: {fire_target * 1.6:,.0f}円")
    print(f"  fire_target_assets: {fire_target:,.0f}円")

    optimal_age_2 = _determine_optimal_pension_start_age(
        current_assets=fire_target * 1.6,
        config=config,
        fire_target_assets=fire_target
    )
    print(f"  → optimal_start_age: {optimal_age_2}歳")
    print(f"  → age_diff: {optimal_age_2 - 65}年")
    print(f"  → 期待調整率: 1 + (0.084 × {optimal_age_2 - 65}) = {1 + 0.084 * (optimal_age_2 - 65):.3f}")

    pension_2 = calculate_pension_income(
        year_offset=35,
        config=config,
        fire_achieved=True,
        fire_year_offset=4,
        current_assets=fire_target * 1.6,
        fire_target_assets=fire_target
    )
    print(f"  → 年金額: {pension_2:,.0f}円/年")
    print(f"  → 実際の調整率: {pension_2 / pension_1:.3f}" if pension_1 > 0 else "  → 計算不可")
    print()

    # ケース3: 62歳、資産=目標の40%（繰り上げ受給）
    print("【ケース3】62歳、資産=目標の40%（繰り上げ受給）")
    print(f"  year_offset: 27 (35 + 27 = 62歳)")
    print(f"  current_assets: {fire_target * 0.4:,.0f}円")
    print(f"  fire_target_assets: {fire_target:,.0f}円")

    optimal_age_3 = _determine_optimal_pension_start_age(
        current_assets=fire_target * 0.4,
        config=config,
        fire_target_assets=fire_target
    )
    print(f"  → optimal_start_age: {optimal_age_3}歳")
    print(f"  → age_diff: {optimal_age_3 - 65}年")
    print(f"  → 期待調整率: 1 - (0.048 × {abs(optimal_age_3 - 65)}) = {1 - 0.048 * abs(optimal_age_3 - 65):.3f}")

    pension_3 = calculate_pension_income(
        year_offset=27,
        config=config,
        fire_achieved=True,
        fire_year_offset=4,
        current_assets=fire_target * 0.4,
        fire_target_assets=fire_target
    )
    print(f"  → 年金額: {pension_3:,.0f}円/年")
    print(f"  → 実際の調整率: {pension_3 / pension_1:.3f}" if pension_1 > 0 and pension_3 > 0 else "  → 計算不可")
    print()

    # 年齢と受給判定の確認
    print("=" * 80)
    print("年齢別の受給判定")
    print("=" * 80)
    print()

    for year_offset in [25, 27, 30, 32, 35]:
        age = 35 + year_offset
        pension = calculate_pension_income(
            year_offset=year_offset,
            config=config,
            fire_achieved=True,
            fire_year_offset=4,
            current_assets=fire_target * 1.6,  # 資産豊富
            fire_target_assets=fire_target
        )
        print(f"  {age}歳（資産豊富）: {pension:,.0f}円/年")

    print()


if __name__ == '__main__':
    debug_pension_calculation()
