#!/usr/bin/env python3
"""
年金受給開始年齢の最適化スクリプト

FIRE達成時期と年金受給開始年齢（62〜75歳）を同時に最適化する。
決定論的ベースラインの最終資産 >= 安全マージンを制約として、最も早いFIRE達成月を求める。

使用方法:
    python scripts/optimize_pension.py
"""

import sys
import re
import json
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
    final_assets = result.get('final_assets', 0)
    pension_ages = result.get('optimal_ages', {})
    extra_budget = result.get('optimal_extra_monthly_budget', 0)

    if fire_month is None:
        print("  [SKIP] 最適解が見つからなかったため config.yaml は更新しません")
        return

    text = re.sub(
        r'(optimal_fire_month:).*',
        rf'\1 {fire_month}       # 最適化結果: 月{fire_month}、最終資産{final_assets/10000:.0f}万円',
        text,
    )

    text = re.sub(
        r'(optimal_extra_monthly_budget:).*',
        rf'\1 {int(extra_budget)}  # 最適化結果: FIRE後追加月額予算',
        text,
    )

    cash_strategy = result.get('optimal_cash_strategy', {})
    if cash_strategy:
        tcr = cash_strategy.get('target_cash_reserve')
        if tcr is not None:
            text = re.sub(
                r'(target_cash_reserve:)\s*\d+',
                rf'\1 {int(tcr)}',
                text,
            )
        ct = cash_strategy.get('market_crash_threshold')
        if ct is not None:
            text = re.sub(
                r'(market_crash_threshold:)\s*-?[\d.]+',
                rf'\1 {ct}',
                text,
            )

    pre_fire_strategy = result.get('optimal_pre_fire_strategy', {})
    if pre_fire_strategy:
        pf_mappings = {
            'cash_buffer_months': (r'(cash_buffer_months:)\s*\d+', lambda v: str(int(v))),
            'auto_invest_threshold': (r'(auto_invest_threshold:)\s*[\d.]+', lambda v: str(v)),
            'min_cash_balance': (r'(min_cash_balance:)\s*\d+', lambda v: str(int(v))),
        }
        for key, (pattern, fmt) in pf_mappings.items():
            val = pre_fire_strategy.get(key)
            if val is not None:
                text = re.sub(pattern, rf'\1 {fmt(val)}', text)

    for person_name, age in pension_ages.items():
        pattern = (
            rf"(- name: '{re.escape(person_name)}'.*\n"
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
        tcr = cash_strategy.get('target_cash_reserve')
        ct = cash_strategy.get('market_crash_threshold')
        if tcr is not None:
            cs_str += f", 現金確保目標={int(tcr/10000)}万"
        if ct is not None:
            cs_str += f", crash_threshold={ct*100:.0f}%"
    pf_str = ""
    if pre_fire_strategy:
        cbm = pre_fire_strategy.get('cash_buffer_months')
        ait = pre_fire_strategy.get('auto_invest_threshold')
        mcb = pre_fire_strategy.get('min_cash_balance')
        parts = []
        if cbm is not None:
            parts.append(f"buffer={cbm}ヶ月")
        if ait is not None:
            parts.append(f"invest_thr={ait}")
        if mcb is not None:
            parts.append(f"min_cash={int(mcb/10000)}万")
        if parts:
            pf_str = ", " + ", ".join(parts)
    print(f"  [OK] config.yaml 更新: fire_month={fire_month}, pension={ages_str}{budget_str}{cs_str}{pf_str}")


def _save_pareto_frontier(result: dict, config: dict) -> None:
    """パレートフロンティアデータをJSONファイルに保存する"""
    pareto_df = result.get('pareto_info')
    if pareto_df is None or len(pareto_df) == 0:
        return

    start_age = config['simulation']['start_age']
    person_names = result.get('person_names', [])
    optimal = result.get('optimal')

    pareto_data = []
    for _, row in pareto_df.iterrows():
        fm = int(row['fire_month'])
        entry = {
            'fire_month': fm,
            'fire_age': round(start_age + fm / 12, 2),
            'final_assets': round(float(row.get('final_assets', 0))),
            'extra_budget': round(float(row.get('extra_budget', 0))),
            'pension_ages': {n: int(row.get(f'age_{n}', 65)) for n in person_names},
        }
        pareto_data.append(entry)

    output = {
        'pareto_frontier': pareto_data,
        'optimal': {
            'fire_month': optimal['fire_month'],
            'fire_age': round(start_age + optimal['fire_month'] / 12, 2),
            'final_assets': round(optimal.get('final_assets', 0)),
        } if optimal else None,
    }

    out_dir = Path('dashboard/data')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'pareto_frontier.json'
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"  [OK] パレートフロンティアデータ保存: {out_path}")


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
        initial_labor_income = config['simulation']['initial_labor_income']
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
        safety_margin = config['post_fire_cash_strategy']['safety_margin']

        result = optimize_pension_start_ages(
            current_cash=current_status['cash_deposits'],
            current_stocks=current_status['investment_trusts'],
            config=config,
            scenario='standard',
            monthly_income=monthly_income,
            monthly_expense=trends['monthly_avg_expense'],
            min_baseline_final_assets=safety_margin,
            fire_month_search_range=72,
            fire_month_step=1,
            extra_budget_candidates=[0, 50000, 100000, 150000, 200000],
            cash_strategy_candidates=[
                {'target_cash_reserve': 5_000_000, 'market_crash_threshold': -0.20},
                {'target_cash_reserve': 3_000_000, 'market_crash_threshold': -0.20},
                {'target_cash_reserve': 3_000_000, 'market_crash_threshold': -0.30},
                {'target_cash_reserve': 8_000_000, 'market_crash_threshold': -0.15},
                {'target_cash_reserve': 5_000_000, 'market_crash_threshold': -0.30},
            ],
            pre_fire_investment_candidates=[
                {},
                {'cash_buffer_months': 3, 'auto_invest_threshold': 1.2, 'min_cash_balance': 3_000_000},
                {'cash_buffer_months': 6, 'auto_invest_threshold': 1.5, 'min_cash_balance': 5_000_000},
                {'cash_buffer_months': 9, 'auto_invest_threshold': 1.5, 'min_cash_balance': 5_000_000},
                {'cash_buffer_months': 12, 'auto_invest_threshold': 2.0, 'min_cash_balance': 8_000_000},
                {'cash_buffer_months': 3, 'auto_invest_threshold': 1.5, 'min_cash_balance': 5_000_000},
                {'cash_buffer_months': 6, 'auto_invest_threshold': 1.2, 'min_cash_balance': 3_000_000},
                {'cash_buffer_months': 6, 'auto_invest_threshold': 2.0, 'min_cash_balance': 8_000_000},
                {'cash_buffer_months': 9, 'auto_invest_threshold': 1.2, 'min_cash_balance': 3_000_000},
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
                'final_assets': optimal.get('final_assets', 0),
                'optimal_ages': optimal['pension_ages'],
                'optimal_extra_monthly_budget': optimal.get('extra_monthly_budget', 0),
                'optimal_cash_strategy': optimal.get('cash_strategy', {}),
                'optimal_pre_fire_strategy': result.get('pre_fire_strategy', {}),
            })

        # 6. パレートフロンティアデータを保存
        print("\n[6] Saving Pareto frontier data...")
        _save_pareto_frontier(result, config)

        print("\n[OK] 最適化完了")
        return 0

    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
