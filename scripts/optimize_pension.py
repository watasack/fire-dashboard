#!/usr/bin/env python3
"""
年金受給開始年齢の最適化スクリプト

FIRE達成時期と年金受給開始年齢（62〜75歳）を同時に最適化する。
成功率 ≥ 95% を制約として、最も早いFIRE達成月を求める。

使用方法:
    python scripts/optimize_pension.py
"""

import sys
import re
from pathlib import Path
from datetime import datetime

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
)
from src.pension_optimizer import optimize_pension_start_ages


def _update_config_with_result(config_path: str, result: dict) -> None:
    """最適化結果を config.yaml に書き戻す（YAML構造を壊さないよう正規表現で置換）"""
    text = Path(config_path).read_text(encoding='utf-8')

    fire_month = result.get('optimal_fire_month')
    success_rate = result.get('best_success_rate', 0)
    pension_ages = result.get('optimal_ages', {})
    extra_budget = result.get('optimal_extra_monthly_budget', 0)

    if fire_month is None:
        print("  [SKIP] 最適解が見つからなかったため config.yaml は更新しません")
        return

    text = re.sub(
        r'(optimal_fire_month:).*',
        rf'\1 {fire_month}       # 最適化結果: 月{fire_month}、成功率{success_rate:.1%}',
        text,
    )

    text = re.sub(
        r'(optimal_extra_monthly_budget:).*',
        rf'\1 {int(extra_budget)}  # 最適化結果: FIRE後追加月額予算',
        text,
    )

    cash_strategy = result.get('optimal_cash_strategy', {})
    if cash_strategy:
        sm = cash_strategy.get('safety_margin')
        if sm is not None:
            text = re.sub(
                r'(safety_margin:)\s*\d+',
                rf'\1 {int(sm)}',
                text,
            )
        ct = cash_strategy.get('market_crash_threshold')
        if ct is not None:
            text = re.sub(
                r'(market_crash_threshold:)\s*-?[\d.]+',
                rf'\1 {ct}',
                text,
            )

    reduction_rates = result.get('optimal_reduction_rates', {})
    if reduction_rates:
        for level_key in ['level_0_normal', 'level_1_warning', 'level_2_concern', 'level_3_crisis']:
            val = reduction_rates.get(level_key)
            if val is not None:
                text = re.sub(
                    rf'({re.escape(level_key)}:)\s*[\d.]+',
                    rf'\1 {val}',
                    text,
                )

    for person_name, age in pension_ages.items():
        pattern = (
            rf'(- name: {re.escape(person_name)}\s*\n'
            rf'(?:.*\n)*?'
            rf'\s*override_start_age:)\s*\d+'
        )
        replacement = rf'\1 {age}'
        text = re.sub(pattern, replacement, text)

    Path(config_path).write_text(text, encoding='utf-8')
    ages_str = ', '.join(f'{k}={v}歳' for k, v in pension_ages.items())
    budget_str = f", extra_budget={int(extra_budget/10000)}万/月" if extra_budget > 0 else ""
    cs_str = ""
    if cash_strategy:
        sm = cash_strategy.get('safety_margin')
        ct = cash_strategy.get('market_crash_threshold')
        if sm is not None:
            cs_str += f", safety_margin={int(sm/10000)}万"
        if ct is not None:
            cs_str += f", crash_threshold={ct*100:.0f}%"
    rr_str = ""
    if reduction_rates:
        l1 = reduction_rates.get('level_1_warning', 0)
        l2 = reduction_rates.get('level_2_concern', 0)
        l3 = reduction_rates.get('level_3_crisis', 0)
        if l1 > 0 or l2 > 0 or l3 > 0:
            rr_str = f", reduction={l1*100:.0f}/{l2*100:.0f}/{l3*100:.0f}%"
    print(f"  [OK] config.yaml 更新: fire_month={fire_month}, pension={ages_str}{budget_str}{cs_str}{rr_str}")


def main():
    print("=" * 60)
    print("年金受給開始年齢 最適化スクリプト")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        # 1. 設定読み込み
        print("[1/4] Loading configuration...")
        config = load_config('config.yaml')
        print("[OK]\n")

        # 2. データ読み込み・処理
        print("[2/4] Loading and processing data...")
        asset_df = load_asset_data(config)
        transaction_df = load_transaction_data(config)
        asset_df = clean_asset_data(asset_df)
        transaction_df = clean_transaction_data(transaction_df)
        cashflow_df = calculate_monthly_cashflow(transaction_df)
        print("[OK]\n")

        # 3. 現状分析
        print("[3/4] Analyzing current status...")
        current_status = analyze_current_status(asset_df)
        trends = analyze_income_expense_trends(cashflow_df, transaction_df, config)

        monthly_income = trends['monthly_avg_income_forecast']
        initial_labor_income = config['simulation'].get('initial_labor_income')
        if initial_labor_income is not None:
            monthly_income = initial_labor_income

        print(f"  現在の純資産: JPY{current_status['net_assets']:,.0f}")
        print(f"  現金: JPY{current_status['cash_deposits']:,.0f}")
        print(f"  投資信託: JPY{current_status['investment_trusts']:,.0f}")
        print(f"  月次収入: JPY{monthly_income:,.0f}")
        print(f"  月次支出: JPY{trends['monthly_avg_expense']:,.0f}")
        print("[OK]\n")

        # 4. 最適化実行
        print("[4/4] Running pension optimization...")
        result = optimize_pension_start_ages(
            current_cash=current_status['cash_deposits'],
            current_stocks=current_status['investment_trusts'],
            config=config,
            scenario='standard',
            monthly_income=monthly_income,
            monthly_expense=trends['monthly_avg_expense'],
            min_success_rate=0.95,
            top_k=50,
            mc_iterations=500,
            fire_month_search_range=36,
            fire_month_step=6,
            extra_budget_candidates=[0, 50000, 100000, 150000, 200000],
            cash_strategy_candidates=[
                {'safety_margin': 5_000_000, 'market_crash_threshold': -0.20},
                {'safety_margin': 3_000_000, 'market_crash_threshold': -0.20},
                {'safety_margin': 3_000_000, 'market_crash_threshold': -0.30},
                {'safety_margin': 8_000_000, 'market_crash_threshold': -0.15},
                {'safety_margin': 5_000_000, 'market_crash_threshold': -0.30},
            ],
            expense_reduction_candidates=[
                {},
                {'level_1_warning': 0.10, 'level_2_concern': 0.30, 'level_3_crisis': 0.50},
                {'level_1_warning': 0.20, 'level_2_concern': 0.50, 'level_3_crisis': 0.70},
            ],
        )

        if 'error' in result:
            print(f"\n[ERROR] {result['error']}")
            return 1

        # 5. 最適化結果を config.yaml に書き戻す
        optimal = result.get('optimal')
        if optimal is not None:
            print("\n[5/5] Updating config.yaml with optimization result...")
            _update_config_with_result('config.yaml', {
                'optimal_fire_month': optimal['fire_month'],
                'best_success_rate': optimal['success_rate'],
                'optimal_ages': optimal['pension_ages'],
                'optimal_extra_monthly_budget': optimal.get('extra_monthly_budget', 0),
                'optimal_cash_strategy': optimal.get('cash_strategy', {}),
                'optimal_reduction_rates': optimal.get('reduction_rates', {}),
            })

        print("\n[OK] 最適化完了")
        return 0

    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
