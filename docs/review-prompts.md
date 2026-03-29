# レビュー用プロンプト集

別の Claude Code セッションにそのまま貼って使うプロンプト。

---

## 1. UI/UX レビュー

```
FIRE Dashboard の UI/UX を独立した視点でレビューしてください。

## 手順

1. `pnpm dev` が起動しているか確認（http://localhost:3000 にアクセスできるか）
2. 起動していれば `set PYTHONIOENCODING=utf-8 && python tools/take_screenshot.py` でスクリーンショットを撮影
3. `docs/screenshots/` のスクリーンショット（result_top.png, full_page.png, assets_chart.png, mobile_top.png, mobile_chart.png）を全て読み込んで確認
4. `components/fire/` の主要コンポーネント（dashboard.tsx, config-panel.tsx, assets-chart.tsx, fire-result-card.tsx）の構造を確認

## チェック観点

### レイアウト
- 要素の重なり・切れ・余白の不均等がないか
- デスクトップ（1440px）で2カラムレイアウトが正しく表示されているか
- モバイル（375px）でスクロール・アコーディオン表示が適切か
- 横スクロールが発生していないか

### 操作性
- KPI（FIRE達成年齢・成功率）が最も目立つ位置にあるか
- 設定パネルのタブ（基本/収入/投資/ライフ/詳細）が直感的に分類されているか
- スライダー・スイッチ・トグルの操作対象と効果が明確か
- Info(?) ボタンのツールチップが分かりやすいか

### 一貫性
- フォントサイズ・色・間隔がコンポーネント間で統一されているか
- ラベルの表現が統一されているか（例: 「万円」の表記が揺れていないか）
- アイコンのスタイルが混在していないか

### レスポンシブ
- デスクトップ→モバイルの切り替え（1024pxブレークポイント）で情報の欠落がないか
- モバイルでタッチターゲット（ボタン・スライダー）が十分な大きさか
- チャートがモバイルで見切れていないか

### 情報設計
- 初見ユーザーが「何を入力すれば何が分かるか」を理解できるか
- 結果（チャート・年次表）と設定（入力パネル）の関係が明確か
- 「次の一手」タブのシナリオ比較が分かりやすいか

## 出力

`.plans/harness/review-report.md` に以下の形式でレポートを書いてください:

- Summary（1-3文の総合評価）
- Findings（問題点を Severity: HIGH/MEDIUM/LOW 付きで列挙）
- Good Practices Noted（良い点）
- Recommendations（優先度順の改善提案）
```

---

## 2. シミュレーション監査

```
FIRE Dashboard のシミュレーションエンジン（lib/simulator.ts）が仕様書（README.md）通りに実装されているか監査してください。

## 手順

1. プロジェクトルートの `README.md`（「FIRE Simulator — シミュレーション仕様書」）を読み、シミュレーション仕様を把握する
   ※ `docs/README.md` はディレクトリ索引なので間違えないこと
2. `lib/simulator.ts` を読み、実装を把握する
3. 仕様と実装を項目ごとに照合する
4. `__tests__/simulator.test.ts` を読み、テストカバレッジの穴を探す

## 照合すべき項目

### 収入計算
- 給与所得控除の計算式（所得区分ごとの控除率）
- 配偶者控除・配偶者特別控除の段階的適用
- 産休育休中の収入（給付金の計算）
- 年金受給額（厚生年金 + 国民年金、マクロ経済スライド）

### 税金計算
- 所得税の累進課税率と控除額
- 住民税の計算
- 社会保険料（健康保険・厚生年金・雇用保険）の料率
- FIRE後の国民健康保険・国民年金保険料

### 資産運用
- 投資リターンの月次適用（複利計算）
- NISA の年間投資枠・非課税枠の取り扱い
- iDeCo の拠出・受取時の税制
- 取り崩し戦略（固定額・定率・ガードレール）の計算式
- 不変条件: `nisaAssets <= stocks` が常に成立するか

### 教育費
- 子ども年齢別の教育費テーブル（公立/私立/ミックス）
- 児童手当の計算

### 住宅ローン
- 月額返済額の計算（元利均等返済）
- 修繕費の定期発生

### モンテカルロ
- 正規分布・平均回帰・ブートストラップの3モデルの実装
- 1000回シミュレーションの集計（中央値・パーセンタイル）
- 成功率の定義（資産が90歳まで持つか）

## チェック観点

### 数式の正確性
- 仕様書の計算式と実装コードが **完全に** 一致するか
- 定数（税率・控除額・保険料率）が現行制度と整合するか

### 数値の方向性（サニティチェック）
- インフレ率を上げる → 生活費が増える → FIRE年齢が悪化する
- 収入を増やす → 貯蓄が増える → FIRE年齢が改善する
- NISA をONにする → 税引後リターンが改善する → FIRE年齢が改善する
- 生活費を増やす → FIRE年齢が悪化する

### 境界条件
- 現在年齢 = 退職年齢（即FIRE）で破綻しないか
- 資産ゼロ・収入ゼロで NaN/Infinity が発生しないか
- 子ども0人で教育費計算がエラーにならないか
- シミュレーション期間が1年でも動作するか

### テストカバレッジ
- `__tests__/simulator.test.ts` で検証されていない計算ロジックはあるか
- 手計算値との突き合わせがないテストケースはあるか

## 出力

`.plans/harness/review-report.md` に以下の形式でレポートを書いてください:

- Summary（1-3文の総合評価）
- Findings（仕様と実装の乖離を Severity: HIGH/MEDIUM/LOW 付きで列挙）
  - 各 Finding に: Location（ファイル:行番号）、仕様の記述、実装の記述、乖離の内容
- Test Coverage Gaps（テストされていない計算ロジック）
- Good Practices Noted（良い実装として評価できる点）
- Recommendations（優先度順の改善提案）
```

---

## 3. コード品質レビュー

```
FIRE Dashboard のコード品質を全体的にレビューしてください。

## 対象ファイル

優先度順に以下のファイルを読んでレビューしてください:

1. `lib/simulator.ts` — シミュレーションエンジン（最重要、2300行）
2. `components/fire/config-panel.tsx` — 設定パネル（最大UIファイル、1500行）
3. `components/fire/dashboard.tsx` — メインオーケストレーター（400行）
4. `components/fire/assets-chart.tsx` — チャート描画（370行）
5. `lib/url-state.ts` — URL状態管理
6. `__tests__/simulator.test.ts` — テストコード（2400行）

## チェック観点

### TypeScript 型安全性
- `any` 型が使われていないか
- `SimulationConfig` に追加されたフィールドが以下に反映されているか:
  - `DEFAULT_CONFIG`（デフォルト値）
  - `url-state.ts`（シリアライズ/デシリアライズ）
- Union 型の網羅チェック（switch 文の default）
- Optional フィールドの null チェック漏れ

### 既知の罠（CLAUDE.md 記載事項）
以下のルール違反がないか確認:
- `ComposedChart` 内で `<Area>`, `<Line>`, `<Bar>` を `<>` フラグメントで囲んでいないか（Recharts + React 19 非互換）
- SVG の `fill` 属性に CSS 変数（`var(--xxx)`）を使っていないか
- `lib/simulator/`（ディレクトリ）と `lib/simulator.ts`（ファイル）が共存していないか
- ライフステージの数値入力で `Math.max(0, val)` が適用されているか

### コード構造
- 1ファイルが大きすぎないか（目安: 500行超で分割検討）
- 関数の命名規則が一貫しているか（`calculateXxx`, `formatXxx`）
- 重複コードが存在しないか
- 不要な import や未使用変数がないか

### React パターン
- 不必要な再レンダリングを引き起こす実装がないか（useCallback/useMemo の不足または過剰）
- useEffect の依存配列が正しいか
- state 管理が適切か（過剰な useState、props drilling）
- Radix UI プリミティブ（Accordion, Switch, Slider 等）の使い方が適切か

### パフォーマンス
- モンテカルロ計算（1000回シミュレーション）がメインスレッドをブロックしていないか
- 大量の配列操作で不必要なコピーが発生していないか
- デバウンス（300ms）の設定が適切か

### セキュリティ・堅牢性
- URL state のデシリアライズで不正入力を処理できるか
- `JSON.parse` に try-catch があるか
- ユーザー入力が直接 eval や dangerouslySetInnerHTML に渡っていないか

## 出力

`.plans/harness/review-report.md` に以下の形式でレポートを書いてください:

- Summary（1-3文の総合評価）
- Findings（問題点を Severity: HIGH/MEDIUM/LOW 付きで列挙）
  - 各 Finding に: File（ファイル:行番号）、Problem、Impact、Suggested Fix
- Good Practices Noted（良い設計・実装として評価できる点）
- Recommendations（優先度順の改善提案）
```
