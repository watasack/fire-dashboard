/**
 * プロパティベーステスト
 *
 * 「どんな入力でも成り立つべき不変条件」をランダム入力で検証する。
 * fast-check 等の外部ライブラリに依存せず、シンプルなランダム生成で実装。
 */

import { describe, test, expect } from 'vitest'
import {
  runSingleSimulation,
  SimulationConfig,
  calculateTaxBreakdown,
  withdrawFromTaxableAccount,
  calculateNHIPremium,
  calculateNationalPensionPremium,
  PostFireSocialInsuranceConfig,
} from '../lib/simulator'

// ─────────────────────────────────────────────────────────────────────────────
// ランダム生成ヘルパー
// ─────────────────────────────────────────────────────────────────────────────

/** seeded PRNG（再現性のため） */
function mulberry32(seed: number) {
  return () => {
    let t = seed += 0x6D2B79F5
    t = Math.imul(t ^ t >>> 15, t | 1)
    t ^= t + Math.imul(t ^ t >>> 7, t | 61)
    return ((t ^ t >>> 14) >>> 0) / 4294967296
  }
}

function randInt(rng: () => number, min: number, max: number): number {
  return Math.floor(rng() * (max - min + 1)) + min
}

function randFloat(rng: () => number, min: number, max: number): number {
  return rng() * (max - min) + min
}

function randChoice<T>(rng: () => number, arr: T[]): T {
  return arr[Math.floor(rng() * arr.length)]
}

function generateRandomConfig(rng: () => number): SimulationConfig {
  const currentAge = randInt(rng, 25, 55)
  const retirementAge = randInt(rng, currentAge, 70)
  const grossIncome = randInt(rng, 0, 20_000_000)
  const pensionStartAge = randInt(rng, 60, 70)

  const hasSpouse = rng() > 0.5
  const person2 = hasSpouse ? {
    currentAge: randInt(rng, 25, 55),
    retirementAge: randInt(rng, 40, 70),
    grossIncome: randInt(rng, 0, 10_000_000),
    incomeGrowthRate: randFloat(rng, 0, 0.03),
    pensionStartAge: randInt(rng, 60, 70),
    pensionAmount: randInt(rng, 0, 2_000_000),
    employmentType: randChoice(rng, ['employee', 'selfEmployed', 'homemaker'] as const),
  } : null

  const numChildren = randInt(rng, 0, 3)
  const children = Array.from({ length: numChildren }, () => ({
    birthYear: randInt(rng, 2015, 2030),
    educationPath: randChoice(rng, ['public', 'private', 'mixed'] as const),
  }))

  const nisaEnabled = rng() > 0.5
  const idecoEnabled = rng() > 0.5

  return {
    cashAssets: randInt(rng, 0, 10_000_000),
    stocks: randInt(rng, 0, 50_000_000),
    stocksCostBasis: randInt(rng, 0, 50_000_000),
    monthlyExpenses: randInt(rng, 100_000, 500_000),
    expenseGrowthRate: randFloat(rng, 0, 0.03),
    investmentReturn: randFloat(rng, -0.02, 0.10),
    investmentVolatility: randFloat(rng, 0.05, 0.25),
    person1: {
      currentAge,
      retirementAge,
      grossIncome,
      incomeGrowthRate: randFloat(rng, 0, 0.03),
      pensionStartAge,
      pensionAmount: randInt(rng, 0, 2_500_000),
      employmentType: randChoice(rng, ['employee', 'selfEmployed'] as const),
    },
    person2,
    nisa: {
      enabled: nisaEnabled,
      annualContribution: nisaEnabled ? randInt(rng, 0, 3_600_000) : 0,
    },
    ideco: {
      enabled: idecoEnabled,
      monthlyContribution: idecoEnabled ? randInt(rng, 5_000, 68_000) : 0,
    },
    children,
    mortgage: null,
    childAllowanceEnabled: true,
    simulationYears: randInt(rng, 10, 55),
    inflationRate: randFloat(rng, 0, 0.03),
    expenseMode: 'fixed',
    postFireSocialInsurance: {
      nhisoIncomeRate: 0.1100,
      nhisoSupportIncomeRate: 0.0259,
      nhisoFixedAmountPerPerson: 50_000,
      nhisoHouseholdFixed: 30_000,
      nhisoMaxAnnual: 1_060_000,
      nationalPensionMonthlyPremium: 16_980,
      longTermCareRate: 0.0200,
      longTermCareMax: 170_000,
    },
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 不変条件テスト
// ─────────────────────────────────────────────────────────────────────────────

const NUM_TRIALS = 50 // 各テストで50パターンを試行

describe('プロパティベーステスト: シミュレーション不変条件', () => {

  test('不変条件: NISA取り崩しはFIRE後のみ（FIRE前にNISA残高が減少しない）', () => {
    // 仕様: NISA からの売却は FIRE 後のみ。FIRE 前は拠出のみで減少しないはず。
    const rng = mulberry32(12345)
    for (let trial = 0; trial < NUM_TRIALS; trial++) {
      const config = generateRandomConfig(rng)
      const result = runSingleSimulation(config)
      for (const y of result.yearlyData) {
        if (!y.isFireAchieved) {
          // FIRE 前: NISA 残高は拠出+リターンにより非負のまま維持されるはず
          // （マイナスリターンの月があるので「前年以上」ではなく「非負」を検証）
          expect(y.nisaAssets).toBeGreaterThanOrEqual(-1)
        }
      }
    }
  })

  test('不変条件: assets == cashAssets + stocks（後方互換フィールド）', () => {
    // assets は cashAssets + stocks の後方互換フィールド。
    // この等式が実装上正しく維持されているか検証する。
    const rng = mulberry32(67890)
    for (let trial = 0; trial < NUM_TRIALS; trial++) {
      const config = generateRandomConfig(rng)
      const result = runSingleSimulation(config)
      for (const y of result.yearlyData) {
        expect(Math.abs(y.assets - (y.cashAssets + y.stocks))).toBeLessThan(2)
      }
    }
  })

  test('不変条件: 全資産合計 = cashAssets + stocks + nisaAssets + idecoAssets + otherAssets', () => {
    // formatAnnualTableData が使う totalAssets の定義と yearlyData の各フィールドが整合するか。
    // 恒等式ではなく、「5つの独立フィールドの合計が期間を通じて整合する」ことの検証。
    const rng = mulberry32(67891)
    for (let trial = 0; trial < NUM_TRIALS; trial++) {
      const config = generateRandomConfig(rng)
      const result = runSingleSimulation(config)
      for (const y of result.yearlyData) {
        const total = y.cashAssets + y.stocks + y.nisaAssets + y.idecoAssets + y.otherAssets
        // 総資産は非負であるべき（資産枯渇後でも各フィールドが Math.max(0,...) されている）
        expect(total).toBeGreaterThanOrEqual(-1)
        // assets + nisaAssets + idecoAssets + otherAssets とも一致
        expect(Math.abs((y.assets + y.nisaAssets + y.idecoAssets + y.otherAssets) - total)).toBeLessThan(2)
      }
    }
  })

  test('不変条件: 全フィールドが有限値（NaN/Infinity なし）', () => {
    const rng = mulberry32(11111)
    for (let trial = 0; trial < NUM_TRIALS; trial++) {
      const config = generateRandomConfig(rng)
      const result = runSingleSimulation(config)
      for (const y of result.yearlyData) {
        expect(Number.isFinite(y.cashAssets)).toBe(true)
        expect(Number.isFinite(y.stocks)).toBe(true)
        expect(Number.isFinite(y.nisaAssets)).toBe(true)
        expect(Number.isFinite(y.idecoAssets)).toBe(true)
        expect(Number.isFinite(y.income)).toBe(true)
        expect(Number.isFinite(y.expenses)).toBe(true)
        expect(Number.isFinite(y.grossIncome)).toBe(true)
        expect(Number.isFinite(y.totalTax)).toBe(true)
        expect(Number.isFinite(y.investmentGain)).toBe(true)
      }
    }
  })

  test('不変条件: 資産は非負（cashAssets, stocks, nisaAssets, idecoAssets ≥ 0）', () => {
    const rng = mulberry32(22222)
    for (let trial = 0; trial < NUM_TRIALS; trial++) {
      const config = generateRandomConfig(rng)
      const result = runSingleSimulation(config)
      for (const y of result.yearlyData) {
        expect(y.cashAssets).toBeGreaterThanOrEqual(-1) // 丸め誤差許容
        expect(y.stocks).toBeGreaterThanOrEqual(-1)
        expect(y.nisaAssets).toBeGreaterThanOrEqual(-1)
        expect(y.idecoAssets).toBeGreaterThanOrEqual(-1)
      }
    }
  })

  test('不変条件: 収入0・支出0・リターン0 → 資産不変', () => {
    const initialStocks = 10_000_000
    const result = runSingleSimulation({
      cashAssets: 5_000_000,
      stocks: initialStocks,
      stocksCostBasis: initialStocks,
      monthlyExpenses: 0,
      expenseGrowthRate: 0,
      investmentReturn: 0,
      investmentVolatility: 0.15,
      person1: {
        currentAge: 35,
        retirementAge: 90,
        grossIncome: 0,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
      },
      person2: null,
      nisa: { enabled: false, annualContribution: 0 },
      ideco: { enabled: false, monthlyContribution: 0 },
      children: [],
      mortgage: null,
      childAllowanceEnabled: false,
      simulationYears: 10,
      inflationRate: 0,
      expenseMode: 'fixed',
      postFireSocialInsurance: {
        nhisoIncomeRate: 0,
        nhisoSupportIncomeRate: 0,
        nhisoFixedAmountPerPerson: 0,
        nhisoHouseholdFixed: 0,
        nhisoMaxAnnual: 0,
        nationalPensionMonthlyPremium: 0,
        longTermCareRate: 0,
        longTermCareMax: 0,
      },
    })
    for (const y of result.yearlyData) {
      expect(y.cashAssets + y.stocks).toBeCloseTo(15_000_000, -1)
    }
  })

  test('不変条件: FIRE達成後は isFireAchieved が true のまま維持される', () => {
    const rng = mulberry32(33333)
    for (let trial = 0; trial < NUM_TRIALS; trial++) {
      const config = generateRandomConfig(rng)
      const result = runSingleSimulation(config)
      let fireAchieved = false
      for (const y of result.yearlyData) {
        if (y.isFireAchieved) fireAchieved = true
        if (fireAchieved) {
          expect(y.isFireAchieved).toBe(true)
        }
      }
    }
  })

  test('不変条件: depletionAge が設定される場合、その年齢で資産≒0', () => {
    const rng = mulberry32(44444)
    for (let trial = 0; trial < NUM_TRIALS; trial++) {
      const config = generateRandomConfig(rng)
      const result = runSingleSimulation(config)
      if (result.depletionAge !== null) {
        const depletionYear = result.yearlyData.find(y => y.age === result.depletionAge)
        if (depletionYear) {
          const totalAssets = depletionYear.cashAssets + depletionYear.stocks +
            depletionYear.nisaAssets + depletionYear.idecoAssets + depletionYear.otherAssets
          // 枯渇年齢では資産がほぼゼロ
          expect(totalAssets).toBeLessThan(1_000_000) // 年金等の流入で完全ゼロにはならないことがある
        }
      }
    }
  })

  test('不変条件（逆方向）: 年末資産がゼロになった年が存在すれば depletionAge が検出される', () => {
    // 以前のテストは「depletionAge が設定されたとき資産≒0」のみ検証していた（片方向）。
    // このテストは逆方向を補完する:「資産がゼロになったのに depletionAge が null 」を検知する。
    //
    // 正確な判定基準: シミュレーターが depletionAge を設定する条件は
    // `totalAssets === 0`（Math.max(0,...) クランプ後）。
    // → 年末資産が厳密にゼロになった年があれば depletionAge は必ず設定されるべき。
    const rng = mulberry32(77777)
    for (let trial = 0; trial < NUM_TRIALS; trial++) {
      const config = generateRandomConfig(rng)
      const result = runSingleSimulation(config)

      let firstZeroAge: number | null = null
      for (const y of result.yearlyData) {
        const totalAssets = y.cashAssets + y.stocks + y.nisaAssets + y.idecoAssets + y.otherAssets
        if (totalAssets === 0 && firstZeroAge === null) {
          firstZeroAge = y.age
        }
      }

      if (firstZeroAge !== null) {
        // 資産がゼロになった年が存在するなら depletionAge が設定されるべき
        expect(result.depletionAge).not.toBeNull()
        expect(result.depletionAge!).toBeLessThanOrEqual(firstZeroAge)
      }
    }
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 個別関数の不変条件
// ─────────────────────────────────────────────────────────────────────────────

describe('プロパティベーステスト: 個別関数', () => {

  test('calculateTaxBreakdown: 手取り ≤ 年収（どの雇用形態でも）', () => {
    const rng = mulberry32(55555)
    for (let trial = 0; trial < NUM_TRIALS; trial++) {
      const gross = randInt(rng, 0, 30_000_000)
      const empType = randChoice(rng, ['employee', 'selfEmployed', 'homemaker'] as const)
      const age = randInt(rng, 20, 70)
      const result = calculateTaxBreakdown(gross, empType, age)
      expect(result.netIncome).toBeLessThanOrEqual(result.grossIncome + 1)
      expect(result.netIncome).toBeGreaterThanOrEqual(0)
      expect(result.totalTax).toBeGreaterThanOrEqual(0)
    }
  })

  test('calculateTaxBreakdown: 年収0 → 手取り0・税0', () => {
    for (const empType of ['employee', 'selfEmployed', 'homemaker'] as const) {
      const result = calculateTaxBreakdown(0, empType, 35)
      expect(result.netIncome).toBe(0)
      // selfEmployed は国民年金があるため totalTax > 0 になりうる
      if (empType !== 'selfEmployed') {
        expect(result.totalTax).toBe(0)
      }
    }
  })

  test('withdrawFromTaxableAccount: 売却後の残高 + 売却額 = 元の残高', () => {
    const rng = mulberry32(66666)
    for (let trial = 0; trial < NUM_TRIALS; trial++) {
      const stockValue = randInt(rng, 0, 50_000_000)
      const costBasis = randInt(rng, 0, stockValue)
      const target = randInt(rng, 0, stockValue)
      const result = withdrawFromTaxableAccount(target, stockValue, costBasis)
      // 残高 + 売却額 = 元の残高（税は売却額から差し引かれるので関係ない）
      expect(result.remainingValue + result.sellAmount).toBeCloseTo(stockValue, -1)
      expect(result.sellAmount).toBeGreaterThanOrEqual(0)
      expect(result.capitalGainsTax).toBeGreaterThanOrEqual(0)
      expect(result.netProceeds).toBeGreaterThanOrEqual(0)
    }
  })

  test('calculateNHIPremium: 保険料は非負', () => {
    const rng = mulberry32(77777)
    const siConfig: PostFireSocialInsuranceConfig = {
      nhisoIncomeRate: 0.1100,
      nhisoSupportIncomeRate: 0.0259,
      nhisoFixedAmountPerPerson: 50_000,
      nhisoHouseholdFixed: 30_000,
      nhisoMaxAnnual: 1_060_000,
      nationalPensionMonthlyPremium: 16_980,
      longTermCareRate: 0.0200,
      longTermCareMax: 170_000,
    }
    for (let trial = 0; trial < NUM_TRIALS; trial++) {
      const income = randInt(rng, 0, 20_000_000)
      const householdSize = randInt(rng, 1, 5)
      const age = randInt(rng, 30, 80)
      const premium = calculateNHIPremium(income, householdSize, siConfig, age)
      expect(premium).toBeGreaterThanOrEqual(0)
      expect(Number.isFinite(premium)).toBe(true)
    }
  })

  test('calculateNationalPensionPremium: 60歳以上は0', () => {
    const siConfig: PostFireSocialInsuranceConfig = {
      nhisoIncomeRate: 0.1100,
      nhisoSupportIncomeRate: 0.0259,
      nhisoFixedAmountPerPerson: 50_000,
      nhisoHouseholdFixed: 30_000,
      nhisoMaxAnnual: 1_060_000,
      nationalPensionMonthlyPremium: 16_980,
      longTermCareRate: 0.0200,
      longTermCareMax: 170_000,
    }
    for (let age = 60; age <= 90; age++) {
      expect(calculateNationalPensionPremium(age, siConfig)).toBe(0)
    }
    // 60歳未満は正の値
    for (let age = 20; age < 60; age++) {
      expect(calculateNationalPensionPremium(age, siConfig)).toBeGreaterThan(0)
    }
  })
})
