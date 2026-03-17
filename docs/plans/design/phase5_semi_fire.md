# Phase 5: FIRE後収入（セミFIRE）

## 概要

FIRE達成後も一定期間は「セミリタイア」として部分的に就労する設定を追加する。
現在の「FIRE達成＝即完全退職」モデルから「FIRE達成後〜指定年齢まで就労収入あり」に拡張。
P1完了後から単独で実装可能。実装コストが小さく競合全社が対応済みの高優先度機能。

## 依存Phase

- 前提: P1（税計算基盤が前提だが、P1前でも簡易実装は可能）
- 影響: P6（セミFIRE期間中の収入は国保計算の前年所得に影響）、P8（UI表示）

---

## インターフェース変更

### SimulationConfig

```typescript
// 変更前
export interface SimulationConfig {
    // FIRE後は即完全退職（postFire収入の概念なし）
    // ...
}

// 変更後
export interface SimulationConfig {
    // ...既存フィールド
    postFireIncome: PostFireIncomeConfig | null   // 追加: セミFIRE設定
}

// 追加
export interface PostFireIncomeConfig {
    monthlyAmount: number    // 月次収入（円）: FIRE後〜untilAge まで
    untilAge: number         // セミFIRE終了年齢（この年齢になったら収入ゼロに）
    // taxable: boolean      // 将来拡張: 課税対象かどうか（デフォルト: true）
}
```

---

## 関数仕様

### `calculatePostFireIncome` — FIRE後収入の計算

```typescript
/**
 * FIRE後のセミリタイア収入を計算する
 * @param postFireIncome セミFIRE設定（null の場合はゼロを返す）
 * @param personAge person1 の現在年齢
 * @param isPostFire FIRE達成済みかどうか
 * @returns 税引き前セミFIRE年収（円）
 */
function calculatePostFireIncome(
    postFireIncome: PostFireIncomeConfig | null,
    personAge: number,
    isPostFire: boolean
): number {
    if (!postFireIncome) return 0
    if (!isPostFire) return 0
    if (personAge >= postFireIncome.untilAge) return 0
    return postFireIncome.monthlyAmount * 12
}
```

### `runSingleSimulation` 内の変更

```typescript
// 変更前: FIRE後は totalIncome = 0（年金以外）
if (isPostFire) {
    totalIncome = 0
    // 年金処理...
}

// 変更後: FIRE後もセミFIRE収入があれば加算
if (isPostFire) {
    totalIncome = 0
    // セミFIRE収入（就労収入扱い → 税計算を通す）
    const semiFIREGross = calculatePostFireIncome(
        config.postFireIncome,
        person1Age,
        true
    )
    if (semiFIREGross > 0) {
        // P1 後は calculateTaxBreakdown を使用
        const empType = config.person1.employmentType ?? 'employee'
        totalIncome += calculateNetIncome(semiFIREGross, empType, person1Age)
        // P6 用に grossIncome も記録
        semiFIREGrossThisYear = semiFIREGross
    }
    // 年金処理（既存）...
}
```

---

## DEFAULT_CONFIG変更

```typescript
// 追加
postFireIncome: null,   // デフォルト: セミFIREなし（即完全退職モード）
```

---

## YearlyData / SimulationResult への追加フィールド

```typescript
// YearlyData に追加
isSemiFire: boolean       // 当年がセミFIRE期間かどうか（UI表示用）
semiFireIncome: number    // セミFIRE収入（税引き前）：0 or postFireIncome.monthlyAmount * 12
```

---

## テスト影響分析

### 既存テストへの影響

`postFireIncome: null` がデフォルトのため既存テストへの影響はゼロ。
「FIRE後収入ゼロ」「FIRE後年金のみ」の挙動は維持される。

### 新規テストケース

```typescript
describe('セミFIRE（FIRE後収入）', () => {
    /**
     * 基本動作: FIRE後〜untilAge まで収入あり
     * currentAssets = 500M → year0 で即FIRE
     * postFireIncome: { monthlyAmount: 100_000, untilAge: 50 }
     * currentAge = 35 → year0〜14 (age35〜49) がセミFIRE期間
     */
    test('FIRE後 untilAge まで毎年 monthlyAmount * 12 の収入がある', () => {
        const result = runSingleSimulation(cfg({
            currentAssets: 500_000_000,
            monthlyExpenses: 100_000,
            postFireIncome: { monthlyAmount: 100_000, untilAge: 50 },
            person1: {
                currentAge: 35, retirementAge: 65, grossIncome: 7_000_000,
                incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0,
                employmentType: 'employee',
            },
            investmentReturn: 0,
            inflationRate: 0,
            simulationYears: 20,
        }))
        // year1 (age36): セミFIRE期間 → income > 0
        expect(result.yearlyData[1].isSemiFire).toBe(true)
        expect(result.yearlyData[1].income).toBeGreaterThan(0)
        // year15 (age50): untilAge到達 → セミFIRE終了
        expect(result.yearlyData[15].isSemiFire).toBe(false)
        expect(result.yearlyData[15].income).toBe(0)
    })

    test('postFireIncome = null: 既存の即完全退職動作と同じ', () => {
        // FIRE後 income = 0（年金前）
        const result = runSingleSimulation(cfg({
            currentAssets: 500_000_000,
            monthlyExpenses: 100_000,
            postFireIncome: null,
            person1: { currentAge: 35, retirementAge: 65, grossIncome: 7_000_000,
                incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0,
                employmentType: 'employee' },
            investmentReturn: 0,
            simulationYears: 10,
        }))
        expect(result.yearlyData[1].income).toBe(0)
    })

    test('untilAge を超えたら収入ゼロに戻る', () => {
        // untilAge = 40, age = 41 → income = 0
    })

    test('セミFIRE収入は税計算を通した手取りが income に反映される', () => {
        // postFireIncome.monthlyAmount * 12 = gross → netIncome < gross
    })

    test('FIRE未達成時はセミFIRE収入が加算されない', () => {
        // FIRE達成前は通常の就労収入のみ
        const result = runSingleSimulation(cfg({
            currentAssets: 1_000,
            monthlyExpenses: 100_000,
            postFireIncome: { monthlyAmount: 100_000, untilAge: 50 },
            // FIRE達成しない設定
        }))
        expect(result.yearlyData[0].isSemiFire).toBe(false)
    })

    test('セミFIRE収入があると資産の減少が遅くなる', () => {
        const withSemiFire = runSingleSimulation(cfg({
            currentAssets: 500_000_000,
            monthlyExpenses: 200_000,
            postFireIncome: { monthlyAmount: 100_000, untilAge: 45 },
            investmentReturn: 0,
            simulationYears: 10,
        }))
        const withoutSemiFire = runSingleSimulation(cfg({
            currentAssets: 500_000_000,
            monthlyExpenses: 200_000,
            postFireIncome: null,
            investmentReturn: 0,
            simulationYears: 10,
        }))
        expect(withSemiFire.finalAssets).toBeGreaterThan(withoutSemiFire.finalAssets)
    })

    test('年次データの isSemiFire フラグが正しく設定される', () => {
        // untilAge=40 → age35〜39 が true、age40 以降が false
    })
})
```

---

## 後方互換性

`postFireIncome: null` がデフォルト値のため、既存の設定・テストへの影響はゼロ。
既存の「FIRE後即完全退職」挙動は `postFireIncome = null` として完全に再現される。

---

## 実装上の注意点

### 1. FIRE後収入の税計算方針

セミFIRE期間の収入源（フリーランス・パートなど）は雇用形態が様々だが、
簡略化として `person1.employmentType` を引き継ぐ。
（例: 会社員として設定されていればセミFIRE中も会社員の税計算を適用）

P6 が実装されると FIRE後の社会保険が「国保」に切り替わるが、
P5 の段階では引き続き `employmentType` ベースの税計算を使い、
P6 でオーバーライドする設計とする。

### 2. `isPostFire` フラグとの関係

現行の `isPostFire = fireAge !== null` ロジックは維持。
セミFIRE期間中は `isPostFire = true` かつ `isSemiFire = true` の状態になる。

```
FIRE未達成: isPostFire=false, isSemiFire=false → 通常就労
FIRE後セミFIRE期間: isPostFire=true, isSemiFire=true → セミFIRE収入
FIRE後完全退職: isPostFire=true, isSemiFire=false → 収入ゼロ（年金まで）
年金期間: isPostFire=true, isSemiFire=false → 年金収入
```

### 3. NISA・iDeCo 拠出との関係

現行コードでは `!isPostFire && age < retirementAge` の条件でNISA・iDeCo拠出。
セミFIRE期間中（`isSemiFire = true`）は就労中と同様に拠出を継続するかどうかの判断が必要。

**推奨: セミFIRE中も就労しているとみなして拠出継続可とする。**
ただし NISA の生涯限度額（4B）は引き続き管理する。

```typescript
// NISA拠出条件の修正
if (config.nisa.enabled && (!isPostFire || isSemiFire) && person1Age < config.person1.retirementAge) {
    // 拠出
}
```

### 4. UI での表示

セミFIRE設定の入力UI:
- 「FIRE後も働く」チェックボックス
- 「月収（万円）」入力
- 「何歳まで」入力

シンプルな2項目のみ。詳細な雇用形態・税制は P6 で拡張。

### 5. 年次ループの前年値繰り越し変数の初期値（全フェーズ共通）

```typescript
// runSingleSimulation 冒頭で初期化
let capitalGainsLastYear = 0        // P4D・P6で使用
let lastYearFireIncome = 0          // P6で使用（FIRE前は0）
// 全ての前年値変数の初期値はゼロ
```
