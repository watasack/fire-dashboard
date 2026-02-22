#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
動的支出削減の効果分析

暴落時の自動削減あり/なしでFIRE成功確率を比較し、効果を定量化する
"""

import sys
from pathlib import Path
import yaml
import copy
import numpy as np

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.simulator import run_monte_carlo_simulation


def load_config():
    """設定ファイルを読み込む"""
    config_path = project_root / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def run_comparison_analysis(iterations=1000):
    """
    動的削減ありとなしでMCシミュレーションを比較

    Args:
        iterations: MCシミュレーションの反復回数

    Returns:
        (result_no_reduction, result_with_reduction): 両方の結果辞書
    """
    print("=" * 80)
    print("動的支出削減の効果分析")
    print("=" * 80)
    print(f"\nシミュレーション回数: {iterations}")
    print("\n設定:")
    print("  - 拡張モデル（GARCH + 非対称多期間平均回帰）を使用")
    print("  - 暴落時の裁量的支出削減あり/なしを比較")
    print()

    config = load_config()

    # 初期資産・収入・支出を取得（configから）
    # 注: 簡略化のため、資産5000万円からスタートと仮定
    # 実際の分析では、CSVデータから取得する方が正確
    current_assets = 50_000_000  # 5000万円

    # 初期収入・支出を取得
    initial_labor_income = config['simulation'].get('initial_labor_income', 0)
    initial_expense = config['simulation'].get('initial_annual_expense', 0) / 12

    print(f"初期状態:")
    print(f"  総資産: {current_assets:,.0f}円")
    print(f"  月次収入: {initial_labor_income:,.0f}円")
    print(f"  月次支出: {initial_expense:,.0f}円")
    print()

    # ケース1: 動的削減なし
    print("-" * 80)
    print("ケース1: 動的削減なし（ベースライン）")
    print("-" * 80)

    config_no_reduction = copy.deepcopy(config)
    config_no_reduction['fire']['dynamic_expense_reduction']['enabled'] = False

    result_no_reduction = run_monte_carlo_simulation(
        current_cash=0.0,
        current_stocks=current_assets,
        monthly_income=initial_labor_income,
        monthly_expense=initial_expense,
        config=config_no_reduction,
        scenario='standard',
        iterations=iterations
    )

    # ケース2: 動的削減あり
    print("\n")
    print("-" * 80)
    print("ケース2: 動的削減あり（暴落対応プロトコル）")
    print("-" * 80)

    config_with_reduction = copy.deepcopy(config)
    config_with_reduction['fire']['dynamic_expense_reduction']['enabled'] = True

    result_with_reduction = run_monte_carlo_simulation(
        current_cash=0.0,
        current_stocks=current_assets,
        monthly_income=initial_labor_income,
        monthly_expense=initial_expense,
        config=config_with_reduction,
        scenario='standard',
        iterations=iterations
    )

    return result_no_reduction, result_with_reduction


def analyze_results(result_no_reduction, result_with_reduction):
    """
    結果を分析して効果を定量化

    Args:
        result_no_reduction: 削減なしの結果
        result_with_reduction: 削減ありの結果
    """
    print("\n")
    print("=" * 80)
    print("効果分析")
    print("=" * 80)

    # 成功率
    success_no_reduction = result_no_reduction['success_rate']
    success_with_reduction = result_with_reduction['success_rate']
    success_improvement = success_with_reduction - success_no_reduction

    # 中央値
    median_no_reduction = result_no_reduction['median_final_assets']
    median_with_reduction = result_with_reduction['median_final_assets']
    median_improvement = ((median_with_reduction / median_no_reduction) - 1) * 100 if median_no_reduction > 0 else 0

    # P10（下位10%）
    p10_no_reduction = result_no_reduction['percentile_10']
    p10_with_reduction = result_with_reduction['percentile_10']

    # P90（上位10%）
    p90_no_reduction = result_no_reduction['percentile_90']
    p90_with_reduction = result_with_reduction['percentile_90']

    # 破産率（P16=0の割合を推定）
    bankruptcy_no_reduction = 1.0 - success_no_reduction
    bankruptcy_with_reduction = 1.0 - success_with_reduction
    bankruptcy_reduction = bankruptcy_no_reduction - bankruptcy_with_reduction

    print("\n【成功率（資産 > 0）】")
    print(f"  削減なし: {success_no_reduction*100:.1f}%")
    print(f"  削減あり: {success_with_reduction*100:.1f}%")
    print(f"  改善:     +{success_improvement*100:.1f}ポイント")

    print("\n【破産率（資産 = 0）】")
    print(f"  削減なし: {bankruptcy_no_reduction*100:.1f}%")
    print(f"  削減あり: {bankruptcy_with_reduction*100:.1f}%")
    print(f"  改善:     -{bankruptcy_reduction*100:.1f}ポイント")

    print("\n【最終資産の中央値】")
    print(f"  削減なし: {median_no_reduction:,.0f}円")
    print(f"  削減あり: {median_with_reduction:,.0f}円")
    print(f"  改善:     {median_improvement:+.1f}%")

    print("\n【最終資産の下位10%（P10）】")
    print(f"  削減なし: {p10_no_reduction:,.0f}円")
    print(f"  削減あり: {p10_with_reduction:,.0f}円")
    if p10_no_reduction > 0:
        p10_improvement = ((p10_with_reduction / p10_no_reduction) - 1) * 100
        print(f"  改善:     {p10_improvement:+.1f}%")
    else:
        print(f"  改善:     破産回避（0円 → {p10_with_reduction:,.0f}円）")

    print("\n【最終資産の上位10%（P90）】")
    print(f"  削減なし: {p90_no_reduction:,.0f}円")
    print(f"  削減あり: {p90_with_reduction:,.0f}円")
    if p90_no_reduction > 0:
        p90_improvement = ((p90_with_reduction / p90_no_reduction) - 1) * 100
        print(f"  改善:     {p90_improvement:+.1f}%")

    # 分布の変化
    range_no_reduction = p90_no_reduction - p10_no_reduction
    range_with_reduction = p90_with_reduction - p10_with_reduction

    print("\n【資産分布の範囲（P90 - P10）】")
    print(f"  削減なし: {range_no_reduction:,.0f}円")
    print(f"  削減あり: {range_with_reduction:,.0f}円")
    if range_no_reduction > 0:
        range_change = ((range_with_reduction / range_no_reduction) - 1) * 100
        print(f"  変化:     {range_change:+.1f}%")

    # 効果の評価
    print("\n" + "=" * 80)
    print("総合評価")
    print("=" * 80)

    if success_improvement > 0.10:  # 10ポイント以上の改善
        print("[OK] 大幅な改善: 成功率が10ポイント以上向上")
    elif success_improvement > 0.05:  # 5ポイント以上の改善
        print("[OK] 中程度の改善: 成功率が5ポイント以上向上")
    elif success_improvement > 0:
        print("[OK] 小幅な改善: 成功率がわずかに向上")
    else:
        print("[NG] 効果なし: 成功率に改善が見られない")

    if median_improvement > 10:
        print(f"[OK] 中央値の大幅改善: {median_improvement:.1f}%上昇")
    elif median_improvement > 5:
        print(f"[OK] 中央値の改善: {median_improvement:.1f}%上昇")
    elif median_improvement > 0:
        print(f"[OK] 中央値のわずかな改善: {median_improvement:.1f}%上昇")

    if p10_no_reduction == 0 and p10_with_reduction > 0:
        print("[OK] 重要: 最悪シナリオ（P10）で破産を回避")

    print("\n動的支出削減は、暴落時に裁量的支出を自動的に削減することで、")
    print("FIRE成功確率を改善します。特に、最悪シナリオでの破産リスクを")
    print("低減する効果が期待できます。")
    print()


def main():
    """メイン処理"""
    # 分析実行
    result_no_reduction, result_with_reduction = run_comparison_analysis(iterations=1000)

    # 結果を分析
    analyze_results(result_no_reduction, result_with_reduction)

    print("\n分析完了！")


if __name__ == '__main__':
    main()
