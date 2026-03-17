# Phase 6: FIRE後税金・社会保険

## 概要

FIRE達成後は給与所得がなくなり、社会保険が会社員の健保・厚年から「国民健康保険+国民年金」に
切り替わる。国保保険料は前年の合計所得（セミFIRE収入+株式売却益）ベースで動的に計算され、
FIRE初年度は前年の高給与所得で国保が急増する「初年度スパイク」が発生する。

## 依存Phase

- 前提: P4D（`capitalGainsLastYear` の追跡）、P5（セミFIRE収入の把握）
- P1（`employmentType`・`grossIncome` 基盤）も前提
- 影響: P7（取り崩し戦略の実手取り計算精度向上）、P8（UI: 社会保険費用の可視化）

---

## インターフェース変更

### SimulationConfig

```typescript
// 変更前
// FIRE後の社会保険は未実装

// 変更後
export interface SimulationConfig {
    // ...既存フィールド
    postFireSocialInsurance: PostFireSocialInsuranceConfig  // 追加
}

// 追加
export interface PostFireSocialInsuranceConfig {
    // 国民健康保険（市区町村によって異なるが平均的な率を使用）
    nhisoIncomeRate: number        // 医療分所得割率（デフォルト: 0.1100, 11%）
    nhisoSupportIncomeRate: number // 後期高齢者支援金分所得割率（デフォルト: 0.0259, 全国平均）
                                   // [P6-CRIT-1] 対応: 医療分と独立して設定
    nhisoFixedAmountPerPerson: number  // 均等割/人（デフォルト: 50_000）
    nhisoHouseholdFixed: number    // 平等割（デフォルト: 30_000）
    nhisoMaxAnnual: number         // 参考値（デフォルト: 1_060_000）
                                   // 実際の上限は各分（医療分650,000 + 支援金分240,000 + 介護分170,000）に個別適用

    // 国民年金保険料
    nationalPensionMonthlyPremium: number  // 月額（デフォルト: 16_980）

    // 介護保険（40〜64歳: 国保の介護分、65歳〜: 第1号被保険者）
    longTermCareRate: number       // 所得割（デフォルト: 0.0200）
    longTermCareMax: number        // 上限（デフォルト: 170_000）
}
```

### YearlyData への追加フィールド

```typescript
export interface YearlyData {
    // ...既存
    nhInsurancePremium: number        // 国保保険料（FIRE後のみ）
    nationalPensionPremium: number    // 国民年金保険料（FIRE後60歳未満のみ）
    postFireSocialInsurance: number   // 国保 + 国民年金の合計
    capitalGainsLastYear: number      // 前年の売却益（国保計算用に記録）
}
```

---

## 関数仕様

### `calculateNHIPremium` — 国民健康保険料計算

```typescript
/**
 * 国民健康保険料を計算する（前年の合計所得ベース）
 * 所得割 + 均等割 + 平等割 の合算、年間上限あり
 *
 * @param lastYearTotalIncome 前年の合計所得
 *   = セミFIRE労働収入（手取り前のグロス） + 株式売却益（capitalGainsLastYear）
 * @param householdSize 世帯人数（保険料の均等割に影響）
 * @param config 国保設定
 * @param age 年齢（介護保険料の加算判定用）
 * @returns 年間国保保険料
 */
function calculateNHIPremium(
    lastYearTotalIncome: number,
    householdSize: number,
    config: PostFireSocialInsuranceConfig,
    age: number
): number
```

アルゴリズム:
```
// 基礎控除（43万円）後の課税所得割合
deductedIncome = max(0, lastYearTotalIncome - 430_000)

// 医療分（上限: 650,000円/年）
medicalIncomeRate = deductedIncome * config.nhisoIncomeRate
medicalFixed = config.nhisoFixedAmountPerPerson * householdSize + config.nhisoHouseholdFixed
medicalTotal = min(medicalIncomeRate + medicalFixed, 650_000)

// 後期高齢者支援分（独立した所得割率: 全国平均 2.59%）
// [P6-CRIT-1] 対応: 「医療分の約30%」という粗い近似ではなく、独立した所得割率を使用
nhisoSupportIncomeRate = 0.0259  // 後期高齢者支援金分所得割率（全国平均値）
supportIncomeRate = deductedIncome * nhisoSupportIncomeRate
supportFixed = config.nhisoFixedAmountPerPerson * 0.3 * householdSize  // 均等割の支援分
supportTotal = min(supportIncomeRate + supportFixed, 240_000)  // 上限: 240,000円/年

// 介護分（40〜64歳のみ、上限: 170,000円/年）
careTotal = 0
if 40 <= age < 65:
    careIncomeRate = deductedIncome * config.longTermCareRate
    careFixed = config.nhisoFixedAmountPerPerson * 0.5 * householdSize
    careTotal = min(careIncomeRate + careFixed, config.longTermCareMax)  // 上限: 170,000

// 合計（各分の上限適用後の合計）
// [P6-CRIT-1] 対応: 各分に個別上限を適用後に合計する（総合上限の二重適用を防止）
// 医療分上限:650,000 + 支援金分上限:240,000 + 介護分上限:170,000 = 各分の上限後合計
// 旧の総合上限 min(total, nhisoMaxAnnual) は削除し、各分の上限適用後の合計をそのまま返す
total = medicalTotal + supportTotal + careTotal
return total

// 参考: 2024年度の各分の上限
// 医療分上限  = 650,000円/年
// 支援金分上限 = 240,000円/年
// 介護分上限  = 170,000円/年
// 3分合計の実質的な上限 = 1,060,000円/年（各分上限の合計）
```

### `calculateNationalPensionPremium` — 国民年金保険料

```typescript
/**
 * FIRE後60歳未満の国民年金保険料を計算する
 * @param age 年齢
 * @param config 社保設定
 * @returns 年間国民年金保険料（60歳以上はゼロ）
 */
function calculateNationalPensionPremium(
    age: number,
    config: PostFireSocialInsuranceConfig
): number {
    if (age >= 60) return 0
    return config.nationalPensionMonthlyPremium * 12  // 年額203,760円（2024年度）
}
```

### `calculatePostFireSocialInsurance` — FIRE後社会保険合計

```typescript
/**
 * FIRE後の社会保険料合計を計算する
 * @param personAge person1 の年齢
 * @param lastYearGrossIncome 前年の就労収入（セミFIRE収入）
 * @param capitalGainsLastYear 前年の株式売却益
 * @param householdSize 世帯人数
 * @param config 社保設定
 * @returns 年間社会保険料合計
 */
function calculatePostFireSocialInsurance(
    personAge: number,
    lastYearGrossIncome: number,
    capitalGainsLastYear: number,
    householdSize: number,
    config: PostFireSocialInsuranceConfig
): number {
    const lastYearTotalIncome = lastYearGrossIncome + capitalGainsLastYear
    const nhip = calculateNHIPremium(lastYearTotalIncome, householdSize, config, personAge)
    const npp = calculateNationalPensionPremium(personAge, config)
    return nhip + npp
}
```

### `runSingleSimulation` 内の変更

```typescript
// FIRE後の年次処理に追加
if (isPostFire) {
    // ... 既存の年金収入計算 ...

    // 社会保険料（支出に加算）
    const postFireSI = calculatePostFireSocialInsurance(
        person1Age,
        semiFIREGrossLastYear,    // P5 で追跡
        capitalGainsLastYear,     // P4D で追跡
        householdSize,            // person2 がいれば 2、いなければ 1
        config.postFireSocialInsurance
    )

    // 社会保険料を支出に上乗せ（生活費以外の固定費として扱う）
    totalExpenses += postFireSI

    yearlyData.push({
        // ...
        nhInsurancePremium: calculateNHIPremium(...),
        nationalPensionPremium: calculateNationalPensionPremium(person1Age, config.postFireSocialInsurance),
        postFireSocialInsurance: postFireSI,
        capitalGainsLastYear: capitalGainsLastYear,
    })
}
```

---

## FIRE初年度スパイクの扱い

```
【問題】
FIRE達成年（例: year3）: 就労収入あり（高給与）
FIRE達成翌年（year4）: 国保計算は「前年（year3）の所得」ベース
→ 前年が高所得のため国保が最大値（106万円）になる「初年度スパイク」

【設計】
year4 の国保計算で lastYearGrossIncome = year3 の就労収入（グロス）を使用
year5 以降は前年のセミFIRE収入+売却益が基準になるため通常水準に落ち着く

【年次ループ内での実装】
let lastYearFireIncome = 0  // 前年の就労収入（年次ループで繰り越し）
// ...（各年のループ内）
if (!isPostFire) {
    lastYearFireIncome = totalGrossIncome  // 就労中は毎年更新
} else {
    lastYearFireIncome = semiFIREGrossThisYear  // FIRE後はセミFIRE収入のみ
}
// 翌年の国保計算に lastYearFireIncome を使用
```

---

## DEFAULT_CONFIG変更

**[P6-CRIT-2] 対応**: `DEFAULT_CONFIG` には本番で使うリアルなデフォルト値を設定する。
テストの `cfg()` ヘルパーでは `postFireSocialInsurance` を全てゼロにする上書きを追加する。

```typescript
// simulator.ts の DEFAULT_CONFIG（本番デフォルト値）
postFireSocialInsurance: {
    nhisoIncomeRate: 0.1100,          // 医療分所得割11%（全国平均）
    nhisoSupportIncomeRate: 0.0259,   // 後期高齢者支援金分所得割2.59%（全国平均）
    nhisoFixedAmountPerPerson: 50_000, // 均等割5万円/人
    nhisoHouseholdFixed: 30_000,       // 平等割3万円
    nhisoMaxAnnual: 1_060_000,         // 参考値（各分の上限合計）
    nationalPensionMonthlyPremium: 16_980,  // 2024年度月額
    longTermCareRate: 0.0200,          // 介護分所得割2%
    longTermCareMax: 170_000,          // 介護分上限17万円
},
```

```typescript
// __tests__/simulator.test.ts の cfg() ヘルパー（テスト用ゼロ値）
// 既存FIRE後テストへの影響をゼロにするため、cfg() 内でゼロ上書きを追加
function cfg(overrides: Partial<SimulationConfig> = {}): SimulationConfig {
    return {
        // ...
        postFireSocialInsurance: {
            nhisoIncomeRate: 0,           // テスト時はゼロに設定
            nhisoSupportIncomeRate: 0,    // テスト時はゼロに設定
            nhisoFixedAmountPerPerson: 0,
            nhisoHouseholdFixed: 0,
            nhisoMaxAnnual: 0,
            nationalPensionMonthlyPremium: 0,
            longTermCareRate: 0,
            longTermCareMax: 0,
        },
        // overrides で上書き可能
        ...overrides,
    }
}
```

この設計により:
- `DEFAULT_CONFIG` は実際のユーザー体験で正確な計算を提供する
- `cfg()` はゼロ上書きで既存FIRE後テストへの影響を完全に排除する

---

## テスト影響分析

### 既存テストへの影響

FIRE後の社会保険は新機能であり、既存テストは FIRE後の `totalExpenses` に社保を含まない。

**[P6-CRIT-2] 対応**: `DEFAULT_CONFIG` には本番値（11%等）を設定し、
テストの `cfg()` ヘルパー内で `postFireSocialInsurance` を全てゼロにオーバーライドする。
（詳細は上記「DEFAULT_CONFIG変更」セクション参照）

これにより既存FIRE後テストへの影響はゼロになる。

### 新規テストケース

```typescript
describe('FIRE後税金・社会保険', () => {
    test('FIRE後60歳未満: 国民年金保険料が支出に加算される', () => {
        // postFireSocialInsurance.nationalPensionMonthlyPremium = 16_980
        // FIRE後 age45 → 年16_980*12 = 203_760 が expenses に加算
    })

    test('FIRE後60歳以上: 国民年金保険料ゼロ', () => {
        // age60 以上 → nationalPensionPremium = 0
    })

    test('前年所得ゼロ: 国保は均等割+平等割のみ', () => {
        // lastYearTotalIncome = 0 → nhip = fixed + household = 50_000 + 30_000 = 80_000
        // (householdSize=1 の場合)
    })

    test('前年所得が高い（FIRE初年度スパイク）: 国保が上限近くになる', () => {
        // lastYearGrossIncome = 7_000_000 → nhip ≈ nhisoMaxAnnual
    })

    test('前年売却益が国保計算に含まれる', () => {
        // lastYearCapGains = 2_000_000 → 所得割増加
    })

    test('FIRE達成翌年の expenses が就労中より増加する（社保スパイク）', () => {
        // year3: FIRE達成, year4: 社保スパイク確認
    })

    test('40歳以上: 介護保険料が加算される', () => {
        // age45 → careTotal > 0
    })

    test('65歳以降: 第1号被保険者の介護保険料（別計算）に切り替わる', () => {
        // age >= 65 → longTermCareRate の計算が変わる
        // 簡略化: age < 40 or age >= 65 なら careTotal = 0 で統一も可
    })

    test('世帯人数が多いと均等割が増える', () => {
        // householdSize=2 vs 1 で nhip が異なる
    })
})
```

---

## 後方互換性

- `DEFAULT_CONFIG` には本番で使うリアルなデフォルト値（`nhisoIncomeRate: 0.1100` 等）を設定する
- テストの `cfg()` ヘルパーに `postFireSocialInsurance` を全てゼロにする上書きを追加し、
  既存FIRE後テストへの影響をゼロにする
- UI で「詳細設定」として折りたたんで表示し、デフォルトは平均値に設定するオプションも検討

---

## 実装上の注意点

### 1. 前年所得の繰り越し（全フェーズ共通の初期値）

年次ループ内で前年の情報を繰り越す変数が増加する:
- `capitalGainsLastYear` (P4D)
- `semiFIREGrossLastYear`（`lastYearFireIncome`）(P5 + P6)

**全ての前年値変数の初期値はゼロ**（`year = 0` の前年値として使用）。

```typescript
// runSingleSimulation 冒頭で初期化（全フェーズ共通）
let capitalGainsLastYear = 0        // P4D・P6で使用
let lastYearFireIncome = 0          // P6で使用（FIRE前は0）

for (let year = 0; year <= config.simulationYears; year++) {
    // ... 処理 ...
    // 次の年のために前年値を更新
    capitalGainsLastYear = capitalGainsThisYear
    lastYearFireIncome = isPostFire ? semiFIREGrossThisYear : totalGrossIncome
}
```

### 2. 世帯人数の計算

`householdSize` は `person2 !== null ? 2 : 1` とシンプルに計算する。
子どもの有無を均等割に反映する場合は将来拡張とする。

### 3. 国保の地域差

国保保険料率は市区町村によって大きく異なる（所得割: 9%〜13%程度）。
デフォルトは全国平均的な11%を使用。UIで調整可能にすることを推奨。

### 4. 65歳以降の社会保険

65歳以降は:
- 国民年金の保険料負担がなくなる（受給側になる）
- 健康保険は後期高齢者医療制度（75歳以降）へ移行
- 介護保険は第1号被保険者として市区町村が徴収（年金天引き）

Phase 6 の実装スコープとしては:
- 60歳以上: 国民年金保険料 = 0
- 65歳以降: 国保継続（後期高齢者移行は75歳で処理、または簡略化して無視）
- 75歳以降: 後期高齢者医療制度（保険料率が異なるが、簡略化として国保と同率で計算可）
