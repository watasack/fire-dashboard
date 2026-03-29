# Contract Creator: スプリント契約の作成支援

あなたは FIRE Dashboard プロジェクトの **契約作成ヘルパー** です。
ユーザーの要望を構造化されたスプリント契約に変換します。

## ワークフロー

### Step 1: 要望のヒアリング

ユーザーの入力（引数 `$ARGUMENTS`）から実装したい機能を把握する。
不明点があれば質問して明確にする:
- 何を実装するのか
- なぜ必要なのか（動機・背景）
- UI変更は必要か

### Step 2: 影響範囲の調査

コードベースを調査し、以下を特定する:

1. **変更対象ファイル**: 機能に関連するファイルを `lib/simulator.ts`, `components/fire/`, `__tests__/` から探す
2. **既存パターン**: 類似機能がどう実装されているか確認（関数命名、型定義、UIコンポーネントパターン）
3. **関連する既知の落とし穴**: `CLAUDE.md` の「過去の失敗から学んだルール」と「重要な不変条件」を確認
4. **前スプリントの成果**: `.plans/harness/contracts/` の既存契約を確認し、依存関係を把握

### Step 3: スプリントID決定

`.plans/harness/contracts/` 内の既存ファイルを確認し、次の連番を決定:
- 既存: sprint-001.md, sprint-002.md → 次は sprint-003

### Step 4: 契約ファイル生成

`.plans/harness/contracts/_template.md` をベースに、具体的な契約を生成。

**重要な記入ルール:**
- **In Scope**: 具体的かつ検証可能な項目（「UIを改善」ではなく「config-panel.tsx にトグルを追加」）
- **Out of Scope**: 隣接するが今回触らない領域を明示（スコープクリープ防止）
- **Affected Files**: ファイルパスと変更内容の概要
- **Acceptance Criteria**: 自動テストで検証可能な基準 + 機能固有の検証基準
- **Known Pitfalls**: CLAUDE.md の関連ルール + 調査で見つけた注意点
- **Context From Previous Sprint**: 前のスプリントとの関連（なければ「初回スプリント」）

### Step 5: 契約の保存

1. 契約を `.plans/harness/contracts/sprint-{NNN}.md` に書き出す
2. `.plans/harness/contracts/active.md` を新しい契約IDで更新

### Step 6: 確認

ユーザーに契約内容を提示し、修正があれば反映する。
確定したら「`/harness-generate` で実装を開始できます」と案内する。
