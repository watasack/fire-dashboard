# 詳細実装計画: ⑦ 収支グラフの追加

最終更新: 2026-03-14

---

## 概要

現在のグラフは「資産残高の推移」（ファンチャート）のみ。
競合は「収入・支出の推移」を別グラフで表示しており、「いつ育休で収入が落ちるか」「教育費がいつピークか」が視覚的にわかる。

**追加するグラフ:**
- 積み上げ棒グラフ: 年次収入の内訳（夫収入・妻収入・年金）
- 折れ線グラフ: 年次支出（生活費・住宅費・教育費の合算）
- 面積グラフ: 収支（収入 - 支出）のプラス/マイナス表示

---

## 現状の実装

### visualizer.py — 現在のグラフ

`create_fire_timeline_chart()` がメインチャートを生成。Plotly ベース。
資産残高の中央値ライン + P16/P84 帯（1σ）+ P2.5/P97.5 帯（2σ）を描画。

### base_df の活用

`base_df` は決定論的シミュレーションの結果で、収支グラフのデータソースとして使える。

---

## 変更方針

### グラフ設計

#### グラフ1: 収入推移（積み上げ棒グラフ）

```
年次 | 夫収入（棒・青）| 妻収入（棒・ピンク）| 年金（棒・黄）
     |               FIRE ライン（縦線）
```

#### グラフ2: 支出推移（積み上げ面グラフ）

```
年次 | 生活費（面・赤）| 住宅費（面・橙）| 教育費（面・緑）
```

#### グラフ3（オプション）: 収支バランス

```
年次 | 収支 = 収入 - 支出（正 = 緑棒、負 = 赤棒）
```

### 実装: `src/visualizer.py` に新規関数追加

```python
def create_cashflow_chart(base_df: pd.DataFrame, fire_month: int, cfg: dict) -> go.Figure:
    """
    年次収支グラフを生成する。
    base_df: simulate_future_assets の月次出力
    fire_month: FIRE達成月インデックス
    cfg: config dict（住宅ローン完済日・子ども情報等）
    """
    # 月次 → 年次集計
    df = base_df.copy()
    df["year"] = df["month_idx"] // 12

    annual = df.groupby("year").agg(
        age_h=("age_h", "first"),
        income_h=("income_h", "sum"),      # 夫年間収入
        income_w=("income_w", "sum"),      # 妻年間収入
        pension=("pension_income", "sum"), # 年金収入
        living=("living_expense", "sum"),  # 生活費
        housing=("housing_expense", "sum"),# 住宅費
        education=("edu_expense", "sum"),  # 教育費
    ).reset_index()

    annual_10k = annual / 10000  # 万円単位

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=["年次収入の推移", "年次支出の推移"],
        shared_xaxes=True,
        vertical_spacing=0.12,
    )

    # 収入: 積み上げ棒
    fig.add_trace(go.Bar(
        x=annual_10k["age_h"], y=annual_10k["income_h"],
        name="夫収入", marker_color="#4472C4",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=annual_10k["age_h"], y=annual_10k["income_w"],
        name="妻収入", marker_color="#ED7D31",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=annual_10k["age_h"], y=annual_10k["pension"],
        name="年金", marker_color="#A9D18E",
    ), row=1, col=1)

    # 支出: 積み上げ面
    fig.add_trace(go.Bar(
        x=annual_10k["age_h"], y=annual_10k["living"],
        name="生活費", marker_color="#FF6B6B",
    ), row=2, col=1)
    fig.add_trace(go.Bar(
        x=annual_10k["age_h"], y=annual_10k["housing"],
        name="住宅費", marker_color="#FFA500",
    ), row=2, col=1)
    fig.add_trace(go.Bar(
        x=annual_10k["age_h"], y=annual_10k["education"],
        name="教育費", marker_color="#4CAF50",
    ), row=2, col=1)

    # FIRE タイミングの縦線
    fire_age_h = ...  # fire_month から逆算
    for row in [1, 2]:
        fig.add_vline(
            x=fire_age_h, line_dash="dash", line_color="red",
            annotation_text="FIRE", row=row, col=1,
        )

    fig.update_layout(
        barmode="stack",
        height=600,
        title="収入・支出の年次推移",
        yaxis_title="金額（万円/年）",
        xaxis2_title="夫の年齢",
    )

    return fig
```

### base_df に収入・支出の内訳列を追加

現状の `base_df` が収入・支出の内訳（夫・妻・年金・生活費・住宅費・教育費）を持っていない場合、
`simulate_future_assets` に `include_cashflow_detail=True` オプションを追加して内訳を返す。

```python
# simulator.py の simulate_future_assets
if include_cashflow_detail:
    df["income_h"] = income_h_list
    df["income_w"] = income_w_list
    df["pension_income"] = pension_list
    df["living_expense"] = living_list
    df["housing_expense"] = housing_list
    df["edu_expense"] = edu_list
```

---

## 実装ステップ

### Step 1: `simulate_future_assets` の出力を確認

現在 `base_df` に含まれる列を確認する。
内訳列がない場合は追加する（`include_cashflow_detail=True` オプション）。

### Step 2: `visualizer.py` — `create_cashflow_chart` 関数を実装

Plotly の `make_subplots` で2段グラフを作成。

### Step 3: `full_app.py` — タブ構造に変更

現在のグラフをタブの中に入れ、収支グラフを別タブとして追加：

```python
tab1, tab2, tab3 = st.tabs(["📈 資産推移", "💰 収支推移", "📊 年次テーブル"])

with tab1:
    # 既存の資産ファンチャート
    fig = create_fire_timeline_chart(mc_res, cfg)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    # 新規: 収支グラフ
    fig2 = create_cashflow_chart(mc_res["base_df"], mc_res["fire_month"], cfg)
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    # ⑥ 年次テーブル
    ...
```

---

## テスト方針

**手動確認ケース:**

| ケース | 確認ポイント |
|--------|------------|
| 育休設定あり | 育休中の年に夫/妻収入が下がっている |
| 住宅ローンあり | 完済年以降に住宅費棒が消える |
| 子ども2人 | 教育費の棒が各子どもの学校年齢に対応している |
| 年金65歳開始 | 65歳の年から年金の棒が追加される |
| FIRE年 | 収入の棒が給与→0→年金に変化している |

---

## 依存関係・注意事項

- **⑥ 年次テーブルとの一貫性**: テーブルとグラフで同じ数値を使うよう、`build_annual_table` とデータ源を共有する
- **base_df の内訳列**: `simulate_future_assets` に大きな変更が必要な場合、パフォーマンスへの影響を測定する
- **MCシミュレーションとの関係**: 収支グラフは決定論的 (`base_df`) ベースで表示。MC の確率帯は資産グラフのみ。これで「平均的なパスでの収支推移」が見える
- **育休の表現**: 育休期間を視覚的に示すため、背景色（シェーディング）を追加すると見やすい。`add_vrect()` で実装可能
- **グラフの高さ**: 2段グラフで height=600 を設定。スマートフォン表示ではスクロールが必要になる可能性がある
