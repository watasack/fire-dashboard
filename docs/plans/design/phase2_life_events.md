# Phase 2: ライフイベント（2A〜2D）

## 概要

Phase 2 は4つのサブフェーズで構成される。2A（ライフステージ別生活費）と2D（児童手当）は
P1と並行実施可能。2B（住宅ローン）はP1と完全独立。2C（産休育休）はP1の標準報酬月額が前提。

## 依存Phase

- 前提: P1（2C のみ）、他は独立
- 影響: P7（ガードレール戦略の裁量支出比率の精緻化）

---

# Phase 2A: ライフステージ別基本生活費

## インターフェース変更

```typescript
// 変更前
export interface SimulationConfig {
    monthlyExpenses: number        // 固定月次生活費
    // ...
}

// 変更後
export interface SimulationConfig {
    monthlyExpenses: number            // 後方互換: 子なし世帯はこちらを使用
    expenseMode: 'fixed' | 'lifecycle' // 追加: 'lifecycle' で自動切替
    lifecycleExpenses?: LifecycleExpenseConfig  // 追加: ライフステージ別設定
    // ...
}

// 追加
export interface LifecycleExpenseConfig {
    // オーバーライド可能な各ステージの年間生活費（省略時はデフォルト値を使用）
    withPreschooler?: number        // 0〜5歳: デフォルト 2,760,000
    withElementaryChild?: number    // 6〜11歳: デフォルト 3,232,000
    withJuniorHighChild?: number    // 12〜14歳: デフォルト 3,468,000
    withHighSchoolChild?: number    // 15〜17歳: デフォルト 3,830,000
    withCollegeChild?: number       // 18〜21歳: デフォルト 3,957,000
    emptyNestActive?: number        // 子なし〜69歳: デフォルト 2,581,000
    emptyNestSenior?: number        // 70〜79歳: デフォルト 2,243,000
    emptyNestElderly?: number       // 80歳〜: デフォルト 1,931,000
}
```

## 関数仕様

### `getLifecycleStageExpenses` — ライフステージ別年間生活費取得

```typescript
/**
 * person1の年齢と子どもの年齢からライフステージを判定し、年間基本生活費を返す
 * @param person1Age person1の年齢（基準人物）
 * @param children 子ども配列
 * @param currentSimYear シミュレーション対象年（子の年齢計算に使用）
 * @param config ライフステージ別設定（省略時はデフォルト値）
 * @returns 年間基本生活費（インフレ調整前）
 */
function getLifecycleStageExpenses(
    person1Age: number,
    children: Child[],
    currentSimYear: number,      // [P2A-MINOR-1] 対応: 子の年齢計算に必要
    config?: LifecycleExpenseConfig
): number
```

アルゴリズム:
```
// 第1子（最年長の子）の年齢でステージを決定
const firstChild = children
    .map(c => ({ ...c, age: currentSimYear - c.birthYear }))
    .filter(c => c.age >= 0)
    .sort((a, b) => b.age - a.age)[0]  // 最年長

if (firstChild && firstChild.age <= 5):
    baseExpenses = config.withPreschooler ?? 2_760_000
elif (firstChild && firstChild.age <= 11):
    baseExpenses = config.withElementaryChild ?? 3_232_000
elif (firstChild && firstChild.age <= 14):
    baseExpenses = config.withJuniorHighChild ?? 3_468_000
elif (firstChild && firstChild.age <= 17):
    baseExpenses = config.withHighSchoolChild ?? 3_830_000
elif (firstChild && firstChild.age <= 21):
    baseExpenses = config.withCollegeChild ?? 3_957_000
elif (person1Age >= 80):
    baseExpenses = config.emptyNestElderly ?? 1_931_000
elif (person1Age >= 70):
    baseExpenses = config.emptyNestSenior ?? 2_243_000
else:
    baseExpenses = config.emptyNestActive ?? 2_581_000

// 第2子以降の追加費用
for each child[1:] (2子目以降):
    childAge = currentSimYear - child.birthYear
    additionalCost += getAdditionalChildCost(childAge)

return baseExpenses + additionalCost
```

### `getAdditionalChildCost` — 第2子以降の追加費用

```typescript
/**
 * 第2子以降1人当たりの追加年間費用を返す
 * 注: 教育費（EDUCATION_COSTS）との重複計上に注意。
 * ライフステージ費用には子に関わる全生活費が含まれるため、
 * 第1子分は baseExpenses に内包済み。
 * @param childAge 子どもの年齢
 * @returns 追加年間費用（円）
 */
function getAdditionalChildCost(childAge: number): number
```

アルゴリズム:
```
if childAge < 0:   return 0
if childAge <= 5:  return 500_000
if childAge <= 11: return 400_000
if childAge <= 17: return 450_000
if childAge <= 21: return 600_000
return 0  // 22歳以降
```

## DEFAULT_CONFIG変更

```typescript
// 変更後
expenseMode: 'fixed',       // デフォルトは後方互換の固定モード
// lifecycleExpenses は省略（固定モードでは使用しない）
```

## YearlyData / SimulationResult への追加フィールド

```typescript
// YearlyData に追加
lifecycleStage: string   // 現在のライフステージ名（デバッグ・UI表示用）
                         // 例: 'withPreschooler' | 'emptyNestActive' | ...
```

## テスト影響分析

### 既存テストへの影響

`expenseMode: 'fixed'` がデフォルトのため既存テストへの影響はゼロ。

### 新規テストケース

```typescript
describe('ライフステージ別生活費', () => {
    test('expenseMode=fixed: 既存の monthlyExpenses が使われる', () => {
        // 後方互換確認
    })
    test('expenseMode=lifecycle: 第1子0歳 → 2,760,000', () => {})
    test('expenseMode=lifecycle: 子が成長するにつれて生活費ステージが切り替わる', () => {
        // year0(子0歳) → year6(子6歳) で expenses が変わる
    })
    test('expenseMode=lifecycle: 子が22歳を超えると空巣期に切り替わる', () => {})
    test('expenseMode=lifecycle: 第2子の追加費用が加算される', () => {})
    test('expenseMode=lifecycle: person1が80歳以上 → emptyNestElderly', () => {})
    test('lifecycleExpenses でデフォルト値をオーバーライドできる', () => {})
})
```

## 後方互換性

`expenseMode` のデフォルトを `'fixed'` とすることで既存の全設定・テストが無変更で動作する。
`children` がある場合に自動で `lifecycle` に切り替えることは**しない**（明示的な指定が必要）。

## 実装上の注意点

### [P2A-CRIT-1] 教育費との二重計上防止

**解決方針**: `expenseMode === 'lifecycle'` のとき、年次ループの `calculateChildCosts()` 呼び出しをスキップする。

ライフステージ費用（`baseExpenses`）には第1子の教育費が含まれている（設計意図）。
`lifecycle` モードで `calculateChildCosts` を引き続き呼ぶと第1子の教育費が二重計上される。

年次ループの擬似コード（変更部分）:

```typescript
// ライフステージモードでは教育費は baseExpenses に内包済みのためスキップ
const childCosts = (config.expenseMode === 'lifecycle')
    ? 0
    : calculateChildCosts(config.children, currentSimYear, config.inflationRate)
```

### 年次ループの前年値繰り越し変数の初期値（全フェーズ共通）

```typescript
// runSingleSimulation 冒頭で初期化
let capitalGainsLastYear = 0        // P4D・P6で使用
let lastYearFireIncome = 0          // P6で使用（FIRE前は0）
// 全ての前年値変数の初期値はゼロ
```

---

# Phase 2B: 住宅ローン

## インターフェース変更

```typescript
// 追加
export interface MortgageConfig {
    monthlyPayment: number   // 月次返済額（元利合計・円）
    endYear: number          // 完済年（西暦）
}

// SimulationConfig に追加
export interface SimulationConfig {
    // ...（既存フィールド）
    mortgage: MortgageConfig | null   // 追加
}
```

## 関数仕様

### `calculateMortgageCost` — 年次ローン返済額

```typescript
/**
 * 当該年のローン返済額（年額）を返す
 * @param mortgage ローン設定（null の場合はゼロを返す）
 * @param currentSimYear シミュレーション対象年（西暦）
 * @returns 年次返済額（円）
 */
function calculateMortgageCost(
    mortgage: MortgageConfig | null,
    currentSimYear: number
): number
```

アルゴリズム:
```
if mortgage === null: return 0
if currentSimYear > mortgage.endYear: return 0
return mortgage.monthlyPayment * 12
```

## DEFAULT_CONFIG変更

```typescript
mortgage: null   // 追加（デフォルトはローンなし）
```

## YearlyData / SimulationResult への追加フィールド

```typescript
// YearlyData に追加
mortgageCost: number   // 当年のローン返済額（完済後はゼロ）
```

## テスト影響分析

### 既存テストへの影響

`mortgage: null` がデフォルトのためゼロ。

### 新規テストケース

```typescript
describe('住宅ローン', () => {
    test('ローンなし(null): mortgageCost = 0', () => {})
    test('ローン期間中: expenses に monthlyPayment * 12 が加算される', () => {
        // endYear=CURRENT_YEAR+9 → year0〜9 は加算、year10 は加算なし
    })
    test('完済後(endYear超過): mortgageCost = 0 に戻る', () => {})
    test('完済により支出が減少し FIRE 達成が早まる', () => {
        // ローンあり vs ローンなし で fireAge を比較
    })
})
```

## 後方互換性

`mortgage: null` がデフォルト。既存テスト・設定への影響はゼロ。

---

# Phase 2C: 産休・育休 ＋ 育休給付金

## インターフェース変更

```typescript
// Child インターフェースに追加
export interface Child {
    birthYear: number           // 既存（後方互換）
    birthDate?: string          // 追加: YYYY-MM-DD（月単位の計算に使用）
    educationPath: "public" | "private" | "mixed"
}

// Person インターフェースに追加（Person の一部として）
export interface Person {
    // ...既存フィールド
    partTimeUntilAge?: number        // 時短勤務終了年齢（この年齢になるまで時短）
    partTimeIncomeRatio?: number     // 時短中の収入比率（例: 0.7 = フル収入の70%）
    maternityLeaveChildBirthYears?: number[]  // 産休・育休を取る子の出生年（年単位近似）
}
```

## 関数仕様

### `calculateMaternityLeaveIncome` — 産休育休給付金計算（年単位近似）

```typescript
/**
 * 産休・育休取得年の収入を給付金ベースで計算する（年単位近似）
 *
 * 正確な計算には出生月単位の処理が必要だが、年次シミュレーターとしての近似:
 * - 産前2ヶ月 + 産後12ヶ月 = 計14ヶ月間の給付を「1年間に平均化」して計算
 *
 * @param grossIncome 産前の税引き前年収
 * @param employmentType 雇用形態
 * @param birthYear 出産年（西暦）
 * @param simYear シミュレーション対象年
 * @returns 給付金ベースの年収（課税対象外扱い）
 */
function calculateMaternityLeaveIncome(
    grossIncome: number,
    employmentType: EmploymentType,
    birthYear: number,
    simYear: number
): number
```

アルゴリズム（年単位近似）:
```
// 年単位近似: birthYear の年と翌年に影響する
// ただしシミュレーターは年次なので、出産年のみ「半減収入」として近似

if employmentType === 'selfEmployed': return 0  // 個人事業主は給付なし

// 産前6週〜産後8週（産休）: 標準報酬日額 × 2/3
standardMonthlyRemuneration = calculateSocialInsurance(grossIncome, 'employee', 30).standardMonthlyRemuneration
dailyWage = standardMonthlyRemuneration / 30
maternityleavePay = dailyWage * (2/3) * (6*7 + 8*7)  // 産前6週+産後8週 = 98日

// 産後8週〜12ヶ月（育休）:
// 前半180日: 標準報酬月額 × 67%
// 後半〜12ヶ月: 標準報酬月額 × 50%
childcareLeave180 = standardMonthlyRemuneration * 0.67 * (180/30)  // 6ヶ月
childcareLeaveRemainder = standardMonthlyRemuneration * 0.50 * 4   // 残り4ヶ月

totalBenefit = maternityleavePay + childcareLeave180 + childcareLeaveRemainder

// 産休育休給付金は非課税なので手取りそのまま
return totalBenefit  // 約1年分の給付金

// 年次ループでの適用方法:
// if (person.maternityLeaveChildBirthYears?.includes(simYear)):
//   income = calculateMaternityLeaveIncome(grossIncome, ...) の給付金計算
// elif (time-shifted part-time work):
//   income = grossIncome * partTimeIncomeRatio → calculateNetIncome
```

### `calculatePartTimeIncome` — 時短勤務収入

```typescript
/**
 * 時短勤務期間中の手取り収入を計算する
 * @param grossIncome フルタイム時の税引き前年収
 * @param partTimeRatio 収入比率（0.0〜1.0）
 * @param employmentType 雇用形態
 * @param age 年齢
 * @returns 時短勤務中の手取り収入
 */
function calculatePartTimeIncome(
    grossIncome: number,
    partTimeRatio: number,
    employmentType: EmploymentType,
    age: number
): number {
    const partTimeGross = grossIncome * partTimeRatio
    return calculateNetIncome(partTimeGross, employmentType, age)
}
```

## 年次ループとの整合（確定した近似方式）

**[P2C-CRIT-1] 対応: 案1（シンプル方式）を採用**

産休育休は本来「月単位のイベント」だが、年次シミュレーターでの近似方法:

```
【採用する近似: 案1（シンプル方式）】
- birthYear の年（year = birthYear - startYear）は妻の収入を maternityLeaveIncome に置き換える
- birthYear + 1 の年は grossIncome * 0.67（育休継続として扱う）
- birthYear + 2 以降は通常収入に戻る

【誤差の許容範囲】
- この近似は year-level で ±1年の誤差を持つ
- 出産月によって年跨ぎになるが、1年単位なら最大12ヶ月の誤差
- 年次シミュレーターとしては許容範囲（1年以内の誤差）と明示する

【birthDate オプション対応（将来拡張）】
- birthDate があれば月単位で前半・後半を分割して年次に配分
- 例: 4月出産なら産休は4〜6月（当年3/12）、育休は7〜翌年3月（当年9/12 + 翌年3/12）
```

**[P2C-CRIT-2] 対応: 給付金の非課税処理を年次ループで明示**

年次ループ内での産休育休年の処理:

```typescript
// 年次ループ内
if (isMaternityLeaveYear) {
    grossIncome_person2 = 0
    tax_person2 = 0
    netIncome_person2 = calculateMaternityLeaveIncome(
        config.person2, childBirthYear, year
    )  // 非課税給付を直接手取りとして設定（税計算をバイパス）
} else {
    // 通常の収入計算（calculateTaxBreakdown を通す）
}
```

これにより `totalIncome → calculateTax → netIncome` の通常フローをバイパスし、
給付金の額面がそのまま手取りになる非課税処理を正確に実装する。

## DEFAULT_CONFIG変更

```typescript
// Person に追加フィールド（デフォルト値）
person1: {
    // ...既存
    partTimeUntilAge: undefined,     // デフォルト: 時短なし
    partTimeIncomeRatio: undefined,  // デフォルト: フルタイム
    maternityLeaveChildBirthYears: undefined,  // デフォルト: 産休なし
}
```

## テスト影響分析

### 既存テストへの影響

全て `maternityLeaveChildBirthYears: undefined` のデフォルトのため影響なし。

### 新規テストケース

```typescript
describe('産休育休給付金', () => {
    test('会社員: 産休育休年の収入が給付金ベースになる', () => {
        // maternityLeaveChildBirthYears: [CURRENT_YEAR]
        // → year0 の income が給付金計算値になる
    })
    test('個人事業主: 産休育休給付金ゼロ', () => {
        // employmentType: 'selfEmployed', maternityLeaveChildBirthYears: [CURRENT_YEAR]
        // → year0 の income が 0 になる
    })
    test('時短勤務: 収入が partTimeIncomeRatio 倍になる', () => {
        // partTimeUntilAge: 40, partTimeIncomeRatio: 0.7, currentAge: 35
        // → year0〜year4(age35〜39) は grossIncome * 0.7 ベースの手取り
        // → year5(age40) は フルタイム収入に戻る
    })
    test('産休育休は非課税: income は給付金の額面そのまま', () => {
        // 通常の税計算が適用されないことを確認
    })
})
```

## 後方互換性

全フィールドが `optional` のため既存テスト・設定への影響はゼロ。

---

# Phase 2D: 児童手当

## インターフェース変更

```typescript
// SimulationConfig に追加
export interface SimulationConfig {
    // ...既存フィールド
    childAllowanceEnabled: boolean  // 追加: デフォルト true
}
```

## 関数仕様

### `calculateChildAllowance` — 児童手当計算

```typescript
/**
 * 当該年の児童手当受取額を計算する（2024年10月改定後の制度）
 * 所得制限撤廃後のルール:
 *   第1子 0〜2歳: 月15,000円
 *   第2子以降 0〜2歳: 月20,000円
 *   全員 3〜17歳（高校卒業まで）: 月10,000円
 * 18歳以降は支給なし
 *
 * @param children 子ども配列
 * @param simYear シミュレーション対象年
 * @returns 年間児童手当受取額（円）
 */
function calculateChildAllowance(
    children: Child[],
    simYear: number
): number
```

アルゴリズム:
```
totalAllowance = 0
for i, child of children:
    childAge = simYear - child.birthYear
    isSecondOrLater = i >= 1   // 0-indexed: 0=第1子, 1=第2子

    if childAge < 0 or childAge >= 18: continue

    if childAge <= 2:
        monthly = isSecondOrLater ? 20_000 : 15_000
    else:  // 3〜17歳
        monthly = 10_000

    totalAllowance += monthly * 12

return totalAllowance
```

## DEFAULT_CONFIG変更

```typescript
childAllowanceEnabled: true   // 追加（デフォルト有効）
```

## YearlyData / SimulationResult への追加フィールド

```typescript
// YearlyData に追加
childAllowance: number   // 当年の児童手当受取額
```

## テスト影響分析

### 既存テストへの影響

**[P2D-CRIT-1] 対応: 影響なしの根拠**

`children: []` がデフォルトのため児童手当はゼロ。既存テストへの影響はゼロ。

詳細な根拠:
- 教育費テスト群（`describe('教育費（子ども）')`）は `children` に子を設定しているが、
  これらのテストは `childCosts` フィールドのみを確認しており、`income` フィールドを直接参照しない
- 上記を確認済みのため、P2D 実装後に `childAllowanceEnabled: true` がデフォルトになっても
  教育費テスト群への影響はゼロ
- `childAllowanceEnabled` のデフォルトを `true` に設定する（使いやすさ優先）
- テスト用 `cfg()` では `children: []` のままにすることで児童手当がゼロになることを確認済み

### 新規テストケース

```typescript
describe('児童手当', () => {
    test('子なし → 0円', () => {})
    test('第1子 0歳 → 15,000 × 12 = 180,000', () => {})
    test('第2子 0歳 → 20,000 × 12 = 240,000', () => {})
    test('3歳以上 → 10,000 × 12 = 120,000（出生順問わず）', () => {})
    test('18歳以上 → 0円', () => {})
    test('複数の子: 各子の手当が加算される', () => {
        // 子1(1歳=第1子): 180,000
        // 子2(5歳=第2子): 120,000
        // 合計: 300,000
    })
    test('児童手当が収入(income)に加算される', () => {
        // yearlyData[i].income には児童手当が含まれる
    })
    test('childAllowanceEnabled=false: 手当がゼロになる', () => {})
})
```

## 後方互換性

`childAllowanceEnabled: true` かつ `children: []` のデフォルト状態では加算額ゼロ。
既存テストの期待値への影響: **なし**（子なしテストが多数）。

ただし `children` を使うテスト（教育費テスト）では児童手当が加算されるため注意が必要。
これらのテストでは `income` フィールドを直接参照しておらず、`childCosts` のみ参照しているため影響なし。

## 実装上の注意点

### 児童手当と収入の扱い

児童手当は現金給付（非課税）であるため:
- `totalIncome`（税引き前収入）には含めない
- 税計算後に `netIncome` に直接加算する
- `YearlyData.income` = `netIncome + childAllowance` として記録
