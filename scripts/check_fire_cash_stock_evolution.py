#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FIRE後の現金と株式の推移を確認するスクリプト
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from config import load_config
from simulator import simulate_future_assets


def check_fire_evolution():
    """
    FIRE後の数年間の現金と株式の推移を確認
    """
    print("=" * 80)
    print("FIRE後の現金・株式推移チェック")
    print("=" * 80)
    print()

    config = load_config('config.yaml')

    # シミュレーション実行
    print("シミュレーション実行中...")

    # 初期値を設定（ダッシュボード生成と同じ）
    initial_assets = 10000000  # 仮の初期資産
    initial_income = config['simulation'].get('initial_labor_income', 800000)
    initial_expense = 300000  # 仮の初期支出

    result = simulate_future_assets(
        current_assets=initial_assets,
        monthly_income=initial_income,
        monthly_expense=initial_expense,
        config=config,
        scenario='standard'
    )

    # FIRE達成時期を確認
    fire_date = None
    fire_idx = None
    for idx, row in result.iterrows():
        if row['fire_achieved'] and fire_date is None:
            fire_date = row['date']
            fire_idx = idx
            break

    if fire_date is None:
        print("[ERROR] FIRE未達成")
        return False

    print(f"FIRE達成: {fire_date}")
    print()

    # FIRE後の最初の12ヶ月を表示
    print("=" * 80)
    print(f"FIRE達成後の12ヶ月間の推移（{fire_date}～）")
    print("=" * 80)
    print()
    print(f"{'月':<6} {'現金':>15} {'株式':>15} {'合計資産':>15} {'現金増減':>12} {'株式増減':>12}")
    print("-" * 80)

    prev_cash = None
    prev_stocks = None

    for offset in range(13):  # FIRE達成月 + 12ヶ月
        if fire_idx + offset >= len(result):
            break

        row = result.iloc[fire_idx + offset]
        cash = row['cash']
        stocks = row['stocks']
        total = row['assets']

        if prev_cash is not None:
            cash_change = cash - prev_cash
            stocks_change = stocks - prev_stocks
        else:
            cash_change = 0
            stocks_change = 0

        print(f"{offset:<6} {cash:>15,.0f} {stocks:>15,.0f} {total:>15,.0f} {cash_change:>+12,.0f} {stocks_change:>+12,.0f}")

        prev_cash = cash
        prev_stocks = stocks

    print()

    # さらに先（FIRE後5年目）を確認
    print("=" * 80)
    print(f"FIRE達成後5年目の状況")
    print("=" * 80)
    print()

    year_5_idx = fire_idx + 60  # 5年 = 60ヶ月
    if year_5_idx < len(result):
        row = result.iloc[year_5_idx]
        print(f"日付: {row['date']}")
        print(f"現金: {row['cash']:,.0f}円")
        print(f"株式: {row['stocks']:,.0f}円")
        print(f"合計資産: {row['assets']:,.0f}円")
    else:
        print("[INFO] 5年目のデータなし（シミュレーション期間外）")

    print()

    # 株式がゼロになる時期を探す
    print("=" * 80)
    print("株式残高の確認")
    print("=" * 80)
    print()

    stocks_zero_date = None
    for idx in range(fire_idx, len(result)):
        row = result.iloc[idx]
        if row['stocks'] <= 0:
            stocks_zero_date = row['date']
            break

    if stocks_zero_date:
        print(f"[WARNING] 株式が{stocks_zero_date}にゼロになっています！")
        print("→ バグが修正されていない可能性があります")
        return False
    else:
        print("[OK] 株式は正常に推移しています")
        return True


if __name__ == '__main__':
    success = check_fire_evolution()
    sys.exit(0 if success else 1)
