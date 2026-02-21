"""
MCシミュレーションと標準シミュレーションの詳細比較テスト

9.55%の乖離の原因を特定するための診断テスト
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from config import load_config
from data_loader import load_asset_data, load_transaction_data
from data_processor import clean_asset_data, clean_transaction_data, calculate_monthly_cashflow
from analyzer import analyze_current_status, analyze_income_expense_trends
from simulator import simulate_future_assets, run_monte_carlo_simulation


def load_test_data():
    """テストデータを読み込む"""
    config = load_config('config.yaml')
    asset_df = load_asset_data(config)
    transaction_df = load_transaction_data(config)
    asset_df = clean_asset_data(asset_df)
    transaction_df = clean_transaction_data(transaction_df)
    cashflow_df = calculate_monthly_cashflow(transaction_df)
    current_status = analyze_current_status(asset_df)
    trends = analyze_income_expense_trends(cashflow_df, transaction_df, config)
    return config, current_status, trends


def diagnose_mc_vs_standard_divergence():
    """
    標準シミュレーションとMCシミュレーションの乖離を詳細診断
    """
    print("=" * 70)
    print("MC vs 標準シミュレーション 詳細比較診断")
    print("=" * 70)

    config, current_status, trends = load_test_data()
    monthly_income = trends['monthly_avg_income_forecast']
    monthly_expense = trends['monthly_avg_expense']
    initial_labor_income = config['simulation'].get('initial_labor_income')
    if initial_labor_income is not None:
        monthly_income = initial_labor_income

    # 標準シミュレーション実行
    print("\n[1/3] 標準シミュレーション実行中...")
    standard_result = simulate_future_assets(
        current_assets=current_status['net_assets'],
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        config=config,
        scenario='standard'
    )

    # MCシミュレーション実行
    print("\n[2/3] モンテカルロシミュレーション実行中...")
    mc_result = run_monte_carlo_simulation(
        current_cash=0.0,
        current_stocks=current_status['net_assets'],
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        config=config,
        scenario='standard',
        iterations=1000
    )

    print("\n[3/3] 乖離分析中...")

    # FIRE達成時点の比較
    fire_rows = standard_result[standard_result['fire_achieved'] == True]
    if len(fire_rows) > 0:
        fire_month = fire_rows.iloc[0]['fire_month']
        fire_assets_standard = fire_rows.iloc[0]['assets']
        fire_cash_standard = fire_rows.iloc[0]['cash']
        fire_stocks_standard = fire_rows.iloc[0]['stocks']
        fire_nisa_standard = fire_rows.iloc[0]['nisa_balance']

        print("\n" + "=" * 70)
        print("FIRE達成時点の比較")
        print("=" * 70)
        print(f"FIRE達成月: {int(fire_month)}ヶ月目 ({fire_month/12:.1f}年)")
        print(f"標準シミュレーション:")
        print(f"  総資産: {fire_assets_standard:,.0f}円")
        print(f"    - 現金: {fire_cash_standard:,.0f}円")
        print(f"    - 株式: {fire_stocks_standard:,.0f}円")
        print(f"    - NISA: {fire_nisa_standard:,.0f}円")
        print(f"\nMCシミュレーション:")
        print(f"  FIRE達成月: {mc_result['fire_month']}ヶ月目 ({mc_result['fire_month']/12:.1f}年)")

        if abs(fire_month - mc_result['fire_month']) > 0.5:
            print(f"\n[!] 警告: FIRE達成月が一致しません！")
            print(f"   標準: {fire_month}, MC: {mc_result['fire_month']}")
        else:
            print(f"[OK] FIRE達成月は一致しています")

    # 最終資産の比較
    standard_final_assets = standard_result['assets'].iloc[-1]
    standard_final_cash = standard_result['cash'].iloc[-1]
    standard_final_stocks = standard_result['stocks'].iloc[-1]
    standard_final_nisa = standard_result['nisa_balance'].iloc[-1]

    mc_median = mc_result['median_final_assets']
    mc_mean = mc_result['mean_final_assets']
    mc_p10 = mc_result['percentile_10']
    mc_p90 = mc_result['percentile_90']

    print("\n" + "=" * 70)
    print("最終資産（90歳時点）の比較")
    print("=" * 70)
    print(f"標準シミュレーション:")
    print(f"  総資産: {standard_final_assets:,.0f}円")
    print(f"    - 現金: {standard_final_cash:,.0f}円")
    print(f"    - 株式: {standard_final_stocks:,.0f}円")
    print(f"    - NISA: {standard_final_nisa:,.0f}円")
    print(f"\nMCシミュレーション分布:")
    print(f"  平均値:   {mc_mean:,.0f}円")
    print(f"  中央値:   {mc_median:,.0f}円")
    print(f"  10%ile:   {mc_p10:,.0f}円")
    print(f"  90%ile:   {mc_p90:,.0f}円")
    print(f"  成功率:   {mc_result['success_rate']*100:.1f}%")

    # 乖離分析
    diff_vs_median = standard_final_assets - mc_median
    diff_vs_mean = standard_final_assets - mc_mean
    rel_diff_median = abs(diff_vs_median) / standard_final_assets
    rel_diff_mean = abs(diff_vs_mean) / standard_final_assets

    print("\n" + "=" * 70)
    print("乖離分析")
    print("=" * 70)
    print(f"標準 vs MC中央値:")
    print(f"  絶対差: {diff_vs_median:+,.0f}円")
    print(f"  相対差: {rel_diff_median:.2%}")
    print(f"\n標準 vs MC平均値:")
    print(f"  絶対差: {diff_vs_mean:+,.0f}円")
    print(f"  相対差: {rel_diff_mean:.2%}")

    # 対数正規分布の特性分析
    median_mean_ratio = mc_median / mc_mean
    print(f"\nMC分布の特性:")
    print(f"  中央値/平均値: {median_mean_ratio:.3f}")
    print(f"  (対数正規分布では通常 < 1.0)")

    # 判定
    print("\n" + "=" * 70)
    print("診断結果")
    print("=" * 70)

    issues = []

    # 1. FIRE達成時点のチェック
    if len(fire_rows) > 0 and abs(fire_month - mc_result['fire_month']) > 0.5:
        issues.append("FIRE達成月が不一致：実装の違いが疑われます")

    # 2. 中央値 vs 平均値のチェック
    if median_mean_ratio > 0.95:
        issues.append(f"MC分布が対数正規からずれています（中央値/平均値={median_mean_ratio:.3f}）")

    # 3. 標準 vs MC平均値のチェック
    if rel_diff_mean > 0.05:
        issues.append(f"標準とMC平均値の乖離が大きい（{rel_diff_mean:.2%}）：FIRE後の実装の違いが疑われます")

    # 4. 標準 vs MC中央値のチェック
    if rel_diff_median > 0.10:
        issues.append(f"標準とMC中央値の乖離が非常に大きい（{rel_diff_median:.2%}）")
    elif rel_diff_median > 0.05:
        print("[!] 注意: 標準とMC中央値に中程度の乖離があります")
        print(f"   対数正規分布の特性により、中央値は期待値より低くなります")
        print(f"   現在の乖離（{rel_diff_median:.2%}）は許容範囲内の可能性があります")

    if len(issues) > 0:
        print("\n[!!] 検出された問題:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        return False
    else:
        print("\n[OK] 重大な問題は検出されませんでした")
        print("  標準とMCの乖離は対数正規分布の統計的特性の範囲内です")
        return True


if __name__ == '__main__':
    success = diagnose_mc_vs_standard_divergence()
    sys.exit(0 if success else 1)
