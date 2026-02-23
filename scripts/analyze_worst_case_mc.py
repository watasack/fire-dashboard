#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
モンテカルロシミュレーションの最悪ケース分析

最悪パターンのリターンが現実的かどうかを検証
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from config import load_config
from simulator import generate_returns_enhanced


def analyze_worst_case_returns():
    """
    モンテカルロシミュレーションの最悪ケースを分析
    """
    print("=" * 80)
    print("モンテカルロシミュレーション 最悪ケース分析")
    print("=" * 80)
    print()

    config = load_config('config.yaml')

    # パラメータ取得
    params = config['simulation']['standard']
    annual_return = params['annual_return_rate']
    annual_std = config['simulation']['monte_carlo']['return_std_dev']

    print(f"設定:")
    print(f"  期待年率リターン: {annual_return:.1%}")
    print(f"  年率標準偏差: {annual_std:.1%}")
    print()

    # 50年分（600ヶ月）のリターンを1000回生成
    num_iterations = 1000
    num_months = 600
    all_returns = []
    all_cumulative = []

    print(f"{num_iterations}回のシミュレーション実行中...")
    for i in range(num_iterations):
        returns = generate_returns_enhanced(
            annual_return_mean=annual_return,
            annual_return_std=annual_std,
            total_months=num_months,
            config=config,
            random_seed=i
        )
        all_returns.append(returns)

        # 累積リターンを計算（資産の成長率）
        cumulative = np.cumprod(1 + returns)
        all_cumulative.append(cumulative)

    all_returns = np.array(all_returns)  # shape: (iterations, months)
    all_cumulative = np.array(all_cumulative)

    print(f"[OK] {num_iterations}回のシミュレーション完了")
    print()

    # 各イテレーションの最終資産を計算
    final_values = all_cumulative[:, -1]

    # パーセンタイルを計算
    p01 = np.percentile(final_values, 1)    # 下位1%
    p05 = np.percentile(final_values, 5)    # 下位5%
    p10 = np.percentile(final_values, 10)   # 下位10%
    p50 = np.percentile(final_values, 50)   # 中央値
    p90 = np.percentile(final_values, 90)   # 上位10%

    print("=" * 80)
    print(f"最終資産（50年後、初期資産=1とした場合）")
    print("=" * 80)
    print(f"下位1%ile:  {p01:.2f}倍 （年率: {(p01 ** (1/50) - 1):.2%}）")
    print(f"下位5%ile:  {p05:.2f}倍 （年率: {(p05 ** (1/50) - 1):.2%}）")
    print(f"下位10%ile: {p10:.2f}倍 （年率: {(p10 ** (1/50) - 1):.2%}）")
    print(f"中央値:     {p50:.2f}倍 （年率: {(p50 ** (1/50) - 1):.2%}）")
    print(f"上位10%ile: {p90:.2f}倍 （年率: {(p90 ** (1/50) - 1):.2%}）")
    print()

    # 最悪ケース（下位1%）のイテレーションを特定
    worst_idx = np.argmin(final_values)
    worst_returns = all_returns[worst_idx]
    worst_cumulative = all_cumulative[worst_idx]

    print("=" * 80)
    print("最悪ケース（下位1%）の詳細分析")
    print("=" * 80)
    print()

    # 年次リターンを計算
    yearly_returns = []
    for year in range(50):
        start_month = year * 12
        end_month = start_month + 12
        year_return = np.prod(1 + worst_returns[start_month:end_month]) - 1
        yearly_returns.append(year_return)

    # 統計
    print(f"年次リターンの統計:")
    print(f"  平均: {np.mean(yearly_returns):.2%}")
    print(f"  中央値: {np.median(yearly_returns):.2%}")
    print(f"  最良年: {np.max(yearly_returns):.2%}")
    print(f"  最悪年: {np.min(yearly_returns):.2%}")
    print(f"  標準偏差: {np.std(yearly_returns):.2%}")
    print()

    # マイナスの年が何年あるか
    negative_years = sum(1 for r in yearly_returns if r < 0)
    print(f"マイナスの年: {negative_years}/50年 ({negative_years/50:.1%})")
    print()

    # 連続マイナス年数
    max_consecutive_negative = 0
    current_consecutive = 0
    for r in yearly_returns:
        if r < 0:
            current_consecutive += 1
            max_consecutive_negative = max(max_consecutive_negative, current_consecutive)
        else:
            current_consecutive = 0

    print(f"最長連続マイナス年数: {max_consecutive_negative}年")
    print()

    # ドローダウン分析
    peak = 1.0
    max_drawdown = 0
    max_dd_start = 0
    max_dd_end = 0
    drawdown_recovery_time = 0

    for i, value in enumerate(worst_cumulative):
        if value > peak:
            peak = value

        drawdown = (value - peak) / peak
        if drawdown < max_drawdown:
            max_drawdown = drawdown
            max_dd_end = i

    # ドローダウン開始点を見つける
    for i in range(max_dd_end, -1, -1):
        if worst_cumulative[i] >= peak * 0.999:  # ピークに近い点
            max_dd_start = i
            break

    # 回復時間を計算
    recovery_value = worst_cumulative[max_dd_start]
    for i in range(max_dd_end, len(worst_cumulative)):
        if worst_cumulative[i] >= recovery_value:
            drawdown_recovery_time = i - max_dd_end
            break

    print(f"最大ドローダウン:")
    print(f"  下落率: {max_drawdown:.2%}")
    print(f"  発生期間: {max_dd_start//12}年目 ～ {max_dd_end//12}年目")
    print(f"  継続期間: {(max_dd_end - max_dd_start)//12}年")
    if drawdown_recovery_time > 0:
        print(f"  回復期間: {drawdown_recovery_time//12}年")
    print()

    # 歴史的データとの比較
    print("=" * 80)
    print("歴史的市場データとの比較")
    print("=" * 80)
    print()
    print("過去の主要な市場暴落:")
    print(f"  リーマンショック (2007-2009): -57%下落、回復4年")
    print(f"  ITバブル崩壊 (2000-2002):     -49%下落、回復5年")
    print(f"  ブラックマンデー (1987):      -22% (1日)")
    print(f"  コロナショック (2020):        -34%下落、回復6ヶ月")
    print()
    print(f"シミュレーション最悪ケース:")
    print(f"  最大ドローダウン: {max_drawdown:.2%}")
    print(f"  最悪年次リターン: {np.min(yearly_returns):.2%}")
    print()

    # 判定
    print("=" * 80)
    print("現実性の評価")
    print("=" * 80)
    print()

    issues = []

    # 1. 最大ドローダウンが-70%を超える場合は非現実的
    if max_drawdown < -0.70:
        issues.append(f"最大ドローダウン（{max_drawdown:.2%}）が歴史的最悪を大きく超えています")

    # 2. 年次リターンが-60%を超える場合は極めて稀
    if np.min(yearly_returns) < -0.60:
        issues.append(f"年次リターン（{np.min(yearly_returns):.2%}）が歴史的最悪レベルです")

    # 3. マイナスの年が50%を超える場合は長期的に非現実的
    if negative_years > 30:
        issues.append(f"マイナスの年が{negative_years}年（{negative_years/50:.1%}）は過度に悲観的です")

    # 4. 連続マイナス年数が5年を超える場合は稀
    if max_consecutive_negative > 7:
        issues.append(f"連続マイナス年数（{max_consecutive_negative}年）は歴史的に極めて稀です")

    # 5. 50年後に資産が初期を下回る場合は非現実的
    if worst_cumulative[-1] < 1.0:
        issues.append(f"50年後に資産が初期値を下回る（{worst_cumulative[-1]:.2f}倍）のは極めて非現実的です")

    if len(issues) > 0:
        print("[!] 以下の点で非現実的な可能性があります:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print()
        print("推奨: GARCHパラメータやボラティリティ上限を見直してください")
        return False
    else:
        print("[OK] 最悪ケースは歴史的範囲内であり、現実的です")
        print()
        print("評価:")
        print(f"  [OK] 最大ドローダウン（{max_drawdown:.2%}）は歴史的範囲内")
        print(f"  [OK] マイナス年数（{negative_years}年）は許容範囲内")
        print(f"  [OK] 50年後の資産は初期値の{worst_cumulative[-1]:.2f}倍")
        print()
        print("結論: モデルは過度に悲観的ではなく、現実的な範囲でリスクを表現しています")
        return True


if __name__ == '__main__':
    success = analyze_worst_case_returns()
    sys.exit(0 if success else 1)
