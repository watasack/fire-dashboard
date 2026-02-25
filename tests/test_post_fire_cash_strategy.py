#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FIRE後の現金管理戦略のテスト

平常時: 安全マージン500万円 + 生活費1ヶ月分を確保
暴落時: 株式売却停止（ドローダウン-20%以下）
回復時: 株式売却再開（ドローダウン-10%以上）
緊急時: 現金25万円未満で強制売却
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from config import load_config
from simulator import _manage_post_fire_cash


def test_normal_operation():
    """
    テスト1: 平常時の動作（月初に生活費1ヶ月分を株式売却）
    """
    print("=" * 80)
    print("テスト1: 平常時の月初株式売却")
    print("=" * 80)
    print()

    config = load_config('config.yaml')

    # 初期状態: 現金500万円（支出後または収入前の状態）、株式1000万円
    # 目標レベル = 500万（安全マージン）+ 25万（生活費1ヶ月分）= 525万円
    # 現金不足 = 525万 - 500万 = 25万円 → 株式売却が発生する
    cash = 5000000
    stocks = 10000000
    nisa_balance = 3000000
    nisa_cost_basis = 3000000
    stocks_cost_basis = 10000000
    monthly_expense = 250000  # 月25万円
    drawdown = 0  # 平常時
    capital_gains_tax_rate = 0.20315
    allocation_enabled = True
    is_start_of_month = True

    print(f"初期状態:")
    print(f"  現金: {cash:,}円（目標525万円に対して25万円不足）")
    print(f"  株式: {stocks:,}円")
    print(f"  月次支出: {monthly_expense:,}円")
    print(f"  ドローダウン: {drawdown:.1%}")
    print()

    result = _manage_post_fire_cash(
        cash, stocks, nisa_balance, nisa_cost_basis, stocks_cost_basis,
        monthly_expense, drawdown, config, capital_gains_tax_rate,
        allocation_enabled, is_start_of_month
    )

    print(f"月初処理後:")
    print(f"  現金: {result['cash']:,}円（目標525万円）")
    print(f"  株式: {result['stocks']:,}円")
    print(f"  売却額: {result['stocks_sold_for_monthly']:,}円")
    print(f"  暴落中: {result['in_market_crash']}")
    print()

    # 検証
    issues = []
    target_cash = 5000000 + 250000  # 安全マージン + 生活費1ヶ月分

    # 現金が目標レベルに達しているか確認
    if abs(result['cash'] - target_cash) > 1000:  # 1000円の誤差を許容（税金の影響）
        issues.append(f"現金が目標レベルに達していません: {result['cash']:,}円 (目標: {target_cash:,}円)")

    # 株式売却が発生したか確認
    if result['stocks_sold_for_monthly'] == 0:
        issues.append("現金不足なのに株式売却が発生していません")

    if result['in_market_crash']:
        issues.append("平常時なのに暴落フラグがTrueです")

    if issues:
        print("[NG] 平常時の動作に問題があります:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("[OK] 平常時の月初株式売却は正常に動作しています")
        return True


def test_market_crash():
    """
    テスト2: 暴落時の動作（株式売却停止）
    """
    print()
    print("=" * 80)
    print("テスト2: 暴落時の株式売却停止")
    print("=" * 80)
    print()

    config = load_config('config.yaml')

    # 初期状態: 現金525万円、株式1000万円、ドローダウン-25%
    cash = 5250000
    stocks = 10000000
    nisa_balance = 3000000
    nisa_cost_basis = 3000000
    stocks_cost_basis = 10000000
    monthly_expense = 250000
    drawdown = -0.25  # 暴落中
    capital_gains_tax_rate = 0.20315
    allocation_enabled = True
    is_start_of_month = True

    print(f"初期状態:")
    print(f"  現金: {cash:,}円")
    print(f"  株式: {stocks:,}円")
    print(f"  月次支出: {monthly_expense:,}円")
    print(f"  ドローダウン: {drawdown:.1%} ← 暴落中")
    print()

    result = _manage_post_fire_cash(
        cash, stocks, nisa_balance, nisa_cost_basis, stocks_cost_basis,
        monthly_expense, drawdown, config, capital_gains_tax_rate,
        allocation_enabled, is_start_of_month
    )

    print(f"月初処理後:")
    print(f"  現金: {result['cash']:,}円 (変化なし、安全マージンは温存)")
    print(f"  株式: {result['stocks']:,}円 (変化なし、売却停止)")
    print(f"  売却額: {result['stocks_sold_for_monthly']:,}円")
    print(f"  暴落中: {result['in_market_crash']}")
    print()

    # 検証
    issues = []
    if result['stocks_sold_for_monthly'] != 0:
        issues.append(f"暴落中なのに株式を売却しています: {result['stocks_sold_for_monthly']:,}円")

    if not result['in_market_crash']:
        issues.append("暴落中なのに暴落フラグがFalseです")

    if issues:
        print("[NG] 暴落時の動作に問題があります:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("[OK] 暴落時の株式売却停止は正常に動作しています")
        return True


def test_market_recovery():
    """
    テスト3: 回復時の動作（株式売却再開）
    """
    print()
    print("=" * 80)
    print("テスト3: 回復時の株式売却再開")
    print("=" * 80)
    print()

    config = load_config('config.yaml')

    # 初期状態: 現金500万円（目標未達）、株式1000万円、ドローダウン-8%（回復）
    cash = 5000000
    stocks = 10000000
    nisa_balance = 3000000
    nisa_cost_basis = 3000000
    stocks_cost_basis = 10000000
    monthly_expense = 250000
    drawdown = -0.08  # 回復（-10%以上）
    capital_gains_tax_rate = 0.20315
    allocation_enabled = True
    is_start_of_month = True

    print(f"初期状態:")
    print(f"  現金: {cash:,}円（目標525万円に対して25万円不足）")
    print(f"  株式: {stocks:,}円")
    print(f"  月次支出: {monthly_expense:,}円")
    print(f"  ドローダウン: {drawdown:.1%} ← 回復（-10%以上）")
    print()

    result = _manage_post_fire_cash(
        cash, stocks, nisa_balance, nisa_cost_basis, stocks_cost_basis,
        monthly_expense, drawdown, config, capital_gains_tax_rate,
        allocation_enabled, is_start_of_month
    )

    print(f"月初処理後:")
    print(f"  現金: {result['cash']:,}円（目標525万円）")
    print(f"  株式: {result['stocks']:,}円")
    print(f"  売却額: {result['stocks_sold_for_monthly']:,}円")
    print(f"  暴落中: {result['in_market_crash']}")
    print()

    # 検証
    issues = []
    target_cash = 5000000 + 250000

    # 現金が目標レベルに達しているか確認
    if abs(result['cash'] - target_cash) > 1000:
        issues.append(f"現金が目標レベルに達していません: {result['cash']:,}円 (目標: {target_cash:,}円)")

    # 株式売却が発生したか確認
    if result['stocks_sold_for_monthly'] == 0:
        issues.append("回復時なのに株式売却が発生していません")

    if issues:
        print("[NG] 回復時の動作に問題があります:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("[OK] 回復時の株式売却再開は正常に動作しています")
        return True


def test_emergency_low_cash():
    """
    テスト4: 緊急時の動作（現金25万円未満で強制売却）
    """
    print()
    print("=" * 80)
    print("テスト4: 緊急時の強制売却（現金25万円未満）")
    print("=" * 80)
    print()

    config = load_config('config.yaml')

    # 初期状態: 現金20万円（緊急）、株式1000万円、ドローダウン-25%（暴落中）
    cash = 200000  # 緊急ライン（25万円）未満
    stocks = 10000000
    nisa_balance = 3000000
    nisa_cost_basis = 3000000
    stocks_cost_basis = 10000000
    monthly_expense = 250000
    drawdown = -0.25  # 暴落中だが緊急時は売却
    capital_gains_tax_rate = 0.20315
    allocation_enabled = True
    is_start_of_month = True

    print(f"初期状態:")
    print(f"  現金: {cash:,}円 ← 緊急ライン（25万円）未満")
    print(f"  株式: {stocks:,}円")
    print(f"  月次支出: {monthly_expense:,}円")
    print(f"  ドローダウン: {drawdown:.1%} ← 暴落中だが緊急")
    print()

    result = _manage_post_fire_cash(
        cash, stocks, nisa_balance, nisa_cost_basis, stocks_cost_basis,
        monthly_expense, drawdown, config, capital_gains_tax_rate,
        allocation_enabled, is_start_of_month
    )

    print(f"月初処理後:")
    print(f"  現金: {result['cash']:,}円")
    print(f"  株式: {result['stocks']:,}円")
    print(f"  売却額: {result['stocks_sold_for_monthly']:,}円")
    print(f"  暴落中: {result['in_market_crash']}")
    print()

    # 検証
    issues = []
    if result['stocks_sold_for_monthly'] == 0:
        issues.append("緊急時（現金25万円未満）なのに株式を売却していません")

    if result['in_market_crash'] and result['stocks_sold_for_monthly'] == 0:
        issues.append("暴落中かつ緊急時なのに売却が実行されていません")

    if issues:
        print("[NG] 緊急時の動作に問題があります:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("[OK] 緊急時の強制売却は正常に動作しています")
        return True


def main():
    """
    メインテスト関数
    """
    print()
    print("FIRE後の現金管理戦略 動作確認テスト")
    print()

    results = []

    # テスト1: 平常時
    results.append(("平常時の月初株式売却", test_normal_operation()))

    # テスト2: 暴落時
    results.append(("暴落時の株式売却停止", test_market_crash()))

    # テスト3: 回復時
    results.append(("回復時の株式売却再開", test_market_recovery()))

    # テスト4: 緊急時
    results.append(("緊急時の強制売却", test_emergency_low_cash()))

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
