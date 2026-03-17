# Phase 7: 取り崩し戦略

## 概要

現在の「固定額取り崩し（年間支出をそのまま使用）」に加えて、「割合（%）指定」と
「ガードレール（ドローダウン連動の動的削減）」の2方式を追加する。
特にガードレール戦略は、暴落時に支出を自動削減して資産枯渇を防ぐ実践的な方式。

## 依存Phase

- 前提: P4（現金・株式分離管理、取り崩し対象資産の明確化）
- P2A（ライフステージ別生活費）があると裁量支出比率の精緻化が可能（オプション）
- 影響: P8（UI: 戦略別の資産推移グラフ表示）

---

## インターフェース変更

### SimulationConfig

```typescript
// 追加
export type WithdrawalStrategy = 'fixed' | 'percentage' | 'guardrail'

export interface GuardrailConfig {
    // ドローダウン閾値（ピーク比の下落率）ごとの裁量支出削減率
    threshold1: number      // 閾値1（デフォルト: -0.10、-10%）
    reduction1: number      // 削減率1（デフォルト: 0.40、裁量支出の40%削減）
    threshold2: number      // 閾値2（デフォルト: -0.20、-20%）
    reduction2: number      // 削減率2（デフォルト: 0.80）
    threshold3: number      // 閾値3（デフォルト: -0.35、-35%）
    reduction3: number      // 削減率3（デフォルト: 0.95）
    // 裁量支出の割合（削減対象になる支出比率）
    discretionaryRatio: number   // デフォルト: 0.30（生活費の30%が裁量支出）
}

// SimulationConfig に追加
export interface SimulationConfig {
    // ...既存
    withdrawalStrategy: WithdrawalStrategy   // 追加: デフォルト 'fixed'
    guardrailConfig?: GuardrailConfig         // 追加: guardrail 選択時に使用
}
```

---

## 関数仕様

### `calculateWithdrawalAmount` — 取り崩し額の計算

```typescript
/**
 * 取り崩し戦略に基づいて当年の実際の支出（取り崩し）額を決定する
 *
 * @param strategy 取り崩し戦略
 * @param baseExpenses 基準支出（インフレ・ライフステージ調整後）
 * @param totalAssets 現在の総資産
 * @param peakAssets シミュレーション開始以降の資産ピーク値
 * @param safeWithdrawalRate SWR（percentage 戦略で使用）
 * @param guardrailConfig ガードレール設定
 * @returns 当年の実際の支出額
 */
function calculateWithdrawalAmount(
    strategy: WithdrawalStrategy,
    baseExpenses: number,
    totalAssets: number,
    peakAssets: number,
    safeWithdrawalRate: number,
    guardrailConfig?: GuardrailConfig
): number
```

アルゴリズム:

**固定額（`'fixed'`）:**
```
return baseExpenses  // 現在の動作と同じ
```

**割合（`'percentage'`）:**
```
// [P7-CRIT-1] 対応: 取り崩し額と収入を独立して管理する
targetWithdrawal = totalAssets * safeWithdrawalRate

// 収入は独立して計算（年金・セミFIREなど）
netIncome = calculateIncome(...)   // 年金・セミFIREなど

// 取り崩し額と収入を独立して管理
shortfall = max(0, targetWithdrawal - netIncome)   // 収入で賄えない分だけ資産から取り崩す
assets -= shortfall
// 注意: 収入がtargetWithdrawalを超えても資産に戻さない（消費として扱う）
actualExpenses = max(totalExpenses, targetWithdrawal)  // 実支出は生活費以上

// この設計により:
// - 収入 > targetWithdrawal の場合: 資産取り崩しゼロ（収入で生活費を賄える）
// - 収入 < targetWithdrawal の場合: 差額を資産から取り崩す
// - 資産が積み上がるシナリオ（収入が生活費を上回る）は actualExpenses で防止
```

**ガードレール（`'guardrail'`）:**
```
drawdownFromPeak = (totalAssets - peakAssets) / peakAssets  // 負の値

if drawdownFromPeak >= guardrailConfig.threshold1:
    // 閾値1未満の下落 → 削減なし
    discretionaryReductionRate = 0.0
elif drawdownFromPeak >= guardrailConfig.threshold2:
    // 閾値1〜2 の下落 → 裁量支出を40%削減
    discretionaryReductionRate = guardrailConfig.reduction1
elif drawdownFromPeak >= guardrailConfig.threshold3:
    // 閾値2〜3 の下落 → 裁量支出を80%削減
    discretionaryReductionRate = guardrailConfig.reduction2
else:
    // 閾値3以上の下落 → 裁量支出を95%削減（生活最低限のみ）
    discretionaryReductionRate = guardrailConfig.reduction3

// 必須支出と裁量支出に分割
essentialExpenses = baseExpenses * (1 - guardrailConfig.discretionaryRatio)
discretionaryExpenses = baseExpenses * guardrailConfig.discretionaryRatio

// 裁量支出を削減
actualExpenses = essentialExpenses + discretionaryExpenses * (1 - discretionaryReductionRate)
return actualExpenses
```

### `peakAssets` の追跡

```typescript
// runSingleSimulation 内に追加
let peakAssets = config.cashAssets + config.taxableStockAssets  // 初期値

for (let year = 0; year <= config.simulationYears; year++) {
    // ...（投資リターン・収入計算）

    const totalAssets = assets + nisaAssets + idecoAssets

    // ピーク資産の更新（FIRE後のみ追跡: 就労中は資産増加が自然なため）
    if (isPostFire) {
        peakAssets = Math.max(peakAssets, totalAssets)
    }

    // 取り崩し戦略の適用
    const actualExpenses = calculateWithdrawalAmount(
        config.withdrawalStrategy,
        baseExpenses,
        totalAssets,
        peakAssets,
        config.safeWithdrawalRate,
        config.guardrailConfig
    )

    // ...
}
```

---

## DEFAULT_CONFIG変更

```typescript
// 追加
withdrawalStrategy: 'fixed',   // デフォルト: 現在の固定額方式（後方互換）
guardrailConfig: {
    threshold1: -0.10,
    reduction1: 0.40,
    threshold2: -0.20,
    reduction2: 0.80,
    threshold3: -0.35,
    reduction3: 0.95,
    discretionaryRatio: 0.30,
},
```

---

## YearlyData / SimulationResult への追加フィールド

```typescript
// YearlyData に追加
withdrawalStrategy: WithdrawalStrategy  // 当年適用された戦略（ガードレールは動的）
drawdownFromPeak: number               // ピークからの下落率（%）
discretionaryReductionRate: number     // 当年の裁量支出削減率（0〜1）
actualExpenses: number                 // 戦略適用後の実際の支出（expenses と同義だが明示）

// SimulationResult に追加
peakAssets: number                     // シミュレーション期間中の資産ピーク
depletionAge: number | null            // 資産枯渇年齢（P8 の KPI 表示で使用）
```

---

## テスト影響分析

### 既存テストへの影響

`withdrawalStrategy: 'fixed'` がデフォルトのため既存テストへの影響はゼロ。
`expenses` フィールドは固定戦略では変わらないため、全66テストが引き続きパス。

### 新規テストケース

```typescript
describe('取り崩し戦略', () => {
    describe('固定額（fixed）', () => {
        test('既存の動作と完全に同じ: expenses が baseExpenses と等しい', () => {
            // withdrawalStrategy: 'fixed' → 現在の動作と同一
        })
    })

    describe('割合（percentage）', () => {
        test('年間取り崩し額 = totalAssets * safeWithdrawalRate', () => {
            // totalAssets = 30_000_000, SWR = 0.04 → expenses = 1_200_000
        })

        test('資産が減ると翌年の取り崩し額も減る', () => {
            // 資産が減るにつれて支出も比例して減少
        })

        test('資産が増えると取り崩し額も増える', () => {
            // リターンが高い年は翌年の取り崩し可能額が増加
        })
    })

    describe('ガードレール（guardrail）', () => {
        test('ドローダウン < -10%: 裁量支出削減なし', () => {
            // drawdown = -0.05 → reduction = 0 → actualExpenses = baseExpenses
        })

        test('ドローダウン -10% 〜 -20%: 裁量支出40%削減', () => {
            // drawdown = -0.15, baseExpenses = 2_400_000, discretionaryRatio = 0.30
            // essential = 1_680_000, discretionary = 720_000
            // actual = 1_680_000 + 720_000 * 0.60 = 2_112_000
        })

        test('ドローダウン -20% 〜 -35%: 裁量支出80%削減', () => {
            // drawdown = -0.25 → actual = 1_680_000 + 720_000 * 0.20 = 1_824_000
        })

        test('ドローダウン -35% 超: 裁量支出95%削減（生活最低限）', () => {
            // drawdown = -0.40 → actual = 1_680_000 + 720_000 * 0.05 = 1_716_000
        })

        test('ガードレール戦略は固定額戦略より長く資産が持つ（MC結果の比較）', () => {
            // 同一設定で guardrail vs fixed の finalAssets を比較
            // guardrail の方が下位パーセンタイルで資産が多い
        })

        test('ピーク資産が正しく追跡される', () => {
            // 資産増加後に減少するシナリオで peakAssets が最大値を維持する
        })
    })

    describe('資産枯渇年齢（depletionAge）', () => {
        test('全期間資産が持つ場合: depletionAge = null', () => {})
        test('資産が途中でゼロになる場合: 枯渇した年齢が返る', () => {
            // assets = 0 になった年の age が depletionAge
        })
    })
})
```

---

## 後方互換性

`withdrawalStrategy: 'fixed'` がデフォルト値のため既存テスト・設定への影響はゼロ。
`guardrailConfig` は `withdrawalStrategy === 'guardrail'` 時のみ参照されるため、
省略しても `fixed` または `percentage` では問題ない。

---

## 実装上の注意点

### 1. ガードレール戦略のピーク資産追跡タイミング

ピーク資産は「FIRE後から追跡開始」が実践的。就労中は定期的に資産が増えるため、
就労期間のピークを含めるとFIRE直後は常に「ピーク比マイナス」になってしまう。

代替案: ピーク追跡は FIRE達成年以降のみ。`fireYear` 以降で `peakAssets` を更新。

### 2. percentage 戦略と income の関係

`percentage` 戦略では「支出 = 資産 × SWR」なので、
年金収入やセミFIRE収入があれば実際の取り崩し額は「支出 - 収入」になる。
`savings = netIncome - actualExpenses` の計算は既存と同じため、
`actualExpenses` を正しく設定すれば自動的に取り崩し額が決まる。

### 3. ガードレール戦略と MC との相互作用

MCシミュレーションでランダムリターンを使うと、
ガードレール戦略が発動するシナリオと発動しないシナリオが混在する。
MCの成功率・資産分布がより楽観的になることを P9 のドキュメントに記載する。

### 4. `depletionAge` の計算

```typescript
// runSingleSimulation の最後に計算
let depletionAge: number | null = null
for (const data of yearlyData) {
    if (data.assets + data.nisaAssets + data.idecoAssets <= 0) {
        depletionAge = data.age
        break
    }
}
return {
    // ...既存
    depletionAge,
    peakAssets,
}
```

### 5. 年次ループの前年値繰り越し変数の初期値（全フェーズ共通）

```typescript
// runSingleSimulation 冒頭で初期化
let capitalGainsLastYear = 0        // P4D・P6で使用
let lastYearFireIncome = 0          // P6で使用（FIRE前は0）
// 全ての前年値変数の初期値はゼロ
```
