# 詳細実装計画: ② FIRE後収入（サイドFIRE）の入力

最終更新: 2026-03-14

---

## 概要

FIRE後に少額の労働収入（パート・副業・フリーランス等）がある「セミFIRE」「サイドFIRE」を正式にサポートする。
現状は「生活費から差し引いてください」という workaround での案内になっており、ユーザー体験が悪い。

---

## 現状の実装

### FAQ の現状回答

> 「生活費」からパート・副業収入を差し引いた純支出を入力することで、セミFIRE想定のシミュレーションができます。
> 例: 生活費28万円、パート5万円/月 → 「生活費」に23万円を入力

### full_app.py — 支出計算 (推定 lines 290-320)

`monthly_exp` は住宅費 + 生活費 + 教育費で構成。FIRE後収入の概念はなし。

### simulator.py — `_compute_post_fire_monthly_expenses` (lines 2177-2228)

FIRE後の月次支出を計算する関数。ここに「post_fire_income（月次労働収入）」を追加することで
「実質支出 = 支出 - 労働収入」の形にできる。

```python
def _compute_post_fire_monthly_expenses(cfg, age_h, age_w, month_idx):
    """現状: 支出のみ返す"""
    ...
    return total_expense  # 円/月
```

---

## 変更方針

### UI: FIRE後収入の入力欄を追加

FIRE後の労働収入は、夫婦それぞれの状況に応じた柔軟な設定（例：夫は完全にリタイアし、妻は扶養内でパートを続ける等）を可能にするため、**夫婦個別に設定**できるようにする。
また、ユーザーが「何の収入か」「いつまでか」を迷わないよう、言葉の定義（例：「FIRE後副収入」等）に注意する。

```python
# full_app.py — FIRE設定セクションに追加
st.subheader("FIRE後の副収入（サイドFIRE）")
st.write("完全なリタイアではなく、パートや副業などで部分的に収入を得る場合に入力してください。")

col_sh, col_sw = st.columns(2)
with col_sh:
    husband_post_fire_income = st.number_input(
        "夫のFIRE後副収入（月額・万円）",
        value=0, min_value=0, step=1,
        help="FIRE後に夫が得るパート・副業・フリーランスなどの月間労働収入。"
    )
    husband_side_fire_until = st.number_input(
        "夫の副収入 終了年齢（歳）",
        value=65, min_value=0, max_value=100, step=1,
        help="夫の労働収入が何歳まで続くか。65歳以降は年金のみとして計算します。"
    )
with col_sw:
    wife_post_fire_income = st.number_input(
        "妻のFIRE後副収入（月額・万円）",
        value=0, min_value=0, step=1,
        help="FIRE後に妻が得るパート・副業・フリーランスなどの月間労働収入。"
    )
    wife_side_fire_until = st.number_input(
        "妻の副収入 終了年齢（歳）",
        value=65, min_value=0, max_value=100, step=1,
        help="妻の労働収入が何歳まで続くか。65歳以降は年金のみとして計算します。"
    )
```

### config.yaml および _build_simulation_config の扱い

新規パラメータを追加するのではなく、すでに内部に存在している変数（`husband_post_fire_income` 等）にマッピングする。終了年齢については新規の変数を使って期間制御を行う。

```yaml
simulation:
  # 既存パラメータを活用
  husband_post_fire_income: 0
  wife_post_fire_income: 0
  # 新規追加パラメータ
  husband_side_fire_until: 65
  wife_side_fire_until: 65
```

### _build_simulation_config — パラメータを cfg に追加

```python
cfg["simulation"]["husband_post_fire_income"] = husband_post_fire_income * 10000
cfg["simulation"]["wife_post_fire_income"] = wife_post_fire_income * 10000
cfg["simulation"]["husband_side_fire_until"] = husband_side_fire_until
cfg["simulation"]["wife_side_fire_until"] = wife_side_fire_until
```

### simulator.py — `_compute_post_fire_monthly_expenses` 修正

```python
def _compute_post_fire_monthly_expenses(cfg, age_h, age_w, month_idx):
    total_expense = ...  # 既存計算

    # FIRE後労働収入を差し引く
    husband_side_income = cfg["simulation"].get("husband_post_fire_income", 0)
    wife_side_income = cfg["simulation"].get("wife_post_fire_income", 0)
    husband_until = cfg["simulation"].get("husband_side_fire_until", 65)
    wife_until = cfg["simulation"].get("wife_side_fire_until", 65)

    total_side_income = 0
    if age_h < husband_until:
        total_side_income += husband_side_income
    if age_w < wife_until:
        total_side_income += wife_side_income

    total_expense = max(0, total_expense - total_side_income)

    return total_expense
```

### 表示 — サイドFIRE効果の可視化

結果表示に「FIRE後労働収入あり」バナーを追加：

```python
if husband_post_fire_income > 0 or wife_post_fire_income > 0:
    st.info(
        f"サイドFIRE設定: 夫 {husband_post_fire_income}万円/月（{husband_side_fire_until}歳まで）、"
        f"妻 {wife_post_fire_income}万円/月（{wife_side_fire_until}歳まで）\n"
        f"FIRE後実質支出 = 支出 − 労働収入 として計算しています。"
    )
```

---

## 実装ステップ

### Step 1: config.yaml にデフォルト値追加

```yaml
simulation:
  side_fire_income: 0
  side_fire_income_until: 65
```

### Step 2: full_app.py — UI追加

FIRE後収入入力欄を「FIRE設定」セクションの末尾に追加。
`_build_simulation_config` の引数に `side_fire_income`, `side_fire_income_until` を追加。

### Step 3: simulator.py — `_compute_post_fire_monthly_expenses` 修正

FIRE後の支出計算に `side_fire_income` を差し引くロジックを追加。

### Step 4: 表示の確認

- 月次支出グラフ（収支グラフ）がある場合はそこにも反映されているか確認
- `base_df` の支出列が正しく反映されているか確認

---

## テスト方針

```bash
python tests/test_simulation_convergence.py
```

**手動確認ケース:**

| 設定 | 期待結果 |
|------|---------|
| サイドFIRE0万円（完全FIRE） | 現状と同じ結果 |
| サイドFIRE5万円/月、65歳まで | FIRE到達年齢が数年早まる |
| サイドFIRE=生活費全額 | FIRE到達年齢が大幅に早まる（資産0でもFIRE可） |

---

## 依存関係・注意事項

- **① 年収入力移行との順序**: ① の完了後に実施することが望ましいが、独立した変更なので先行実施も可能
- **税金計算との整合**: サイドFIRE収入にも所得税・住民税・社会保険料がかかるが、現フェーズでは無視する（正確な税計算は ④ で対応）
- **年金との二重計上**: 年金受給開始後はサイドFIRE収入を止める（`side_fire_income_until` で制御可能）
- **支出がマイナスにならない**: `max(0, total_expense - side_income)` で保護する
- **MCシミュレーションへの影響**: `_compute_post_fire_monthly_expenses` は MC の全パスで呼ばれるため、修正は全パスに自動反映される
