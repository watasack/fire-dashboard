"""
MC近似テーブル生成スクリプト
Googleスプレッドシート版のFIRE成功確率テーブルを事前計算する。

出力: data/mc_table.csv
  - 行: 資産倍率（資産 ÷ 年間支出）= 10〜40倍
  - 列: FIRE後年数 = 20〜55年
  - 値: FIRE成功確率 (%)（資産が枯渇しない確率）

前提:
  - 年率リターン: 正規分布 μ=5%, σ=15%（長期株式標準的仮定）
  - インフレ率: 2%（支出が毎年2%増加）
  - 月次シミュレーション
  - 成功基準: シミュレーション期間中に資産がゼロ以下にならない
"""

import numpy as np
import pandas as pd
from pathlib import Path

# -------------------------------------------------------------------
# パラメータ
# -------------------------------------------------------------------
N_SIMULATIONS = 2000          # シミュレーション回数
ANNUAL_RETURN_MEAN = 0.05     # 年率期待リターン
ANNUAL_RETURN_STD = 0.15      # 年率リターン標準偏差
INFLATION_RATE = 0.02         # インフレ率（支出成長率）
RANDOM_SEED = 42

# テーブルの軸
ASSET_MULTIPLES = list(range(10, 45, 5))   # 10, 15, 20, 25, 30, 35, 40
FIRE_YEARS = list(range(20, 60, 5))         # 20, 25, 30, 35, 40, 45, 50, 55

# -------------------------------------------------------------------
# MC シミュレーション（単純モデル）
# -------------------------------------------------------------------
rng = np.random.default_rng(RANDOM_SEED)


def simulate_success_rate(asset_multiple: float, fire_years: int) -> float:
    """
    資産倍率とFIRE後年数を与え、FIRE成功確率を返す。

    Args:
        asset_multiple: 資産 / 年間支出（例: 25 = 25倍 = 4%ルール）
        fire_years: FIRE後の生存年数（例: 30 = 65歳FIREなら95歳まで）

    Returns:
        成功確率（0.0〜1.0）
    """
    months = fire_years * 12
    monthly_return_mean = (1 + ANNUAL_RETURN_MEAN) ** (1 / 12) - 1
    monthly_return_std = ANNUAL_RETURN_STD / 12 ** 0.5
    monthly_inflation = (1 + INFLATION_RATE) ** (1 / 12) - 1

    # 初期資産を1（正規化）、初期月次支出を 1/months_equivalent
    # asset_multiple = 資産 / 年間支出 → 月次支出 = 1 / (asset_multiple * 12)
    initial_monthly_expense = 1.0 / (asset_multiple * 12)

    # N_SIMULATIONS 本のリターン系列を一括生成（月数 × シミュレーション数）
    returns = rng.normal(
        loc=monthly_return_mean,
        scale=monthly_return_std,
        size=(months, N_SIMULATIONS),
    )

    assets = np.ones(N_SIMULATIONS)   # 全シミュレーションの初期資産 = 1.0
    survived = np.ones(N_SIMULATIONS, dtype=bool)
    monthly_expense = initial_monthly_expense

    for m in range(months):
        # 投資リターン
        assets = assets * (1 + returns[m])
        # 生活費を引く（インフレ考慮）
        assets = assets - monthly_expense
        monthly_expense *= (1 + monthly_inflation)
        # 破綻判定
        survived &= (assets > 0)

    return float(survived.mean())


# -------------------------------------------------------------------
# テーブル生成
# -------------------------------------------------------------------
def main():
    print(f"MC近似テーブル生成開始")
    print(f"  シミュレーション回数: {N_SIMULATIONS:,}")
    print(f"  資産倍率: {ASSET_MULTIPLES}")
    print(f"  FIRE後年数: {FIRE_YEARS}")
    print()

    results = {}
    total = len(ASSET_MULTIPLES) * len(FIRE_YEARS)
    done = 0

    for multiple in ASSET_MULTIPLES:
        results[multiple] = {}
        for years in FIRE_YEARS:
            rate = simulate_success_rate(multiple, years)
            results[multiple][years] = round(rate * 100, 1)
            done += 1
            print(f"  [{done:2d}/{total}] 資産{multiple:2d}倍 × {years}年後: {rate*100:.1f}%")

    # DataFrame に変換
    df = pd.DataFrame(results).T
    df.index.name = "資産倍率（資産÷年間支出）"
    df.columns.name = "FIRE後年数（年）"

    # CSV 出力
    output_path = Path(__file__).parent.parent / "data" / "mc_table.csv"
    output_path.parent.mkdir(exist_ok=True)
    df.to_csv(output_path, encoding="utf-8-sig")
    print(f"\n保存完了: {output_path}")

    # 結果表示
    print("\n=== FIRE成功確率テーブル（%） ===")
    print(f"{'':>12}", end="")
    for y in FIRE_YEARS:
        print(f"  {y}年", end="")
    print()
    for multiple in ASSET_MULTIPLES:
        print(f"資産{multiple:2d}倍: ", end="")
        for y in FIRE_YEARS:
            print(f"  {results[multiple][y]:5.1f}", end="")
        print()

    print("\n=== Googleスプレッドシートへの貼り付け方 ===")
    print("1. data/mc_table.csv を開く")
    print("2. スプレッドシートの「MC成功確率テーブル」シートに貼り付け")
    print("3. VLOOKUP/INDEX-MATCH で参照する")


if __name__ == "__main__":
    main()
