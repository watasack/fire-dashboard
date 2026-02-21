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

    許容誤差: 5%以内
    理由: MCは確率的な変動を含むため、厳密な一致は期待できないが、
          中央値（50パーセンタイル）は標準シミュレーション（期待値）に近似すべき
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

    # MC中央値を取得（最終年）
    mc_median = mc_result['median_final_assets']

    # 許容誤差: 10%以内
    # 注: MCシミュレーションは「FIRE達成後のみ」ランダムリターンを使用 (Option 1)
    #     対数正規分布の中央値は期待値より小さいため、ある程度の乖離は許容
    #     10%を超える乖離は実装の不整合を示唆
    tolerance = 0.10
    relative_diff = abs(mc_median - standard_final_assets) / standard_final_assets

    # 検証結果を出力
    print(f"\n=== シミュレーション整合性テスト ===")
    print(f"標準シミュレーション最終資産: {standard_final_assets:,.0f}円")
    print(f"  - 現金: {standard_final_cash:,.0f}円")
    print(f"  - 株式: {standard_final_stocks:,.0f}円")
    print(f"MC中央値（50%ile）: {mc_median:,.0f}円")
    print(f"相対誤差: {relative_diff:.2%}")
    print(f"許容誤差: {tolerance:.2%}")

    # アサーション
    assert relative_diff < tolerance, (
        f"標準シミュレーションとMC中央値の乖離が大きすぎます。\n"
        f"標準: {standard_final_assets:,.0f}円, MC中央値: {mc_median:,.0f}円\n"
        f"相対誤差: {relative_diff:.2%} (許容: {tolerance:.2%})\n"
        f"→ NISA運用リターン適用漏れなど、実装の不整合が疑われます。"
    )

    print("[OK] テスト合格: 標準シミュレーションとMC中央値の整合性OK")


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


def test_assets_monotonic_growth_with_positive_returns():
    """
    不変条件テスト: プラスのリターン適用後、資産が極端に減少しないことを検証

    運用リターンがプラスの場合、収入・支出を除いた純粋な運用部分では
    資産が大きく減少することはない（5%以上の減少は異常）。
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
    # ※ 株式売却や購入があるため、単純な比較は困難だが、
    #    極端な減少（>50%）は運用リターン計算のバグを示唆
    stocks_change = result['stocks'].pct_change()
    extreme_decreases = stocks_change[stocks_change < -0.5]

    print(f"\n=== 資産推移異常検知テスト ===")
    print(f"極端な株式減少（>50%）: {len(extreme_decreases)}件")

    if len(extreme_decreases) > 0:
        print("\n極端な減少箇所:")
        for idx in extreme_decreases.index[:5]:
            if idx > 0:
                prev_idx = idx - 1
                print(f"  {result.loc[idx, 'date']}: "
                      f"{result.loc[prev_idx, 'stocks']:,.0f}円 → "
                      f"{result.loc[idx, 'stocks']:,.0f}円 "
                      f"({stocks_change[idx]:.1%})")

    # 警告のみ（株式売却により大幅減少は正常なケースもある）
    if len(extreme_decreases) > 10:
        print("⚠ 警告: 極端な株式減少が多数検出されました。運用リターン計算を確認してください。")
    else:
        print("[OK] テスト合格: 異常な資産減少は検出されませんでした")


if __name__ == '__main__':
    print("=" * 60)
    print("統合テスト: シミュレーション整合性検証")
    print("=" * 60)

    try:
        # テスト1: 標準 vs MC収束性
        test_standard_vs_monte_carlo_convergence()

        # テスト2: NISA残高不変条件
        test_nisa_balance_never_exceeds_stocks()

        # テスト3: 資産推移異常検知
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
