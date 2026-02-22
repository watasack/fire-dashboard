#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FIRE達成時期の感度分析スクリプト

各パラメータを変更した場合のFIRE達成時期への影響を分析
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_config
from src.data_loader import load_asset_data, load_transaction_data
from src.data_processor import clean_asset_data, clean_transaction_data, calculate_monthly_cashflow
from src.analyzer import analyze_current_status, analyze_income_expense_trends
from src.simulator import simulate_future_assets

def run_scenario(description, changes=None):
    """
    シナリオを実行してFIRE達成時期を取得

    Args:
        description: シナリオの説明
        changes: 変更内容のディクショナリ

    Returns:
        FIRE達成月数
    """
    # 設定を読み込み
    config = load_config('config.yaml')

    # 設定を変更
    if changes:
        for key_path, value in changes.items():
            keys = key_path.split('.')
            target = config
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value

    # データ読み込みと処理
    asset_df = load_asset_data(config)
    transaction_df = load_transaction_data(config)
    asset_df = clean_asset_data(asset_df)
    transaction_df = clean_transaction_data(transaction_df)
    cashflow_df = calculate_monthly_cashflow(transaction_df)

    # 現状分析
    current_status = analyze_current_status(asset_df)
    trends = analyze_income_expense_trends(cashflow_df, transaction_df, config)

    # 労働収入
    monthly_income = config['simulation'].get('initial_labor_income', trends['monthly_avg_income_forecast'])

    # シミュレーション実行
    result = simulate_future_assets(
        current_assets=current_status['net_assets'],
        monthly_income=monthly_income,
        monthly_expense=trends['monthly_avg_expense'],
        config=config,
        scenario='standard'
    )

    # FIRE達成時期を取得
    fire_rows = result[result['fire_achieved'] == True]
    if len(fire_rows) > 0:
        fire_month = fire_rows.iloc[0]['month']
        return fire_month
    else:
        return None

def main():
    print("=" * 80)
    print("FIRE達成時期の感度分析")
    print("=" * 80)
    print()

    print("[ベースライン] 現在の設定")
    baseline_months = run_scenario("ベースライン")
    baseline_years = baseline_months / 12 if baseline_months else None
    print(f"  FIRE達成: {baseline_months}ヶ月後 ({baseline_years:.1f}年)")
    print()

    # 感度分析シナリオ
    scenarios = [
        # 収入増加シナリオ
        {
            'name': '収入+5万円/月（昇給・副業）',
            'changes': {'simulation.initial_labor_income': 765875 + 50000},
            'cost': '実施難易度: 中（スキルアップ、副業開始）'
        },
        {
            'name': '収入+10万円/月（転職・大幅昇給）',
            'changes': {'simulation.initial_labor_income': 765875 + 100000},
            'cost': '実施難易度: 高（転職、大幅な業務拡大）'
        },

        # 支出削減シナリオ
        {
            'name': '基本生活費-10%（節約努力）',
            'changes': {'fire.base_expense_by_stage.young_child': int(2800000 * 0.9)},
            'cost': '実施難易度: 低（家計見直し、節約）'
        },
        {
            'name': '基本生活費-20%（徹底節約）',
            'changes': {'fire.base_expense_by_stage.young_child': int(2800000 * 0.8)},
            'cost': '実施難易度: 中（大幅な生活水準変更）'
        },

        # 運用リターン向上シナリオ
        {
            'name': '運用リターン6%（+1%）',
            'changes': {'simulation.standard.annual_return_rate': 0.06},
            'cost': '実施難易度: 中（リスク資産比率増加）'
        },
        {
            'name': '運用リターン7%（+2%）',
            'changes': {'simulation.standard.annual_return_rate': 0.07},
            'cost': '実施難易度: 高（高リスク運用、再現性低）'
        },

        # 現金バッファ削減シナリオ
        {
            'name': '現金バッファ4ヶ月（-2ヶ月）',
            'changes': {'asset_allocation.cash_buffer_months': 4},
            'cost': '実施難易度: 低（設定変更のみ、リスク小増）'
        },
        {
            'name': '現金バッファ3ヶ月（-3ヶ月）',
            'changes': {'asset_allocation.cash_buffer_months': 3},
            'cost': '実施難易度: 低（設定変更のみ、リスク中増）'
        },

        # 複合シナリオ
        {
            'name': '【複合1】収入+5万 & 支出-10% & リターン6%',
            'changes': {
                'simulation.initial_labor_income': 765875 + 50000,
                'fire.base_expense_by_stage.young_child': int(2800000 * 0.9),
                'simulation.standard.annual_return_rate': 0.06
            },
            'cost': '実施難易度: 中（総合的な改善）'
        },
        {
            'name': '【複合2】収入+5万 & 支出-10% & バッファ4ヶ月',
            'changes': {
                'simulation.initial_labor_income': 765875 + 50000,
                'fire.base_expense_by_stage.young_child': int(2800000 * 0.9),
                'asset_allocation.cash_buffer_months': 4
            },
            'cost': '実施難易度: 低（実現性高）'
        },
    ]

    print("=" * 80)
    print("感度分析結果")
    print("=" * 80)
    print()

    results = []

    for scenario in scenarios:
        months = run_scenario(scenario['name'], scenario['changes'])

        if months:
            years = months / 12
            delta_months = baseline_months - months
            delta_years = delta_months / 12

            results.append({
                'name': scenario['name'],
                'months': months,
                'years': years,
                'delta_months': delta_months,
                'delta_years': delta_years,
                'cost': scenario['cost']
            })

            print(f"[{scenario['name']}]")
            print(f"  FIRE達成: {months}ヶ月後 ({years:.1f}年)")
            print(f"  短縮効果: -{delta_months}ヶ月 (-{delta_years:.1f}年)")
            print(f"  {scenario['cost']}")
            print()

    # 費用対効果ランキング
    print("=" * 80)
    print("費用対効果ランキング（短縮効果順）")
    print("=" * 80)
    print()

    # 短縮効果でソート
    results.sort(key=lambda x: x['delta_months'], reverse=True)

    for i, result in enumerate(results, 1):
        print(f"{i}. {result['name']}")
        print(f"   短縮効果: -{result['delta_months']}ヶ月 (-{result['delta_years']:.1f}年)")
        print(f"   FIRE達成: {result['months']}ヶ月後 ({result['years']:.1f}年)")
        print(f"   {result['cost']}")
        print()

    print("=" * 80)
    print("分析完了")
    print("=" * 80)

if __name__ == '__main__':
    main()
