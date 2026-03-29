# AI Agent Harness 使い方ガイド

FIRE Dashboard プロジェクト向けの AI エージェントハーネス。
Anthropic の [Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps) に基づく設計。

---

## 概要

ハーネスは **4つの slash command** で構成されています。

| コマンド | 役割 | いつ使うか |
|---|---|---|
| `/harness-contract` | 契約作成 | 新機能やバグ修正を始めるとき |
| `/harness-generate` | 実装 + 自動検証 | 契約に基づいてコードを書かせるとき |
| `/harness-evaluate` | 独立レビュー | 実装結果を評価させるとき |
| `/harness-review` | 既存コード・UIの監査 | 実装なしでレビューだけしたいとき |

---

## 前提条件

- Claude Code がインストール済み
- Node.js + pnpm が利用可能
- Playwright がインストール済み（UIテスト・スクリーンショット用）

---

## 使い方 1: 機能を実装する

### ターミナル構成

```
ターミナルA: Claude Code（全ての slash command を実行）
ターミナルB: pnpm dev（起動しっぱなし）
```

### Step 1: 契約を作る

```
/harness-contract 教育費にインフレ率を適用する機能を追加したい
```

Claude が以下を自動で行います:
- コードベースを調査して影響範囲を特定
- `.plans/harness/contracts/sprint-001.md` に契約ファイルを生成
- `.plans/harness/contracts/active.md` を更新

**契約ファイルの内容:**
- Scope: 何を実装するか（In Scope / Out of Scope）
- Affected Files: 変更するファイル一覧
- Acceptance Criteria: 合格条件
- Known Pitfalls: 既知の落とし穴

契約内容が表示されるので、修正があればその場で伝えてください。

### Step 2: dev server を起動

```bash
# ターミナルB
pnpm dev
```

UIテスト・スクリーンショットの検証に必要です。
ビルドとユニットテストのみで十分な場合は不要です。

### Step 3: 実装を実行

```
/harness-generate
```

Claude が以下を自動で行います:
1. 契約ファイルを読む
2. CLAUDE.md のルールを確認
3. コードを実装
4. `tools/verify.py` で自動検証（Build → Unit Tests → UI Tests → Screenshots）
5. 失敗したら修正して再実行（最大3回）
6. `.plans/harness/generator-report.md` に完了報告を書く

### Step 4: 独立レビュー

```
/harness-evaluate
```

Claude が **Generator の会話を忘れた状態で** 以下をチェックします:
- シミュレーション正確性（数式が仕様と一致するか）
- UI品質（スクリーンショット確認）
- コード品質（型安全性、パターン準拠）
- 仕様準拠（契約の Acceptance Criteria を満たすか）

**判定結果:**

| Verdict | 意味 | 次のアクション |
|---------|------|----------------|
| APPROVED | 問題なし | git diff を確認してコミット |
| REVISE | 修正が必要 | `/harness-generate` を再実行 |
| REJECT | 根本的な問題 | 契約を見直す |

### Step 5: 修正ループ（REVISE の場合）

```
/harness-generate
```

Generator は evaluation-report.md の Issues を読み、修正して再検証します。
最大2回の修正ループ後、まだ REVISE なら人間にエスカレーションされます。

### Step 6: コミット

Evaluator が APPROVED を出したら:
```bash
git diff          # 変更内容を確認
git add ...       # 必要なファイルをステージ
git commit -m "feat: ..."
```

---

## 使い方 2: 既存コード・UIをレビューする

実装なしで、現状のコードやUIを監査します。

### UI/UX レビュー

```
/harness-review UI全体の操作性を確認して
/harness-review モバイルのレイアウトが崩れていないか確認して
/harness-review KPIカードとチャートの情報階層を評価して
```

スクリーンショットを撮影して目視確認し、レイアウト・一貫性・操作性をチェックします。
`pnpm dev` が起動している必要があります。

### シミュレーション監査

```
/harness-review simulator.ts の年金計算が仕様通りか監査して
/harness-review NISA の取り崩しロジックが正しいか確認して
/harness-review 教育費計算の境界条件をチェックして
```

プロジェクトルートの `README.md`（仕様書）と `lib/simulator.ts`（実装）を照合し、
数式の正確性・数値の方向性・境界条件を検証します。

### コード品質レビュー

```
/harness-review config-panel.tsx のコード品質をチェックして
/harness-review TypeScript の型安全性を全体的に確認して
/harness-review Recharts 周りに React 19 の問題がないか確認して
```

型安全性、命名規則、既知のアンチパターン（Recharts フラグメント、SVG fill の CSS変数）をチェックします。

### リグレッション分析

```
/harness-review 直近5コミットのリグレッションリスクを確認して
/harness-review 先週の変更でURL共有の互換性が壊れていないか確認して
```

`git diff` で変更を分析し、既存機能への影響リスクを評価します。

### レビュー結果

レビュー結果は `.plans/harness/review-report.md` に出力されます。
問題が見つかった場合、そのまま修正フローに流せます:

```
/harness-review UI全体を確認して
  ↓ 問題発見
/harness-contract レビューで見つかった問題Xを修正したい
  ↓ 契約作成
/harness-generate
  ↓ 実装 + 検証
/harness-evaluate
```

---

## 検証パイプライン（verify.py）

slash command の外でも直接使えます。

```bash
# 全ステージ実行（pnpm dev 起動済み前提）
python -X utf8 tools/verify.py

# ビルド + ユニットテストのみ（高速、dev server 不要）
python -X utf8 tools/verify.py --stages build,unit

# UIテストのみ
python -X utf8 tools/verify.py --stages ui
```

**4つのステージ:**

| ステージ | コマンド | 所要時間 | dev server |
|----------|----------|----------|------------|
| build | `npx next build` | ~20秒 | 不要 |
| unit | `npx vitest run` | ~1秒 | 不要 |
| ui | `python tools/ui_test.py` | ~1分 | 必要 |
| screenshot | `python tools/take_screenshot.py` | ~15秒 | 必要 |

- 前のステージが失敗すると、後続はスキップされます
- dev server が起動していない場合、ui と screenshot は自動スキップ（警告付き）
- レポートは `.plans/harness/verification-report.md` に出力されます

---

## ファイル構成

```
.plans/harness/
  contracts/
    active.md                # 現在アクティブな契約ID（1行）
    _template.md             # 契約テンプレート
    sprint-001.md            # 各スプリントの契約
    sprint-002.md
    ...
  verification-report.md     # verify.py の出力（git管理外）
  generator-report.md        # Generator の完了報告（git管理外）
  evaluation-report.md       # Evaluator のレビュー結果（git管理外）
  review-report.md           # Reviewer のレビュー結果（git管理外）

.claude/commands/
  harness-generate.md        # Generator の指示書
  harness-evaluate.md        # Evaluator の指示書
  harness-contract.md        # 契約作成ヘルパーの指示書
  harness-review.md          # Reviewer の指示書

tools/
  verify.py                  # 検証パイプライン
```

**git 管理:**
- 契約ファイル (`sprint-*.md`, `_template.md`, `active.md`) → git 管理対象
- レポートファイル (`*-report.md`) → `.gitignore` 済み（一時成果物）
- slash command ファイル (`harness-*.md`) → git 管理対象
- `tools/verify.py` → git 管理対象

---

## コンテキスト分離について

ハーネスの品質は **Generator と Evaluator のコンテキスト分離** に依存します。

**通常運用（ターミナル2つ）:**
同じ Claude Code セッションで `/harness-generate` → `/harness-evaluate` を実行。
簡便だが、Claude が Generator の記憶を持ったまま Evaluator を動かすため、
レビューの独立性がやや弱くなります。

**厳密運用（ターミナル3つ）:**
```
ターミナルA: Claude Code セッション1 → /harness-contract, /harness-generate
ターミナルB: pnpm dev
ターミナルC: Claude Code セッション2 → /harness-evaluate
```
Evaluator が完全に別セッションで動くため、コンテキスト分離が保証されます。

**推奨:** まず2ターミナルで試し、Evaluator の品質に不満が出たら3ターミナルに分ける。

---

## トラブルシューティング

### verify.py の UI テストがスキップされる
→ `pnpm dev` が起動しているか確認。`http://localhost:3000` にアクセスできる必要があります。

### Generator が契約を見つけられない
→ `.plans/harness/contracts/active.md` にスプリントIDが記載されているか確認。
   コメントアウトされたテンプレート状態のままだと読み取れません。

### Evaluator が常に APPROVED を返す
→ 同一セッション内で Generator → Evaluator を実行すると、自己評価バイアスが発生しやすい。
   別セッション（ターミナルC）で Evaluator を実行してみてください。

### 検証パイプラインがタイムアウトする
→ `tools/verify.py` のデフォルトタイムアウト:
   - build: 120秒
   - unit: 60秒
   - ui: 300秒
   - screenshot: 120秒
   初回ビルドやモンテカルロ計算で時間がかかる場合があります。
