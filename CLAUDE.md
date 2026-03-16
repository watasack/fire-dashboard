# CLAUDE.md — Claude Code 向け作業ルール

## 技術スタック

- **フロントエンド**: Next.js 15 / React 19 / TypeScript / Tailwind CSS v4
- **デプロイ**: Vercel（GitHub 連携で自動デプロイ）
- **シミュレーション**: クライアントサイド TypeScript（`lib/simulator.ts`）
- **シミュレーションエンジン**: クライアントサイド TypeScript のみ（Python エンジンは削除済み）

## 必須テスト手順

### 1. Next.js のビルド確認（コード変更後）

```bash
npx next build
```

期待結果: エラーなし・型エラーなし

### 2. Playwright でのビジュアル確認（UI 変更後）

```bash
# pnpm dev を起動した状態で別ターミナルから実行
set PYTHONIOENCODING=utf-8 && python take_screenshot.py
```

出力先: `docs/screenshots/` （result_top.png / full_page.png / assets_chart.png）

**スクリーンショットの運用ルール:**
- `docs/screenshots/` は `.gitignore` 済み → コミットしない
- 実行のたびに同名ファイルで上書き → 蓄積しない
- 確認が終わったらそのままで構わない（次回実行時に上書きされる）
- note記事など外部公開用に使う場合は `docs/screenshots/` 以外の場所にコピーする

**注意: `pnpm dev` は `--turbopack` なしで起動すること（package.json で設定済み）**
Turbopack（Next.js 15.5.12）には React Client Manifest のバグがあり、アプリが起動しない。

## 重要な不変条件

### Recharts + React 19 の非互換

Recharts 2.x は `react-is@16` に依存しており、React 19 のフラグメント（`<>...</>`）を
`ComposedChart` の直接の子として認識できない。

**規則: `ComposedChart` 内の `Area` / `Line` / `Bar` は `<>` で囲まない。**
各コンポーネントを個別の三項演算子（`{cond ? <Area .../> : null}`）で渡すこと。

## ローカル開発

```bash
pnpm dev        # http://localhost:3000 で起動
npx next build  # 本番ビルド確認
```

## 過去の失敗から学んだルール

- **UI 変更は必ず Playwright で動作確認してからプッシュする**
- Recharts の `Area` / `Line` を `<>` フラグメントで囲むと React 19 で描画されない
- SVG の `fill` 属性に CSS 変数（`var(--xxx)`）は使えない → ハードコードした hex 値を使う
- `lib/simulator/`（ディレクトリ）と `lib/simulator.ts`（ファイル）を共存させると TS が解決できない
