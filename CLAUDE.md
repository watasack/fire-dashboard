# CLAUDE.md — Claude Code 向け作業ルール

## 参照ドキュメント

以下のタスクに着手する前に `docs/DEVELOPMENT.md` を読むこと：
- `lib/simulator.ts` の計算ロジック（特に月次処理・NISA・iDeCo）を変更するとき
- Recharts のチャートコンポーネント（`assets-chart.tsx` / `cashflow-chart.tsx`）を変更するとき
- テストの追加・修正をするとき

## 必須テスト手順

コード変更後は以下を実行すること。

```bash
npx next build                                              # 1. ビルド確認
set PYTHONIOENCODING=utf-8 && python tools/take_screenshot.py  # 2. UI変更時のみ
python -X utf8 tools/ui_test.py                              # 3. UI変更時のみ
```

## 重要な不変条件

### Recharts + React 19 の非互換

Recharts 2.x は `react-is@16` に依存しており、React 19 のフラグメント（`<>...</>`）を
`ComposedChart` の直接の子として認識できない。

**規則: `ComposedChart` 内の `Area` / `Line` / `Bar` は `<>` で囲まない。**
各コンポーネントを個別の三項演算子（`{cond ? <Area .../> : null}`）で渡すこと。

## 過去の失敗から学んだルール

- **UI 変更は必ず Playwright で動作確認してからプッシュする**
- `lib/simulator/`（ディレクトリ）と `lib/simulator.ts`（ファイル）を共存させると TS が解決できない
- ライフステージ入力フィールド（`input[type='number'][min=0]`）は React の onChange で `Math.max(0, val)` を明示しないと負の値を受け入れてしまう
