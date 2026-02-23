#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最悪ケース条件下での生存戦略分析

副収入追加・基礎支出削減以外の対応策を検証
"""

import sys
from pathlib import Path
import numpy as np

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from config import load_config


def analyze_survival_strategies():
    """
    破産回避のための戦略を分析
    """
    print("=" * 80)
    print("最悪ケース条件下での生存戦略分析")
    print("=" * 80)
    print()

    config = load_config('config.yaml')

    # 現在の設定を確認
    base_expense = config['fire']['base_expense_by_stage']['empty_nest']
    fire_target = 79995755  # 実際のダッシュボードから取得した値

    print("現在の設定:")
    print(f"  FIRE目標資産: {fire_target:,}円")
    print(f"  年間支出: {base_expense:,}円（empty_nest）")
    print(f"  出口戦略: 年間支出 / 資産 = {base_expense/fire_target:.2%}")
    print()

    # 基礎支出とワーケーション費用
    workation_cost = config.get('workation', {}).get('annual_cost', 0)

    print("=" * 80)
    print("戦略1: 裁量的支出の柔軟な調整（すでに実装済み）")
    print("=" * 80)
    print()
    print("[実装済み] 動的支出削減")
    print(f"  対象: ワーケーション費用 {workation_cost:,}円/年")
    print(f"  削減条件: 資産がベースラインを下回った場合")
    print(f"  削減可能額: 最大{workation_cost:,}円/年（{workation_cost/base_expense:.1%}）")
    print()
    print("効果:")
    print(f"  → 資産不足時に年間{workation_cost:,}円の支出を削減可能")
    print(f"  → 最悪ケースでの生存期間を延長")
    print()

    print("=" * 80)
    print("戦略2: より保守的な出口戦略（引き出し率の調整）")
    print("=" * 80)
    print()
    print("現在の実装:")
    print(f"  年間支出: {base_expense:,}円")
    print(f"  FIRE目標: {fire_target:,}円")
    print(f"  引き出し率: {base_expense / fire_target:.2%}")
    print()

    # より保守的な出口戦略
    safer_rates = [0.030, 0.035, 0.040]
    print("より安全な引き出し率:")
    for rate in safer_rates:
        required_assets = base_expense / rate
        current_target = fire_target
        additional_needed = required_assets - current_target

        print(f"  {rate:.1%}ルール:")
        print(f"    必要資産: {required_assets:,.0f}円")
        print(f"    現在目標との差: {additional_needed:+,.0f}円")
        print(f"    FIRE達成時期への影響: 約{additional_needed / (12 * config['simulation'].get('initial_labor_income', 765875) * 0.9):.1f}年遅延")
        print()

    print("推奨:")
    print("  3.5%ルール（年間支出/資産 ≦ 3.5%）が最適バランス")
    print("  → 安全性と実現可能性のトレードオフ")
    print()

    print("=" * 80)
    print("戦略3: FIRE目標の上方修正（安全マージンの追加）")
    print("=" * 80)
    print()
    print("現在の目標:")
    print(f"  FIRE目標資産: {fire_target:,}円")
    print(f"  年間支出の何倍: {fire_target / base_expense:.1f}倍")
    print()

    # 安全マージンの追加
    safety_margins = [1.1, 1.2, 1.3, 1.5]
    print("安全マージンを追加した場合:")
    for margin in safety_margins:
        new_target = fire_target * margin
        additional = new_target - fire_target

        print(f"  {margin:.0%}マージン（+{(margin-1):.0%}）:")
        print(f"    新目標: {new_target:,.0f}円")
        print(f"    追加必要額: {additional:,.0f}円")
        print(f"    FIRE達成時期への影響: 約{additional / (12 * config['simulation'].get('initial_labor_income', 765875) * 0.9):.1f}年遅延")
        print()

    print("推奨:")
    print("  10-20%の安全マージンが現実的")
    print("  → 最悪ケースでも余裕を持った運用が可能")
    print()

    print("=" * 80)
    print("戦略4: 年金受給戦略の最適化")
    print("=" * 80)
    print()

    # 年金情報
    pension_people = config.get('pension', {}).get('people', [])
    pension_start_age = config.get('pension', {}).get('start_age', 65)

    print(f"現在の設定: {pension_start_age}歳から受給開始")
    print()
    print("繰り下げ受給の効果:")

    # 繰り下げ受給のシミュレーション
    base_pension = 816000 + 1500000  # 概算（国民年金 + 厚生年金）

    for delay_years in [0, 1, 3, 5]:
        receive_age = pension_start_age + delay_years
        increase_rate = 1 + (delay_years * 0.084)  # 年0.7%×12ヶ月=8.4%増
        annual_pension = base_pension * increase_rate

        print(f"  {receive_age}歳受給開始（{delay_years}年繰り下げ）:")
        print(f"    年金額: {annual_pension:,.0f}円/年（+{(increase_rate-1):.1%}）")
        print(f"    支出カバー率: {annual_pension / base_expense:.1%}")
        print()

    print("推奨:")
    print("  資産が潤沢な場合は繰り下げ受給で年金額を最大化")
    print("  資産が減少した場合の安全ネットとして活用")
    print()

    print("=" * 80)
    print("戦略5: 大型支出のタイミング調整")
    print("=" * 80)
    print()

    # 住宅メンテナンス費用
    maintenance = config.get('house_maintenance', {})
    if maintenance.get('enabled'):
        print("住宅メンテナンス費用:")
        for item in maintenance.get('items', []):
            print(f"  {item['name']}: {item['cost']:,}円（{item['frequency_years']}年ごと）")
        print()
        print("タイミング調整の効果:")
        print("  市況が良い時（資産がベースラインを上回る時）に実施")
        print("  → 暴落時の資産売却を回避")
        print("  → ドローダウンを最小化")
        print()

    print("推奨:")
    print("  延期可能な大型支出は市況を見て判断")
    print("  緊急性の高い支出（健康関連など）は即実行")
    print()

    print("=" * 80)
    print("戦略6: 資産配分の見直し（株式100%の是非）")
    print("=" * 80)
    print()
    print("現在の実装: 株式100%（全世界株式インデックス想定）")
    print()
    print("代替案:")
    print()

    # 株式/債券の配分シナリオ
    allocations = [
        (100, 0, "株式100%", "高リターン・高リスク", "現在の実装"),
        (80, 20, "株式80% / 債券20%", "バランス型", "リスク軽減"),
        (60, 40, "株式60% / 債券40%", "保守的", "大幅リスク軽減"),
    ]

    for stock, bond, name, type_str, note in allocations:
        expected_return = stock * 0.05 + bond * 0.02  # 株式5%、債券2%と仮定
        expected_vol = (stock * 0.06) ** 2 + (bond * 0.03) ** 2  # 簡易計算
        expected_vol = expected_vol ** 0.5

        print(f"  {name}:")
        print(f"    タイプ: {type_str}")
        print(f"    期待リターン: {expected_return:.2%}/年")
        print(f"    期待ボラティリティ: {expected_vol:.2%}/年")
        print(f"    備考: {note}")
        print()

    print("推奨:")
    print("  FIRE前: 株式100%で資産成長を最大化")
    print("  FIRE後: 年齢に応じて徐々に債券比率を上げる")
    print("  例: 60歳で80/20、70歳で60/40など")
    print()

    print("=" * 80)
    print("戦略7: リバランシング戦略")
    print("=" * 80)
    print()
    print("定期的なリバランシングの効果:")
    print("  株式が大幅に上昇 → 一部を現金化して利益確定")
    print("  株式が大幅に下落 → 現金から株式を買い増し")
    print()
    print("実装方法:")
    print("  年1回、目標配分（例: 80/20）からのズレが±5%以上ならリバランス")
    print()
    print("効果:")
    print("  → ボラティリティを抑制")
    print("  → 暴落時の資産減少を緩和")
    print("  → 「安く買って高く売る」を自動化")
    print()

    print("=" * 80)
    print("戦略8: 緊急時資金の確保")
    print("=" * 80)
    print()

    cash_buffer_months = config['asset_allocation'].get('cash_buffer_months', 6)
    monthly_expense = base_expense / 12
    cash_buffer = cash_buffer_months * monthly_expense

    print(f"現在の実装:")
    print(f"  現金バッファ: {cash_buffer_months}ヶ月分 = {cash_buffer:,.0f}円")
    print()
    print("より保守的な設定:")
    for months in [12, 18, 24]:
        buffer = months * monthly_expense
        print(f"  {months}ヶ月分: {buffer:,.0f}円")
    print()
    print("効果:")
    print("  暴落時に株式を売らずに生活費を賄える")
    print("  → 底値での売却を回避")
    print("  → 回復時の恩恵を最大化")
    print()

    print("=" * 80)
    print("総合評価: 各戦略の優先度")
    print("=" * 80)
    print()

    strategies = [
        ("◎", "戦略1: 裁量的支出の柔軟な調整", "すでに実装済み", "即効性あり、実装済み"),
        ("◎", "戦略3: FIRE目標の上方修正", "10-20%のマージン追加", "最も確実、計画段階で対応可能"),
        ("○", "戦略2: 出口戦略の見直し", "3.5%ルールの採用", "長期的な安全性向上"),
        ("○", "戦略8: 緊急時資金の増額", "12-18ヶ月分確保", "暴落時の防御力向上"),
        ("△", "戦略4: 年金繰り下げ受給", "状況に応じて判断", "資産状況次第で有効"),
        ("△", "戦略6: 資産配分の見直し", "FIRE後に検討", "年齢に応じた調整"),
        ("△", "戦略7: リバランシング", "年1回実施", "ボラティリティ抑制"),
        ("△", "戦略5: 大型支出タイミング調整", "状況判断", "柔軟な対応が必要"),
    ]

    print("優先度  戦略                          推奨内容                   備考")
    print("-" * 80)
    for priority, name, recommendation, note in strategies:
        print(f"{priority:^8} {name:30} {recommendation:25} {note}")

    print()
    print("=" * 80)
    print("結論")
    print("=" * 80)
    print()
    print("最悪ケース（下位1%）でも50年後に資産は約4倍に成長しており、")
    print("現在の設定でも破産リスクは極めて低いです。")
    print()
    print("さらに安全性を高めるための推奨策:")
    print()
    print("【短期的対応（すぐ実施可能）】")
    print("  1. FIRE目標資産を10-20%上方修正")
    print("     現在: 79,995,755円 → 推奨: 88,000,000-96,000,000円")
    print()
    print("  2. 緊急時資金を12ヶ月分に増額")
    print(f"     現在: {cash_buffer_months}ヶ月分 → 推奨: 12ヶ月分")
    print()
    print("【長期的対応（FIRE後に実施）】")
    print("  3. 年齢に応じて株式比率を徐々に下げる")
    print("     50歳: 100%株式 → 60歳: 80%株式 → 70歳: 60%株式")
    print()
    print("  4. 年1回のリバランシングで利益確定とリスク管理")
    print()
    print("  5. 年金は資産状況を見て繰り下げ受給を検討")
    print()
    print("これらの対応により、最悪ケースでも安心して生活できる体制が整います。")
    print()


if __name__ == '__main__':
    analyze_survival_strategies()
