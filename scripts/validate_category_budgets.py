#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
カテゴリ別予算の妥当性検証スクリプト

config.yamlのexpense_categoriesセクションを検証:
1. 各ステージの合計が base_expense_by_stage と一致するか
2. 裁量的支出比率が discretionary_ratio_by_stage と一致するか
3. カテゴリIDの重複がないか
"""

import yaml
from pathlib import Path
from typing import Dict, List, Tuple


def load_config() -> Dict:
    """設定ファイルを読み込む"""
    config_path = Path(__file__).parent.parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def validate_category_ids(config: Dict) -> List[str]:
    """カテゴリIDの重複チェック"""
    warnings = []

    if not config['fire']['expense_categories'].get('definitions'):
        return warnings

    ids = [cat['id'] for cat in config['fire']['expense_categories']['definitions']]
    duplicates = [cat_id for cat_id in ids if ids.count(cat_id) > 1]

    if duplicates:
        warnings.append(f"[NG] 重複するカテゴリID: {set(duplicates)}")

    return warnings


def validate_stage_totals(config: Dict) -> List[str]:
    """各ステージの合計が想定総額と一致するかチェック"""
    warnings = []

    base_expenses = config['fire']['base_expense_by_stage']
    budgets = config['fire']['expense_categories'].get('budgets_by_stage', {})

    if not budgets:
        return warnings

    print("\n" + "=" * 80)
    print("ライフステージ別予算の検証")
    print("=" * 80)

    for stage, expected_total in base_expenses.items():
        if stage not in budgets:
            warnings.append(f"[NG] ステージ '{stage}' の予算が未定義")
            continue

        actual_total = sum(budgets[stage].values())
        difference = actual_total - expected_total

        print(f"\n【{stage}】")
        print(f"  期待値: {expected_total:>12,}円")
        print(f"  実際値: {actual_total:>12,}円")

        if abs(difference) > 100:  # 100円以上の誤差
            print(f"  差分:   {difference:>+12,}円 [NG] 不一致")
            warnings.append(
                f"[NG] ステージ '{stage}' の合計が不一致: "
                f"期待 {expected_total:,}円、実際 {actual_total:,}円 (差分 {difference:+,}円)"
            )
        else:
            print(f"  差分:   {difference:>+12,}円 [OK]")

    return warnings


def validate_discretionary_ratios(config: Dict) -> List[str]:
    """裁量的支出比率が想定値と一致するかチェック"""
    warnings = []

    expected_ratios = config['fire']['discretionary_ratio_by_stage']
    budgets = config['fire']['expense_categories'].get('budgets_by_stage', {})
    definitions = config['fire']['expense_categories'].get('definitions', [])

    if not budgets or not definitions:
        return warnings

    # カテゴリIDと裁量フラグのマップを作成
    discretionary_map = {cat['id']: cat['discretionary'] for cat in definitions}

    print("\n" + "=" * 80)
    print("裁量的支出比率の検証")
    print("=" * 80)

    for stage, expected_ratio in expected_ratios.items():
        if stage not in budgets:
            continue

        total = sum(budgets[stage].values())
        discretionary_total = sum(
            amount for cat_id, amount in budgets[stage].items()
            if discretionary_map.get(cat_id, False)
        )

        actual_ratio = discretionary_total / total if total > 0 else 0
        ratio_diff = actual_ratio - expected_ratio

        print(f"\n【{stage}】")
        print(f"  期待比率: {expected_ratio:>6.1%}")
        print(f"  実際比率: {actual_ratio:>6.1%}")
        print(f"  裁量支出: {discretionary_total:>12,}円")
        print(f"  基礎支出: {total - discretionary_total:>12,}円")

        if abs(ratio_diff) > 0.02:  # 2%以上の誤差
            print(f"  差分:     {ratio_diff:>+6.1%} [NG] 不一致")
            warnings.append(
                f"[NG] ステージ '{stage}' の裁量的支出比率が不一致: "
                f"期待 {expected_ratio:.1%}、実際 {actual_ratio:.1%} (差分 {ratio_diff:+.1%})"
            )
        else:
            print(f"  差分:     {ratio_diff:>+6.1%} [OK]")

    return warnings


def print_category_summary(config: Dict):
    """カテゴリ定義のサマリを表示"""
    definitions = config['fire']['expense_categories'].get('definitions', [])

    if not definitions:
        return

    print("\n" + "=" * 80)
    print("カテゴリ定義のサマリ")
    print("=" * 80)

    essential = [cat for cat in definitions if not cat['discretionary']]
    discretionary = [cat for cat in definitions if cat['discretionary']]

    print(f"\n【基礎生活費】（{len(essential)}カテゴリ）")
    for cat in essential:
        print(f"  - {cat['id']:25s} {cat['name']:20s} {cat['description']}")

    print(f"\n【裁量的支出】（{len(discretionary)}カテゴリ）")
    for cat in discretionary:
        print(f"  - {cat['id']:25s} {cat['name']:20s} {cat['description']}")

    print(f"\n合計: {len(definitions)}カテゴリ")


def main():
    """メイン処理"""
    print("=" * 80)
    print("カテゴリ別予算の妥当性検証")
    print("=" * 80)

    config = load_config()

    # カテゴリ定義のサマリ表示
    print_category_summary(config)

    # 検証実行
    all_warnings = []

    # 1. カテゴリID重複チェック
    all_warnings.extend(validate_category_ids(config))

    # 2. ステージ別合計チェック
    all_warnings.extend(validate_stage_totals(config))

    # 3. 裁量的支出比率チェック
    all_warnings.extend(validate_discretionary_ratios(config))

    # 結果サマリ
    print("\n" + "=" * 80)
    print("検証結果サマリ")
    print("=" * 80)

    if all_warnings:
        print(f"\n[NG] 警告: {len(all_warnings)}件\n")
        for warning in all_warnings:
            print(warning)
        print("\n注意: 警告があっても実行可能ですが、設定の見直しを推奨します。")
    else:
        print("\n[OK] すべての検証に合格しました！")
        print("  - カテゴリIDに重複なし")
        print("  - 全ステージの合計が想定値と一致")
        print("  - 裁量的支出比率が想定値と一致")

    print()


if __name__ == '__main__':
    main()
