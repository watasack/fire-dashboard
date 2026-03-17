# Phase 1: 年収（税引き前）入力 ＋ 税計算リアーキテクチャ

## 概要

`Person.currentIncome`（手取り想定）を `grossIncome`（税引き前年収）に置き換え、税計算ロジックを
グロスインカム基準に完全書き直しする。これは後続全フェーズの計算精度に直結する最重要フェーズ。

## 依存Phase

- 前提: なし（最初に実施）
- 影響: P2C（産休育休・標準報酬月額が必要）、P3（年金詳細・標準報酬月額が必要）、
  P4D（売却税）、P5（セミFIRE）、P6（FIRE後税金）

---

## 現状の問題分析

### `DEFAULT_CONFIG` の曖昧さ

現在の `person1.currentIncome: 7000000` は「年収700万円」としてコメントされているが、
`calculateTax(income)` がこの値に対して社会保険料・所得税・住民税を計算している。
つまり「税引き前700万円として扱われている」が、変数名が `currentIncome`（手取りを連想）で混乱を招く。

**結論: 現在の実装は `currentIncome` を税引き前年収として扱っている。**
変数名が誤解を生んでいるだけで、計算ロジック自体は「グロス→税計算→手取り」の正しい順序になっている。

### 現行 `calculateTax` の問題点

1. **社会保険料が上限なしの比例計算**: `income * 0.15` と単純計算しているが、
   実際は厚生年金（月額63.5万円上限）・健康保険（月額139万円上限）に上限がある
2. **雇用形態を考慮しない**: 会社員は事業主折半だが、個人事業主は全額自己負担
3. **介護保険料の年齢対応なし**: 40歳以上で追加される介護保険料が未考慮
4. **基礎控除48万円のみ**: 給与所得控除（給与収入に対する控除）が未実装

### テストスイートの現状理解

現テスト66本はすべて `currentIncome` を税引き前年収として入力しており、
`calculateTax()` がそれを「グロス」と見なして計算している前提で期待値が書かれている。
たとえば「年収 5,000,000 → 手取り 3,321,500」テストは、
5M を `calculateTax` に通した結果が期待値になっている。

---

## インターフェース変更

### Person インターフェース

```typescript
// 変更前
export interface Person {
    currentAge: number
    retirementAge: number
    currentIncome: number       // 名称が曖昧（手取り？年収？）
    incomeGrowthRate: number
    pensionStartAge: number
    pensionAmount: number
}

// 変更後
export interface Person {
    currentAge: number
    retirementAge: number
    grossIncome: number          // 税引き前年収（円）[変更: currentIncome → grossIncome]
    incomeGrowthRate: number
    pensionStartAge: number
    pensionAmount: number
    employmentType: EmploymentType  // 追加
    // 後方互換フィールド（P3実装後に削除候補）
    currentIncome?: number       // @deprecated: grossIncome を使うこと
}

// 追加
export type EmploymentType = 'employee' | 'selfEmployed' | 'homemaker'
```

### 新規型: 税計算結果の中間値

```typescript
// 追加: 税計算の内訳を保持（P3の標準報酬月額再利用・P6の国保計算で使用）
export interface TaxBreakdown {
    grossIncome: number               // 税引き前年収
    employmentIncome: number          // 給与所得（給与所得控除後）
    standardMonthlyRemuneration: number  // 標準報酬月額（社保計算の基礎）
    healthInsurancePremium: number    // 健康保険料（本人負担分）
    longTermCareInsurancePremium: number // 介護保険料（40歳以上のみ）
    pensionInsurancePremium: number   // 厚生年金保険料（本人負担分）
    totalSocialInsurance: number      // 社会保険料合計
    taxableIncome: number             // 課税所得（控除後）
    incomeTax: number                 // 所得税
    residentTax: number               // 住民税
    totalTax: number                  // 税・社会保険料の合計
    netIncome: number                 // 手取り（grossIncome - totalTax）
}
```

### YearlyData への追加フィールド

```typescript
// 変更前
export interface YearlyData {
    year: number
    age: number
    assets: number
    nisaAssets: number
    idecoAssets: number
    income: number        // 手取り収入（合算）
    expenses: number
    savings: number
    childCosts: number
    fireNumber: number
    isFireAchieved: boolean
}

// 変更後
export interface YearlyData {
    year: number
    age: number
    assets: number
    nisaAssets: number
    idecoAssets: number
    grossIncome: number       // 追加: 税引き前収入合計（P8のテーブル表示で使用）
    income: number            // 維持: 手取り収入（後方互換）
    totalTax: number          // 追加: 税・社保合計（P8の収支内訳表示で使用）
    expenses: number
    savings: number
    childCosts: number
    fireNumber: number
    isFireAchieved: boolean
}
```

---

## 関数仕様

### `calculateEmploymentIncome` — 給与所得控除計算

```typescript
/**
 * 税引き前給与収入から給与所得を計算する（給与所得控除を適用）
 * 国税庁「給与所得控除額の計算方法」2024年度版に準拠
 * @param grossIncome 税引き前給与年収（円）
 * @returns 給与所得（円）
 */
function calculateEmploymentIncome(grossIncome: number): number
```

アルゴリズム:
```
給与所得控除額:
  grossIncome <= 1,625,000:   控除 = 550,000
  grossIncome <= 1,800,000:   控除 = grossIncome * 0.40 - 100,000
  grossIncome <= 3,600,000:   控除 = grossIncome * 0.30 + 80,000
  grossIncome <= 6,600,000:   控除 = grossIncome * 0.20 + 440,000
  grossIncome <= 8,500,000:   控除 = grossIncome * 0.10 + 1,100,000
  grossIncome > 8,500,000:    控除 = 1,950,000（上限）

給与所得 = max(0, grossIncome - 給与所得控除額)
```

### `calculateSocialInsurance` — 社会保険料計算

```typescript
/**
 * 税引き前年収から社会保険料を計算する
 * @param grossIncome 税引き前年収（円）
 * @param employmentType 雇用形態
 * @param age 年齢（介護保険料の判定に使用）
 * @returns 社会保険料の内訳
 */
function calculateSocialInsurance(
    grossIncome: number,
    employmentType: EmploymentType,
    age: number
): {
    standardMonthlyRemuneration: number
    healthInsurance: number
    longTermCare: number
    pension: number
    total: number
}
```

アルゴリズム（会社員 `'employee'`）:
```
標準報酬月額（健保）= min(grossIncome / 12, 1_390_000)
標準報酬月額（年金）= min(grossIncome / 12, 635_000)

健康保険料率 = 0.0998  // 協会けんぽ東京都2024年度
介護保険料率 = 0.0182  // 40歳以上のみ加算（協会けんぽ2024年度）

健康保険料（年間・本人負担）= 標準報酬月額（健保） × 健保率 / 2 × 12
介護保険料（年間・本人負担）= age >= 40 ? 標準報酬月額（健保） × 介護率 / 2 × 12 : 0
厚生年金保険料（年間・本人負担）= 標準報酬月額（年金） × 0.0915 × 12  // 18.3% / 2

社会保険料合計 = 健康保険料 + 介護保険料 + 厚生年金保険料
```

アルゴリズム（個人事業主 `'selfEmployed'`）:
```
国民健康保険料 = min(grossIncome * 0.10, 1_060_000)  // 簡略計算（P6で精緻化）
国民年金保険料 = 203_760  // 2024年度: 16,980円/月 × 12
介護保険料 = age >= 40 ? min(grossIncome * 0.02, 170_000) : 0  // 所得割+均等割の簡略計算

社会保険料合計 = 国民健康保険料 + 国民年金保険料 + 介護保険料
```

アルゴリズム（専業主婦 `'homemaker'`）:
```
// 第3号被保険者: 社会保険料自己負担なし（配偶者の扶養内）
社会保険料合計 = 0
```

### `calculateTaxBreakdown` — 税計算の完全書き直し

```typescript
/**
 * 税引き前年収から税・社保の内訳と手取りを計算する
 * @param grossIncome 税引き前年収（円）
 * @param employmentType 雇用形態
 * @param age 年齢
 * @returns 税計算の内訳（標準報酬月額はP3・P6で再利用）
 */
function calculateTaxBreakdown(
    grossIncome: number,
    employmentType: EmploymentType,
    age: number
): TaxBreakdown
```

アルゴリズム:
```
1. 給与所得控除（会社員のみ）:
   employmentIncome = employmentType === 'employee'
       ? calculateEmploymentIncome(grossIncome)
       : grossIncome  // 個人事業主は控除なし

2. 社会保険料:
   si = calculateSocialInsurance(grossIncome, employmentType, age)

3. 課税所得:
   basicDeduction = 480_000  // 基礎控除48万円
   taxableIncome = max(0, employmentIncome - si.total - basicDeduction)

4. 所得税（累進課税・2024年度税率表）:
   if taxableIncome <= 1_950_000:    incomeTax = taxableIncome * 0.05
   elif taxableIncome <= 3_300_000:  incomeTax = 97_500 + (taxableIncome - 1_950_000) * 0.10
   elif taxableIncome <= 6_950_000:  incomeTax = 232_500 + (taxableIncome - 3_300_000) * 0.20
   elif taxableIncome <= 9_000_000:  incomeTax = 962_500 + (taxableIncome - 6_950_000) * 0.23
   elif taxableIncome <= 18_000_000: incomeTax = 1_434_000 + (taxableIncome - 9_000_000) * 0.33
   elif taxableIncome <= 40_000_000: incomeTax = 4_404_000 + (taxableIncome - 18_000_000) * 0.40
   else:                             incomeTax = 13_204_000 + (taxableIncome - 40_000_000) * 0.45

   // 復興特別所得税（2037年まで）: +2.1%
   incomeTax = incomeTax * 1.021

5. 住民税:
   residentTax = taxableIncome * 0.10  // 所得割10%（均等割は省略）

6. 合計・手取り:
   totalTax = si.total + incomeTax + residentTax
   netIncome = grossIncome - totalTax
```

### `calculateTax` — Phase 1.0 での扱い（後方互換ラッパー不要）

**[P1-CRIT-2] 対応**: 後方互換ラッパーは作成しない。

Phase 1.0 では `calculateTax` の実装を変更せず、そのまま維持する（計算ロジック変更なし）。

Phase 1.1 の実装時に以下を行う:
1. `calculateTaxBreakdown` を新規実装する（給与所得控除・社保上限・介護保険を含む正確な税計算）
2. `calculateTax` を完全削除する（後方互換ラッパーを作成しない）
3. 全コードパスで `calculateTaxBreakdown` を使用する
4. 全66テストの期待値を一括更新する

**後方互換ラッパーを作成してはいけない理由**: `calculateTaxBreakdown` が給与所得控除を適用すると
計算結果が旧 `calculateTax` と異なる値を返すため、「後方互換」の目的を果たせない。
さらに `si` を計算した直後に `breakdown` で全部やり直す構造はデッドコードになる（設計の自己矛盾）。
Phase 1.1 では正直に「テスト期待値を更新する」方針を徹底する。

### `calculateNetIncome` — 年次ループ用ラッパー

```typescript
/**
 * 就労フェーズの手取り収入を計算する
 * @param grossIncome 税引き前年収（円）
 * @param employmentType 雇用形態
 * @param age 年齢
 * @returns 手取り年収（円）
 */
function calculateNetIncome(
    grossIncome: number,
    employmentType: EmploymentType,
    age: number
): number {
    return calculateTaxBreakdown(grossIncome, employmentType, age).netIncome
}
```

### `calculateIncome` — 既存関数のシグネチャ変更

```typescript
// 変更前
function calculateIncome(
    person: Person,
    age: number,
    inflationRate: number,
    yearsFromStart: number
): number

// 変更後（Person に grossIncome と employmentType が追加されるため内部実装が変わるが、
//         シグネチャは維持して既存の呼び出し箇所を変更なし）
function calculateIncome(
    person: Person,
    age: number,
    inflationRate: number,
    yearsFromStart: number
): number
// 内部実装: currentIncome の参照を grossIncome に変更
//           税計算を calculateTaxBreakdown に切り替え
```

---

## DEFAULT_CONFIG変更

```typescript
// 変更前
person1: {
    currentAge: 35,
    retirementAge: 65,
    currentIncome: 7000000,    // 700万円/年（税引き前として扱われていた）
    ...
},
person2: {
    currentAge: 33,
    retirementAge: 65,
    currentIncome: 5000000,    // 500万円/年
    ...
},

// 変更後
person1: {
    currentAge: 35,
    retirementAge: 65,
    grossIncome: 7000000,      // 税引き前年収700万円（変更: フィールド名のみ）
    employmentType: 'employee', // 追加: 会社員
    ...
},
person2: {
    currentAge: 33,
    retirementAge: 65,
    grossIncome: 5000000,      // 税引き前年収500万円
    employmentType: 'employee',
    ...
},
```

**注意: 数値は変更しない。** 現在のテストは `currentIncome` を税引き前年収として使っており、
数値を変えると全テストの期待値が変わる。フィールド名変更のみで既存の計算結果を保つ。

---

## YearlyData / SimulationResult への追加フィールド

```typescript
// YearlyData に追加
grossIncome: number     // 税引き前収入合計（person1+person2のグロス合算）
totalTax: number        // 税・社保合計

// YearlyData の既存フィールド（維持）
income: number          // 手取り収入（後方互換）= grossIncome - totalTax
```

---

## テスト影響分析

### Phase 1.0 と Phase 1.1 の2段階移行方針

**[P1-CRIT-1] 対応**: Phase 1 は以下の2段階に分割して実装する。

---

#### Phase 1.0: フィールド名変更のみ（計算結果は変わらない）

**目的**: `currentIncome` → `grossIncome` リネーム + `employmentType` 追加のみ。税計算ロジックは変更しない。

**テスト期待値の変更: ゼロ**（計算結果が変わらないため）

移行方針:

1. `Person` インターフェースで `grossIncome` を必須フィールドに追加
2. `currentIncome` を `@deprecated` の optional フィールドとして残す
3. `cfg()` ヘルパー内で `currentIncome` → `grossIncome` を自動マッピングする移行コードを追加
4. 計算エンジン内では `grossIncome ?? currentIncome` でフォールバック

```typescript
// テストファイルの cfg() への変更（Phase 1.0: 最小限）
function cfg(overrides: Partial<SimulationConfig> = {}): SimulationConfig {
    const base: SimulationConfig = {
        // ...
        person1: {
            currentAge: 35,
            retirementAge: 90,
            grossIncome: 0,           // currentIncome → grossIncome に変更
            currentIncome: 0,         // @deprecated: 後方互換で一時維持
            incomeGrowthRate: 0,
            pensionStartAge: 90,
            pensionAmount: 0,
            employmentType: 'employee', // 追加
        },
        // ...
    }
    // overrides の person1 に currentIncome があれば grossIncome にマッピング
    // Phase 1.0 では cfg() に以下のマッピングを追加:
    //   grossIncome: overrides.person1?.currentIncome ?? overrides.person1?.grossIncome ?? 0
    if (overrides.person1?.currentIncome !== undefined && overrides.person1?.grossIncome === undefined) {
        overrides.person1.grossIncome = overrides.person1.currentIncome
    }
    // ...
}
```

**Phase 1.0 完了条件**: 全66テストが期待値変更なしでパスすること。

---

#### Phase 1.1: 税計算ロジック改善（給与所得控除・社保上限・介護保険）

**目的**: `calculateTaxBreakdown` を新規実装し、正確な税計算に切り替える。

**テスト影響: 全66テストの期待値を一括更新する**

給与所得控除を追加すると課税所得が大幅に下がり手取りが増えるため、
例えば「年収 7,000,000 → 手取り X」等の全期待値が変化する。
**Phase 1.1 実装時は全66テストの期待値を一度だけ一括更新することを計画に含める。**

**`calculateTax` の後方互換ラッパーは Phase 1.1 実施時に完全削除する**（[P1-CRIT-2] 対応）。
Phase 1.1 以降は全コードパスで `calculateTaxBreakdown` を使用する。
後方互換ラッパーは作成しない（「後方互換」と称しながら計算結果が変わるため意味をなさない）。

---

#### 各テスト群への影響サマリー

| テスト群 | Phase 1.0 | Phase 1.1 |
|---------|-----------|-----------|
| 収入計算（7テスト） | `cfg()` マッピングで吸収・変更なし | 期待値更新が必要 |
| 税計算ブラケット（8テスト） | 変更なし | 期待値更新が必要 |
| 教育費（13テスト） | 変更なし | 変更なし（収入計算に非依存） |
| NISA積立（4テスト） | 変更なし | 変更なし（収入ゼロのケースが多い） |
| iDeCo積立（4テスト） | 変更なし | 変更なし（収入ゼロのケースが多い） |
| FIRE判定（6テスト） | `cfg()` マッピングで吸収 | 期待値更新が必要 |
| 投資リターン（5テスト） | 変更なし | 変更なし（収入計算に非依存） |
| 90歳時点（6テスト） | `cfg()` マッピングで吸収 | 期待値更新が必要 |
| エッジケース（9テスト） | `cfg()` マッピングで吸収 | 期待値更新が必要 |
| FIRE後取り崩し（4テスト） | `cfg()` マッピングで吸収 | 期待値更新が必要 |

**Phase 1.0 結論**: テストの期待値は一切変更不要。`cfg()` ヘルパーと `Person` 型の後方互換処理のみで対応可能。

**Phase 1.1 結論**: 全66テストの期待値を一括更新する。これは1回限りの計画的な更新であり、以降のフェーズでは変更不要。

### 新規テストケース（Phase 1で追加すべきもの）

```typescript
describe('給与所得控除', () => {
    test('年収162.5万以下: 控除 550,000', () => {
        // grossIncome = 1_500_000 → 控除 = 550_000 → employmentIncome = 950_000
    })
    test('年収360万: 控除 = 360万 * 0.30 + 8万 = 116万', () => {
        // grossIncome = 3_600_000 → 控除 = 1_160_000 → employmentIncome = 2_440_000
    })
    test('年収850万超: 控除上限 195万', () => {
        // grossIncome = 10_000_000 → 控除 = 1_950_000 → employmentIncome = 8_050_000
    })
})

describe('社会保険料（会社員）', () => {
    test('厚生年金は月額63.5万円上限が適用される', () => {
        // grossIncome = 15_000_000 → 標準報酬月額（年金）= 635_000（上限）
        // 厚生年金 = 635_000 * 0.0915 * 12 = 697_410
    })
    test('健康保険は月額139万円上限が適用される', () => {
        // grossIncome = 30_000_000 → 標準報酬月額（健保）= 1_390_000（上限）
    })
    test('40歳以上: 介護保険料が加算される', () => {
        // age=40 → 介護保険料 > 0
        // age=39 → 介護保険料 = 0
    })
})

describe('社会保険料（個人事業主 vs 会社員）', () => {
    test('同一所得でも個人事業主の方が社会保険料が高い', () => {
        // selfEmployed: 国保全額+国民年金全額
        // employee: 事業主折半のため半額
    })
    test('専業主婦の社会保険料自己負担はゼロ', () => {
        // homemaker → socialInsurance.total = 0
    })
})

describe('雇用形態別 手取り計算', () => {
    test('同一grossIncomeで会社員・個人事業主・専業主婦の手取りが異なる', () => {
        // employee < selfEmployed（社保が高い）< homemaker（社保ゼロ）
    })
})

describe('YearlyData の grossIncome / totalTax フィールド', () => {
    test('grossIncome + totalTax の差が income（手取り）と一致する', () => {
        // yearlyData[i].grossIncome - yearlyData[i].totalTax ≈ yearlyData[i].income
    })
})
```

---

## 後方互換性

### `currentIncome` → `grossIncome` 移行戦略

```typescript
// Person インターフェースでの互換処理
export interface Person {
    grossIncome: number        // 必須（新フィールド）
    currentIncome?: number     // @deprecated: optional で残す
    employmentType: EmploymentType  // 必須（新フィールド）、デフォルト: 'employee'
    // ... 他フィールドは変更なし
}
```

ランタイムでのフォールバック（`calculateIncome` 内部）:
```typescript
const gross = person.grossIncome ?? person.currentIncome ?? 0
const empType = person.employmentType ?? 'employee'
```

### 既存ユーザー設定データの保護

本アプリのユーザー設定が `localStorage` に保存されている場合:

```typescript
// 設定読み込み時のマイグレーション（UI層に実装）
function migrateConfig(stored: any): SimulationConfig {
    const config = stored as SimulationConfig
    // currentIncome が残っていれば grossIncome にコピー
    if (config.person1?.currentIncome !== undefined && config.person1?.grossIncome === undefined) {
        config.person1.grossIncome = config.person1.currentIncome
        config.person1.employmentType = config.person1.employmentType ?? 'employee'
    }
    if (config.person2?.currentIncome !== undefined && config.person2?.grossIncome === undefined) {
        config.person2.grossIncome = config.person2.currentIncome
        config.person2.employmentType = config.person2.employmentType ?? 'employee'
    }
    return config
}
```

---

## 実装上の注意点

### 1. 給与所得控除の追加による手取り計算結果の変化（Phase 1.1 限定）

現行実装は給与所得控除を適用していない（`taxableIncome = income - 480_000` のみ）。
給与所得控除を追加すると課税所得が減り、**手取りが現行より増える**。

例: 年収500万円の場合
- 現行: 課税所得 = 500万 - 48万 = 452万 → 所得税 = 232,500 + (452万 - 330万) * 0.20 = 476,500
- 変更後: 給与所得 = 500万 - (500万 * 0.20 + 44万) = 356万 → 課税所得 = 356万 - 48万 = 308万 → 所得税 = 97,500 + (308万 - 195万) * 0.10 = 210,500

**既存テスト66本の期待値が全て無効になる。**

**確定した移行方針: Phase 1.0 → Phase 1.1 の2段階**
- Phase 1.0（フィールド名変更のみ）: テスト期待値変更ゼロ
- Phase 1.1（税計算ロジック改善）: 全66テストの期待値を一括更新する

この2段階方針が確定しているため「オプション」としての曖昧さはない。

### 2. 社会保険料の実効税率への影響

会社員の厚生年金は月額63.5万円（年収762万円相当）を超えると頭打ちになる。
これにより高所得者の実効税率が逆転する可能性がある（社保上限後は税のみ増える）。

### 3. `calculateTax` の後方互換ラッパー

既存コードの `calculateTax(income)` 呼び出しを全て置き換えるのは Phase 1 のスコープ。
ただし外部からエクスポートされていないため、`simulator.ts` 内部のみ変更すれば十分。

### 4. 復興特別所得税（2.1%加算）の適用期間

2013〜2037年までの時限措置。2026年現在は適用対象。
`simulationYears` が2038年以降に跨がる場合は年ごとに判定するか、
設計上は一律適用（保守的）として簡略化するかを決定する必要がある。
**推奨: 計算期間全体に適用（保守的・シンプル）。**

### 5. 住民税の均等割

現行は所得割（10%）のみ。正確には均等割（5,000円程度）も加わるが、
総収入に比して微小のため省略可（設計方針として記録しておく）。

### 6. 年次ループの前年値繰り越し変数の初期値（全フェーズ共通）

```typescript
// runSingleSimulation 冒頭で初期化
let capitalGainsLastYear = 0        // P4D・P6で使用
let lastYearFireIncome = 0          // P6で使用（FIRE前は0）
// 全ての前年値変数の初期値はゼロ
```

これらの変数は年次ループ外で管理し、`year = 0` の前年値として全てゼロを使用する。
