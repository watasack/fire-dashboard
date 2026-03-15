# impl_12: 詳細診断レポート（HTML/ポータブル形式）の詳細設計

最終更新: 2026-03-15

**※ステータス: 実装済み**
`full_app.py`（L937-1000）の「年次収支テーブル」エクスパンダー内に「診断レポート(HTML)を作成」ボタンが実装済み。
`src/html_generator.py` の `generate_dashboard_html()` を呼び出し、`st.download_button` でHTMLファイルをダウンロード提供。

---

## Goal
リッチなグラフや詳細な内訳を含むシミュレーション結果を、ブラウザで閲覧可能な自己完結型HTMLレポートとして出力します。
これにより、アプリケーションの実行環境がない場所でも、家族やパートナーと診断結果を正確に共有・記録できる「成果物」を提供します。

## User Review Required
> [!IMPORTANT]
> 当初はPDF出力を検討していましたが、本プロジェクトのグラフ（Plotly）の動的な特性（ホバーでの詳細表示、ウォーターフォール図の連動等）を維持するため、**「高度なインタラクティビティを保持した自己完結型HTML」**を出力形式の主軸とします。印刷が必要な場合はブラウザの「PDFとして保存」機能を利用することを推奨します。

## Proposed Changes

### [Component] Report Engine (`src/html_generator.py`)

#### [REUSE] `generate_dashboard_html`
既に存在する `src/html_generator.py` (37KB) は、Plotlyグラフ、KPIパネル、ライフイベント履歴を包含したシングルページダッシュボードを生成可能です。この機能をレポート出力用としてラッピングします。

- 外部依存（CSS/JS）のインライン化、またはReliableなCDN参照（現状維持）を確実に行い、単体ファイルで動作するように調整します。

### [Component] UI Integration (`full_app.py`)

#### [NEW] 「診断レポートを出力」ボタン
シミュレーション完了後、サマリーセクションの横にダウンロードボタンを設置します。
`st.download_button` を使用し、オンメモリで生成したHTML文字列を提供します。

```python
# 実装イメージ
report_html = generate_dashboard_html(charts, summary_data, action_items, config)
st.download_button(
    label="診断レポート(HTML)を保存",
    data=report_html,
    file_name="FIRE_Diagnostic_Report.html",
    mime="text/html"
)
```

---

## Verification Plan

### Automated Tests
- `tests/test_report_generation.py` を作成。
- `generate_dashboard_html` が例外なく実行され、出力文字列に必須のキーワード（例：`class="dashboard-container"`, `Plotly.newPlot`）が含まれていることをアサーション。

### Manual Verification
1. シミュレーションを実行し、出力されたボタンをクリック。
2. 保存された `FIRE_Diagnostic_Report.html` を別のブラウザ（例：Edge, Chrome）で単体開き、アプリ上と同じグラフが表示・操作できることを確認。
3. ネット接続がない環境（オフライン想定）でも、CDNキャッシュが効いていれば基本機能が見られるか確認。
