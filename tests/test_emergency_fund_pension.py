#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
緊急時資金3層構造と年金繰り下げ戦略のテスト

実装された機能が正しく動作しているか検証する
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from config import load_config
from simulator import (
    _determine_optimal_pension_start_age,
    calculate_pension_income
)


def test_pension_deferral():
    """
    年金繰り下げ戦略のテスト
    """
    print()
    print("=" * 80)
    print("テスト2: 年金繰り下げ受給戦略")
    print("=" * 80)
    print()

    config = load_config('config.yaml')

    # FIRE目標資産（空の巣期の年間支出÷4%）
    base_expense = config['fire']['base_expense_by_stage']['empty_nest']
    fire_target = base_expense / 0.04
    print(f"FIRE目標資産: {fire_target:,.0f}円")
    print()

    # テストケース1: 資産が豊富（150%以上） → 70歳まで繰り下げ
    print("【ケース1】資産豊富（目標の160%）")
    assets1 = fire_target * 1.6
    age1 = _determine_optimal_pension_start_age(
        current_assets=assets1,
        config=config,
        fire_target_assets=fire_target
    )
    print(f"  現在資産: {assets1:,.0f}円")
    print(f"  資産比率: {assets1/fire_target:.1%}")
    print(f"  最適受給開始年齢: {age1}歳")
    print()

    # テストケース2: 資産が適度（120-150%） → 68歳まで繰り下げ
    print("【ケース2】資産適度（目標の130%）")
    assets2 = fire_target * 1.3
    age2 = _determine_optimal_pension_start_age(
        current_assets=assets2,
        config=config,
        fire_target_assets=fire_target
    )
    print(f"  現在資産: {assets2:,.0f}円")
    print(f"  資産比率: {assets2/fire_target:.1%}")
    print(f"  最適受給開始年齢: {age2}歳")
    print()

    # テストケース3: 資産が通常（50-120%） → 65歳で通常受給
    print("【ケース3】資産通常（目標の90%）")
    assets3 = fire_target * 0.9
    age3 = _determine_optimal_pension_start_age(
        current_assets=assets3,
        config=config,
        fire_target_assets=fire_target
    )
    print(f"  現在資産: {assets3:,.0f}円")
    print(f"  資産比率: {assets3/fire_target:.1%}")
    print(f"  最適受給開始年齢: {age3}歳")
    print()

    # テストケース4: 資産不足（50%未満） → 62歳で繰り上げ受給
    print("【ケース4】資産不足（目標の40%）")
    assets4 = fire_target * 0.4
    age4 = _determine_optimal_pension_start_age(
        current_assets=assets4,
        config=config,
        fire_target_assets=fire_target
    )
    print(f"  現在資産: {assets4:,.0f}円")
    print(f"  資産比率: {assets4/fire_target:.1%}")
    print(f"  最適受給開始年齢: {age4}歳")
    print()

    # 検証
    issues = []

    if age1 != 70:
        issues.append(f"ケース1: 70歳を期待しましたが{age1}歳になっています")
    if age2 != 68:
        issues.append(f"ケース2: 68歳を期待しましたが{age2}歳になっています")
    if age3 != 65:
        issues.append(f"ケース3: 65歳を期待しましたが{age3}歳になっています")
    if age4 != 62:
        issues.append(f"ケース4: 62歳を期待しましたが{age4}歳になっています")

    if issues:
        print("[NG] 年金繰り下げ判定に問題があります:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("[OK] 年金繰り下げ戦略は正しく動作しています")
        return True


def test_pension_amount_adjustment():
    """
    年金額の増減率テスト
    """
    print()
    print("=" * 80)
    print("テスト3: 年金額の繰り下げ・繰り上げ調整")
    print("=" * 80)
    print()

    config = load_config('config.yaml')

    base_expense = config['fire']['base_expense_by_stage']['empty_nest']
    fire_target = base_expense / 0.04

    # 65歳時点での年金額（通常受給、資産=目標）
    print("【基準】65歳で通常受給（資産=目標）")
    pension_65_normal = calculate_pension_income(
        year_offset=30,  # 35歳 + 30年 = 65歳
        config=config,
        fire_achieved=True,
        fire_year_offset=4,  # 4年でFIRE達成と仮定
        current_assets=fire_target,  # 目標通り
        fire_target_assets=fire_target
    )
    print(f"  年金額: {pension_65_normal:,.0f}円/年 ({pension_65_normal/12:,.0f}円/月)")
    print()

    # 70歳で受給開始（65歳時点で資産豊富だったため繰り下げ）
    print("【繰り下げ】70歳で受給開始（65歳時点で資産=目標の160%だった想定）")
    pension_70_deferred = calculate_pension_income(
        year_offset=35,  # 35歳 + 35年 = 70歳
        config=config,
        fire_achieved=True,
        fire_year_offset=4,
        current_assets=fire_target * 1.6,  # 70歳時点でも資産豊富
        fire_target_assets=fire_target
    )
    increase_rate = (pension_70_deferred / pension_65_normal - 1) if pension_65_normal > 0 else 0
    print(f"  年金額: {pension_70_deferred:,.0f}円/年 ({pension_70_deferred/12:,.0f}円/月)")
    print(f"  増加率: {increase_rate:+.1%} (期待値: +42.0%)")
    print()

    # 62歳で受給開始（資産不足のため繰り上げ）
    print("【繰り上げ】62歳で受給開始（資産=目標の40%）")
    pension_62_early = calculate_pension_income(
        year_offset=27,  # 35歳 + 27年 = 62歳
        config=config,
        fire_achieved=True,
        fire_year_offset=4,
        current_assets=fire_target * 0.4,  # 目標の40%
        fire_target_assets=fire_target
    )
    decrease_rate = (pension_62_early / pension_65_normal - 1) if pension_65_normal > 0 else 0
    print(f"  年金額: {pension_62_early:,.0f}円/年 ({pension_62_early/12:,.0f}円/月)")
    print(f"  減少率: {decrease_rate:+.1%} (期待値: -14.4%)")
    print()

    # 検証
    issues = []

    # 繰り下げ: 5年 × 8.4% = 42%の増加を期待
    expected_increase = 0.42
    if pension_65_normal > 0 and abs(increase_rate - expected_increase) > 0.02:
        issues.append(f"繰り下げの増加率が期待値と異なります: {increase_rate:.1%} (期待: {expected_increase:.1%})")

    # 繰り上げ: 3年 × 4.8% = 14.4%の減少を期待
    expected_decrease = -0.144
    if pension_65_normal > 0 and abs(decrease_rate - expected_decrease) > 0.02:
        issues.append(f"繰り上げの減少率が期待値と異なります: {decrease_rate:.1%} (期待: {expected_decrease:.1%})")

    # 追加検証: 繰り下げ中は年金0円
    print("【追加検証】繰り下げ中は年金0円")
    pension_66_waiting = calculate_pension_income(
        year_offset=31,  # 66歳
        config=config,
        fire_achieved=True,
        fire_year_offset=4,
        current_assets=fire_target * 1.6,  # 資産豊富なので70歳まで待機
        fire_target_assets=fire_target
    )
    print(f"  66歳時点（資産豊富）: {pension_66_waiting:,.0f}円/年")
    if pension_66_waiting != 0:
        issues.append(f"繰り下げ中（66歳）なのに年金が{pension_66_waiting:,.0f}円受給されています")
    else:
        print(f"  [OK] 70歳まで繰り下げ中のため年金0円")
    print()

    if issues:
        print("[NG] 年金額の調整に問題があります:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("[OK] 年金額の繰り下げ・繰り上げ調整は正しく動作しています")
        return True


def main():
    """
    メインテスト関数
    """
    print()
    print("緊急時資金3層構造と年金繰り下げ戦略の動作確認テスト")
    print()

    results = []

    # テスト1: 年金繰り下げ判定
    results.append(("年金繰り下げ判定", test_pension_deferral()))

    # テスト2: 年金額調整
    results.append(("年金額調整", test_pension_amount_adjustment()))

    # 結果サマリー
    print()
    print("=" * 80)
    print("テスト結果サマリー")
    print("=" * 80)
    print()

    all_passed = True
    for test_name, passed in results:
        status = "[OK]" if passed else "[NG]"
        print(f"  {status} {test_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("全てのテストに合格しました！")
        return 0
    else:
        print("一部のテストに失敗しました。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
