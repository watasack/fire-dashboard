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
    calculate_monthly_cashflow,
    calculate_category_breakdown
)
from src.analyzer import (
    analyze_current_status,
    analyze_income_expense_trends,
    analyze_expense_by_category
)
from src.simulator import simulate_future_assets
from src.fire_calculator import calculate_fire_target
from src.visualizer import (
    create_asset_timeline_chart,
    create_fire_progress_chart,
    create_expense_breakdown_chart,
    create_future_simulation_chart
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
        print("[4/8] Analyzing current status...")
        current_status = analyze_current_status(asset_df)
        trends = analyze_income_expense_trends(cashflow_df)
        expense_breakdown = analyze_expense_by_category(transaction_df)
        print("[OK] Analysis complete\n")

        # 5. FIRE目標額計算
        print("[5/8] Calculating FIRE target...")
        fire_target = calculate_fire_target(
            annual_expense=trends['annual_expense'],
            current_net_assets=current_status['net_assets'],
            config=config
        )
        print("[OK] FIRE target calculated\n")

        # 6. 将来シミュレーション
        print("[6/8] Running future simulations...")
        simulations = {}
        for scenario in ['optimistic', 'standard', 'pessimistic']:
            print(f"  Simulating {scenario} scenario...")
            simulations[scenario] = simulate_future_assets(
                current_assets=current_status['net_assets'],
                monthly_income=trends['monthly_avg_income'],
                monthly_expense=trends['monthly_avg_expense'],
                config=config,
                scenario=scenario
            )
        print("[OK] Simulations complete\n")

        # 7. グラフ生成
        print("[7/8] Creating visualizations...")
        charts = {
            'asset_timeline': create_asset_timeline_chart(asset_df, config),
            'fire_progress': create_fire_progress_chart(
                current_status, fire_target, config
            ),
            'expense_breakdown': create_expense_breakdown_chart(
                expense_breakdown, config
            ),
            'future_simulation': create_future_simulation_chart(
                simulations, fire_target, config
            )
        }
        print("[OK] Visualizations created\n")

        # 8. HTML生成
        print("[8/8] Generating HTML dashboard...")
        generate_dashboard_html(
            charts=charts,
            summary_data={
                'current_status': current_status,
                'fire_target': fire_target,
                'trends': trends,
                'update_time': datetime.now()
            },
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
