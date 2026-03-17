# Phase 3: 年金詳細計算

## 概要

現在の `Person.pensionAmount`（固定値入力）を、雇用形態・加入期間・標準報酬月額から
自動計算する方式に拡張する。P1 の `employmentType` および `standardMonthlyRemuneration`
計算が前提。固定値指定は後方互換として維持する。

## 依存Phase

- 前提: P1（`employmentType`、`standardMonthlyRemuneration` の計算が必要）
- 影響: P6（FIRE後税金の年金所得計算）

---

## インターフェース変更

### Person インターフェース

```typescript
// 変更前
export interface Person {
    // ...
    pensionStartAge: number
    pensionAmount: number       // 固定値（円/年）
}

// 変更後
export interface Person {
    // ...
    pensionStartAge: number
    pensionAmount?: number              // 後方互換: 固定値指定時はこちらが優先
    pensionConfig?: PensionConfig       // 追加: 詳細計算用（省略時は pensionAmount を使用）
}

// 追加
export interface PensionConfig {
    // 過去の厚生年金加入記録（就労開始〜シミュレーション開始まで）
    pastEmployeeMonths: number          // 過去の厚生年金加入月数
    pastAverageMonthlyRemuneration: number  // 過去の平均標準報酬月額（円）

    // 国民年金加入記録（第1号被保険者期間）
    pastNationalPensionMonths: number   // 過去の国民年金加入月数（480ヶ月が満額）

    // マクロ経済スライド
    pensionGrowthRate: number           // デフォルト: 0.01（1%/年）
}
```

### 新規型: 年金計算結果

```typescript
// 追加
export interface PensionBreakdown {
    employeePension: number        // 厚生年金（報酬比例部分）
    nationalPension: number        // 国民年金（基礎年金）
    totalAnnualPension: number     // 合計年金額（円/年）
    source: 'calculated' | 'fixed' // 計算値か固定値かの識別
}
```

---

## 関数仕様

### `calculatePensionAmount` — 年金額の自動計算

```typescript
/**
 * 雇用形態・加入記録・将来の標準報酬月額から年金額を計算する
 *
 * 優先順位:
 * 1. person.pensionAmount が指定されている場合はそのまま使用（後方互換）
 * 2. person.pensionConfig が指定されている場合は詳細計算
 * 3. 両方なければ 0 を返す
 *
 * @param person Person オブジェクト
 * @param yearsWorkedFromNow シミュレーション開始から退職までの年数
 * @param averageFutureMonthlyRemuneration 将来の平均標準報酬月額（P1の計算値）
 * @returns 年金計算結果
 */
function calculatePensionAmount(
    person: Person,
    yearsWorkedFromNow: number,
    averageFutureMonthlyRemuneration: number
): PensionBreakdown
```

アルゴリズム（厚生年金 `'employee'`）:
```
// 過去分の厚生年金（報酬比例部分）
pastEmployeePension =
    person.pensionConfig.pastAverageMonthlyRemuneration
    × person.pensionConfig.pastEmployeeMonths
    × 0.005481  // 乗率（2003年4月以降の加入分）

// 将来分の厚生年金（シミュレーション開始〜退職まで）
futureMonths = yearsWorkedFromNow * 12
futureEmployeePension =
    averageFutureMonthlyRemuneration
    × futureMonths
    × 0.005481

// 厚生年金合計
totalEmployeePension = pastEmployeePension + futureEmployeePension

// 国民年金（基礎年金）
// 厚生年金加入期間は第2号被保険者として国民年金も加入
totalPensionMonths = person.pensionConfig.pastNationalPensionMonths
    + person.pensionConfig.pastEmployeeMonths  // 厚生年金期間も国民年金加入
    + futureMonths
cappedMonths = min(totalPensionMonths, 480)  // 最大480ヶ月（40年）
nationalPension = 816_000 × (cappedMonths / 480)  // 2024年度満額816,000円/年

return {
    employeePension: totalEmployeePension,
    nationalPension: nationalPension,
    totalAnnualPension: totalEmployeePension + nationalPension,
    source: 'calculated',
}
```

アルゴリズム（個人事業主 `'selfEmployed'`）:
```
// 厚生年金なし、国民年金のみ
totalPensionMonths = person.pensionConfig.pastNationalPensionMonths + yearsWorkedFromNow * 12
cappedMonths = min(totalPensionMonths, 480)
nationalPension = 816_000 × (cappedMonths / 480)

return {
    employeePension: 0,
    nationalPension: nationalPension,
    totalAnnualPension: nationalPension,
    source: 'calculated',
}
```

アルゴリズム（専業主婦 `'homemaker'`）:
```
// 第3号被保険者: 国民年金のみ（保険料負担なしで受給資格あり）
totalPensionMonths = person.pensionConfig.pastNationalPensionMonths
cappedMonths = min(totalPensionMonths, 480)
nationalPension = 816_000 × (cappedMonths / 480)

return {
    employeePension: 0,
    nationalPension: nationalPension,
    totalAnnualPension: nationalPension,
    source: 'calculated',
}
```

### `applyMacroEconomicSlide` — マクロ経済スライド適用

```typescript
/**
 * マクロ経済スライドによる年金額調整を適用する
 * @param basePension 計算された基準年金額（円/年）
 * @param yearsFromRetirement 受給開始からの経過年数
 * @param growthRate 年金成長率（デフォルト: 0.01）
 * @returns 調整後の年金額
 */
function applyMacroEconomicSlide(
    basePension: number,
    yearsFromRetirement: number,
    growthRate: number = 0.01
): number {
    return basePension * Math.pow(1 + growthRate, yearsFromRetirement)
}
```

### `calculateIncome` の変更（内部）

`calculateIncome` 関数内の年金フェーズ（`age >= person.pensionStartAge`）の処理を変更:

```typescript
// 変更前
if (age >= person.pensionStartAge) {
    const inflationMultiplier = Math.pow(1 + inflationRate, yearsFromStart)
    return person.pensionAmount * inflationMultiplier
}

// 変更後
if (age >= person.pensionStartAge) {
    const basePension = getPensionAmount(person, ...)  // 固定値 or 計算値
    const yearsFromRetirement = age - person.pensionStartAge
    const growthRate = person.pensionConfig?.pensionGrowthRate ?? inflationRate
    return applyMacroEconomicSlide(basePension, yearsFromRetirement, growthRate)
}

// getPensionAmount: 固定値と計算値の選択
function getPensionAmount(person: Person, ...): number {
    if (person.pensionAmount !== undefined) {
        return person.pensionAmount   // 固定値優先（後方互換）
    }
    // pensionConfig がある場合は計算値
    // ...
}
```

---

## DEFAULT_CONFIG変更

```typescript
// person1 に pensionConfig 追加（デフォルト設定例）
person1: {
    // ...既存
    pensionAmount: 1500000,    // 固定値が指定されているため計算値は使われない（後方互換）
    // pensionConfig は省略（固定値優先）
},
person2: {
    // ...既存
    pensionAmount: 1200000,
    // pensionConfig は省略
},
```

自動計算を使う場合の設定例（ドキュメント用）:
```typescript
person1: {
    // ...既存
    pensionAmount: undefined,         // 固定値なし → 計算値を使用
    pensionConfig: {
        pastEmployeeMonths: 120,           // 10年間の厚生年金加入
        pastAverageMonthlyRemuneration: 400_000,  // 過去の平均標準報酬月額40万
        pastNationalPensionMonths: 120,    // 10年間の国民年金加入
        pensionGrowthRate: 0.01,           // マクロ経済スライド1%
    },
},
```

---

## YearlyData / SimulationResult への追加フィールド

現状の `YearlyData.income` はすでに年金を含む手取り収入を示しているため、
個別の年金内訳は `SimulationResult` に追加する:

```typescript
// SimulationResult に追加
export interface SimulationResult {
    // ...既存
    pensionBreakdown?: {
        person1: PensionBreakdown
        person2: PensionBreakdown | null
    }
}
```

---

## テスト影響分析

### 既存テストへの影響

- `person.pensionAmount` を使うテストは引き続き固定値が優先されるため変更なし
- `pensionConfig` を指定しない限り既存の動作が維持される
- **影響テスト数: 0**

### 新規テストケース

```typescript
describe('年金詳細計算', () => {
    test('会社員: 厚生年金 = 平均標準報酬 × 加入月数 × 0.005481 + 国民年金', () => {
        // pastEmployeeMonths=240, pastAverageMonthlyRemuneration=400_000
        // futureMonths=120（10年就労）, futureMontlyRemuneration=500_000
        // 厚生年金 = 400_000*240*0.005481 + 500_000*120*0.005481
        //          = 527_136 + 328_860 = 855_996
        // 国民年金 = 816_000 * min(240+240+120, 480)/480 = 816_000 (満額)
        // 合計 = 1_671_996
    })

    test('個人事業主: 国民年金のみ', () => {
        // 厚生年金 = 0
        // 国民年金 = 816_000 * 月数/480
    })

    test('専業主婦: 国民年金(第3号)のみ', () => {
        // homemaker
    })

    test('加入月数480未満: 年金が満額より少ない', () => {
        // pastNationalPensionMonths=240 → 国民年金 = 816_000 * 0.5 = 408_000
    })

    test('pensionAmount 固定値が指定されている場合は計算値を無視する（後方互換）', () => {
        // pensionAmount: 1_500_000, pensionConfig: {...}
        // → income に 1_500_000 ベースの年金が使われる
    })

    test('マクロ経済スライド: 年金開始から10年後に約10.5%増加', () => {
        // pensionGrowthRate=0.01 → 10年後 = basePension * 1.01^10 ≈ 1.105 * base
    })

    test('年金計算値を使った55年シミュレーション: 収入フェーズが正しく切り替わる', () => {
        // pensionAmount: undefined, pensionConfig あり
        // → pensionStartAge に達した年から計算された年金額が income に反映される
    })
})
```

---

## 後方互換性

- `person.pensionAmount` が指定されている場合は常にそちらを優先（既存の66テスト全て対象外）
- `pensionConfig` を使う場合のみ新ロジックが実行される
- `DEFAULT_CONFIG` の `pensionAmount` は削除しない（固定値優先のまま）

---

## 実装上の注意点

### 1. 乗率の適用区分

厚生年金の乗率（0.005481）は2003年4月以降の加入分に適用される新乗率。
2003年3月以前の加入分は旧乗率（0.007125）が適用される。
実装簡略化として**全期間を新乗率（0.005481）で統一**する（差異は小さく設計書として記録）。

### 2. 将来の平均標準報酬月額の計算（等比数列の期待値を使用）

**[P3-CRIT-1] 対応**: 退職時点の標準報酬月額を30年間の平均として使うと過大評価になる。

例: 年収500万円・2%成長・30年就労の場合、退職時年収は約905万円になり、
月額754,000円の標準報酬月額を30年間の平均として使うのは実際の平均（約630万円/12）と乖離する。

**採用する解決策: 等比数列の期待値を使用**

```typescript
// 収入成長率 r で N年間就労する場合の平均標準報酬月額
// 等比数列の和の公式: 平均 = grossIncome * (Math.pow(1 + r, N) - 1) / (r * N)

const N = yearsToRetirement  // 就労年数
const r = config.person1.incomeGrowthRate  // 収入成長率

let avgGrossIncome: number
if (r > 0) {
    avgGrossIncome = config.person1.grossIncome * (Math.pow(1 + r, N) - 1) / (r * N)
} else {
    avgGrossIncome = config.person1.grossIncome  // r = 0 の場合（ゼロ除算回避）
}

const avgMonthlyStandardRemuneration = Math.min(avgGrossIncome / 12, 635_000)
const pension = calculatePensionAmount(config.person1, yearsToRetirement, avgMonthlyStandardRemuneration)
// 以降の年次ループでこの pension.totalAnnualPension を使用
```

この計算により、収入成長率が高い場合でも実態に近い平均標準報酬月額を年金計算に使用できる。

### 3. 産休育休期間の年金加入

産休育休中も厚生年金の加入が継続される（本人負担免除）。
P2C との連携で産休育休期間の月数もカウントが必要だが、簡略化として就労月数に含めてよい。

### 4. 年次ループの前年値繰り越し変数の初期値（全フェーズ共通）

```typescript
// runSingleSimulation 冒頭で初期化
let capitalGainsLastYear = 0        // P4D・P6で使用
let lastYearFireIncome = 0          // P6で使用（FIRE前は0）
// 全ての前年値変数の初期値はゼロ
```
