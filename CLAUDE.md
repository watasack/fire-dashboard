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

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1200, 'height': 900})
    page.goto('http://localhost:3001', timeout=30000)
    page.wait_for_timeout(7000)  # React + MC 1000回の計算待ち
    page.screenshot(path='dashboard_screenshots/check.png')
    browser.close()
```

スクリーンショットは `dashboard_screenshots/` に保存（.gitignore 済み）

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
