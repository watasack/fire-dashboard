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
set PYTHONIOENCODING=utf-8 && python tools/take_screenshot.py
```

出力先: `docs/screenshots/` （result_top.png / full_page.png / assets_chart.png / mobile_top.png / mobile_chart.png）

**スクリーンショットの運用ルール:**

| ディレクトリ | 用途 | git管理 |
|---|---|---|
| `docs/screenshots/` | UIテスト・確認用（仮置き） | `.gitignore` 済み・コミット不可 |
| `docs/images/note/` | note記事用の確定画像 | **git管理・コミット対象** |

- `docs/screenshots/` は実行のたびに同名ファイルで上書き → 蓄積しない
- note記事に使う画像が確定したら `--confirm` オプションで `docs/images/note/` にコピーする

```bash
# 撮影のみ（仮置き）
set PYTHONIOENCODING=utf-8 && python tools/take_screenshot.py

# 撮影 + note用ディレクトリに確定コピー
set PYTHONIOENCODING=utf-8 && python tools/take_screenshot.py --confirm
```

**注意: `pnpm dev` は `--turbopack` なしで起動すること（package.json で設定済み）**
Turbopack（Next.js 15.5.12）には React Client Manifest のバグがあり、アプリが起動しない。

### 3. 網羅的 UI テスト（全ボタン・スイッチ・タブの動作確認）

```bash
# pnpm dev を起動した状態で別ターミナルから実行
python -X utf8 tools/ui_test.py
```

**テスト対象 (211項目 = デスクトップ 117 + モバイル 94):**

**デスクトップ (1440px) — 117項目:**
- 初期ロード: ページタイトル・ヘッダー・KPIバナー（FIRE達成年齢・成功率）・タブ数確認
- メインタブ切り替え: 資産推移 / 収支 / 年次表 / 次の一手（アクティブ状態・コンテンツ表示）
- 設定パネルタブ切り替え: 基本 / 収入 / 投資 / ライフ / 詳細
- 基本タブ: 資産スライダー→KPI更新・詳細入力展開・合算表示に戻す・生活費モード切替
- 収入タブ: 配偶者スイッチON/OFF・雇用形態セレクト・時短勤務スイッチON/OFF
- 収入タブ追加: 本人スライダー→KPI更新・**産休育休チェックボックス**・**配偶者詳細（雇用形態・時短勤務スイッチ）**
- 投資タブ: NISAスイッチON/OFF・iDeCoスイッチON/OFF
- 投資タブ追加: **期待リターン/リスク/SWRスライダー→KPI更新**
- ライフタブ: セミFIREスイッチON/OFF・住宅ローンスイッチON/OFF
- ライフタブ追加: **子ども数スライダー・誕生年セクション展開確認・教育費パターン3種ボタン・児童手当スイッチ確認**
- 詳細タブ: モンテカルロスイッチ・取り崩し戦略3種・社会保険料詳細展開・リセット
- 詳細タブ追加: **シミュレーション期間スライダー→KPI更新・インフレ率スライダー・ガードレール詳細スライダー個数確認(17個)**
- Info(?)ボタン: ツールチップ展開（3ボタン確認）
- シナリオ比較: 「この設定を試す →」ボタン → KPI更新確認
- リンクをコピー: テキスト変化 → 2秒後復帰
- レイアウト崩れ: 横スクロール発生なし・2カラムグリッド・チャート描画（資産推移/収支/年次表）
- コンソールエラー・警告: 0件確認
- **X-1: URL状態復元** — シェアURLで設定が完全復元されるか（セミFIREスイッチ・KPI値一致）
- **X-2: KPI変動方向** — 資産増加→FIRE年齢改善・生活費増加→悪化・NISA ON→改善
- **X-3: ブレークポイント遷移** — 1023px/1024px でモバイル↔デスクトップ切り替え・横スクロールなし
- **X-4: ライフステージ数値入力** — 8フィールド確認・KPI更新・負の値→0正規化
- **X-5: ガードレールUIクリーンアップ** — 戦略切替でスライダー増減・裁量支出比率の表示/非表示
- **X-6: 複数機能同時ON** — NISA+iDeCo・セミFIRE+住宅ローン・配偶者+時短の組み合わせ

**モバイル (375px) — 94項目:**
- 初期ロード: タイトル・ヘッダー・KPI・アコーディオン5セクション存在・4タブ存在
- メインタブ切り替え: 4タブ全て（アクティブ状態・コンテンツ表示）
- アコーディオン全5セクション開閉: 基本設定/収入/投資/ライフ/詳細設定
- 基本設定アコーディオン: 資産スライダー→KPI更新・詳細入力展開・生活費モード切替
- 収入アコーディオン: 配偶者スイッチON/OFF・雇用形態セレクト・時短勤務スイッチON/OFF
- 収入アコーディオン追加: **産休育休チェックボックス・配偶者詳細（雇用形態・時短勤務）**
- 投資アコーディオン: NISAスイッチON/OFF・iDeCoスイッチON/OFF・投資スライダー→KPI更新
- 投資アコーディオン追加: **期待リターン/リスク/SWRスライダー→KPI更新**
- ライフアコーディオン: セミFIREスイッチON/OFF・住宅ローンスイッチON/OFF・スライダー操作
- ライフアコーディオン追加: **子ども数スライダー・教育費パターン3種・児童手当セクション確認**
- 詳細設定アコーディオン: モンテカルロスイッチ・取り崩し戦略3種・社会保険料詳細
- 詳細設定追加: **シミュレーション期間・インフレ率スライダー・ガードレール詳細スライダー個数確認(17個)**
- Info(?)ボタン: ツールチップ展開（アコーディオン内）
- シナリオ比較: 「この設定を試す →」ボタン → KPI更新確認
- リンクをコピー: テキスト変化 → 2秒後復帰
- レイアウト崩れ: 横スクロール発生なし・KPIバナー幅・チャート描画・ヘッダー幅
- **M-X2: KPI変動方向** （デスクトップ X-2 相当）
- **M-X4: ライフステージ数値入力** （デスクトップ X-4 相当）
- **M-X5: ガードレールUIクリーンアップ** （デスクトップ X-5 相当）
- **M-X6: 複数機能同時ON** （デスクトップ X-6 相当）

**実装上の注意:**
- モバイルアコーディオントリガー: `button[data-radix-collection-item]`（`data-slot` ではない）
- アコーディオンコンテンツ: `role=region`（aria-controls で紐付け）
- モバイルの tabpanel は複数存在するため `[data-state='active']` かつ `is_visible()` で判定
- デスクトップ設定パネルの tabpanel: `.not-lg:hidden [role='tabpanel'][data-state='active']` でアクティブを取得（`.first` では基本タブのパネルを掴む）
- デスクトップとモバイルは `browser.new_context()` で完全分離（localStorage 汚染防止）
- モバイルページ初期ロード後 KPI が "—" なら自動リロード（dev server 遅延対策）
- Next.js dev mode の CSS preload 警告は除外（本番ビルドでは発生しない）

**出力:** `docs/screenshots/test_*.png`（各セクションのスクリーンショット）

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

## AI Agent Harness

AIエージェントが機能実装→検証→レビューのループを自動で回すためのフレームワーク。
Anthropic の GAN パターン（Generator/Evaluator 分離）に基づく設計。

**詳細な使い方:** `docs/harness-guide.md` を参照。

### コマンド一覧

| コマンド | 役割 | 説明 |
|---|---|---|
| `/harness-contract` | Orchestrator | スプリント契約を作成 |
| `/harness-generate` | Generator | 契約に基づきコードを実装 + 自動検証 |
| `/harness-evaluate` | Evaluator | 独立した視点でコード変更をレビュー |
| `/harness-review` | Reviewer | 既存コード・UI/UXのレビュー・監査 |

### 検証パイプライン

```bash
# 全ステージ実行（pnpm dev 起動済み前提）
python -X utf8 tools/verify.py

# ビルド + ユニットテストのみ（高速）
python -X utf8 tools/verify.py --stages build,unit
```

### ファイル構成

```
.plans/harness/
  contracts/
    active.md              # 現在の契約ID
    _template.md           # 契約テンプレート
    sprint-NNN.md          # 各スプリント契約
  verification-report.md   # verify.py の出力（git管理外）
  generator-report.md      # Generator の完了報告（git管理外）
  evaluation-report.md     # Evaluator のレビュー結果（git管理外）
  review-report.md         # Reviewer のレビュー結果（git管理外）
```

### ワークフロー

```
1. /harness-contract → 契約作成
2. pnpm dev を起動
3. /harness-generate → 実装 + 自動検証
4. /harness-evaluate → 独立レビュー
5. REVISE なら → /harness-generate（修正モード）
6. APPROVED なら → git diff 確認 → コミット

# レビュー・監査（実装なし）
/harness-review UI全体の操作性を確認して
/harness-review simulator.ts の年金計算が仕様通りか監査して
/harness-review 直近5コミットのリグレッションリスクを確認して
```

## 過去の失敗から学んだルール

- **UI 変更は必ず Playwright で動作確認してからプッシュする**
- Recharts の `Area` / `Line` を `<>` フラグメントで囲むと React 19 で描画されない
- SVG の `fill` 属性に CSS 変数（`var(--xxx)`）は使えない → ハードコードした hex 値を使う
- `lib/simulator/`（ディレクトリ）と `lib/simulator.ts`（ファイル）を共存させると TS が解決できない
- ライフステージ入力フィールド（`input[type='number'][min=0]`）は React の onChange で `Math.max(0, val)` を明示しないと負の値を受け入れてしまう
