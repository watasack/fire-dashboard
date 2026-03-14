# impl_11: シナリオ比較（ABテスト機能）の詳細設計

## Goal
「標準プラン」と「比較用プラン（例：教育費増額、FIRE時期変更）」を同一のグラフ上に重ねて表示し、意思決定の判断材料を提供します。
これまでの「1つのシナリオを上書きし続ける」モデルから、「複数の結果をメモリ上で保持・比較する」モデルへ拡張します。

## User Review Required
> [!IMPORTANT]
> シナリオ比較時にはグラフの凡例が複雑になります。モンテカルロの信頼区間（95%区間など）を両方のシナリオで表示すると視認性が低下するため、比較モード時は「中央値のラインのみ」または「片方の信頼区間を半透明化」するなどのUI上の工夫が必要です。

## Proposed Changes

### [Component] Visualization Logic (`src/visualizer.py`)

#### [MODIFY] `create_fire_timeline_chart` (L698付近)
現在 `simulations['standard']` に固定されているプロットロジックを、辞書内の全キーをループ処理するように汎用化します。

```python
# 修正イメージ
for scenario_name, df in simulations.items():
    color = colors.get(scenario_name, default_color)
    # 中央値のプロット
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['median'],
        name=f"{scenario_name} (中央値)",
        line=dict(color=color, width=3)
    ))
    # 信頼区間のプロット（比較時はオプション化）
```

### [Component] UI State Management (`full_app.py`)

#### [MODIFY] シミュレーション実行ロジック
`st.button` 押下時の結果を `st.session_state` に特定のラベル（例：`scenario_a`, `scenario_b`）で保存する仕組みを追加します。
「現在の結果をプランAとして固定」ボタンを設置し、その後のパラメータ変更による結果と対比させます。

---

## Verification Plan

### Automated Tests
- `tests/test_visualizer_multi.py` を作成。
- `simulations` 辞書に2つのデータフレームを渡した際、Plotlyの `data` 配列に期待される数のトレース（ライン）が含まれていることを確認。

### Manual Verification
1. 標準設定で「計算実行」し、その結果を「プランA」として保存。
2. パラメータ（例：年間支出を+50万）を変更して再度「計算実行」。
3. 同一グラフ上に青（プランA）と赤（プランB）の2本のラインが表示され、資産枯渇時期の差が視覚的に把握できることを確認。
