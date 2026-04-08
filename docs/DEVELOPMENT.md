# 開発者向けガイド

FIRE Simulator（Next.js / TypeScript）の開発者向けガイドです。

---

## プロジェクト構造

```
.
├── app/
│   ├── page.tsx                 # メインページ（UI エントリポイント）
│   ├── layout.tsx               # レイアウト
│   ├── globals.css              # グローバルスタイル
│   ├── faq/page.tsx             # FAQ ページ
│   └── api/                     # API ルート（ping, validate）
├── components/
│   ├── fire/                    # FIRE 機能コンポーネント
│   └── ui/                      # 汎用 UI コンポーネント（shadcn/ui）
├── lib/
│   ├── simulator.ts             # シミュレーションエンジン本体（最重要）
│   ├── auth.ts                  # アクセスコード認証
│   ├── url-state.ts             # URL 状態シリアライズ
│   └── utils.ts                 # ユーティリティ
├── __tests__/
│   └── simulator.test.ts        # 計算整合性テスト（vitest）
├── docs/
│   ├── DEVELOPMENT.md           # このファイル
│   ├── content/                 # note 記事・マーケティングコンテンツ
│   ├── plans/                   # 機能設計書・競合調査
│   ├── images/note/             # note 記事用の確定画像（git 管理）
│   └── screenshots/             # ビジュアルテスト用（.gitignore 済み）
├── tools/
│   ├── take_screenshot.py       # Playwright スクリーンショットツール
│   ├── ui_test.py               # 網羅的 UI テスト（211項目）
│   └── generate-codes.ts        # アクセスコード生成
├── CLAUDE.md                    # Claude Code 向け作業ルール
└── README.md                    # シミュレーション仕様書
```

---

## クイックスタート

```bash
pnpm dev          # 開発サーバー起動 → http://localhost:3000
npx next build    # 本番ビルド確認
npx vitest run    # ユニットテスト（162テスト）
```

---

## 開発ガイドライン

### NISA 計算の注意点

#### 重要な不変条件

```typescript
// 常に成立すべき条件
assert cashAssets >= 0 && stocks >= 0 && nisaAssets >= 0 && idecoAssets >= 0
assert nisaTotalContributed <= nisaLifetimeLimit  // NISA 生涯拠出上限
assert Number.isFinite(全資産フィールド)           // NaN/Infinity なし
```

NISA 口座と課税口座は独立して管理される。NISA への優先投資により
`nisaAssets > stocks` となることがある（非課税枠の活用として正常な動作）。

取り崩し順序は「現金→課税口座→その他→NISA（FIRE後のみ）」で、
非課税口座を最後まで温存する設計になっている。

#### NISA 残高の更新タイミング

1. **新規投資時**: `nisaAssets += 投資額`
2. **運用リターン適用時**: `nisaAssets *= (1 + monthlyReturnRate)` ⚠️ **必須**
3. **売却時**: `nisaAssets -= 売却額`

運用リターン適用を忘れると NISA 残高が実際より低くなり、
標準シミュレーションと MC シミュレーションの間に大きな乖離が発生します。

### Recharts + React 19 の非互換

Recharts 2.x は `react-is@16` に依存しており、React 19 のフラグメント（`<>...</>`）を
`ComposedChart` の直接の子として認識できない。

**規則: `ComposedChart` 内の `Area` / `Line` / `Bar` は `<>` で囲まない。**

```tsx
// ✅ OK
{showArea ? <Area key="a" ... /> : null}
{showLine ? <Line key="b" ... /> : null}

// ❌ NG
{showArea && showLine && (
  <>
    <Area ... />
    <Line ... />
  </>
)}
```

### simulator.ts のモジュール解決

`lib/simulator/`（ディレクトリ）と `lib/simulator.ts`（ファイル）を共存させると
TypeScript がモジュールを解決できない。必ずどちらか一方にすること。

---

## テストの実行

### 計算整合性テスト

```bash
npx vitest run
```

**検証内容:**
- 収入計算（給与所得控除・税計算・産休育休給付金）
- 配偶者控除
- 教育費（文科省データ準拠・0〜2歳保育費含む）
- 年金計算（厚生年金・国民年金・マクロ経済スライド）
- NISA / iDeCo の取り崩し計算
- 取り崩し戦略（固定・割合・ガードレール）
- モンテカルロシミュレーション
- シナリオ比較

### ビジュアルテスト（UI 変更後）

```bash
# pnpm dev を起動した状態で別ターミナルから実行
set PYTHONIOENCODING=utf-8 && python tools/take_screenshot.py

# note記事用に確定コピーする場合
set PYTHONIOENCODING=utf-8 && python tools/take_screenshot.py --confirm
```

| ディレクトリ | 用途 | git管理 |
|---|---|---|
| `docs/screenshots/` | UIテスト・確認用（仮置き・上書き） | `.gitignore` 済み・コミット不可 |
| `docs/images/note/` | note記事用の確定画像 | **git管理・コミット対象** |

### 網羅的 UI テスト（全ボタン・スイッチ・タブの動作確認）

```bash
python -X utf8 tools/ui_test.py
```

デスクトップ117項目 + モバイル94項目 = 計211項目を自動テスト。

---

## コード変更時のチェックリスト

- [ ] `npx next build` が通るか（型エラーなし）？
- [ ] `npx vitest run` が全 pass か？
- [ ] NISA 残高への運用リターン適用を忘れていないか？（月次処理変更時）
- [ ] UI 変更がある場合、Playwright スクリーンショットで確認したか？

---

## トラブルシューティング

### テストが失敗する場合

```bash
npx vitest run --reporter=verbose
```

#### 症状: NISA 残高が負の値になる

1. 売却処理で `nisaAssets` の売却額が残高を超えていないか
2. `Math.max(0, newNisa)` のガードが適用されているか
3. FIRE 前に NISA から取り崩していないか（NISA 売却は FIRE 後のみ）

> **注意**: `nisaAssets > stocks` は正常な状態。NISA に優先投資するため、
> 課税口座より NISA 残高が大きくなることがある。

#### 症状: MC 中央値と標準シミュレーションの乖離が大きい

原因の多くは NISA 残高への運用リターン適用漏れ。
`lib/simulator.ts` の FIRE 後処理で `nisaAssets *= (1 + monthlyReturnRate)` が
実行されているか確認してください。

### ビルドが失敗する場合

型エラーが出た場合は `lib/simulator.ts` のインターフェース定義と
`app/page.tsx` の呼び出し側の整合性を確認してください。

---

## コミットメッセージ規約

プレフィックス: `fix:` / `feat:` / `refactor:` / `test:` / `docs:` / `chore:`

スコープ例: `feat(simulator):`, `fix(ui):`, `test(simulator):`

---

## 参考資料

- [README.md](../README.md) — プロジェクト概要
- [SPECIFICATION.md](SPECIFICATION.md) — シミュレーション仕様書
- [CLAUDE.md](../CLAUDE.md) — Claude Code 向け作業ルール
