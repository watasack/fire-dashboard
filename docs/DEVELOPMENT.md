# 開発者向けガイド

このドキュメントは FIRE Simulator（Next.js / TypeScript 実装）の開発者向けガイドです。

---

## プロジェクト構造

```
.
├── app/
│   ├── page.tsx                 # メインページ（UI エントリポイント）
│   └── layout.tsx               # レイアウト
├── lib/
│   └── simulator.ts             # シミュレーションエンジン本体（最重要）
├── components/                  # UI コンポーネント
├── __tests__/
│   └── simulator.test.ts        # 計算整合性テスト（vitest）
├── docs/
│   ├── DEVELOPMENT.md           # このファイル
│   ├── content/                 # note 記事・マーケティングコンテンツ
│   ├── plans/                   # 機能設計書・競合調査
│   └── screenshots/             # ビジュアルテスト用（.gitignore 済み）
├── tools/
│   └── take_screenshot.py       # Playwright スクリーンショットツール
├── CLAUDE.md                    # Claude Code 向け作業ルール
└── README.md                    # シミュレーション仕様書
```

---

## クイックスタート

### 開発サーバー起動

```bash
pnpm dev
# → http://localhost:3000
```

**注意**: `--turbopack` なしで起動すること（`package.json` で設定済み）。
Turbopack（Next.js 15.5.12）には React Client Manifest のバグがあり、アプリが起動しない。

### テスト実行

```bash
npx vitest run
```

**期待される結果**: 全テスト pass（156テスト・約0.3秒）

### 本番ビルド確認

```bash
npx next build
```

**期待される結果**: エラーなし・型エラーなし

### ビジュアル確認（UI 変更後）

```bash
# pnpm dev を起動した状態で別ターミナルから実行
set PYTHONIOENCODING=utf-8 && python tools/take_screenshot.py
```

出力先: `docs/screenshots/`（result_top.png / full_page.png / assets_chart.png）

---

## 開発ガイドライン

### NISA 計算の注意点

#### 重要な不変条件

```typescript
// 常に成立すべき条件
assert nisaAssets <= stocks, "NISA残高は株式残高を超えてはならない"
```

NISA 残高は株式資産の一部であるため、この条件は常に真でなければなりません。

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

### SVG の fill に CSS 変数は使えない

SVG の `fill` 属性に `var(--color)` は使用不可。ハードコードした hex 値を使う。

### simulator.ts のモジュール解決

`lib/simulator/`（ディレクトリ）と `lib/simulator.ts`（ファイル）を共存させると
TypeScript がモジュールを解決できない。必ずどちらか一方にすること。

---

## コード変更時のチェックリスト

月次処理ロジックを変更する際は、以下を確認してください：

- [ ] NISA 残高への運用リターン適用を忘れていないか？
- [ ] `npx next build` が通るか（型エラーなし）？
- [ ] `npx vitest run` が全 pass か？
- [ ] UI 変更がある場合、Playwright スクリーンショットで確認したか？

---

## テストの実行

### 計算整合性テスト

```bash
npx vitest run
```

`__tests__/simulator.test.ts` に 156 件のテストが定義されています。

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
pnpm dev &
set PYTHONIOENCODING=utf-8 && python tools/take_screenshot.py
```

スクリーンショットの運用ルール:
- `docs/screenshots/` は `.gitignore` 済み → コミットしない
- 実行のたびに同名ファイルで上書き
- note 記事等の外部公開用は `docs/screenshots/` 以外にコピーする

---

## トラブルシューティング

### テストが失敗する場合

```bash
# 失敗したテストだけを詳細表示
npx vitest run --reporter=verbose
```

#### 症状: NISA 残高が株式残高を超える

NISA 計算ロジックにバグがあります。以下を確認：

1. 売却処理で `nisaAssets` が正しく減少しているか
2. 運用リターンが `stocks` と `nisaAssets` の両方に適用されているか
3. 自動投資後に不変条件が維持されているか

#### 症状: MC 中央値と標準シミュレーションの乖離が大きい

```
原因の多くは NISA 残高への運用リターン適用漏れ
```

`lib/simulator.ts` の FIRE 後処理で `nisaAssets *= (1 + monthlyReturnRate)` が
実行されているか確認してください。

### ビルドが失敗する場合

```bash
npx next build 2>&1 | head -50
```

型エラーが出た場合は `lib/simulator.ts` のインターフェース定義と
`app/page.tsx` の呼び出し側の整合性を確認してください。

---

## コミットメッセージ規約

以下のプレフィックスを使用してください：

- `fix:` — バグ修正
- `feat:` — 新機能追加
- `refactor:` — リファクタリング
- `test:` — テスト追加・修正
- `docs:` — ドキュメント更新
- `chore:` — ビルド・設定変更

スコープ例: `feat(simulator):`, `fix(ui):`, `test(simulator):`

**例:**
```
feat(simulator): 配偶者控除の実装

配偶者所得に応じた控除額を計算する calculateSpouseDeduction を追加。
夫婦間で相互に適用し、配偶者所得 ≤48万→38万控除、48〜133万→逓減テーブル。

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

---

## バージョン履歴（主要マイルストーン）

### 2026-03-20: 5機能追加（Python エンジンとの機能ギャップ解消）

- 産休・育休: `MaternityLeaveEntry`（月単位精度）を追加
- 住宅メンテナンス費用: `MaintenanceCost`（周期型）を追加
- 配偶者控除: `calculateSpouseDeduction` を追加
- 教育費: 文科省令和3年度データに修正 + 0〜2歳保育費追加
- ガードレール: ライフステージ別裁量支出比率（総務省家計調査ベース）を追加

### 2026-03-17〜19: Phase 1〜10 実装完了（TypeScript 移行）

Python エンジン（`src/simulator.py`）の全機能を TypeScript に移植完了。

- Phase 1: 年収（税引き前）入力 + 税計算
- Phase 2: 産休育休・ライフイベント
- Phase 3: 年金計算（厚生年金・国民年金）
- Phase 4: 資産管理（NISA/iDeCo・現金管理戦略）
- Phase 5: セミ FIRE / FIRE 後収入
- Phase 6: FIRE 後税金計算（国保・住民税）
- Phase 7: 取り崩し戦略（固定・割合・ガードレール）
- Phase 8: UI 拡張（年次テーブル・収支グラフ）
- Phase 9: MC シミュレーション精度向上（平均回帰・ブートストラップ）
- Phase 10: シナリオ比較（A/B テスト）

---

## 参考資料

- [README.md](../README.md) — シミュレーション仕様書
- [CLAUDE.md](../CLAUDE.md) — Claude Code 向け作業ルール
- [docs/plans/feature_gap_plan.md](plans/feature_gap_plan.md) — 実装状況サマリー
