/**
 * スナップショット回帰テスト
 *
 * 代表的な入力パターンでシミュレーション全期間の yearlyData を
 * スナップショットとして保存し、意図しない計算変更を検知する。
 *
 * 計算ロジックを意図的に変更した場合は `npx vitest -u` でスナップショットを更新する。
 */

import { describe, test, expect } from 'vitest'
import { runSingleSimulation, findEarliestFireAge, SimulationConfig, DEFAULT_CONFIG } from '../lib/simulator'

// ─────────────────────────────────────────────────────────────────────────────
// ヘルパー: yearlyData から計算結果に関係するフィールドのみ抽出
// （year/age などのメタデータは除外し、計算値に集中）
// ─────────────────────────────────────────────────────────────────────────────

function extractSnapshotData(result: ReturnType<typeof runSingleSimulation>) {
  return {
    fireAge: result.fireAge,
    fireNumber: result.fireNumber,
    depletionAge: result.depletionAge,
    peakAssets: result.peakAssets,
    fireAchievementRate: result.fireAchievementRate,
    yearlyData: result.yearlyData.map(y => ({
      age: y.age,
      cashAssets: Math.round(y.cashAssets),
      stocks: Math.round(y.stocks),
      nisaAssets: Math.round(y.nisaAssets),
      idecoAssets: Math.round(y.idecoAssets),
      otherAssets: Math.round(y.otherAssets),
      grossIncome: Math.round(y.grossIncome),
      totalTax: Math.round(y.totalTax),
      income: Math.round(y.income),
      expenses: Math.round(y.expenses),
      childCosts: Math.round(y.childCosts),
      childAllowance: Math.round(y.childAllowance),
      mortgageCost: Math.round(y.mortgageCost),
      capitalGains: Math.round(y.capitalGains),
      capitalGainsTax: Math.round(y.capitalGainsTax),
      isFireAchieved: y.isFireAchieved,
      postFireSocialInsurance: Math.round(y.postFireSocialInsurance),
      investmentGain: Math.round(y.investmentGain),
    })),
  }
}

function cfg(overrides: Partial<SimulationConfig> = {}): SimulationConfig {
  const base: SimulationConfig = {
    cashAssets: 0,
    stocks: 0,
    stocksCostBasis: 0,
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
    childAllowanceEnabled: true,
    simulationYears: 1,
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
  }
  const { person1, person2, nisa, ideco, ...rest } = overrides
  const effectiveStocks = overrides.stocks ?? (overrides.currentAssets ?? 0)
  return {
    ...base,
    ...rest,
    currentAssets: undefined,
    cashAssets: overrides.cashAssets ?? 0,
    stocks: effectiveStocks,
    stocksCostBasis: overrides.stocksCostBasis ?? effectiveStocks,
    person1: person1 ? { ...base.person1, ...person1 } : base.person1,
    person2: person2 !== undefined ? person2 : base.person2,
    nisa: nisa ? { ...base.nisa, ...nisa } : base.nisa,
    ideco: ideco ? { ...base.ideco, ...ideco } : base.ideco,
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// パターン 1: 単身・会社員・基本設定（収入のみ、投資なし）
// ─────────────────────────────────────────────────────────────────────────────

describe('スナップショット回帰テスト', () => {
  test('パターン1: 単身・会社員・年収500万・支出20万/月・リターン0%・10年', () => {
    const result = runSingleSimulation(cfg({
      person1: {
        currentAge: 35,
        retirementAge: 65,
        grossIncome: 5_000_000,
        incomeGrowthRate: 0.02,
        pensionStartAge: 65,
        pensionAmount: 1_200_000,
        employmentType: 'employee',
      },
      monthlyExpenses: 200_000,
      simulationYears: 10,
    }))
    expect(extractSnapshotData(result)).toMatchSnapshot()
  })

  test('パターン2: 単身・投資リターン5%・NISA有・20年', () => {
    const result = findEarliestFireAge(cfg({
      stocks: 5_000_000,
      stocksCostBasis: 3_000_000,
      person1: {
        currentAge: 35,
        retirementAge: 65,
        grossIncome: 7_000_000,
        incomeGrowthRate: 0.02,
        pensionStartAge: 65,
        pensionAmount: 1_500_000,
        employmentType: 'employee',
      },
      nisa: { enabled: true, annualContribution: 1_200_000 },
      monthlyExpenses: 250_000,
      investmentReturn: 0.05,
      simulationYears: 20,
    }))
    expect(extractSnapshotData(result)).toMatchSnapshot()
  })

  test('パターン3: 夫婦・子1人・NISA+iDeCo・30年', () => {
    const result = findEarliestFireAge(cfg({
      cashAssets: 2_000_000,
      stocks: 8_000_000,
      stocksCostBasis: 6_000_000,
      person1: {
        currentAge: 35,
        retirementAge: 50,
        grossIncome: 7_000_000,
        incomeGrowthRate: 0.02,
        pensionStartAge: 65,
        pensionAmount: 1_500_000,
        employmentType: 'employee',
      },
      person2: {
        currentAge: 33,
        retirementAge: 50,
        grossIncome: 5_000_000,
        incomeGrowthRate: 0.02,
        pensionStartAge: 65,
        pensionAmount: 1_200_000,
        employmentType: 'employee',
      },
      nisa: { enabled: true, annualContribution: 1_200_000 },
      ideco: { enabled: true, monthlyContribution: 23_000 },
      children: [{ birthYear: 2022, educationPath: 'public' as const }],
      monthlyExpenses: 350_000,
      expenseGrowthRate: 0.01,
      investmentReturn: 0.05,
      inflationRate: 0.01,
      simulationYears: 30,
      childAllowanceEnabled: true,
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
    }))
    expect(extractSnapshotData(result)).toMatchSnapshot()
  })

  test('パターン4: FIRE後取り崩し・資産枯渇ケース', () => {
    // 少ない資産で即FIRE→資産が枯渇するパターン
    const result = findEarliestFireAge(cfg({
      stocks: 30_000_000,
      stocksCostBasis: 20_000_000,
      person1: {
        currentAge: 50,
        retirementAge: 50, // 即退職
        grossIncome: 0,
        incomeGrowthRate: 0,
        pensionStartAge: 65,
        pensionAmount: 1_500_000,
        employmentType: 'employee',
      },
      monthlyExpenses: 300_000,
      investmentReturn: 0.03,
      simulationYears: 40,
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
    }))
    expect(extractSnapshotData(result)).toMatchSnapshot()
  })

  test('パターン5: DEFAULT_CONFIG をそのまま使用（全機能統合）', () => {
    const result = findEarliestFireAge(DEFAULT_CONFIG)
    expect(extractSnapshotData(result)).toMatchSnapshot()
  })

  test('パターン6: 住宅ローン + 子2人（私立）+ ライフサイクル支出', () => {
    const result = findEarliestFireAge(cfg({
      cashAssets: 3_000_000,
      stocks: 10_000_000,
      stocksCostBasis: 7_000_000,
      person1: {
        currentAge: 35,
        retirementAge: 55,
        grossIncome: 10_000_000,
        incomeGrowthRate: 0.02,
        pensionStartAge: 65,
        pensionAmount: 2_000_000,
        employmentType: 'employee',
      },
      person2: {
        currentAge: 33,
        retirementAge: 55,
        grossIncome: 4_000_000,
        incomeGrowthRate: 0.01,
        pensionStartAge: 65,
        pensionAmount: 800_000,
        employmentType: 'employee',
      },
      mortgage: { monthlyPayment: 120_000, endYear: 2055 },
      children: [
        { birthYear: 2022, educationPath: 'private' as const },
        { birthYear: 2025, educationPath: 'mixed' as const },
      ],
      nisa: { enabled: true, annualContribution: 1_800_000 },
      ideco: { enabled: true, monthlyContribution: 23_000 },
      monthlyExpenses: 400_000,
      expenseGrowthRate: 0.01,
      investmentReturn: 0.05,
      inflationRate: 0.01,
      simulationYears: 30,
      childAllowanceEnabled: true,
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
    }))
    expect(extractSnapshotData(result)).toMatchSnapshot()
  })
})
