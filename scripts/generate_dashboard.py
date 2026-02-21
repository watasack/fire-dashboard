#!/usr/bin/env python3
"""
FIRE Dashboard Generator

FIRE（Financial Independence, Retire Early）達成・維持のための
可視化ダッシュボードを生成するメインスクリプト

使用方法:
    python scripts/generate_dashboard.py
"""

import sys
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import load_config
from src.data_loader import load_asset_data, load_transaction_data
from src.data_processor import (
    clean_asset_data,
    clean_transaction_data,
    calculate_monthly_cashflow
)
from src.analyzer import (
    analyze_current_status,
    analyze_income_expense_trends,
    analyze_expense_by_category,
    generate_action_items
)
from src.simulator import simulate_future_assets, run_monte_carlo_simulation
from src.visualizer import (
    create_fire_timeline_chart
)
from src.html_generator import generate_dashboard_html


def main():
    """メイン実行関数"""
    print("=" * 60)
    print("FIRE Dashboard Generation Started")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        # 1. 設定読み込み
        print("[1/8] Loading configuration...")
        config = load_config('config.yaml')
        print("[OK] Configuration loaded\n")

        # 2. データ読み込み
        print("[2/8] Loading data files...")
        asset_df = load_asset_data(config)
        transaction_df = load_transaction_data(config)
        print("[OK] Data files loaded\n")

        # 3. データ処理
        print("[3/8] Processing data...")
        asset_df = clean_asset_data(asset_df)
        transaction_df = clean_transaction_data(transaction_df)
        cashflow_df = calculate_monthly_cashflow(transaction_df)
        print("[OK] Data processed\n")

        # 4. 現状分析
        print("[4/9] Analyzing current status...")
        current_status = analyze_current_status(asset_df)
        trends = analyze_income_expense_trends(cashflow_df, transaction_df, config)
        expense_breakdown = analyze_expense_by_category(transaction_df)
        print("[OK] Analysis complete\n")

        # 5. 将来シミュレーション（FIRE達成判定を含む）
        print("[5/9] Running future simulations with FIRE detection...")
        
        # 初期労働収入の設定確認
        monthly_income = trends['monthly_avg_income_forecast']
        initial_labor_income = config['simulation'].get('initial_labor_income')
        if initial_labor_income is not None:
            print(f"  Using fixed initial labor income: JPY{initial_labor_income:,.0f}/month")
            monthly_income = initial_labor_income

        simulations = {}
        for scenario in ['standard']:  # 標準シナリオのみ
            print(f"  Simulating {scenario} scenario...")
            simulations[scenario] = simulate_future_assets(
                current_assets=current_status['net_assets'],
                monthly_income=monthly_income,  # 設定値または予測値を使用
                monthly_expense=trends['monthly_avg_expense'],
                config=config,
                scenario=scenario
            )
        print("[OK] Simulations complete\n")

        # 6. FIRE達成情報を標準シナリオから抽出
        print("[6/9] Extracting FIRE achievement info...")
        fire_achievement = None
        fire_target = None

        if 'standard' in simulations:
            df = simulations['standard']
            # FIRE達成月を探す（シミュレーションで記録されたfire_achievedフラグを使用）
            fire_rows = df[df['fire_achieved'] == True]

            if len(fire_rows) > 0:
                # FIRE達成した最初の月を取得
                fire_row = fire_rows.iloc[0]
                fire_date = fire_row['date']
                month_num = fire_row['fire_month']
                years = int(month_num / 12)
                months = int(month_num % 12)

                fire_achievement = {
                    'achieved': False,
                    'achievement_date': fire_date,
                    'months_to_fire': month_num,
                    'years_to_fire': years,
                    'remaining_months': months,
                    'fire_assets': fire_row['assets']
                }

                # 後方互換性のためfire_target辞書を作成
                fire_target = {
                    'recommended_target': fire_row['assets'],
                    'current_net_assets': current_status['net_assets'],
                    'progress_rate': current_status['net_assets'] / fire_row['assets'],
                    'shortfall': max(0, fire_row['assets'] - current_status['net_assets']),
                    'annual_expense': trends['annual_expense']
                }

                print(f"  FIRE Achievement: {fire_date.strftime('%Y-%m')}")
                print(f"  Time to FIRE: {years} years {months} months")
                print(f"  Assets at FIRE: JPY{fire_row['assets']:,.0f}")
                print(f"  FIRE Target: JPY{fire_target['recommended_target']:,.0f}")
            else:
                print("  FIRE not achievable within simulation period")
                # デフォルト値を設定
                fire_target = {
                    'recommended_target': 0,
                    'current_net_assets': current_status['net_assets'],
                    'progress_rate': 0,
                    'shortfall': 0,
                    'annual_expense': trends['annual_expense']
                }

        print("[OK] FIRE info extracted\n")

        # 7. アクションアイテム生成
        print("[7/9] Generating action items...")
        action_items = generate_action_items(
            fire_target=fire_target,
            fire_achievement=fire_achievement,
            trends=trends,
            expense_breakdown=expense_breakdown,
            config=config
        )
        print(f"  Generated {len(action_items)} action items")
        print("[OK] Action items generated\n")

        # 7.5. モンテカルロシミュレーション（有効な場合のみ）
        mc_results = None
        mc_config = config['simulation'].get('monte_carlo', {})
        if mc_config.get('enabled', False):
            print("[7.5/10] Running Monte Carlo simulation...")
            mc_iterations = mc_config.get('iterations', 1000)
            mc_results = run_monte_carlo_simulation(
                current_cash=current_status['cash_deposits'],
                current_stocks=current_status['investment_trusts'],
                config=config,
                scenario='standard',
                iterations=mc_iterations,
                monthly_income=monthly_income,
                monthly_expense=trends['monthly_avg_expense']
            )
            print("[OK] Monte Carlo simulation complete\n")

        # 8. グラフ生成
        print("[8/10] Creating visualizations...")
        charts = {
            'fire_timeline': create_fire_timeline_chart(
                current_status, fire_target, fire_achievement, simulations, config,
                monte_carlo_results=mc_results  # モンテカルロデータを渡す
            )
        }

        print("[OK] Visualizations created\n")

        # 9. HTML生成
        print("[9/10] Generating HTML dashboard...")
        generate_dashboard_html(
            charts=charts,
            summary_data={
                'current_status': current_status,
                'fire_target': fire_target,
                'fire_achievement': fire_achievement,
                'trends': trends,
                'expense_breakdown': expense_breakdown,
                'monte_carlo': mc_results,
                'update_time': datetime.now()
            },
            action_items=action_items,
            config=config
        )
        print("[OK] HTML dashboard generated\n")

        # 完了サマリー
        print("=" * 60)
        print("[OK] FIRE Dashboard Generation Complete!")
        print("=" * 60)
        print(f"\nOutput: {config['output']['html_file']}")
        print(f"\nKey Metrics:")
        print(f"  Current Net Assets: JPY{current_status['net_assets']:,.0f}")
        print(f"  FIRE Target: JPY{fire_target['recommended_target']:,.0f}")
        print(f"  Progress: {fire_target['progress_rate']:.1%}")
        print(f"  Shortfall: JPY{fire_target['shortfall']:,.0f}")
        if fire_achievement and not fire_achievement.get('achieved'):
            print(f"  Achievement Date: {fire_achievement['achievement_date'].strftime('%Y-%m')}")
            print(f"  Time to FIRE: {fire_achievement['years_to_fire']} years {fire_achievement['remaining_months']} months")
        print(f"  Annual Expense: JPY{trends['annual_expense']:,.0f}")
        print(f"  Savings Rate: {trends['savings_rate']:.1%}")
        print("\nNext steps:")
        print("  1. Open docs/index.html in your browser")
        print("  2. Commit and push to GitHub to update GitHub Pages")
        print("  3. Configure GitHub Pages: Settings → Pages → main/docs\n")

        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print("[ERROR] Error occurred during dashboard generation")
        print("=" * 60)
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
