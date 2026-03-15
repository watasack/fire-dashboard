# impl_10: ガードレール戦略（動的支出調整）の詳細設計

最終更新: 2026-03-15

**※ステータス: 実装済み**
`src/simulator.py` の `_process_post_fire_monthly_cycle`（L2394付近）で `calculate_drawdown_level` と `calculate_proportional_expense_adjustment` が結合済み。
`full_app.py` の「詳細シミュレーション設定」タブ（L620-637）で余剰反映率α・最大削減率の入力UIも実装済み。

---

## Goal
市場のボラティリティが高い状況下で、資産残高の推移（ドローダウン）に応じて支出を動的に調整する「ガードレール戦略（Proportional Expense Adjustment）」を完全に機能させます。
現状、ロジックの一部がスタブ（固定値 `0.0`）となっており、これを実際の計算パスと結合することが目的です。

## User Review Required
> [!IMPORTANT]
> ガードレール戦略は「裁量的支出（Discretionary Expense）」を調整対象とします。現在、カテゴリ別予算が有効な場合は裁量フラグから算出されますが、手動入力（単一金額）の場合は一定比率（デフォルト30%）を仮定します。この比率がユーザーの感覚と乖離する可能性があります。

## Proposed Changes

### [Component] Simulator (`src/simulator.py`)

#### [MODIFY] `_process_post_fire_monthly_cycle` (L2418付近)
現在 `drawdown = 0.0` となっている箇所を、ベースライン資産との比較に基づいた計算に置き換えます。

```python
# 乖離率の算出
drawdown, _ = calculate_drawdown_level(
    current_assets=current_total_assets,
    peak_assets_history=[], # 将来的に Peak-to-Trough 制御を行う場合は履歴を活用
    config=config,
    planned_assets=baseline_assets[month] if baseline_assets is not None else None
)
```

#### [MODIFY] `_compute_post_fire_monthly_expenses` (L2206付近)
引数に `drawdown` を追加し、支出計算後に `calculate_proportional_expense_adjustment` (L532) を呼び出して合計支出 (`total`) を補正します。

```python
# 調整額の算出と適用
if config['fire']['dynamic_expense_reduction']['enabled']:
    disc_ratio = _get_discretionary_ratio(years, config)
    disc_monthly = annual_base_expense * disc_ratio / 12.0
    
    # 乖離額（surplus）の取得。drawdownから逆算または別途算出
    surplus = current_total_assets - planned_assets
    
    adjustment = calculate_proportional_expense_adjustment(
        surplus, disc_monthly, config
    )
    total += adjustment
```

### [Component] UI / Config (`full_app.py`, `demo_config.yaml`)

#### [MODIFY] `full_app.py`
「詳細シミュレーション設定」タブに以下のパラメータ入力を追加します。
- α値 (`surplus_spending_rate`): 余剰資産に対してどれだけ支出を増やすか。
- 最大削減率 (`max_cut_ratio`): 裁量的支出を最大何%削れるか。

---

## Verification Plan

### Automated Tests
- `tests/test_guardrail_logic.py` を新規作成。
- `calculate_proportional_expense_adjustment` が、裁量的支出のキャップ（`max_cut_ratio`, `max_boost_ratio`）を守ること、および α値に従って比例調整されることを検証。
- 実行コマンド: `pytest tests/test_guardrail_logic.py`

### Manual Verification
1. `full_app.py` の詳細設定で「ガードレール（動的支出調整）」を有効化。
2. 標準シナリオ（期待リターン通り）と、運用リターンをマイナスにしたカスタムシナリオで、年次収支テーブルの「年支出」を比較。
3. 資産減少時に支出が自動で削減されていることを確認。
