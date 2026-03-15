# 詳細実装計画: ⑥ 年次収支テーブルの表示

最終更新: 2026-03-15

---

## 概要

**※ステータス: 実装済み**
`full_app.py` の `build_annual_table()` 関数（L339-363）および「年次収支テーブル（詳細）」エクスパンダー（L898-935）として実装済み。
FIRE後行のハイライト・CSVダウンロードボタンも含む。

---

（以下、過去の計画メモとして残す）

競合（Life Plan Designer）は年次の収支・資産推移を表形式で表示する。
グラフでは読み取りにくい「○年に住宅ローン完済」「○年に教育費ピーク」などの数字が一目でわかる。

**追加する表示:**
- 現在〜90歳までの年次テーブル
- 列: 年齢（夫/妻）、年収入（夫/妻）、年支出、年収支、年末資産残高

---

## 現状の実装

### `base_df` の構造

`run_mc_fixed_fire` が返す `base_df` は決定論的シミュレーションの月次データ。

```python
# base_df の列（推定）
base_df.columns = [
    "month_idx",       # 月インデックス
    "total_assets",    # 資産残高（円）
    "monthly_income",  # 月次収入（円）
    "monthly_expense", # 月次支出（円）
    "age_h",           # 夫年齢
    "age_w",           # 妻年齢
]
```

実際の列名は `simulator.py` の `simulate_future_assets` 返り値を確認して決定する必要がある。

---

## 変更方針

### 月次 → 年次の集計処理

```python
# full_app.py — 年次テーブル生成

def build_annual_table(base_df: pd.DataFrame, fire_month: int) -> pd.DataFrame:
    """月次 DataFrame から年次集計テーブルを作成"""
    df = base_df.copy()

    # 年次グループ（シミュレーション開始年 = 0年目）
    df["year"] = df["month_idx"] // 12

    annual = df.groupby("year").agg(
        age_h=("age_h", "first"),
        age_w=("age_w", "first"),
        annual_income=("monthly_income", "sum"),
        annual_expense=("monthly_expense", "sum"),
        year_end_assets=("total_assets", "last"),
    ).reset_index()

    # 年収支
    annual["annual_cashflow"] = annual["annual_income"] - annual["annual_expense"]

    # FIRE前後フラグ
    annual["is_post_fire"] = annual["year"] * 12 >= fire_month

    # 住宅ローン完済年の判定（支出が大きく変化した年）
    annual["note"] = ""
    # 住宅ローン完済年: mortgage_end_date と突き合わせる
    # 教育費発生年: 子どもの年齢が6/12/15/18になる年

    # 表示用フォーマット
    annual["age_display"]    = annual["age_h"].apply(lambda x: f"{x:.0f}歳")
    annual["income_display"] = annual["annual_income"].apply(lambda x: f"{x/10000:.0f}万")
    annual["expense_display"]= annual["annual_expense"].apply(lambda x: f"{x/10000:.0f}万")
    annual["cashflow_display"]= annual["annual_cashflow"].apply(
        lambda x: f"+{x/10000:.0f}万" if x >= 0 else f"{x/10000:.0f}万"
    )
    annual["assets_display"] = annual["year_end_assets"].apply(lambda x: f"{x/10000:.0f}万")

    return annual
```

### 表示 — Streamlit データフレーム表示

```python
# full_app.py

with st.expander("📊 年次収支テーブル（詳細）", expanded=False):
    annual_df = build_annual_table(mc_res["base_df"], mc_res["fire_month"])

    # 表示列を選択
    display_df = annual_df[[
        "age_display", "income_display", "expense_display",
        "cashflow_display", "assets_display"
    ]].rename(columns={
        "age_display":     "夫年齢",
        "income_display":  "年収入",
        "expense_display": "年支出",
        "cashflow_display":"年収支",
        "assets_display":  "年末資産",
    })

    # FIRE後の行を色付け（pandas Styler）
    def highlight_post_fire(row_idx):
        is_fire = annual_df.iloc[row_idx]["is_post_fire"]
        return ["background-color: #e8f4fd" if is_fire else ""] * len(display_df.columns)

    st.dataframe(
        display_df.style.apply(highlight_post_fire, axis=1),
        use_container_width=True,
        height=400,  # スクロール可能な高さ
    )

    # CSV ダウンロードボタン
    csv = annual_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "📥 CSVダウンロード",
        data=csv,
        file_name="fire_simulation.csv",
        mime="text/csv",
    )
```

---

## base_df の列名確認

`simulator.py` の `simulate_future_assets` 関数の返り値を確認して、
実際の列名に合わせて `build_annual_table` の列参照を修正する必要がある。

現在の `base_df` が持つであろう列（要コード確認）:
- 月次資産残高は確実に含まれる（グラフ描画に使われているため）
- 月次収入・支出が別列になっているか、収支のみかは要確認

もし月次収入・支出が `base_df` に含まれていない場合は、
`simulate_future_assets` に `include_cashflow=True` オプションを追加する。

---

## 実装ステップ

### Step 1: `base_df` の実際の列名を確認

```python
# デバッグコード（実装前に確認）
mc_res = run_mc_fixed_fire(...)
print(mc_res["base_df"].columns.tolist())
print(mc_res["base_df"].head(3))
```

### Step 2: `simulate_future_assets` — 収入・支出を `base_df` に追加（必要な場合）

現状 `base_df` に収入・支出が含まれていない場合、シミュレーター側で追加する。

### Step 3: `build_annual_table` 関数を `full_app.py` に実装

月次集計 → 年次集計 → 表示用フォーマット。

### Step 4: 結果表示に `st.expander` でテーブルセクション追加

デフォルトは折りたたみ（expanded=False）で、メイン画面をすっきり保つ。

### Step 5: CSV ダウンロードボタンの実装

---

## テスト方針

**手動確認ケース:**

| ケース | 確認ポイント |
|--------|------------|
| 住宅ローンあり | 完済年に年支出が大きく減少する |
| 子ども2人 | 教育費が発生する年齢で支出増加が確認できる |
| FIRE前後 | FIRE年に収入が大きく変化し、FIRE後行が色付けされる |
| 年金受給開始（65歳） | 65歳の年に収入が増加する |

---

## 依存関係・注意事項

- **`base_df` の構造に依存**: 実際の列名を確認してから実装する
- **月次 → 年次集計の境界**: `month_idx // 12` で年グループを作成するが、シミュレーション開始月が暦年1月でない場合にズレが生じる。「シミュレーション年数」として扱い、実際の暦年との対応は別途計算する
- **「収入」の定義**: 育休中の給付金・FIRE後の年金も「収入」として含める。内訳を別列で持つか、合算値のみにするかは UI の複雑さと相談
- **データ量**: 35歳から90歳まで = 55年 = 55行。テーブルとして扱いやすいサイズ
- **パフォーマンス**: `base_df` は決定論的シミュレーションの結果なので、再計算コストは低い
