# Phase 8: UI拡張（年次テーブル・収支グラフ・枯渇年齢）

## 概要

P1〜P7の計算結果を可視化する UI コンポーネントを追加する。年次収支テーブル・収支グラフ・
枯渇年齢表示・FIRE達成率KPIの4つが主要な追加要素。

## 依存Phase

- 前提: P1〜P7（表示するデータが揃ってから実装）
- 影響: P10（シナリオA/B比較ではこのUI拡張を基に重ね表示を実装）

---

## インターフェース変更

### simulator.ts への変更

P8 は主に UI 層の変更であるが、いくつかの計算結果が追加で必要。

```typescript
// SimulationResult に追加
export interface SimulationResult {
    // ...既存
    depletionAge: number | null          // P7で追加（資産枯渇年齢）
    fireAchievementRate: number          // 追加: FIRE達成率（現在資産/FIRE数値）
    yearlyData: YearlyData[]             // P1〜P6で追加フィールドを持つ
}
```

### 新規 UI コンポーネント型定義（UI層）

```typescript
// UI コンポーネントのprops型（simulator.ts には含まない、UIファイルで定義）

interface AnnualTableProps {
    yearlyData: YearlyData[]
    person1StartAge: number
    currency?: 'JPY'   // 将来拡張用
}

interface CashFlowChartProps {
    yearlyData: YearlyData[]
    groupByYears?: number   // デフォルト: 5（5年間隔でグループ化）
}

interface DepletionSummaryProps {
    mcResult: MonteCarloResult
    singleResult: SimulationResult
}
```

---

## 関数仕様（simulator.ts への追加）

### `calculateFireAchievementRate` — FIRE達成率

```typescript
/**
 * 現在の総資産が FIRE 目標額（fireNumber）に対して何%達成しているかを返す
 * @param yearlyData 年次データ
 * @param fireNumber FIRE目標額
 * @returns 達成率（0.0〜1.0以上）
 */
function calculateFireAchievementRate(
    yearlyData: YearlyData[],
    fireNumber: number
): number {
    if (yearlyData.length === 0 || fireNumber <= 0) return 0
    const currentAssets = yearlyData[0]  // year0 = 現時点
    const totalCurrentAssets = currentAssets.assets + currentAssets.nisaAssets + currentAssets.idecoAssets
    return totalCurrentAssets / fireNumber
}
```

### `formatAnnualTableData` — 年次テーブルのデータ整形

```typescript
/**
 * YearlyData を年次テーブル表示用に整形する
 * @param yearlyData シミュレーション結果の年次データ
 * @returns テーブル行データの配列
 */
interface AnnualTableRow {
    year: number
    age: number
    totalAssets: number      // 総資産（円）
    grossIncome: number      // 税引き前収入（円）
    netIncome: number        // 手取り収入（円）
    expenses: number         // 支出合計（円）
    netCashFlow: number      // 純CF = netIncome - expenses
    isFireAchieved: boolean
    isSemiFire: boolean
    fireNumber: number
}

function formatAnnualTableData(yearlyData: YearlyData[]): AnnualTableRow[]
```

### `formatCashFlowChartData` — 収支グラフのデータ整形

```typescript
/**
 * 収支グラフ用に5年間隔で集計する
 * @param yearlyData 年次データ
 * @param groupByYears グループ化間隔（デフォルト5）
 * @returns グループ化された収支データ
 */
interface CashFlowChartGroup {
    label: string       // 例: "35〜39歳"
    income: number      // 期間合計収入
    expenses: number    // 期間合計支出
    netCF: number       // 期間合計純CF
}

function formatCashFlowChartData(
    yearlyData: YearlyData[],
    groupByYears: number = 5
): CashFlowChartGroup[]
```

---

## DEFAULT_CONFIG変更

変更なし（P8は表示層のみ）。

---

## YearlyData / SimulationResult への追加フィールド

### SimulationResult への追加

```typescript
export interface SimulationResult {
    // ...既存
    fireAchievementRate: number     // FIRE達成率（0.0〜1.0以上）
    depletionAge: number | null     // P7 で既に追加済み
}
```

### MonteCarloResult への追加

```typescript
export interface MonteCarloResult {
    // ...既存
    depletionAgeP10: number | null   // 下位10%シナリオの枯渇年齢
    depletionAgeP50: number | null   // 中央値シナリオの枯渇年齢
    successCountFormatted: string    // 例: "1000通りのうち800通りで90歳まで資産が持ちました"
}
```

---

## UI コンポーネント仕様

### 1. 年次収支テーブル

**場所**: メインシミュレーション画面の下部（グラフの後）

**表示列**:
| 列 | 内容 | 備考 |
|---|---|---|
| 年齢 | person1の年齢 | |
| 西暦 | シミュレーション年 | |
| 総資産 | assets + nisaAssets + idecoAssets | 万円表示 |
| 年収（税前） | grossIncome | P1実装後に表示 |
| 手取り | netIncome | |
| 支出 | expenses | |
| 純CF | netIncome - expenses | 正=黒字, 負=赤字（色分け） |
| FIRE | isFireAchieved | ✅ or - |

**実装上の注意**:
- Recharts の `<>` フラグメント禁止ルール（CLAUDE.md）に準拠
- データが多い（55年=56行）ためスクロール可能な固定高さコンテナに収める
- スマホ対応: 重要列のみ表示して横スクロール可

### 2. 収支グラフ（グループド棒グラフ）

**場所**: 年次テーブルの上（または別タブ）

**仕様**:
- 5年ごとの集計値をグループド棒グラフで表示
- 3系列: 収入（青）/ 支出（赤）/ 純CF（緑/オレンジ）
- Recharts の `ComposedChart` を使用
- 各Barは個別の三項演算子で描画（フラグメント禁止）

**Recharts 注意点（CLAUDE.md準拠）**:
```tsx
// NG: フラグメントで囲む
<ComposedChart>
    <>
        <Bar dataKey="income" ... />
        <Bar dataKey="expenses" ... />
    </>
</ComposedChart>

// OK: 個別に条件付きレンダリング
<ComposedChart>
    {showIncome ? <Bar dataKey="income" fill="#3B82F6" /> : null}
    {showExpenses ? <Bar dataKey="expenses" fill="#EF4444" /> : null}
    {showNetCF ? <Bar dataKey="netCF" fill="#10B981" /> : null}
</ComposedChart>
```

### 3. 枯渇年齢・成功率サマリー

**場所**: シミュレーション結果のKPIカード群（上部）

**表示内容**:
```
✅ 1,000通りのうち 800通りで90歳まで資産が持ちました（成功率80%）
⚠️ 最悪ケース（下位10%）でも XX歳まで資産が持ちます
📊 中央値シナリオ: YY歳まで資産が持ちます
```

**実装**:
```typescript
// runMonteCarloSimulation での枯渇年齢集計
const depletionAges = results.map(r => r.depletionAge).filter(a => a !== null) as number[]
const depletionAgeP10 = depletionAges.length > 0
    ? depletionAges.sort((a, b) => a - b)[Math.floor(depletionAges.length * 0.10)]
    : null
```

### 4. FIRE達成率 KPI

**場所**: KPIカードの1つ

**表示内容**:
```
FIRE達成率: 67%
（現在資産: 1,000万円 / FIRE目標: 1,500万円）
```

**プログレスバー**:
- 0〜100%: 青いバー
- 100%超: 緑色に変化（FIRE達成）

---

## テスト影響分析

### 既存テストへの影響

P8 は表示層の追加のみで `simulator.ts` のコア計算は変更しない。
`SimulationResult` への `fireAchievementRate` 追加のみ影響あり（非破壊的追加）。

### 新規テストケース

```typescript
describe('FIRE達成率', () => {
    test('資産がFIRE数値の67%の場合: achievementRate ≈ 0.67', () => {
        // currentAssets = 30_000_000, fireNumber = 45_000_000
        // → fireAchievementRate ≈ 0.667
    })
    test('FIRE達成済み: achievementRate >= 1.0', () => {})
    test('資産ゼロ: achievementRate = 0', () => {})
})

describe('年次テーブルデータ整形', () => {
    test('yearlyData から AnnualTableRow が正しく生成される', () => {})
    test('totalAssets = assets + nisaAssets + idecoAssets', () => {})
    test('netCashFlow = income - expenses', () => {})
})

describe('収支グラフデータ整形', () => {
    test('5年間隔でグループ化される（55年 → 11グループ）', () => {})
    test('グループ内の income / expenses は期間合計', () => {})
})

describe('MC 枯渇年齢', () => {
    test('全シミュレーション成功: depletionAgeP10 = null', () => {})
    test('一部失敗: 下位10%の枯渇年齢が返る', () => {})
    test('successCountFormatted が正しくフォーマットされる', () => {
        // "1000通りのうち800通りで90歳まで資産が持ちました"
    })
})
```

---

## 後方互換性

`SimulationResult` への追加フィールドは非破壊的追加のため互換性問題なし。
既存の `runSingleSimulation` の戻り値に新フィールドが追加されるのみ。

---

## 実装上の注意点

### 1. Recharts の SVG fill と CSS 変数

CLAUDE.md の制約:
> SVG の `fill` 属性に CSS 変数（`var(--xxx)`）は使えない → ハードコードした hex 値を使う

```tsx
// NG
<Bar fill="var(--color-income)" />

// OK
<Bar fill="#3B82F6" />
```

### 2. テーブルのパフォーマンス

55年分（56行）のテーブルは仮想化なしでも問題ないが、
将来的に100年以上のシミュレーションをサポートする場合は
`react-virtual` などの仮想化ライブラリを検討する。

### 3. スクリーンショットでの確認

CLAUDE.md の手順に従い、UI変更後は必ず Playwright でスクリーンショット確認:
```bash
set PYTHONIOENCODING=utf-8 && python tools/take_screenshot.py
```

### 4. モバイル対応

年次テーブルは列数が多いため、モバイルでは重要列のみ表示（年齢・総資産・純CF）し、
横スクロールまたはアコーディオン展開で詳細を表示する設計を推奨。
