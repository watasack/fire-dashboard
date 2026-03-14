# 詳細実装計画: ⑧ 取り崩し戦略の選択

最終更新: 2026-03-14

---

## 概要

現在は固定支出モデル（「毎月一定額を取り崩す」）のみ。
競合（63400r）は「ガードレール戦略」を実装しており、相場が悪いときに支出を自動削減するアダプティブな戦略が選べる。

**取り崩し戦略の選択肢:**
1. **固定額** （現在の実装）: 毎月一定額を取り崩す。シンプルだが暴落時に資産が速く減る
2. **定率** : 残高の一定割合（例: 年4%）を取り崩す。資産に連動するため枯渇しにくいが生活費が不安定
3. **ガードレール戦略** : 残高が基準額を下回ると支出を削減、回復したら元に戻す。柔軟で現実的

---

## 現状の実装

### simulator.py — FIRE後の取り崩しロジック

`_compute_post_fire_monthly_expenses` が毎月の支出額を返し、それが資産から引かれる。
現状は固定額（生活費 + 住宅費 + 教育費）で変動しない。

### run_mc_fixed_fire — MCシミュレーション

各パスで `_compute_post_fire_monthly_expenses` を呼んで月次支出を決定。
取り崩し戦略の「資産残高に応じた動的変更」を追加するのに適した場所。

---

## 変更方針

### UI: 取り崩し戦略の選択

```python
# full_app.py — FIRE後設定セクション

st.subheader("取り崩し戦略")
withdrawal_strategy = st.selectbox(
    "FIRE後の取り崩し方法",
    options=["固定額", "定率（残高×年率）", "ガードレール戦略"],
    index=0,
    help=(
        "固定額: 毎月一定額を取り崩します。\n"
        "定率: 残高の一定割合（年率）を毎年取り崩します。\n"
        "ガードレール戦略: 資産が目標を下回ると支出を自動削減します。"
    )
)

if withdrawal_strategy == "定率（残高×年率）":
    withdrawal_rate = st.slider(
        "年間取り崩し率（%）",
        min_value=2.0, max_value=6.0, value=4.0, step=0.1,
        help="残高の何%を年間で取り崩すか。4%が一般的な目安（4%ルール）。"
    )
else:
    withdrawal_rate = 4.0  # デフォルト値（UI非表示）

if withdrawal_strategy == "ガードレール戦略":
    guardrail_lower = st.number_input(
        "下限ガードレール（FIRE時資産の何%）",
        value=80, min_value=50, max_value=95, step=5,
        help="資産がFIRE時の○%を下回ったら支出を削減します。"
    )
    guardrail_upper = st.number_input(
        "上限ガードレール（FIRE時資産の何%）",
        value=120, min_value=105, max_value=200, step=5,
        help="資産がFIRE時の○%を上回ったら支出を増やせます。"
    )
    guardrail_reduction = st.slider(
        "下限時の支出削減率（%）",
        min_value=5, max_value=30, value=10, step=5,
        help="下限ガードレールを下回ったときに支出を何%削減するか。"
    )
```

### config.yaml — 戦略パラメータを追加

```yaml
simulation:
  withdrawal_strategy: "fixed"   # "fixed" | "percentage" | "guardrail"
  withdrawal_rate: 0.04           # 定率モード用
  guardrail_lower: 0.80           # ガードレール下限（FIRE時資産比）
  guardrail_upper: 1.20           # ガードレール上限
  guardrail_reduction: 0.10       # 下限時の支出削減率
```

### simulator.py — 取り崩しロジックの変更

#### 固定額モード（現状維持）

```python
monthly_withdrawal = base_expense  # 変更なし
```

#### 定率モード

```python
def _calc_withdrawal_percentage(current_assets, withdrawal_rate):
    annual = current_assets * withdrawal_rate
    return annual / 12
```

#### ガードレール戦略モード

```python
def _calc_withdrawal_guardrail(
    current_assets,
    fire_assets,    # FIRE時点の資産額（基準）
    base_expense,   # 基本生活費
    cfg,
):
    lower = cfg["simulation"]["guardrail_lower"]
    upper = cfg["simulation"]["guardrail_upper"]
    reduction = cfg["simulation"]["guardrail_reduction"]

    ratio = current_assets / fire_assets

    if ratio < lower:
        # 資産が減っている → 支出を削減
        return base_expense * (1 - reduction)
    elif ratio > upper:
        # 資産が増えている → 支出を少し増やす（上限あり）
        return base_expense * 1.05
    else:
        return base_expense
```

### `_compute_post_fire_monthly_expenses` の修正

```python
def _compute_post_fire_monthly_expenses(
    cfg, age_h, age_w, month_idx, fire_month,
    current_assets=None,    # 追加引数
    fire_assets=None,       # 追加引数
):
    base_expense = ...  # 既存の計算（生活費 + 住宅費 + 教育費）

    strategy = cfg["simulation"].get("withdrawal_strategy", "fixed")

    if strategy == "fixed":
        return base_expense

    elif strategy == "percentage":
        if current_assets is not None:
            return _calc_withdrawal_percentage(
                current_assets,
                cfg["simulation"]["withdrawal_rate"]
            )
        return base_expense  # フォールバック

    elif strategy == "guardrail":
        if current_assets is not None and fire_assets is not None:
            return _calc_withdrawal_guardrail(
                current_assets, fire_assets, base_expense, cfg
            )
        return base_expense

    return base_expense
```

### `simulate_future_assets` / MCループへの影響

月次シミュレーションループ内で `current_assets` を渡す必要がある：

```python
# MCループ内（概念コード）
for month in range(fire_month, total_months):
    expense = _compute_post_fire_monthly_expenses(
        cfg, age_h, age_w, month, fire_month,
        current_assets=assets_at_month,    # 追加
        fire_assets=assets_at_fire_month,  # 追加
    )
    assets_at_month = assets_at_month * (1 + monthly_return) - expense
```

---

## 戦略比較の表示

```python
# 結果表示: 取り崩し戦略の説明

if withdrawal_strategy == "ガードレール戦略":
    st.info(
        "ガードレール戦略: 資産がFIRE時の80%を下回ると支出を10%削減します。"
        "相場が回復すると元の支出水準に戻ります。"
        "これにより破産リスクを減らしつつ、生活水準の柔軟な調整が可能です。"
    )
```

---

## 実装ステップ

### Step 1: config.yaml にデフォルト戦略パラメータを追加

### Step 2: `src/withdrawal.py`（新規）に取り崩し計算関数を実装

`_calc_withdrawal_percentage`, `_calc_withdrawal_guardrail` を分離して実装。

### Step 3: `_compute_post_fire_monthly_expenses` に `current_assets`, `fire_assets` 引数を追加

シグネチャ変更のため呼び出し元をすべて修正（`None` デフォルトで後方互換を維持）。

### Step 4: MCシミュレーションループで `current_assets` を渡すよう修正

### Step 5: `full_app.py` — UI追加と結果表示の更新

### Step 6: テスト

---

## テスト方針

**ガードレール戦略の動作確認:**

| シナリオ | 期待動作 |
|---------|---------|
| 相場が悪くて資産が80%以下に | 支出が10%削減される |
| 資産が120%以上に | 支出が5%増加する |
| 通常時（80〜120%） | 支出は変わらない |

**成功確率の比較:**

| 戦略 | 成功確率（目安） |
|------|---------------|
| 固定額 | XX% |
| 定率4% | XX% （固定額より若干高い傾向） |
| ガードレール | XX% （最も高い傾向） |

---

## 依存関係・注意事項

- **① との依存**: `fire_assets` の計算は `run_mc_fixed_fire` が既に `fire_month` の資産額を返しているはず → 確認して `fire_assets` として渡す
- **定率モードと FIRE 後収入の関係**: 定率モードでは「取り崩し額 = 残高 × 年率 / 12」となるが、サイドFIRE収入（②）があれば不足分のみ取り崩す形にする。実装の複雑さに注意
- **ガードレール戦略の「削減」の意味**: 単純に支出削減するのではなく、「最低生活費（住宅費・教育費）は削減しない、生活費のみ削減」という実装が現実的だが、今フェーズではシンプルに全支出の一定率削減とする
- **パフォーマンス**: 条件分岐が増えるが、単純な計算のため MC 1,000回への影響は軽微
- **表示**: 戦略ごとに「この戦略のメリット・デメリット」を help テキストで説明する
