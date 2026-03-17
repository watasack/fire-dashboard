# Phase 10: シナリオA/B比較

## 概要

現在の設定をプランAとして保存し、変更後をプランBとして並列シミュレーションを実行。
同一グラフにA/Bの資産推移を重ねて表示することで、設定変更の効果を直感的に比較できる。
P8の UI 拡張が完了してから実装する。

## 依存Phase

- 前提: **P8（P8完了後に実装すること）** — `SimulationResult.fireAchievementRate` フィールドは
  P8 で追加されるため、P8 が未実装の状態で P10 を実装しようとすると型エラーが発生する
  **[P10-CRIT-1] 対応: P8 未実装状態での P10 実装を禁止する**
- P1〜P7（比較に意味を持たせるには各機能が実装済みであることが望ましい）
- 影響: なし（最終フェーズ）

---

## インターフェース変更

### simulator.ts への変更

```typescript
// 追加（シナリオ比較の実行）
export interface ScenarioComparisonResult {
    planA: SimulationResult
    planB: SimulationResult
    planAConfig: SimulationConfig
    planBConfig: SimulationConfig
    diffSummary: ScenarioDiffSummary
}

export interface ScenarioDiffSummary {
    fireAgeDiff: number | null       // B.fireAge - A.fireAge（負=BのほうがFIRE早い）
                                     // null の場合は planAFiresOnly / planBFiresOnly で詳細確認
    finalAssetsDiff: number          // B.finalAssets - A.finalAssets
    fireAchievementRateDiff: number  // B.achievementRate - A.achievementRate
    // [P10-CRIT-1] 対応: どちらか一方のみFIREするケースの明示
    planAFiresOnly: boolean          // AだけがシミュレーションYears内にFIREする
    planBFiresOnly: boolean          // BだけがシミュレーションYears内にFIREする
}
```

### 既存 Scenario インターフェースの拡張

```typescript
// 変更前
export interface Scenario {
    name: string
    description: string
    changes: Omit<Partial<SimulationConfig>, 'person1' | 'person2' | 'nisa' | 'ideco'> & {
        person1?: Partial<Person>
        person2?: Partial<Person>
        nisa?: Partial<NISAConfig>
        ideco?: Partial<IDeCoConfig>
    }
}

// 変更後（後方互換を維持しつつ拡張）
export interface Scenario {
    name: string
    description: string
    changes: Omit<Partial<SimulationConfig>, 'person1' | 'person2' | 'nisa' | 'ideco'> & {
        person1?: Partial<Person>
        person2?: Partial<Person>
        nisa?: Partial<NISAConfig>
        ideco?: Partial<IDeCoConfig>
    }
    // 追加:
    id?: string          // 識別子（localStorage保存時のキー）
    savedAt?: number     // 保存日時（epoch ms）
}
```

---

## 関数仕様

### `runScenarioComparison` — A/B比較実行

```typescript
/**
 * プランAとプランBの設定でシミュレーションを実行し、比較結果を返す
 * @param planAConfig プランAの設定
 * @param planBConfig プランBの設定
 * @returns 比較結果
 */
export function runScenarioComparison(
    planAConfig: SimulationConfig,
    planBConfig: SimulationConfig
): ScenarioComparisonResult {
    const planA = runSingleSimulation(planAConfig)
    const planB = runSingleSimulation(planBConfig)

    const fireAgeDiff = (planB.fireAge !== null && planA.fireAge !== null)
        ? planB.fireAge - planA.fireAge
        : null

    // [P10-CRIT-1] 対応: どちらか一方のみFIREするケースを明示
    const planAFiresOnly = planA.fireAge !== null && planB.fireAge === null
    const planBFiresOnly = planB.fireAge !== null && planA.fireAge === null

    return {
        planA,
        planB,
        planAConfig,
        planBConfig,
        diffSummary: {
            fireAgeDiff,
            finalAssetsDiff: planB.finalAssets - planA.finalAssets,
            fireAchievementRateDiff: planB.fireAchievementRate - planA.fireAchievementRate,
            planAFiresOnly,
            planBFiresOnly,
        },
    }
}
```

### `applyScenarioChanges` — シナリオ変更をベース設定に適用

```typescript
/**
 * ベース設定にシナリオの変更を適用した新しい設定を返す
 * 既存の generateScenarios() と同様のマージロジック
 * @param baseConfig ベース設定（プランA）
 * @param scenario 適用するシナリオ
 * @returns 変更適用後の設定（プランB）
 */
export function applyScenarioChanges(
    baseConfig: SimulationConfig,
    scenario: Scenario
): SimulationConfig {
    const changes = scenario.changes
    return {
        ...baseConfig,
        ...Object.fromEntries(
            Object.entries(changes).filter(([key]) =>
                !['person1', 'person2', 'nisa', 'ideco'].includes(key)
            )
        ),
        person1: changes.person1
            ? { ...baseConfig.person1, ...changes.person1 }
            : baseConfig.person1,
        // [P10-CRIT-1] 対応: person2: null バグを修正
        // baseConfig.person2 が null のとき { ...null, ...changes.person2 } は
        // 必須フィールドが欠落した不完全な Person を生成するため修正が必要
        person2: changes.person2 !== undefined
            ? (changes.person2 === null
                ? null
                : { ...(baseConfig.person2 ?? getDefaultPerson2()), ...changes.person2 })
            : baseConfig.person2,
        nisa: changes.nisa ? { ...baseConfig.nisa, ...changes.nisa } : baseConfig.nisa,
        ideco: changes.ideco ? { ...baseConfig.ideco, ...changes.ideco } : baseConfig.ideco,
    }
}
```

---

## UI層の設計（localStorage管理）

### プランの保存・復元

```typescript
// UI 層のユーティリティ（simulator.ts には含まない）

const PLAN_A_KEY = 'fire_simulator_plan_a'
const PLAN_B_KEY = 'fire_simulator_plan_b'

function savePlan(plan: 'A' | 'B', config: SimulationConfig): void {
    const key = plan === 'A' ? PLAN_A_KEY : PLAN_B_KEY
    try {
        localStorage.setItem(key, JSON.stringify({
            config,
            savedAt: Date.now(),
        }))
    } catch (e) {
        console.error('プランの保存に失敗しました:', e)
    }
}

function loadPlan(plan: 'A' | 'B'): SimulationConfig | null {
    const key = plan === 'A' ? PLAN_A_KEY : PLAN_B_KEY
    try {
        const stored = localStorage.getItem(key)
        if (!stored) return null
        const { config } = JSON.parse(stored)
        return migrateConfig(config)  // P1 で実装したマイグレーション関数を適用
    } catch {
        return null
    }
}

function clearPlan(plan: 'A' | 'B'): void {
    const key = plan === 'A' ? PLAN_A_KEY : PLAN_B_KEY
    localStorage.removeItem(key)
}
```

### UI ボタン仕様

```
[プランAとして保存]  → 現在の設定を localStorage に保存
[プランBとして比較]  → 現在の設定をプランBとして設定し、プランAと並列実行
[比較をリセット]     → プランB をクリアし、単一シミュレーション表示に戻す
```

---

## DEFAULT_CONFIG変更

変更なし（P10は既存計算を流用するのみ）。

---

## YearlyData / SimulationResult への追加フィールド

```typescript
// ScenarioComparisonResult（新規型・上記参照）
// SimulationResult には変更なし
```

---

## テスト影響分析

### 既存テストへの影響

P10 は新規関数の追加のみで既存関数を変更しないため影響なし。

### 新規テストケース

```typescript
describe('シナリオA/B比較', () => {
    test('同一設定でA/B比較: 差分がゼロ', () => {
        const config = cfg({
            currentAssets: 10_000_000,
            monthlyExpenses: 200_000,
            investmentReturn: 0.05,
            simulationYears: 20,
        })
        const result = runScenarioComparison(config, config)
        expect(result.diffSummary.finalAssetsDiff).toBe(0)
        expect(result.diffSummary.fireAgeDiff).toBe(0)
    })

    test('支出削減シナリオ: B の FIRE が A より早い', () => {
        const planA = cfg({
            currentAssets: 10_000_000,
            monthlyExpenses: 300_000,
            investmentReturn: 0.05,
            simulationYears: 30,
        })
        const planB = applyScenarioChanges(planA, {
            name: '支出削減',
            description: '月次支出を10%カット',
            changes: { monthlyExpenses: 270_000 },
        })
        const result = runScenarioComparison(planA, planB)
        expect(result.diffSummary.fireAgeDiff).toBeLessThan(0)  // B の方が早い
        expect(result.diffSummary.finalAssetsDiff).toBeGreaterThan(0)  // B の方が資産多い
    })

    test('applyScenarioChanges: person1 の変更が正しくマージされる', () => {
        const base = cfg({
            person1: { currentAge: 35, retirementAge: 65, grossIncome: 7_000_000,
                incomeGrowthRate: 0.02, pensionStartAge: 65, pensionAmount: 1_500_000,
                employmentType: 'employee' },
        })
        const scenario: Scenario = {
            name: '副業',
            description: '副業+100万円',
            changes: { person1: { grossIncome: 8_000_000 } },
        }
        const result = applyScenarioChanges(base, scenario)
        expect(result.person1.grossIncome).toBe(8_000_000)
        expect(result.person1.currentAge).toBe(35)  // 変更していないフィールドは維持
    })

    test('applyScenarioChanges: person2=null のシナリオが正しく適用される', () => {
        const base = cfg({
            person2: { currentAge: 33, retirementAge: 65, grossIncome: 5_000_000,
                incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 1_200_000,
                employmentType: 'employee' },
        })
        const scenario: Scenario = {
            name: 'シングル',
            description: '配偶者なしシナリオ',
            changes: { person2: null },
        }
        const result = applyScenarioChanges(base, scenario)
        expect(result.person2).toBeNull()
    })

    test('generateScenarios との後方互換: 既存シナリオが動作する', () => {
        const base = cfg({
            currentAssets: 10_000_000,
            monthlyExpenses: 300_000,
            investmentReturn: 0.05,
            simulationYears: 30,
        })
        const scenarios = generateScenarios(base)
        // 各シナリオに applyScenarioChanges を適用できる
        for (const scenario of scenarios) {
            const modified = applyScenarioChanges(base, scenario)
            expect(modified).toBeDefined()
            const result = runSingleSimulation(modified)
            expect(result.yearlyData.length).toBe(31)
        }
    })
})
```

---

## 後方互換性

既存の `generateScenarios` 関数はそのまま維持する。
`applyScenarioChanges` は `generateScenarios` で生成したシナリオを受け取れる互換性を持つ。

---

## 実装上の注意点

### 1. プランA/B の localStorage キーの設計

ユーザーがページをリロードしても設定が維持されるよう、`localStorage` を使用する。
`sessionStorage` は「タブを閉じると消える」ため、長期的な設定保存には不向き。

### 2. 設定の型変換（マイグレーション）

`localStorage` に保存された古い設定（`currentIncome` を含む可能性）は
P1 で実装した `migrateConfig()` でロード時に変換する。

### 3. グラフの重ね表示

A/B の資産推移を同一グラフに重ねる際:
- プランA: 実線（青系）
- プランB: 破線（橙系）
- 差分を示す塗りつぶし領域（A > B: 赤, A < B: 緑）はオプション

Recharts での実装例:
```tsx
<LineChart data={mergedData}>
    {showPlanA ? <Line dataKey="planA_assets" stroke="#3B82F6" strokeDasharray="" /> : null}
    {showPlanB ? <Line dataKey="planB_assets" stroke="#F97316" strokeDasharray="5 5" /> : null}
</LineChart>
```

### 4. MC比較（将来拡張）

現時点では `runSingleSimulation` のみ比較するが、将来的に
`runMonteCarloSimulation` で A/B の成功率・パーセンタイルを比較する機能も有用。
Phase 10 の完了条件には含まないが、設計上の拡張ポイントとして記録する。

### 5. 既存の generateScenarios との関係

現在の `generateScenarios` は4種類のシナリオを自動生成する。
これらは「プリセットシナリオ」として引き続き使用し、
P10 の A/B 比較とは別機能として並立させる設計とする:

- `generateScenarios` → プリセットシナリオ（自動生成4種類）
- P10 A/B 比較 → ユーザーが自由に設定したプランA・Bの比較

### 6. 年次ループの前年値繰り越し変数の初期値（全フェーズ共通）

```typescript
// runSingleSimulation 冒頭で初期化
let capitalGainsLastYear = 0        // P4D・P6で使用
let lastYearFireIncome = 0          // P6で使用（FIRE前は0）
// 全ての前年値変数の初期値はゼロ
```
