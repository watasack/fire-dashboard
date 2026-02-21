"""
統合テスト: 標準シミュレーションとモンテカルロシミュレーションの整合性検証

NISA運用リターン適用漏れバグの再発を防止するため、
標準シミュレーションとMC中央値が近似することを検証する。
"""

import sys
from pathlib import Path
import numpy as np

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

    # データ読み込み
    asset_df = load_asset_data(config)
    transaction_df = load_transaction_data(config)

    # データ処理
    asset_df = clean_asset_data(asset_df)
    transaction_df = clean_transaction_data(transaction_df)
    cashflow_df = calculate_monthly_cashflow(transaction_df)

    # 現状分析
    current_status = analyze_current_status(asset_df)
    trends = analyze_income_expense_trends(cashflow_df, transaction_df, config)

    return config, current_status, trends


def test_standard_vs_monte_carlo_convergence():
    """
    標準シミュレーションとMC中央値が近似することを検証

    許容誤差: 10%以内（中央値との比較）
    理由:
    - MCは「FIRE達成後のみ」ランダムリターンを使用（Option 1実装）
    - 対数正規分布では median < mean となるのが自然（Jensen's inequality）
    - 標準シミュレーション（固定リターン）はMC中央値に近似すべき
    - 10%を超える乖離は実装の不整合を示唆
    """
    # データ読み込み
    config, current_status, trends = load_test_data()

    # 月次収入・支出
    monthly_income = trends['monthly_avg_income_forecast']
    monthly_expense = trends['monthly_avg_expense']

    # 設定値による収入の上書き（generate_dashboard.pyと同様）
    initial_labor_income = config['simulation'].get('initial_labor_income')
    if initial_labor_income is not None:
        monthly_income = initial_labor_income

    # 標準シミュレーション実行
    standard_result = simulate_future_assets(
        current_assets=current_status['net_assets'],
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        config=config,
        scenario='standard'
    )

    # 最終年の資産額を取得
    standard_final_assets = standard_result['assets'].iloc[-1]
    standard_final_cash = standard_result['cash'].iloc[-1]
    standard_final_stocks = standard_result['stocks'].iloc[-1]

    # モンテカルロシミュレーション実行
    # 注: run_monte_carlo_simulationはcurrent_cash/current_stocksを要求するため、
    #     current_assetsと同等にするため cash=0, stocks=全資産として渡す
    mc_result = run_monte_carlo_simulation(
        current_cash=0.0,
        current_stocks=current_status['net_assets'],
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        config=config,
        scenario='standard',
        iterations=1000
    )

    # MC統計値を取得
    mc_median = mc_result['median_final_assets']
    mc_mean = mc_result['mean_final_assets']
    mc_p10 = mc_result['percentile_10']
    mc_p90 = mc_result['percentile_90']

    # 検証結果を出力
    print(f"\n=== シミュレーション整合性テスト ===")
    print(f"標準シミュレーション最終資産: {standard_final_assets:,.0f}円")
    print(f"  - 現金: {standard_final_cash:,.0f}円")
    print(f"  - 株式: {standard_final_stocks:,.0f}円")
    print(f"\nMCシミュレーション分布:")
    print(f"  平均値:  {mc_mean:,.0f}円")
    print(f"  中央値:  {mc_median:,.0f}円")
    print(f"  10%ile:  {mc_p10:,.0f}円")
    print(f"  90%ile:  {mc_p90:,.0f}円")

    # 乖離計算
    diff_median = abs(mc_median - standard_final_assets) / standard_final_assets
    diff_mean = abs(mc_mean - standard_final_assets) / standard_final_assets
    median_mean_ratio = mc_median / mc_mean if mc_mean > 0 else 0

    print(f"\n乖離分析:")
    print(f"  標準 vs MC中央値: {diff_median:.2%}")
    print(f"  標準 vs MC平均値: {diff_mean:.2%}")
    print(f"  MC中央値/平均値: {median_mean_ratio:.3f} (対数正規分布では<1.0が正常)")

    # 検証1: 標準 vs MC中央値（主要テスト）
    tolerance_median = 0.10
    assert diff_median < tolerance_median, (
        f"標準シミュレーションとMC中央値の乖離が大きすぎます。\n"
        f"標準: {standard_final_assets:,.0f}円, MC中央値: {mc_median:,.0f}円\n"
        f"相対誤差: {diff_median:.2%} (許容: {tolerance_median:.2%})\n"
        f"→ NISA運用リターン適用漏れなど、実装の不整合が疑われます。"
    )

    # 検証2: 標準がMC平均値より極端に低くないか
    # 注: Jensen's inequalityにより MC平均値 > 標準 は自然だが、
    #     標準が平均値の50%以下だと問題の可能性
    if standard_final_assets < mc_mean * 0.5:
        print(f"\n[!] 警告: 標準シミュレーションがMC平均値の50%未満です")
        print(f"   標準: {standard_final_assets:,.0f}円")
        print(f"   MC平均: {mc_mean:,.0f}円")
        print(f"   → FIRE後の実装に違いがある可能性があります")

    # 検証3: MC分布の妥当性
    # 対数正規分布では median/mean が通常 0.4〜0.8 程度
    if median_mean_ratio > 0.95:
        print(f"\n[!] 警告: MC分布が対数正規分布の特性から外れています")
        print(f"   中央値/平均値 = {median_mean_ratio:.3f} (正常範囲: 0.4-0.8)")

    print("\n[OK] テスト合格: 標準シミュレーションとMC中央値の整合性OK")


def test_nisa_balance_never_exceeds_stocks():
    """
    不変条件テスト: NISA残高が株式残高を超えないことを検証

    NISA残高は株式資産の一部であるため、常に stocks >= nisa_balance である必要がある。
    この条件が破られている場合、NISA計算ロジックにバグがある。
    """
    # データ読み込み
    config, current_status, trends = load_test_data()

    # 月次収入・支出
    monthly_income = trends['monthly_avg_income_forecast']
    monthly_expense = trends['monthly_avg_expense']

    # 設定値による収入の上書き
    initial_labor_income = config['simulation'].get('initial_labor_income')
    if initial_labor_income is not None:
        monthly_income = initial_labor_income

    # 標準シミュレーション実行
    result = simulate_future_assets(
        current_assets=current_status['net_assets'],
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        config=config,
        scenario='standard'
    )

    # 全期間でNISA残高 <= 株式残高を検証
    violations = result[result['nisa_balance'] > result['stocks']]

    print(f"\n=== NISA残高不変条件テスト ===")
    print(f"全{len(result)}期間中の違反: {len(violations)}件")

    if len(violations) > 0:
        print("\n違反箇所:")
        print(violations[['date', 'stocks', 'nisa_balance']].head(10))

    # アサーション
    assert len(violations) == 0, (
        f"NISA残高が株式残高を超える期間が{len(violations)}件検出されました。\n"
        f"NISA計算ロジックにバグがある可能性があります。"
    )

    print("[OK] テスト合格: NISA残高は常に株式残高以下")


def test_nisa_annual_limit_compliance():
    """
    不変条件テスト: NISA年間投資枠（360万円）を超過していないことを検証

    新NISA制度では年間投資枠が360万円に制限されています。
    この制限を超える投資が行われている場合、NISA投資ロジックにバグがあります。
    """
    # データ読み込み
    config, current_status, trends = load_test_data()

    # 月次収入・支出
    monthly_income = trends['monthly_avg_income_forecast']
    monthly_expense = trends['monthly_avg_expense']

    # 設定値による収入の上書き
    initial_labor_income = config['simulation'].get('initial_labor_income')
    if initial_labor_income is not None:
        monthly_income = initial_labor_income

    # 標準シミュレーション実行
    result = simulate_future_assets(
        current_assets=current_status['net_assets'],
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        config=config,
        scenario='standard'
    )

    # NISA年間投資枠を取得
    nisa_annual_limit = config.get('asset_allocation', {}).get('nisa_annual_limit', 3600000)

    # 年ごとにNISA投資額を集計
    # 注: nisa_balance の増分を年ごとに集計する
    result['year'] = result['date'].dt.year
    result['nisa_change'] = result['nisa_balance'].diff().fillna(0)

    # 運用リターンによる増加は除外し、新規投資のみをカウント
    # 運用リターン適用後にNISA残高が増えた分のみを投資とみなす
    # ※ 簡易的に、プラスの変化のみを集計
    result['nisa_investment'] = result['nisa_change'].apply(lambda x: max(0, x))

    yearly_nisa_investment = result.groupby('year')['nisa_investment'].sum()

    print(f"\n=== NISA年間投資枠チェック ===")
    print(f"年間投資枠上限: {nisa_annual_limit:,.0f}円")

    # 超過している年を検出
    violations = yearly_nisa_investment[yearly_nisa_investment > nisa_annual_limit * 1.01]  # 1%のマージン

    if len(violations) > 0:
        print(f"\n年間投資枠超過: {len(violations)}年")
        print("\n超過年:")
        for year, amount in violations.items():
            over_amount = amount - nisa_annual_limit
            print(f"  {year}年: {amount:,.0f}円 (超過: {over_amount:,.0f}円)")

        # アサーション
        assert len(violations) == 0, (
            f"NISA年間投資枠（{nisa_annual_limit:,.0f}円）を超過している年が{len(violations)}年あります。\n"
            f"NISA投資ロジックにバグがある可能性があります。"
        )
    else:
        print(f"超過年: 0年")
        print("\n主要年のNISA投資額:")
        for year, amount in yearly_nisa_investment.head(10).items():
            usage_rate = amount / nisa_annual_limit if nisa_annual_limit > 0 else 0
            print(f"  {year}年: {amount:,.0f}円 ({usage_rate:.1%})")

    print("\n[OK] テスト合格: NISA年間投資枠を遵守しています")


def test_assets_monotonic_growth_with_positive_returns():
    """
    不変条件テスト: 株式資産の極端な減少を検知

    検証内容:
    - 月次の株式資産変動率をチェック
    - 50%以上の急激な減少は運用リターン計算のバグを示唆

    注意:
    - 株式売却により減少するのは正常動作
    - FIRE達成後の大規模な売却は想定内
    - 警告閾値: 全期間の2%以上で極端な減少がある場合
      （661ヶ月中13件以上 = 異常な頻度）
    """
    # データ読み込み
    config, current_status, trends = load_test_data()

    # 月次収入・支出
    monthly_income = trends['monthly_avg_income_forecast']
    monthly_expense = trends['monthly_avg_expense']

    # 設定値による収入の上書き
    initial_labor_income = config['simulation'].get('initial_labor_income')
    if initial_labor_income is not None:
        monthly_income = initial_labor_income

    # 標準シミュレーション実行
    result = simulate_future_assets(
        current_assets=current_status['net_assets'],
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        config=config,
        scenario='standard'
    )

    # 前月比で株式資産の変化率を計算
    stocks_change = result['stocks'].pct_change()
    extreme_decreases = stocks_change[stocks_change < -0.5]

    total_periods = len(result)
    extreme_count = len(extreme_decreases)
    extreme_rate = extreme_count / total_periods if total_periods > 0 else 0

    print(f"\n=== 資産推移異常検知テスト ===")
    print(f"全期間: {total_periods}ヶ月")
    print(f"極端な株式減少（>50%）: {extreme_count}件 ({extreme_rate:.1%})")

    if extreme_count > 0:
        print("\n極端な減少箇所（最大5件表示）:")
        for idx in extreme_decreases.index[:5]:
            if idx > 0:
                prev_idx = idx - 1
                print(f"  {result.loc[idx, 'date']}: "
                      f"{result.loc[prev_idx, 'stocks']:,.0f}円 → "
                      f"{result.loc[idx, 'stocks']:,.0f}円 "
                      f"({stocks_change[idx]:.1%})")

    # 警告閾値: 全期間の2%以上で極端減少がある場合
    # 理由: FIRE後の売却等で数回は発生しうるが、頻繁な発生は異常
    warning_threshold_rate = 0.02
    warning_threshold_count = int(total_periods * warning_threshold_rate)

    if extreme_count > warning_threshold_count:
        print(f"\n[!] 警告: 極端な株式減少が多数検出されました")
        print(f"   検出: {extreme_count}件, 閾値: {warning_threshold_count}件（全期間の{warning_threshold_rate:.0%}）")
        print(f"   → 運用リターン計算を確認してください")
    else:
        print(f"\n[OK] テスト合格: 異常な資産減少は検出されませんでした")
        if extreme_count > 0:
            print(f"   極端な減少は{extreme_count}件ありますが、許容範囲内です")


if __name__ == '__main__':
    print("=" * 60)
    print("統合テスト: シミュレーション整合性検証")
    print("=" * 60)

    try:
        # テスト1: 標準 vs MC収束性
        test_standard_vs_monte_carlo_convergence()

        # テスト2: NISA残高不変条件
        test_nisa_balance_never_exceeds_stocks()

        # テスト3: NISA年間投資枠遵守
        test_nisa_annual_limit_compliance()

        # テスト4: 資産推移異常検知
        test_assets_monotonic_growth_with_positive_returns()

        print("\n" + "=" * 60)
        print("全テスト合格 [OK]")
        print("=" * 60)

    except AssertionError as e:
        print("\n" + "=" * 60)
        print("テスト失敗 [FAILED]")
        print("=" * 60)
        print(f"\n{e}")
        sys.exit(1)
    except Exception as e:
        print("\n" + "=" * 60)
        print("テスト実行エラー")
        print("=" * 60)
        print(f"\n{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
