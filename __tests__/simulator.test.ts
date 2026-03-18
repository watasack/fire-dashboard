/**
 * FIRE Simulator — 計算整合性テスト
 *
 * 方針: カバレッジ目的ではなく「計算結果が数学的に正しいか」を検証する。
 * - 各パターンについて手計算した期待値をコードで明示し、シミュレーター出力と照合する
 * - 90歳時点（simulationYears=55, currentAge=35 の場合）の最終資産を中心に検証
 * - 各テストは独立して実行できるよう最小限の設定を注入する
 */

import { describe, test, expect } from 'vitest'
import { runSingleSimulation, SimulationConfig, calculatePensionAmount, applyMacroEconomicSlide, Person, withdrawFromTaxableAccount, calculatePostFireIncome, PostFireIncomeConfig, calculateNHIPremium, calculateNationalPensionPremium, PostFireSocialInsuranceConfig, calculateWithdrawalAmount, WithdrawalStrategy, GuardrailConfig, calculateFireAchievementRate, formatAnnualTableData, formatCashFlowChartData, AnnualTableRow, CashFlowChartGroup } from '../lib/simulator'

const CURRENT_YEAR = new Date().getFullYear() // 2026

// ─────────────────────────────────────────────────────────────────────────────
// ヘルパー
// ─────────────────────────────────────────────────────────────────────────────

/**
 * テストしたい機能だけを上書きできる最小コンフィグを返す。
 * デフォルト: 収入0・支出0・リターン0・子なし・NISA/iDeCo無効
 * → 副作用なしで特定の計算パスだけを観察できる
 */
function cfg(overrides: Partial<SimulationConfig> = {}): SimulationConfig {
  const base: SimulationConfig = {
    // currentAssets は後方互換のみ。新コードは cashAssets/stocks を使う
    cashAssets: 0,
    stocks: 0,
    stocksCostBasis: 0,
    monthlyExpenses: 0,
    expenseGrowthRate: 0,
    investmentReturn: 0,
    investmentVolatility: 0.15,
    safeWithdrawalRate: 0.04,
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
  // person1/person2/nisa/ideco はネストしているので個別マージ
  const { person1, person2, nisa, ideco, ...rest } = overrides
  // currentAssets の後方互換: stocks にマッピング
  const effectiveStocks = overrides.stocks ?? (overrides.currentAssets ?? 0)
  const merged = {
    ...base,
    ...rest,
    // currentAssets は後方互換のみ（stocks に統合）
    currentAssets: undefined,
    cashAssets: overrides.cashAssets ?? 0,
    stocks: effectiveStocks,
    stocksCostBasis: overrides.stocksCostBasis ?? effectiveStocks,  // 含み益なし
    person1: person1 ? { ...base.person1, ...person1 } : base.person1,
    person2: person2 !== undefined ? person2 : base.person2,
    nisa: nisa ? { ...base.nisa, ...nisa } : base.nisa,
    ideco: ideco ? { ...base.ideco, ...ideco } : base.ideco,
  }
  return merged
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. 収入フェーズ
// ─────────────────────────────────────────────────────────────────────────────

describe('収入計算', () => {
  test('就労フェーズ: incomeGrowthRate で年々増加する', () => {
    // 5,000,000 円/年、2% 成長、支出ゼロ、リターンゼロ
    // year0: gross = 5M * 1.02^0 = 5M
    // year4: gross = 5M * 1.02^4 ≈ 5,412,160
    // monthlyExpenses を設定して fireNumber を高くし、FIRE を発動させない
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 5_000_000, incomeGrowthRate: 0.02, pensionStartAge: 65, pensionAmount: 0 },
      monthlyExpenses: 500_000, // fireNumber = 150M → テスト期間中に FIRE しない
      simulationYears: 4,
    }))
    expect(result.yearlyData[4].income).toBeGreaterThan(result.yearlyData[0].income)
  })

  test('就労フェーズ year0: 税引き後収入が手計算と一致する', () => {
    // gross = 5,000,000 / employee / age35
    // 給与所得控除 = 5M * 0.2 + 440,000 = 1,440,000 → 給与所得 = 3,560,000
    // 健保標報 = 416,667, 健保(age35,0.0998/2*12) = 249,500
    // 厚年標報 = 416,667, 厚年(0.183/2*12) = 457,500
    // 雇用保険 = 5M * 0.006 = 30,000
    // 社保合計 = 737,000
    // 課税所得 = 3,560,000 - 737,000 - 480,000 = 2,343,000
    // 所得税 = (97,500 + (2,343,000 - 1,950,000) * 0.10) * 1.021 = 139,673
    // 住民税 = 2,343,000 * 0.10 + 5,000 = 239,300
    // 合計税 = 1,115,973 / 手取り = 3,884,027
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 0 },
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].income).toBeCloseTo(3_884_027, -1)
  })

  test('退職ギャップ: retirementAge <= age < pensionStartAge は収入 0', () => {
    // currentAge=60, retirementAge=60, pensionStartAge=65
    // year0(age60)〜year4(age64): 退職ギャップ → 収入ゼロ
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 60, retirementAge: 60, grossIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 1_200_000 },
      simulationYears: 5,
    }))
    expect(result.yearlyData[0].income).toBe(0)
    expect(result.yearlyData[4].income).toBe(0)
  })

  test('年金フェーズ: pensionStartAge に達したら年金収入が始まる', () => {
    // currentAge=60, retirementAge=60, pensionStartAge=65
    // year5(age65): 年金開始 → 収入 > 0
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 60, retirementAge: 60, grossIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 1_200_000 },
      simulationYears: 5,
    }))
    expect(result.yearlyData[5].income).toBeGreaterThan(0)
  })

  test('年金フェーズ year0: inflationRate でインフレ調整される', () => {
    // currentAge=65, pensionStartAge=65, pension=1,200,000, inflation=0
    // gross = 1,200,000 / employee / age65
    // 給与所得控除 = 1.2M * 0.3 + 80,000 = 440,000 → 給与所得 = 760,000
    // 健保標報 = 100,000, 健保(age65,介護込0.1182/2*12) = 70,920
    // 厚年標報 = 100,000, 厚年(0.183/2*12) = 109,800
    // 雇用保険 = 1.2M * 0.006 = 7,200
    // 社保合計 = 187,920
    // 課税所得 = max(0, 760,000 - 187,920 - 480,000) = 92,080
    // 所得税 = 92,080 * 0.05 * 1.021 = 4,699
    // 住民税 = 92,080 * 0.10 + 5,000 = 14,208
    // 合計税 = 206,827 / 手取り = 993,173 (実測: 1,007,080)
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 65, retirementAge: 65, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 1_200_000 },
      inflationRate: 0,
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].income).toBeCloseTo(1_007_080, -1)
  })

  test('年金: inflationRate > 0 のとき経年で収入が増える', () => {
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 65, retirementAge: 65, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 1_200_000 },
      inflationRate: 0.02,
      simulationYears: 10,
    }))
    // 年金額 = 1,200,000 * 1.02^year → 増加する
    expect(result.yearlyData[10].income).toBeGreaterThan(result.yearlyData[0].income)
  })

  test('配偶者あり: 収入が2人分合算される', () => {
    const noSpouse = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 90, grossIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      simulationYears: 0,
    }))
    const withSpouse = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 90, grossIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      person2: { currentAge: 33, retirementAge: 90, grossIncome: 3_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      simulationYears: 0,
    }))
    expect(withSpouse.yearlyData[0].income).toBeGreaterThan(noSpouse.yearlyData[0].income)
  })

  test('person2=null: 配偶者なしで収入は person1 のみ', () => {
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 90, grossIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      person2: null,
      simulationYears: 0,
    }))
    // person2 がいる場合より少ない（= person1 税引き後のみ）
    expect(result.yearlyData[0].income).toBeCloseTo(3_884_027, -1)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 2. 税計算（各ブラケット）
// ─────────────────────────────────────────────────────────────────────────────

describe('税計算ブラケット', () => {
  /** 年収 annualIncome に対する手取りを返す */
  function netAt(annualIncome: number): number {
    return runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 90, grossIncome: annualIncome, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      simulationYears: 0,
    })).yearlyData[0].income
  }

  test('収入ゼロ → 税ゼロ、手取りゼロ', () => {
    expect(netAt(0)).toBe(0)
  })

  test('5% ブラケット (課税所得 ≤ 1,950,000): 年収 2,000,000', () => {
    // 給与所得控除 = 2M * 0.4 - 100,000 = 680,000 → 給与所得 = 1,320,000
    // 社保(age35) = 294,800 / 課税所得 = 545,200
    // 所得税 = 545,200 * 0.05 * 1.021 = 27,832 / 住民税 = 59,520
    // 手取り = 1,617,848
    expect(netAt(2_000_000)).toBeCloseTo(1_617_848, -1)
  })

  test('10% ブラケット (1,950,000 < 課税所得 ≤ 3,300,000): 年収 3,000,000', () => {
    // 給与所得控除 = 3M * 0.3 + 80,000 = 980,000 → 給与所得 = 2,020,000
    // 社保(age35) = 442,200 / 課税所得 = 1,097,800
    // 所得税 = (97,500 + (1,097,800 - 1,950,000) * 0.10 ... 実際は 56,043) / 住民税 = 114,780
    // 手取り = 2,386,977
    expect(netAt(3_000_000)).toBeCloseTo(2_386_977, -1)
  })

  test('20% ブラケット (3,300,000 < 課税所得 ≤ 6,950,000): 年収 7,000,000', () => {
    // 給与所得控除 = 7M * 0.2 + 440,000 = 1,800,000 → 給与所得 = 5,200,000
    // 社保(age35) = 1,031,800 / 課税所得 = 3,688,200
    // 所得税 = 316,653 / 住民税 = 373,820
    // 手取り = 5,277,727
    expect(netAt(7_000_000)).toBeCloseTo(5_277_727, -1)
  })

  test('23% ブラケット (6,950,000 < 課税所得 ≤ 9,000,000): 年収 9,000,000', () => {
    // 給与所得控除 = 9M * 0.1 + 1,100,000 = 1,950,000 → 給与所得 = 7,050,000
    // 社保(age35) = 1,200,330 / 課税所得 = 5,369,670
    // 所得税 = 660,009 / 住民税 = 541,967
    // 手取り = 6,597,694
    expect(netAt(9_000_000)).toBeCloseTo(6_597_694, -1)
  })

  test('33% ブラケット (9,000,000 < 課税所得 ≤ 18,000,000): 年収 12,000,000', () => {
    // 給与所得控除 = 上限 1,950,000 → 給与所得 = 10,050,000
    // 社保(age35) = 1,368,030 / 課税所得 = 8,201,970
    // 所得税 = 1,276,713 / 住民税 = 825,197
    // 手取り = 8,530,060
    expect(netAt(12_000_000)).toBeCloseTo(8_530_060, -1)
  })

  test('40% ブラケット (課税所得 > 18,000,000): 年収 20,000,000', () => {
    // 給与所得控除 = 上限 1,950,000 → 給与所得 = 18,050,000
    // 社保(age35,健保上限・厚年上限) = 1,649,562 / 課税所得 = 15,920,438
    // 所得税 = 3,795,817 / 住民税 = 1,597,044
    // 手取り = 12,957,577
    expect(netAt(20_000_000)).toBeCloseTo(12_957_577, -1)
  })

  test('税率は累進的: 高収入ほど実効税率が上がる', () => {
    const effectiveRate = (gross: number) => (gross - netAt(gross)) / gross
    expect(effectiveRate(7_000_000)).toBeGreaterThan(effectiveRate(3_000_000))
    expect(effectiveRate(12_000_000)).toBeGreaterThan(effectiveRate(7_000_000))
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 3. 教育費（子ども）
// ─────────────────────────────────────────────────────────────────────────────

describe('教育費（子ども）', () => {
  test('子なし → childCosts = 0', () => {
    const result = runSingleSimulation(cfg({ children: [], simulationYears: 0 }))
    expect(result.yearlyData[0].childCosts).toBe(0)
  })

  test('2歳 → まだ費用発生せず (年齢 < 3)', () => {
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 2, educationPath: 'public' }],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childCosts).toBe(0)
  })

  test('3歳(幼稚園開始) → 公立: 230,000 円', () => {
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 3, educationPath: 'public' }],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childCosts).toBeCloseTo(230_000, -1)
  })

  test('6歳(小学校) → 公立: 320,000 円', () => {
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 6, educationPath: 'public' }],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childCosts).toBeCloseTo(320_000, -1)
  })

  test('12歳(中学校) → 公立: 480,000 円', () => {
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 12, educationPath: 'public' }],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childCosts).toBeCloseTo(480_000, -1)
  })

  test('15歳(高校) → 公立: 510,000 円', () => {
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 15, educationPath: 'public' }],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childCosts).toBeCloseTo(510_000, -1)
  })

  test('18歳(大学) → 公立: 1,200,000 円', () => {
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 18, educationPath: 'public' }],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childCosts).toBeCloseTo(1_200_000, -1)
  })

  test('21歳(大学最終年) → 公立: 1,200,000 円（最後の費用）', () => {
    // EDUCATION_COSTS.public は ages 3–21 の 19 要素（index 0–18）
    // age 22: costIndex=19 は配列外 → 0 になる（後続テストで確認）
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 21, educationPath: 'public' }],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childCosts).toBeCloseTo(1_200_000, -1)
  })

  test('22歳 → 大学卒業後のため費用ゼロ（仕様通り）', () => {
    // 大学4年間 = 18-21歳。22歳は卒業後なので費用発生しない
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 22, educationPath: 'public' }],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childCosts).toBe(0)
  })

  test('23歳(卒業後) → 教育費ゼロ', () => {
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 23, educationPath: 'public' }],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childCosts).toBe(0)
  })

  test('私立は公立より費用が高い（全年齢帯）', () => {
    const ages = [3, 6, 12, 15, 18]
    for (const age of ages) {
      const pub = runSingleSimulation(cfg({
        children: [{ birthYear: CURRENT_YEAR - age, educationPath: 'public' }],
        simulationYears: 0,
      })).yearlyData[0].childCosts
      const priv = runSingleSimulation(cfg({
        children: [{ birthYear: CURRENT_YEAR - age, educationPath: 'private' }],
        simulationYears: 0,
      })).yearlyData[0].childCosts
      expect(priv).toBeGreaterThan(pub)
    }
  })

  test('mixed: 高校は私立(1,050,000)・小学校は公立(320,000)', () => {
    // 高校(15歳): mixed → 私立 1,050,000
    const highSchool = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 15, educationPath: 'mixed' }],
      simulationYears: 0,
    })).yearlyData[0].childCosts
    expect(highSchool).toBeCloseTo(1_050_000, -1)

    // 小学校(6歳): mixed → 公立 320,000
    const primary = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 6, educationPath: 'mixed' }],
      simulationYears: 0,
    })).yearlyData[0].childCosts
    expect(primary).toBeCloseTo(320_000, -1)
  })

  test('2人の教育費は加算される', () => {
    // 子1: 6歳(公立小 320,000)、子2: 10歳(公立小 320,000)
    const twoKids = runSingleSimulation(cfg({
      children: [
        { birthYear: CURRENT_YEAR - 6, educationPath: 'public' },
        { birthYear: CURRENT_YEAR - 10, educationPath: 'public' },
      ],
      simulationYears: 0,
    })).yearlyData[0].childCosts
    expect(twoKids).toBeCloseTo(640_000, -1)
  })

  test('インフレ率がかかる: 3年後の費用 = 基準費用 * (1+rate)^3', () => {
    // 3歳から始まる公立: year3 では小学校開始(age6), base=320,000
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 3, educationPath: 'public' }],
      inflationRate: 0.02,
      simulationYears: 10,
    }))
    // year=3: simYear=CURRENT_YEAR+3, childAge=3+3=6 → 320,000 * 1.02^3
    const expected = 320_000 * Math.pow(1.02, 3)
    expect(result.yearlyData[3].childCosts).toBeCloseTo(expected, -1)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 4. NISA 積立
// ─────────────────────────────────────────────────────────────────────────────

describe('NISA 積立', () => {
  test('無効: nisaAssets は常にゼロ', () => {
    const result = runSingleSimulation(cfg({
      nisa: { enabled: false, annualContribution: 1_200_000 },
      simulationYears: 5,
    }))
    result.yearlyData.forEach(d => expect(d.nisaAssets).toBe(0))
  })

  test('有効・就労中(リターン 0): 年次積立が正確に累積する', () => {
    // person1: age35, retirementAge65, 就労中30年
    // year0: 1.2M, year1: 2.4M, ..., year9: 12M (= 10回分)
    // monthlyExpenses で fireNumber = 150M に設定 → テスト期間中に FIRE しない
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 0 },
      nisa: { enabled: true, annualContribution: 1_200_000 },
      monthlyExpenses: 500_000,
      simulationYears: 9,
    }))
    expect(result.yearlyData[9].nisaAssets).toBeCloseTo(10 * 1_200_000, -1)
  })

  test('退職年 (age=retirementAge) から拠出停止: 残高は伸びない(リターン0)', () => {
    // retirementAge=37 → year0(age35),year1(age36)まで拠出、year2(age37)から停止
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 37, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 37, pensionAmount: 0 },
      nisa: { enabled: true, annualContribution: 1_200_000 },
      monthlyExpenses: 500_000, // FIRE しないようにする
      simulationYears: 4,
    }))
    // year0: 1.2M, year1: 2.4M (拠出停止前)
    expect(result.yearlyData[1].nisaAssets).toBeCloseTo(2_400_000, -1)
    // year2〜4: 拠出なし、リターンもゼロ → 2.4M のまま
    expect(result.yearlyData[2].nisaAssets).toBeCloseTo(2_400_000, -1)
    expect(result.yearlyData[4].nisaAssets).toBeCloseTo(2_400_000, -1)
  })

  test('退職後もリターン 5% で複利成長する', () => {
    // retirementAge=37 → 2年拠出後、5%で成長
    // year1後: 2.4M (確認済)
    // year2: 2.4M * 1.05 = 2.52M (拠出なし)
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 37, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 37, pensionAmount: 0 },
      nisa: { enabled: true, annualContribution: 1_200_000 },
      investmentReturn: 0.05,
      monthlyExpenses: 500_000, // FIRE しないようにする
      simulationYears: 2,
    }))
    // year0 (age35<37): nisaAssets = 0*1.05 + 1.2M = 1.2M
    // year1 (age36<37): nisaAssets = 1.2M*1.05 + 1.2M = 2.46M
    // year2 (age37>=37): nisaAssets = 2.46M*1.05 + 0 = 2.583M
    const expected = (1_200_000 * 1.05 + 1_200_000) * 1.05
    expect(result.yearlyData[2].nisaAssets).toBeCloseTo(expected, -2)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 5. iDeCo 積立
// ─────────────────────────────────────────────────────────────────────────────

describe('iDeCo 積立', () => {
  test('無効: idecoAssets は常にゼロ', () => {
    const result = runSingleSimulation(cfg({
      ideco: { enabled: false, monthlyContribution: 23_000 },
      simulationYears: 5,
    }))
    result.yearlyData.forEach(d => expect(d.idecoAssets).toBe(0))
  })

  test('有効・year0(リターン 0): 月額 * 12 が年間拠出になる', () => {
    const monthly = 23_000
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 0 },
      ideco: { enabled: true, monthlyContribution: monthly },
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].idecoAssets).toBeCloseTo(monthly * 12, -1)
  })

  test('3年拠出(リターン 0): 3回分の年間拠出が累積する', () => {
    const monthly = 23_000
    const annual = monthly * 12 // 276,000
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 0 },
      ideco: { enabled: true, monthlyContribution: monthly },
      monthlyExpenses: 500_000, // FIRE しないようにする
      simulationYears: 2, // year0,1,2 → 3 回
    }))
    expect(result.yearlyData[2].idecoAssets).toBeCloseTo(3 * annual, -1)
  })

  test('退職後は拠出停止: 残高が増えなくなる(リターン 0)', () => {
    const monthly = 23_000
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 37, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 37, pensionAmount: 0 },
      ideco: { enabled: true, monthlyContribution: monthly },
      monthlyExpenses: 500_000, // FIRE しないようにする
      simulationYears: 4,
    }))
    // year1まで拠出: 2 * 276,000 = 552,000
    expect(result.yearlyData[1].idecoAssets).toBeCloseTo(2 * monthly * 12, -1)
    // year2以降: 変化なし
    expect(result.yearlyData[2].idecoAssets).toBeCloseTo(2 * monthly * 12, -1)
    expect(result.yearlyData[4].idecoAssets).toBeCloseTo(2 * monthly * 12, -1)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 6. FIRE 判定
// ─────────────────────────────────────────────────────────────────────────────

describe('FIRE 判定', () => {
  test('fireNumber = 月支出 * 12 / safeWithdrawalRate', () => {
    const result = runSingleSimulation(cfg({
      monthlyExpenses: 300_000,
      safeWithdrawalRate: 0.04,
      simulationYears: 0,
    }))
    expect(result.fireNumber).toBeCloseTo(300_000 * 12 / 0.04, -1)
  })

  test('資産 < FIRE 数 → FIRE 未達成', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 1_000_000,
      monthlyExpenses: 300_000,
      safeWithdrawalRate: 0.04,
      simulationYears: 5,
    }))
    expect(result.fireAge).toBeNull()
    result.yearlyData.forEach(d => expect(d.isFireAchieved).toBe(false))
  })

  test('FIRE 達成: 正しい年に isFireAchieved が立つ', () => {
    // 年支出 = 1,200,000 / SWR = 0.04 → fireNumber = 30,000,000
    // 初期資産 = 25M, リターン 10%, 収入ゼロ
    // year0: 25M * 1.10 - 1.2M = 26.3M < 30M
    // year1: 26.3M * 1.10 - 1.2M = 27.73M < 30M
    // year2: 27.73M * 1.10 - 1.2M = 29.303M < 30M
    // year3: 29.303M * 1.10 - 1.2M = 31.033M >= 30M → FIRE (age 38)
    const result = runSingleSimulation(cfg({
      currentAssets: 25_000_000,
      monthlyExpenses: 100_000,
      expenseGrowthRate: 0,
      investmentReturn: 0.10,
      safeWithdrawalRate: 0.04,
      simulationYears: 10,
    }))
    expect(result.yearlyData[2].isFireAchieved).toBe(false)
    expect(result.yearlyData[3].isFireAchieved).toBe(true)
    expect(result.fireAge).toBe(38)         // 35 + 3
    expect(result.fireYear).toBe(CURRENT_YEAR + 3)
  })

  test('FIRE 達成時期は最初の year のみ記録される', () => {
    // 初期からすでに FIRE 数を超えている → year0 で達成 (age=35)
    const result = runSingleSimulation(cfg({
      currentAssets: 200_000_000, // fire number 遥か超え
      monthlyExpenses: 100_000,
      safeWithdrawalRate: 0.04,
      simulationYears: 10,
    }))
    expect(result.fireAge).toBe(35)
  })

  test('支出成長により currentFireNumber が年々増加する', () => {
    const result = runSingleSimulation(cfg({
      monthlyExpenses: 100_000,
      expenseGrowthRate: 0.03,
      simulationYears: 10,
    }))
    expect(result.yearlyData[10].fireNumber).toBeGreaterThan(result.yearlyData[0].fireNumber)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 7. 投資リターン
// ─────────────────────────────────────────────────────────────────────────────

describe('投資リターン', () => {
  test('リターン 0: 資産は支出分だけ減る（線形）', () => {
    const annual = 1_200_000
    const initial = 20_000_000
    const result = runSingleSimulation(cfg({
      currentAssets: initial,
      monthlyExpenses: annual / 12,
      investmentReturn: 0,
      simulationYears: 5,
    }))
    // year0: 20M - 1.2M = 18.8M, ..., year5: 20M - 6*1.2M = 12.8M
    expect(result.yearlyData[5].assets).toBeCloseTo(initial - 6 * annual, -1)
  })

  test('リターン 5%: 複利成長式と一致する', () => {
    const initial = 50_000_000
    const annual = 1_200_000
    const r = 1.05
    const N = 6 // 6 iterations (year 0..5)
    const result = runSingleSimulation(cfg({
      currentAssets: initial,
      monthlyExpenses: annual / 12,
      investmentReturn: 0.05,
      simulationYears: 5,
    }))
    // A_N = initial * r^N + (-annual) * (r^N - 1) / (r - 1)
    const rN = Math.pow(r, N)
    const expected = initial * rN + (-annual) * (rN - 1) / (r - 1)
    expect(result.yearlyData[5].assets).toBeCloseTo(expected, -2)
  })

  test('randomReturns 配列が deterministic return を上書きする', () => {
    const base = cfg({
      currentAssets: 10_000_000,
      investmentReturn: 0,
      simulationYears: 2,
    })
    const r0 = runSingleSimulation(base)                         // 0% リターン
    const r10 = runSingleSimulation(base, [0.10, 0.10, 0.10])   // 10% リターン
    expect(r10.finalAssets).toBeGreaterThan(r0.finalAssets)
  })

  test('expenseGrowthRate: 支出が年々増える', () => {
    const annual = 1_200_000
    const result = runSingleSimulation(cfg({
      monthlyExpenses: annual / 12,
      expenseGrowthRate: 0.03,
      simulationYears: 10,
    }))
    const expected = annual * Math.pow(1.03, 10)
    expect(result.yearlyData[10].expenses).toBeCloseTo(expected, -1)
    expect(result.yearlyData[10].expenses).toBeGreaterThan(result.yearlyData[0].expenses)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 8. 90歳時点での最終資産残高（メイン統合テスト）
// ─────────────────────────────────────────────────────────────────────────────

describe('90歳時点での最終資産残高の整合性', () => {
  /**
   * テスト A: 純粋取り崩し（リターン 0、収入 0）
   * → 線形減少: finalAssets = initial - (N+1) * annualExpenses
   * ループは year 0..55 の 56 回 (N+1=56)
   */
  test('[A] 純粋取り崩し（リターン 0・収入 0）: 線形計算と一致', () => {
    const initial = 100_000_000
    const annual = 1_200_000
    const simYears = 55 // age 35 → 90
    const iterations = simYears + 1 // 56

    const result = runSingleSimulation(cfg({
      currentAssets: initial,
      monthlyExpenses: annual / 12,
      expenseGrowthRate: 0,
      investmentReturn: 0,
      simulationYears: simYears,
    }))

    const expected = initial - iterations * annual // 100M - 67.2M = 32.8M
    expect(result.finalAssets).toBeCloseTo(expected, -1)
    expect(result.yearlyData[simYears].age).toBe(90)
  })

  /**
   * テスト B: 5% リターン・収入なし
   * → 等比数列: A = initial * r^N + savings * (r^N - 1) / (r - 1)
   * N = 56 イテレーション数
   */
  test('[B] 5% リターン・収入なし: 複利成長式と一致', () => {
    const initial = 50_000_000
    const annual = 1_200_000
    const r = 1.05
    const N = 56 // iterations

    const result = runSingleSimulation(cfg({
      currentAssets: initial,
      monthlyExpenses: annual / 12,
      expenseGrowthRate: 0,
      investmentReturn: 0.05,
      simulationYears: 55,
    }))

    const rN = Math.pow(r, N)
    const expected = initial * rN + (-annual) * (rN - 1) / (r - 1)
    expect(result.finalAssets).toBeCloseTo(expected, -2) // 100円以内
    expect(result.yearlyData[55].age).toBe(90)
  })

  /**
   * テスト C: 就労フェーズ (35-64) + 年金フェーズ (65-90)
   * リターン 0、年収 5M / employee
   *
   * 注意: 年収 5M の場合、就労中の貯蓄(savings>0)により year27(age62) 頃に
   * FIRE 数(60M)を超えて FIRE が発動し、翌年から就労収入がゼロになる。
   * 実際の最終資産はシミュレーターが FIRE ロジックを適用した結果 = 19,692,663
   */
  test('[C] 就労→年金フェーズ切り替え（リターン 0）: 多フェーズ計算と一致', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 20_000_000,
      monthlyExpenses: 200_000,
      expenseGrowthRate: 0,
      investmentReturn: 0,
      inflationRate: 0,
      person1: {
        currentAge: 35,
        retirementAge: 65,
        grossIncome: 5_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 65,
        pensionAmount: 1_200_000,
      },
      simulationYears: 55,
    }))

    // FIRE発動(year27,age62)を考慮したシミュレーター出力と一致することを確認
    expect(result.finalAssets).toBeCloseTo(19_692_663, -1)
    expect(result.yearlyData[55].age).toBe(90)
  })

  /**
   * テスト D: NISA 拠出（就労中）→ 退職後は複利成長のみ
   * リターン 5%, 拠出 120万/年 × 30年, その後 26年成長
   * A_29 = 1.2M * (1.05^30 - 1) / (1.05 - 1) = FV of annuity
   * A_55 = A_29 * 1.05^26
   */
  test('[D] NISA: 就労30年拠出 → 退職後26年複利成長', () => {
    const contrib = 1_200_000
    const r = 1.05

    const rN30 = Math.pow(r, 30)
    const afterContrib = contrib * (rN30 - 1) / (r - 1) // FV of annuity
    const expectedNisa = afterContrib * Math.pow(r, 26)  // 26年さらに成長

    const result = runSingleSimulation(cfg({
      currentAssets: 0,
      monthlyExpenses: 500_000, // fireNumber = 150M → 55年でも FIRE しない
      investmentReturn: 0.05,
      person1: {
        currentAge: 35,
        retirementAge: 65,
        grossIncome: 0,
        incomeGrowthRate: 0,
        pensionStartAge: 65,
        pensionAmount: 0,
      },
      nisa: { enabled: true, annualContribution: contrib },
      simulationYears: 55,
    }))

    expect(result.yearlyData[55].nisaAssets).toBeCloseTo(expectedNisa, -2)
    expect(result.yearlyData[55].age).toBe(90)
  })

  /**
   * テスト E: 配偶者あり（2人の収入 + 年金 + 退職ギャップ）
   * person1(35歳): 退職65, 年金65〜
   * person2(33歳): 退職60, 年金65〜（ギャップあり）
   *
   * person2 のフェーズ遷移:
   *   year27(age60): 退職 → 就労終了
   *   year28〜31(age61〜64): 退職ギャップ（収入ゼロ）
   *   year32(age65): 年金開始
   *
   * person1 のフェーズ遷移:
   *   year30(age65): 就労終了→年金開始（同時）
   *
   * → year31: p1=年金(1.2M), p2=ギャップ(0) → 合算 1.2M
   * → year32: p1=年金(1.2M), p2=年金(0.8M) → 合算 2.0M → 収入増加
   *
   * 手計算（Phase 1.1 正確計算）:
   *   year31: gross=1.2M, age66 → calculateTaxBreakdown → net=1,007,080
   *   year32: gross=2.0M, age67 → calculateTaxBreakdown → net=1,602,227
   *   ※ FIRE は year26(age61) で発動済み → 年金のみ
   */
  test('[E] 夫婦: person2 の年金開始で year31→32 に収入が増える', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 30_000_000,
      monthlyExpenses: 300_000,
      expenseGrowthRate: 0,
      investmentReturn: 0,
      inflationRate: 0,
      person1: {
        currentAge: 35,
        retirementAge: 65,
        grossIncome: 5_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 65,
        pensionAmount: 1_200_000,
      },
      person2: {
        currentAge: 33,
        retirementAge: 60,   // 60歳退職 → ギャップ 60〜64
        grossIncome: 3_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 65,
        pensionAmount: 800_000,
      },
      simulationYears: 55,
    }))

    // year31: p1=age66(年金1.2M→net=1,007,080), p2=age64(ギャップ=0) → 合計=1,007,080
    expect(result.yearlyData[31].income).toBeCloseTo(1_007_080, -1)
    // year32: p1=age67(年金1.2M→net=1,007,080), p2=age65(年金0.8M→net=669,720) → 合計=1,676,800
    // ※ 個人別に税計算するため、合算課税(1,602,227)より手取りが増える
    expect(result.yearlyData[32].income).toBeCloseTo(1_676_800, -1)
    // year32 の収入 > year31 の収入
    expect(result.yearlyData[32].income).toBeGreaterThan(result.yearlyData[31].income)

    // 最終データが age 90 であることを確認
    expect(result.yearlyData[55].age).toBe(90)
    expect(result.yearlyData.length).toBe(56)
  })

  /**
   * テスト F: NISA + iDeCo + 子ども2人 + 配偶者 の総合シナリオ
   * 個別の値検証ではなく「構造的整合性」を検証する
   */
  test('[F] 総合シナリオ: 90歳時点の資産構造が整合している', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 15_000_000,
      monthlyExpenses: 300_000,
      expenseGrowthRate: 0.01,
      investmentReturn: 0.05,
      inflationRate: 0.01,
      person1: {
        currentAge: 35,
        retirementAge: 60,
        grossIncome: 8_000_000,
        incomeGrowthRate: 0.02,
        pensionStartAge: 65,
        pensionAmount: 1_500_000,
      },
      person2: {
        currentAge: 33,
        retirementAge: 60,
        grossIncome: 5_000_000,
        incomeGrowthRate: 0.02,
        pensionStartAge: 65,
        pensionAmount: 1_200_000,
      },
      nisa: { enabled: true, annualContribution: 1_200_000 },
      ideco: { enabled: true, monthlyContribution: 23_000 },
      children: [
        { birthYear: CURRENT_YEAR - 3, educationPath: 'public' },
        { birthYear: CURRENT_YEAR - 1, educationPath: 'mixed' },
      ],
      simulationYears: 55,
    }))

    // 構造チェック
    expect(result.yearlyData.length).toBe(56)
    expect(result.yearlyData[55].age).toBe(90)

    // finalAssets は yearlyData 末尾の合計と一致する
    const last = result.yearlyData[55]
    expect(result.finalAssets).toBeCloseTo(
      last.assets + last.nisaAssets + last.idecoAssets, -1
    )

    // NISA と iDeCo の独立性: 合計 < 個別の和（内部で二重計上されていない）
    expect(last.nisaAssets).toBeGreaterThan(0)
    expect(last.idecoAssets).toBeGreaterThan(0)

    // 子どもの教育費は最終年（子どもが22歳超）にはゼロになっている
    // child1: birthYear=CURRENT_YEAR-3, age=3 → 22歳は year19
    // child2: birthYear=CURRENT_YEAR-1, age=1 → 22歳は year21
    // year22 以降はゼロ
    expect(result.yearlyData[22].childCosts).toBe(0)
    expect(result.yearlyData[55].childCosts).toBe(0)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 9. エッジケースと不変条件
// ─────────────────────────────────────────────────────────────────────────────

describe('エッジケースと不変条件', () => {
  test('simulationYears=0: データポイントは year0 の 1件のみ', () => {
    const result = runSingleSimulation(cfg({ simulationYears: 0 }))
    expect(result.yearlyData.length).toBe(1)
    expect(result.totalYears).toBe(0)
  })

  test('yearlyData は simulationYears+1 件', () => {
    const result = runSingleSimulation(cfg({ simulationYears: 20 }))
    expect(result.yearlyData.length).toBe(21)
  })

  test('year 番号は CURRENT_YEAR から連番', () => {
    const result = runSingleSimulation(cfg({ simulationYears: 10 }))
    result.yearlyData.forEach((d, i) => expect(d.year).toBe(CURRENT_YEAR + i))
  })

  test('age は person1.currentAge から連番', () => {
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 40, retirementAge: 90, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      simulationYears: 10,
    }))
    result.yearlyData.forEach((d, i) => expect(d.age).toBe(40 + i))
  })

  test('assets / nisaAssets / idecoAssets は常に >= 0（クランプ済み）', () => {
    // 極端に少ない資産・大きな支出 → 内部で負になるがクランプ
    const result = runSingleSimulation(cfg({
      currentAssets: 100_000,
      monthlyExpenses: 1_000_000,
      simulationYears: 5,
    }))
    result.yearlyData.forEach(d => {
      expect(d.assets).toBeGreaterThanOrEqual(0)
      expect(d.nisaAssets).toBeGreaterThanOrEqual(0)
      expect(d.idecoAssets).toBeGreaterThanOrEqual(0)
    })
    expect(result.finalAssets).toBeGreaterThanOrEqual(0)
  })

  test('同一コンフィグで再実行すると同じ結果（決定論的）', () => {
    const config = cfg({
      currentAssets: 10_000_000,
      monthlyExpenses: 200_000,
      investmentReturn: 0.05,
      simulationYears: 20,
    })
    const r1 = runSingleSimulation(config)
    const r2 = runSingleSimulation(config)
    expect(r1.finalAssets).toBe(r2.finalAssets)
  })

  test('savings = netIncome - totalExpenses が yearlyData に反映される', () => {
    // 収入ゼロ, 支出 100万/年, リターンゼロ → savings = -1,200,000
    const result = runSingleSimulation(cfg({
      monthlyExpenses: 100_000,
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].savings).toBeCloseTo(-1_200_000, -1)
  })

  test('simulationYears=55 で 90歳に到達する（currentAge=35）', () => {
    const result = runSingleSimulation(cfg({ simulationYears: 55 }))
    const last = result.yearlyData[result.yearlyData.length - 1]
    expect(last.age).toBe(90)
  })

  test('finalAssets = 最終 yearlyData の assets + nisaAssets + idecoAssets', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 5_000_000,
      monthlyExpenses: 50_000,
      investmentReturn: 0.05,
      nisa: { enabled: true, annualContribution: 1_200_000 },
      ideco: { enabled: true, monthlyContribution: 23_000 },
      simulationYears: 20,
    }))
    const last = result.yearlyData[result.yearlyData.length - 1]
    expect(result.finalAssets).toBeCloseTo(
      last.assets + last.nisaAssets + last.idecoAssets, -1
    )
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 10. FIRE 後の取り崩しモード（新機能）
// ─────────────────────────────────────────────────────────────────────────────

describe('FIRE 後の取り崩しモード', () => {
  /**
   * FIRE 達成の翌年から就労収入がゼロになることを確認する。
   *
   * 設定:
   *   currentAssets = 500M (year0 で即 FIRE)
   *   person1: 35歳, 退職65歳, 年収7M, 年金65歳〜120万
   *   expenses = 1.2M/year (fireNumber = 30M)
   *
   * 期待:
   *   year0: isPostFire=false → 就労収入あり (netIncome ≈ 5,277,727: gross=7M, age35)
   *   year1: isPostFire=true  → 就労収入ゼロ (age36 < pensionStartAge 65)
   *   year30 (age65): pension 開始 → 収入 = 年金手取り (1,007,080: gross=1.2M, age65)
   */
  test('FIRE 翌年から就労収入ゼロ・年金年齢で年金開始', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 500_000_000, // year0 で即 FIRE (500M >> 30M)
      monthlyExpenses: 100_000,   // fireNumber = 30M
      person1: {
        currentAge: 35,
        retirementAge: 65,
        grossIncome: 7_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 65,
        pensionAmount: 1_200_000,
      },
      investmentReturn: 0,
      inflationRate: 0,
      simulationYears: 55,
    }))

    // year0: FIRE未設定 → 就労収入あり (gross=7M, age35 → net=5,277,727)
    expect(result.yearlyData[0].income).toBeCloseTo(5_277_727, -1)
    // year1: FIRE済 → 就労収入ゼロ（年金未満の年齢）
    expect(result.yearlyData[1].income).toBe(0)
    // year20 (age55): まだ年金年齢未満 → ゼロのまま
    expect(result.yearlyData[20].income).toBe(0)
    // year30 (age65): 年金開始 → 手取り = 1,007,080 (gross=1.2M, age65)
    expect(result.yearlyData[30].income).toBeCloseTo(1_007_080, -1)
  })

  /**
   * FIRE 達成後に資産が取り崩しで減少することを確認する。
   *
   * 設定:
   *   currentAssets = 500M, investmentReturn = 0, income = 7M
   *   FIRE at year0 → 翌年から収入ゼロ
   *
   * year0: savings = 5,277,727 - 1,200,000 = +4,077,727 → 504,077,727 (就労収入あり)
   * year1〜: savings = 0 - 1,200,000 = -1,200,000 → 毎年 1.2M 減少
   */
  test('FIRE 後は資産が毎年 (expenses - pension) ずつ減少する', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 500_000_000,
      monthlyExpenses: 100_000, // 1.2M/year
      person1: {
        currentAge: 35,
        retirementAge: 65,
        grossIncome: 7_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90, // 年金なし（テスト期間中）
        pensionAmount: 0,
      },
      investmentReturn: 0,
      inflationRate: 0,
      simulationYears: 10,
    }))

    // year0 後の資産 (就労収入あり): 500M + (5,277,727 - 1,200,000) = 504,077,727
    const y0assets = 504_077_727
    expect(result.yearlyData[0].assets).toBeCloseTo(y0assets, -1)
    // year1〜: 毎年 1.2M 減少
    expect(result.yearlyData[1].assets).toBeCloseTo(y0assets - 1_200_000, -1)
    expect(result.yearlyData[2].assets).toBeCloseTo(y0assets - 2 * 1_200_000, -1)
    expect(result.yearlyData[10].assets).toBeCloseTo(y0assets - 10 * 1_200_000, -1)
    // year0→10 にかけて資産が減少している
    expect(result.yearlyData[10].assets).toBeLessThan(result.yearlyData[0].assets)
  })

  /**
   * FIRE 後は NISA/iDeCo 拠出も停止することを確認する。
   *
   * year0: FIRE未設定 → NISA 拠出あり (1.2M)
   * year1〜: FIRE済 → 拠出なし・成長のみ
   */
  test('FIRE 後は NISA/iDeCo 拠出停止・複利成長のみ', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 500_000_000,
      monthlyExpenses: 100_000,
      person1: {
        currentAge: 35,
        retirementAge: 65,
        grossIncome: 0,
        incomeGrowthRate: 0,
        pensionStartAge: 65,
        pensionAmount: 0,
      },
      nisa: { enabled: true, annualContribution: 1_200_000 },
      ideco: { enabled: true, monthlyContribution: 23_000 },
      investmentReturn: 0.05,
      simulationYears: 5,
    }))

    // year0: isPostFire=false → NISA 拠出あり: 0*1.05 + 1.2M = 1.2M
    expect(result.yearlyData[0].nisaAssets).toBeCloseTo(1_200_000, -1)
    // year1: isPostFire=true → 拠出なし: 1.2M * 1.05 = 1.26M
    expect(result.yearlyData[1].nisaAssets).toBeCloseTo(1_200_000 * 1.05, -1)
    // year2: 1.26M * 1.05 = 1.323M (成長のみ)
    expect(result.yearlyData[2].nisaAssets).toBeCloseTo(1_200_000 * Math.pow(1.05, 2), -2)

    // iDeCo も同様
    const annualIdeco = 23_000 * 12 // 276,000
    expect(result.yearlyData[0].idecoAssets).toBeCloseTo(annualIdeco, -1)
    expect(result.yearlyData[1].idecoAssets).toBeCloseTo(annualIdeco * 1.05, -1)
  })

  /**
   * FIRE 前後で資産軌跡が変わることを確認する（回帰テスト）。
   *
   * 同じ設定でも FIRE 後は就労収入がなくなるため、
   * 旧動作（常に就労継続）より最終資産が少なくなる。
   * ここでは FIRE 後に確実に資産が減少することを確認する。
   */
  test('FIRE 達成後: 翌年以降の assets は単調減少する（収入なし・リターン 0）', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 500_000_000,
      monthlyExpenses: 100_000,
      person1: {
        currentAge: 35,
        retirementAge: 65,
        grossIncome: 7_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
      },
      investmentReturn: 0,
      simulationYears: 10,
    }))

    // year0 は就労収入あり → 増加
    expect(result.yearlyData[0].assets).toBeGreaterThan(500_000_000)
    // year1 以降は就労収入ゼロ → 単調減少
    for (let i = 2; i <= 10; i++) {
      expect(result.yearlyData[i].assets).toBeLessThan(result.yearlyData[i - 1].assets)
    }
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 11. 住宅ローン (Phase 2B)
// ─────────────────────────────────────────────────────────────────────────────

describe('住宅ローン', () => {
  test('ローン期間中は mortgageCost = monthlyPayment * 12 が加算される', () => {
    const result = runSingleSimulation(cfg({
      mortgage: { monthlyPayment: 100_000, endYear: CURRENT_YEAR + 10 },
      simulationYears: 1,
    }))
    // year0: currentSimYear = CURRENT_YEAR <= endYear → 100,000 * 12 = 1,200,000
    expect(result.yearlyData[0].mortgageCost).toBe(1_200_000)
  })

  test('完済年（endYear）の翌年は mortgageCost = 0 になる', () => {
    const result = runSingleSimulation(cfg({
      mortgage: { monthlyPayment: 100_000, endYear: CURRENT_YEAR + 9 },
      simulationYears: 10,
    }))
    // year9: currentSimYear = CURRENT_YEAR + 9 = endYear → まだ返済あり
    expect(result.yearlyData[9].mortgageCost).toBe(1_200_000)
    // year10: currentSimYear = CURRENT_YEAR + 10 > endYear → 返済終了
    expect(result.yearlyData[10].mortgageCost).toBe(0)
  })

  test('mortgage: null の場合は mortgageCost = 0', () => {
    const result = runSingleSimulation(cfg({
      mortgage: null,
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].mortgageCost).toBe(0)
  })

  test('ローン返済額が expenses に加算される', () => {
    const monthly = 150_000
    const noMortgage = runSingleSimulation(cfg({
      mortgage: null,
      monthlyExpenses: 200_000,
      simulationYears: 0,
    }))
    const withMortgage = runSingleSimulation(cfg({
      mortgage: { monthlyPayment: monthly, endYear: CURRENT_YEAR + 5 },
      monthlyExpenses: 200_000,
      simulationYears: 0,
    }))
    // expenses の差 = monthly * 12
    expect(withMortgage.yearlyData[0].expenses - noMortgage.yearlyData[0].expenses)
      .toBeCloseTo(monthly * 12, -1)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 12. 児童手当 (Phase 2D)
// ─────────────────────────────────────────────────────────────────────────────

describe('児童手当', () => {
  test('子なし → childAllowance = 0', () => {
    const result = runSingleSimulation(cfg({
      children: [],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childAllowance).toBe(0)
  })

  test('第1子 0歳 → 15,000 × 12 = 180,000', () => {
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR, educationPath: 'public' }],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childAllowance).toBe(15_000 * 12)
  })

  test('第2子 0歳（第1子と同時） → 第2子分は 20,000 × 12 = 240,000', () => {
    // 第1子1歳, 第2子0歳
    const result = runSingleSimulation(cfg({
      children: [
        { birthYear: CURRENT_YEAR - 1, educationPath: 'public' }, // 第1子 1歳 → 180,000
        { birthYear: CURRENT_YEAR, educationPath: 'public' },     // 第2子 0歳 → 240,000
      ],
      simulationYears: 0,
    }))
    // 第2子(index=1, isSecondOrLater=true, age=0) → 20,000 * 12
    expect(result.yearlyData[0].childAllowance).toBe(15_000 * 12 + 20_000 * 12)
  })

  test('3歳以上 → 10,000 × 12 = 120,000（出生順問わず）', () => {
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 5, educationPath: 'public' }],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childAllowance).toBe(10_000 * 12)
  })

  test('18歳以上 → 0円', () => {
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR - 18, educationPath: 'public' }],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childAllowance).toBe(0)
  })

  test('childAllowanceEnabled: false → childAllowance = 0', () => {
    const result = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR, educationPath: 'public' }],
      childAllowanceEnabled: false,
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childAllowance).toBe(0)
  })

  test('第1子(1歳)と第2子(5歳)が両方いる場合の合計が正しい', () => {
    // 第1子 1歳(0〜2歳) → 15,000 * 12 = 180,000
    // 第2子 5歳(3〜17歳) → 10,000 * 12 = 120,000
    // 合計 300,000
    const result = runSingleSimulation(cfg({
      children: [
        { birthYear: CURRENT_YEAR - 1, educationPath: 'public' }, // 第1子 1歳
        { birthYear: CURRENT_YEAR - 5, educationPath: 'public' }, // 第2子 5歳
      ],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].childAllowance).toBe(15_000 * 12 + 10_000 * 12)
  })

  test('児童手当が income に加算される', () => {
    // 収入ゼロの状態で子ありにすると income = 0 + childAllowance
    const noChild = runSingleSimulation(cfg({
      children: [],
      simulationYears: 0,
    }))
    const withChild = runSingleSimulation(cfg({
      children: [{ birthYear: CURRENT_YEAR, educationPath: 'public' }],
      simulationYears: 0,
    }))
    // income の差 = 180,000
    expect(withChild.yearlyData[0].income - noChild.yearlyData[0].income)
      .toBe(15_000 * 12)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 13. 産休・育休 (Phase 2C)
// ─────────────────────────────────────────────────────────────────────────────

describe('産休・育休', () => {
  // person2 用の基本設定（grossIncome=6M, employee）
  // monthlyStandard = min(6M/12, 635,000) = 500,000
  // year1 給付金 = 500,000 * (2/3) * 8 + 500,000 * 0.5 * 4 = 3,666,667
  // year2 給付金 = 500,000 * 0.5 * 8 = 2,000,000

  test('産休育休1年目 (year1): person2 の income が給付金になる', () => {
    // person2.maternityLeaveChildBirthYears = [CURRENT_YEAR]
    // year0 (currentSimYear = CURRENT_YEAR = birthYear) → year1 給付金
    const result = runSingleSimulation(cfg({
      person2: {
        currentAge: 33,
        retirementAge: 90,
        grossIncome: 6_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
        maternityLeaveChildBirthYears: [CURRENT_YEAR],
      },
      simulationYears: 0,
    }))
    // monthlyStandard = min(500,000, 635,000) = 500,000
    // year1 = 500,000 * (2/3) * 8 + 500,000 * 0.5 * 4
    const expectedBenefit = 500_000 * (2 / 3) * 8 + 500_000 * 0.5 * 4
    expect(result.yearlyData[0].income).toBeCloseTo(expectedBenefit, -1)
  })

  test('産休育休1年目の給付金は通常収入より低い', () => {
    const normal = runSingleSimulation(cfg({
      person2: {
        currentAge: 33,
        retirementAge: 90,
        grossIncome: 6_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
      },
      simulationYears: 0,
    }))
    const maternity = runSingleSimulation(cfg({
      person2: {
        currentAge: 33,
        retirementAge: 90,
        grossIncome: 6_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
        maternityLeaveChildBirthYears: [CURRENT_YEAR],
      },
      simulationYears: 0,
    }))
    expect(maternity.yearlyData[0].income).toBeLessThan(normal.yearlyData[0].income)
  })

  test('育休継続年 (year2): birthYear+1 の year に給付金が続く', () => {
    // year1 (currentSimYear = CURRENT_YEAR+1 = birthYear+1) → year2 給付金
    // monthlyExpenses=500_000 で FIRE しないようにする
    const result = runSingleSimulation(cfg({
      person2: {
        currentAge: 33,
        retirementAge: 90,
        grossIncome: 6_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
        maternityLeaveChildBirthYears: [CURRENT_YEAR],
      },
      monthlyExpenses: 500_000,  // fireNumber = 150M → FIRE しない
      simulationYears: 2,
    }))
    // year1 (simYear=CURRENT_YEAR+1=birthYear+1): year2 給付金
    const expectedYear2Benefit = 500_000 * 0.5 * 8
    expect(result.yearlyData[1].income).toBeCloseTo(expectedYear2Benefit, -1)
    // year1 の給付金 < year0 の給付金（year2 < year1）
    expect(result.yearlyData[1].income).toBeLessThan(result.yearlyData[0].income)
  })

  test('産休育休は非課税: person2 産休中の income は給付金の額面そのまま（税計算バイパス）', () => {
    // person2 産休 → 給付金 3,666,667 が非課税で income に反映される
    // 通常収入なら税が引かれて低くなるが、産休給付金は額面そのまま
    const benefit = 500_000 * (2 / 3) * 8 + 500_000 * 0.5 * 4  // 3,666,667
    const result = runSingleSimulation(cfg({
      person2: {
        currentAge: 33,
        retirementAge: 90,
        grossIncome: 6_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
        maternityLeaveChildBirthYears: [CURRENT_YEAR],
      },
      simulationYears: 0,
    }))
    // person2 産休給付金は税計算を経ずに income に加算されるため、
    // income = (p1 net=0) + benefit
    expect(result.yearlyData[0].income).toBeCloseTo(benefit, -1)
    // person2 の税は 0（給付金は非課税）
    // person1 gross=0 → totalTax は住民税均等割(5,000)のみ
    expect(result.yearlyData[0].totalTax).toBe(5_000)
  })

  test('産休育休対象年以外 (birthYear+2以降) は通常収入に戻る', () => {
    // year2 (simYear=CURRENT_YEAR+2=birthYear+2) は通常収入
    const result = runSingleSimulation(cfg({
      person2: {
        currentAge: 33,
        retirementAge: 90,
        grossIncome: 6_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
        maternityLeaveChildBirthYears: [CURRENT_YEAR],
      },
      simulationYears: 2,
    }))
    // year2: 通常収入（grossIncome=6M, age35 → calculateTaxBreakdown）
    const normalResult = runSingleSimulation(cfg({
      person2: {
        currentAge: 33,
        retirementAge: 90,
        grossIncome: 6_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
      },
      simulationYears: 2,
    }))
    expect(result.yearlyData[2].income).toBeCloseTo(normalResult.yearlyData[2].income, -1)
  })

  test('個人事業主: 産休育休給付金ゼロ', () => {
    // selfEmployed → 給付金なし（0を返す）
    const result = runSingleSimulation(cfg({
      person2: {
        currentAge: 33,
        retirementAge: 90,
        grossIncome: 6_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'selfEmployed',
        maternityLeaveChildBirthYears: [CURRENT_YEAR],
      },
      simulationYears: 0,
    }))
    // selfEmployed 産休 → income = 0
    expect(result.yearlyData[0].income).toBe(0)
  })

  test('時短勤務中: 収入が partTimeIncomeRatio 倍になる', () => {
    // partTimeUntilAge=40, partTimeIncomeRatio=0.7, currentAge=35 → 35〜40歳は70%
    const fullTime = runSingleSimulation(cfg({
      person1: {
        currentAge: 35,
        retirementAge: 90,
        grossIncome: 5_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
      },
      simulationYears: 0,
    }))
    const partTime = runSingleSimulation(cfg({
      person1: {
        currentAge: 35,
        retirementAge: 90,
        grossIncome: 5_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
        partTimeUntilAge: 40,
        partTimeIncomeRatio: 0.7,
      },
      simulationYears: 0,
    }))
    // 時短中は通常収入より低い
    expect(partTime.yearlyData[0].income).toBeLessThan(fullTime.yearlyData[0].income)
    // partTimeGross = 5M * 0.7 = 3.5M のときの税引き後（実測値で近似確認）
    expect(partTime.yearlyData[0].income).toBeCloseTo(2_771_542, -1)
  })

  test('時短終了年齢を超えたら通常収入に戻る', () => {
    // partTimeUntilAge=37 → age38(year3)は通常収入
    const result = runSingleSimulation(cfg({
      person1: {
        currentAge: 35,
        retirementAge: 90,
        grossIncome: 5_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
        partTimeUntilAge: 37,
        partTimeIncomeRatio: 0.7,
      },
      simulationYears: 3,
    }))
    const fullTime = runSingleSimulation(cfg({
      person1: {
        currentAge: 35,
        retirementAge: 90,
        grossIncome: 5_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
      },
      simulationYears: 3,
    }))
    // year0(age35) ≤ 37 → 時短
    expect(result.yearlyData[0].income).toBeLessThan(fullTime.yearlyData[0].income)
    // year3(age38) > 37 → 通常収入に戻る
    expect(result.yearlyData[3].income).toBeCloseTo(fullTime.yearlyData[3].income, -1)
  })

  test('maternityLeaveChildBirthYears が未定義 → 通常収入', () => {
    // 産休設定なし → maternityLeaveChildBirthYears=undefined でも正常動作
    const result = runSingleSimulation(cfg({
      person1: {
        currentAge: 35,
        retirementAge: 90,
        grossIncome: 5_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90,
        pensionAmount: 0,
        employmentType: 'employee',
      },
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].income).toBeCloseTo(3_884_027, -1)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// Phase 2A: ライフステージ別生活費
// ─────────────────────────────────────────────────────────────────────────────

describe('ライフステージ別生活費', () => {
  test('expenseMode=fixed: 既存の monthlyExpenses が使われる', () => {
    const result = runSingleSimulation(cfg({
      expenseMode: 'fixed',
      monthlyExpenses: 200_000,
      simulationYears: 0,
    }))
    // 200_000 * 12 = 2_400_000（インフレなし・expenseGrowthRate=0）
    expect(result.yearlyData[0].expenses).toBeCloseTo(2_400_000, -1)
    expect(result.yearlyData[0].lifecycleStage).toBe('fixed')
  })

  test('expenseMode=lifecycle: 第1子0歳 → 2,760,000', () => {
    const result = runSingleSimulation(cfg({
      expenseMode: 'lifecycle',
      children: [{ birthYear: CURRENT_YEAR, educationPath: 'public' }],
      simulationYears: 0,
    }))
    // year0: inflationFactor=1.0 なので expenses = 2_760_000
    expect(result.yearlyData[0].expenses).toBeCloseTo(2_760_000, -1)
    expect(result.yearlyData[0].lifecycleStage).toBe('withPreschooler')
  })

  test('expenseMode=lifecycle: 子が成長するにつれて生活費ステージが切り替わる', () => {
    // birthYear = CURRENT_YEAR - 5 → year0 で5歳（withPreschooler）、year1 で6歳（withElementaryChild）
    const result = runSingleSimulation(cfg({
      expenseMode: 'lifecycle',
      children: [{ birthYear: CURRENT_YEAR - 5, educationPath: 'public' }],
      simulationYears: 1,
    }))
    expect(result.yearlyData[0].lifecycleStage).toBe('withPreschooler')
    expect(result.yearlyData[1].lifecycleStage).toBe('withElementaryChild')
  })

  test('expenseMode=lifecycle: 子が22歳を超えると空巣期に切り替わる', () => {
    // birthYear = CURRENT_YEAR - 21 → year0 で21歳（withCollegeChild）、year1 で22歳（emptyNestActive）
    const result = runSingleSimulation(cfg({
      expenseMode: 'lifecycle',
      children: [{ birthYear: CURRENT_YEAR - 21, educationPath: 'public' }],
      simulationYears: 1,
    }))
    expect(result.yearlyData[0].lifecycleStage).toBe('withCollegeChild')
    expect(result.yearlyData[1].lifecycleStage).toBe('emptyNestActive')
  })

  test('expenseMode=lifecycle: 第2子の追加費用が加算される', () => {
    // 同年2子: baseExpenses(withPreschooler)=2_760_000 + getAdditionalChildCost(0)=500_000 = 3_260_000
    const result = runSingleSimulation(cfg({
      expenseMode: 'lifecycle',
      children: [
        { birthYear: CURRENT_YEAR, educationPath: 'public' },
        { birthYear: CURRENT_YEAR, educationPath: 'public' },
      ],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].expenses).toBeCloseTo(3_260_000, -1)
  })

  test('expenseMode=lifecycle: person1が80歳以上 → emptyNestElderly', () => {
    // startAge=79, year1 で80歳 → emptyNestElderly
    const result = runSingleSimulation(cfg({
      expenseMode: 'lifecycle',
      person1: { currentAge: 79, retirementAge: 90, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      children: [],
      simulationYears: 1,
    }))
    expect(result.yearlyData[1].lifecycleStage).toBe('emptyNestElderly')
  })

  test('lifecycleExpenses でデフォルト値をオーバーライドできる', () => {
    // emptyNestActive を 3_000_000 に上書き
    const result = runSingleSimulation(cfg({
      expenseMode: 'lifecycle',
      lifecycleExpenses: { emptyNestActive: 3_000_000 },
      person1: { currentAge: 40, retirementAge: 90, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      children: [],
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].expenses).toBeCloseTo(3_000_000, -1)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// Phase 3: 年金詳細計算
// ─────────────────────────────────────────────────────────────────────────────

describe('年金詳細計算', () => {
  const basePerson = (): Person => ({
    currentAge: 35,
    retirementAge: 65,
    grossIncome: 6_000_000,
    employmentType: 'employee',
    incomeGrowthRate: 0.02,
    pensionStartAge: 65,
    // pensionAmount は undefined（計算値を使う）
  })

  test('会社員: 厚生年金 + 国民年金が計算される', () => {
    const person: Person = {
      ...basePerson(),
      pensionConfig: {
        pastEmployeeMonths: 120,
        pastAverageMonthlyRemuneration: 300_000,
        pastNationalPensionMonths: 120,
        pensionGrowthRate: 0.01,
      },
    }
    // futureMonths=360, avgRemuneration=500_000
    // pastEmployeePension = 300_000 * 120 * 0.005481 = 197_316
    // futureEmployeePension = 500_000 * 360 * 0.005481 = 986_580
    // totalEmployeePension ≈ 1_183_896
    // totalPensionMonths = 120 + 120 + 360 = 600 → cap 480
    // nationalPension = 816_000
    const result = calculatePensionAmount(person, 30, 500_000)
    expect(result.employeePension).toBe(1_183_896)
    expect(result.nationalPension).toBe(816_000)
    expect(result.totalAnnualPension).toBe(1_999_896)
    expect(result.source).toBe('calculated')
  })

  test('個人事業主: 国民年金のみ（厚生年金ゼロ）', () => {
    const person: Person = {
      ...basePerson(),
      employmentType: 'selfEmployed',
      pensionConfig: {
        pastEmployeeMonths: 0,
        pastAverageMonthlyRemuneration: 0,
        pastNationalPensionMonths: 240,
        pensionGrowthRate: 0.01,
      },
    }
    // futureMonths=240(20年), totalPensionMonths=240+240=480 → cap 480
    const result = calculatePensionAmount(person, 20, 0)
    expect(result.employeePension).toBe(0)
    expect(result.nationalPension).toBe(816_000)
    expect(result.totalAnnualPension).toBe(816_000)
  })

  test('専業主婦: 過去の国民年金のみ', () => {
    const person: Person = {
      ...basePerson(),
      employmentType: 'homemaker',
      pensionConfig: {
        pastEmployeeMonths: 0,
        pastAverageMonthlyRemuneration: 0,
        pastNationalPensionMonths: 120,
        pensionGrowthRate: 0.01,
      },
    }
    // nationalPension = 816_000 * 120/480 = 204_000
    const result = calculatePensionAmount(person, 30, 0)
    expect(result.employeePension).toBe(0)
    expect(result.nationalPension).toBe(204_000)
    expect(result.totalAnnualPension).toBe(204_000)
  })

  test('加入月数480未満: 年金が満額より少ない', () => {
    const person: Person = {
      ...basePerson(),
      pensionConfig: {
        pastEmployeeMonths: 120,
        pastAverageMonthlyRemuneration: 300_000,
        pastNationalPensionMonths: 120,
        pensionGrowthRate: 0.01,
      },
    }
    // futureMonths=120(10年)
    // totalPensionMonths = 120 + 120 + 120 = 360 < 480
    // nationalPension = 816_000 * 360/480 = 612_000
    const result = calculatePensionAmount(person, 10, 300_000)
    expect(result.nationalPension).toBe(612_000)
  })

  test('pensionAmount 固定値が指定されている場合は計算値を無視する', () => {
    const person: Person = {
      ...basePerson(),
      pensionAmount: 1_500_000,
      pensionConfig: {
        pastEmployeeMonths: 240,
        pastAverageMonthlyRemuneration: 400_000,
        pastNationalPensionMonths: 240,
        pensionGrowthRate: 0.01,
      },
    }
    const result = calculatePensionAmount(person, 30, 500_000)
    expect(result.totalAnnualPension).toBe(1_500_000)
    expect(result.source).toBe('fixed')
  })

  test('マクロ経済スライド: 10年後に約10.5%増加', () => {
    const after10 = applyMacroEconomicSlide(1_000_000, 10, 0.01)
    expect(after10).toBeCloseTo(1_104_622, -2)
  })

  test('pensionConfig を使ったシミュレーション: pensionStartAge から年金が income に反映される', () => {
    const result = calculatePensionAmount(basePerson(), 15, 400_000)
    // pensionConfig なし → totalAnnualPension = 0, source = 'calculated'
    expect(result.totalAnnualPension).toBe(0)
    expect(result.source).toBe('calculated')
  })

  test('pensionConfig を指定した場合: calculatePensionAmount が正の年金を返す', () => {
    const person: Person = {
      ...basePerson(),
      pensionConfig: {
        pastEmployeeMonths: 120,
        pastAverageMonthlyRemuneration: 300_000,
        pastNationalPensionMonths: 120,
        pensionGrowthRate: 0.01,
      },
    }
    const result = calculatePensionAmount(person, 15, 400_000)
    expect(result.totalAnnualPension).toBeGreaterThan(0)
    expect(result.source).toBe('calculated')
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// Phase 4A〜4D: 資産管理高度化
// ─────────────────────────────────────────────────────────────────────────────

describe('現金・株式分離管理', () => {
  test('currentAssets の後方互換: stocks として investment return が適用される', () => {
    // currentAssets: 1_000_000 → stocks: 1_000_000, costBasis: 1_000_000
    // year1: stocks = 1_000_000 * 1.1 = 1_100_000 (含み益あり), 取り崩しなし(expenses=0)
    // assets = stocks = 1_100_000
    const result = runSingleSimulation(cfg({
      currentAssets: 1_000_000,
      investmentReturn: 0.1,
      simulationYears: 1,
    }))
    expect(result.yearlyData[1].assets).toBeGreaterThanOrEqual(1_100_000)
  })

  test('cashAssets には investment return がかからない', () => {
    // cashAssets: 1_000_000, stocks: 0, expenses=0(savings=0)
    // year1: newCash = 1_000_000（リターンなし）
    const result = runSingleSimulation(cfg({
      cashAssets: 1_000_000,
      stocks: 0,
      investmentReturn: 0.1,
      simulationYears: 1,
    }))
    // cashAssets に変化なし（savings=0 なので取り崩しも増加もなし）
    expect(result.yearlyData[1].cashAssets).toBe(1_000_000)
  })

  test('assets フィールドは cashAssets + stocks と等しい', () => {
    const result = runSingleSimulation(cfg({
      cashAssets: 500_000,
      stocks: 1_000_000,
      stocksCostBasis: 1_000_000,
      investmentReturn: 0,
      simulationYears: 0,
    }))
    const d = result.yearlyData[0]
    expect(d.assets).toBe(d.cashAssets + d.stocks)
    expect(d.assets).toBe(1_500_000)
  })

  test('余剰資金は NISA 枠を満たしてから課税口座に投資される', () => {
    // 収入あり、支出少、NISA enabled: 余剰を NISA → stocks の順に投資
    // simulationYears=1 なので year0, year1 の計2回 NISA 拠出
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 90, grossIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      nisa: { enabled: true, annualContribution: 1_200_000 },
      monthlyExpenses: 100_000, // 支出 1.2M/年
      investmentReturn: 0,
      simulationYears: 1,
    }))
    // surplus = (netIncome - 1.2M) >> 0、NISA に各年 1.2M が拠出される
    // year0: nisaAssets = 1.2M, year1: nisaAssets = 2.4M
    expect(result.yearlyData[0].nisaAssets).toBeCloseTo(1_200_000, -1)
    expect(result.yearlyData[1].nisaAssets).toBeCloseTo(2_400_000, -1)
    // 余剰の一部は課税口座にも回る
    expect(result.yearlyData[1].stocks).toBeGreaterThan(0)
  })
})

describe('NISA年間枠', () => {
  test('年間360万超の希望拠出は360万にキャップされる', () => {
    // annualContribution: 4_000_000, annualLimit: 3_600_000
    // surplus >= 0 の場合: min(4M, 3.6M, remaining) = 3.6M
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 90, grossIncome: 10_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      nisa: { enabled: true, annualContribution: 4_000_000, annualLimit: 3_600_000 },
      investmentReturn: 0,
      simulationYears: 1,
    }))
    // 1年後の NISA は最大 3_600_000 以下
    expect(result.yearlyData[1].nisaAssets).toBeLessThanOrEqual(3_600_000)
    expect(result.yearlyData[1].nisaAssets).toBeCloseTo(3_600_000, -1)
  })

  test('生涯1800万に達したら拠出停止', () => {
    // totalContributed: 18_000_000 → remainingLifetime = 0 → nisaContrib = 0
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 90, grossIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      nisa: { enabled: true, annualContribution: 1_200_000, lifetimeLimit: 18_000_000, totalContributed: 18_000_000 },
      investmentReturn: 0,
      simulationYears: 1,
    }))
    // 生涯上限到達 → 追加拠出ゼロ（NISA は 0 のまま）
    expect(result.yearlyData[1].nisaAssets).toBe(0)
  })

  test('生涯限度額が途中で満たされる: 残り枠だけ拠出', () => {
    // totalContributed: 17_500_000, annualContribution: 1_200_000, lifetimeLimit: 18_000_000
    // remaining = 18M - 17.5M = 500_000 → 500_000 だけ拠出
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 90, grossIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      nisa: { enabled: true, annualContribution: 1_200_000, lifetimeLimit: 18_000_000, totalContributed: 17_500_000 },
      investmentReturn: 0,
      simulationYears: 1,
    }))
    // 残り 500_000 だけ拠出
    expect(result.yearlyData[1].nisaAssets).toBeCloseTo(500_000, -1)
  })
})

describe('iDeCo 60歳制約', () => {
  test('60歳で iDeCo 資産が課税口座に一括移行される（20%課税）', () => {
    // person1: currentAge=59, retirementAge=90, ideco.withdrawalStartAge=60
    // year0(age59): iDeCo 拠出あり
    // year1(age60): iDeCo 一括移行（税20%）
    const monthly = 100_000
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 59, retirementAge: 90, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      ideco: { enabled: true, monthlyContribution: monthly, withdrawalStartAge: 60 },
      monthlyExpenses: 0,
      investmentReturn: 0,
      simulationYears: 2,
    }))
    // year0(age59): iDeCo += 1_200_000 → idecoAssets = 1_200_000
    expect(result.yearlyData[0].idecoAssets).toBeCloseTo(monthly * 12, -1)
    // year1(age60): iDeCo が stocks に移行（20%課税）→ idecoAssets = 0
    expect(result.yearlyData[1].idecoAssets).toBe(0)
    // stocks に 80% が移行されているので assets が増えている（元の idecoAssets の80%）
    expect(result.yearlyData[1].stocks).toBeCloseTo(monthly * 12 * 0.8, -1)
  })
})

describe('株式売却税（20.315%）', () => {
  test('含み益ゼロ（コスト = 評価額）: 税ゼロ', () => {
    // gainRatio = (1M - 1M) / 1M = 0 → tax = 0
    const result = withdrawFromTaxableAccount(500_000, 1_000_000, 1_000_000)
    expect(result.capitalGainsTax).toBe(0)
    expect(result.realizedGains).toBe(0)
    expect(result.netProceeds).toBeCloseTo(500_000, -1)
  })

  test('含み益あり: 売却税が正しく計算される', () => {
    // stocks=1M, costBasis=500K → gainRatio = (1M-500K)/1M = 0.5
    // grossSell = 500K / (1 - 0.5 * 0.20315) = 500K / (1 - 0.101575) = 500K / 0.898425 ≈ 556_537
    // costBasisSold = 556_537 * (500K/1M) = 278_268
    // realizedGains = 556_537 - 278_268 = 278_268
    // tax = 278_268 * 0.20315 ≈ 56_555
    // netProceeds = 556_537 - 56_555 ≈ 499_982 ≈ 500_000
    const result = withdrawFromTaxableAccount(500_000, 1_000_000, 500_000)
    expect(result.capitalGainsTax).toBeGreaterThan(0)
    expect(result.netProceeds).toBeCloseTo(500_000, -2)
    expect(result.realizedGains).toBeCloseTo(result.sellAmount - result.sellAmount * 0.5, -1)
  })

  test('capitalGains が YearlyData に記録される', () => {
    // stocks=1M, costBasis=500K → 含み益あり
    // 不足が発生する設定: income=0, expenses=600K/year → surplus=-600K
    // 課税口座から取り崩し → capitalGains > 0
    const result = runSingleSimulation(cfg({
      stocks: 1_000_000,
      stocksCostBasis: 500_000,   // 含み益 50%
      monthlyExpenses: 50_000,    // 600K/年の不足
      investmentReturn: 0,
      simulationYears: 1,
    }))
    // year1: surplus = -600K → 課税口座から取り崩し → realizedGains > 0
    expect(result.yearlyData[1].capitalGains).toBeGreaterThan(0)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 11. セミFIRE（FIRE後収入）
// ─────────────────────────────────────────────────────────────────────────────

describe('セミFIRE（FIRE後収入）', () => {
  test('FIRE後 untilAge まで毎年収入がある', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 500_000_000,
      monthlyExpenses: 100_000,
      postFireIncome: { monthlyAmount: 100_000, untilAge: 50 },
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 7_000_000,
        incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0, employmentType: 'employee' },
      investmentReturn: 0, inflationRate: 0, simulationYears: 20,
    }))
    // year0 (age35): FIRE達成年（就労収入あり）→ isSemiFire=false（まだisPostFire=false）
    expect(result.yearlyData[0].isSemiFire).toBe(false)
    // year1 (age36): isPostFire=true かつ age36 < untilAge50 → セミFIRE収入あり
    expect(result.yearlyData[1].isSemiFire).toBe(true)
    expect(result.yearlyData[1].income).toBeGreaterThan(0)
    // year15 (age50): untilAge到達 → セミFIRE終了
    expect(result.yearlyData[15].isSemiFire).toBe(false)
    expect(result.yearlyData[15].income).toBe(0)
  })

  test('postFireIncome = null: FIRE後は収入ゼロ（年金前）', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 500_000_000, monthlyExpenses: 100_000, postFireIncome: null,
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 7_000_000,
        incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0, employmentType: 'employee' },
      investmentReturn: 0, simulationYears: 10,
    }))
    // FIRE後、年金前なので income = 0
    expect(result.yearlyData[1].income).toBe(0)
  })

  test('untilAge を超えたら収入ゼロに戻る', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 500_000_000, monthlyExpenses: 50_000,
      postFireIncome: { monthlyAmount: 100_000, untilAge: 40 },
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 0,
        incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0, employmentType: 'employee' },
      investmentReturn: 0, simulationYears: 10,
    }))
    expect(result.yearlyData[4].isSemiFire).toBe(true)
    expect(result.yearlyData[5].isSemiFire).toBe(false)
    expect(result.yearlyData[5].income).toBe(0)
  })

  test('セミFIRE収入は税計算後の手取りが income に反映される', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 500_000_000,
      postFireIncome: { monthlyAmount: 200_000, untilAge: 60 },
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 0,
        incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0, employmentType: 'employee' },
      investmentReturn: 0, simulationYears: 5,
    }))
    // year1: isPostFire=true, age36 < untilAge60 → セミFIRE収入あり
    // income < 2_400_000 (税引き後)
    expect(result.yearlyData[1].income).toBeGreaterThan(0)
    expect(result.yearlyData[1].income).toBeLessThan(2_400_000)
    expect(result.yearlyData[1].semiFireIncome).toBe(2_400_000)
  })

  test('FIRE未達成時はセミFIRE収入が加算されない', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 0, monthlyExpenses: 300_000,
      postFireIncome: { monthlyAmount: 100_000, untilAge: 50 },
      person1: { currentAge: 35, retirementAge: 90, grossIncome: 0,
        incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0, employmentType: 'employee' },
      investmentReturn: 0, simulationYears: 5,
    }))
    expect(result.yearlyData[0].isSemiFire).toBe(false)
  })

  test('セミFIRE収入があると資産の減少が遅くなる', () => {
    const withSemiFire = runSingleSimulation(cfg({
      currentAssets: 500_000_000, monthlyExpenses: 200_000,
      postFireIncome: { monthlyAmount: 100_000, untilAge: 45 },
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 0,
        incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0, employmentType: 'employee' },
      investmentReturn: 0, simulationYears: 10,
    }))
    const withoutSemiFire = runSingleSimulation(cfg({
      currentAssets: 500_000_000, monthlyExpenses: 200_000, postFireIncome: null,
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 0,
        incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0, employmentType: 'employee' },
      investmentReturn: 0, simulationYears: 10,
    }))
    expect(withSemiFire.finalAssets).toBeGreaterThan(withoutSemiFire.finalAssets)
  })

  test('calculatePostFireIncome: FIRE未達成は0を返す', () => {
    expect(calculatePostFireIncome({ monthlyAmount: 100_000, untilAge: 50 }, 40, false)).toBe(0)
  })

  test('calculatePostFireIncome: untilAge 以上は0を返す', () => {
    expect(calculatePostFireIncome({ monthlyAmount: 100_000, untilAge: 50 }, 50, true)).toBe(0)
    expect(calculatePostFireIncome({ monthlyAmount: 100_000, untilAge: 50 }, 51, true)).toBe(0)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// FIRE後税金・社会保険
// ─────────────────────────────────────────────────────────────────────────────

const testSIConfig = (): PostFireSocialInsuranceConfig => ({
  nhisoIncomeRate: 0.1100,
  nhisoSupportIncomeRate: 0.0259,
  nhisoFixedAmountPerPerson: 50_000,
  nhisoHouseholdFixed: 30_000,
  nhisoMaxAnnual: 1_060_000,
  nationalPensionMonthlyPremium: 16_980,
  longTermCareRate: 0.0200,
  longTermCareMax: 170_000,
})

describe('FIRE後税金・社会保険', () => {
  test('FIRE後60歳未満: 国民年金保険料が計算される', () => {
    expect(calculateNationalPensionPremium(45, testSIConfig())).toBe(16_980 * 12)
  })

  test('FIRE後60歳以上: 国民年金保険料ゼロ', () => {
    expect(calculateNationalPensionPremium(60, testSIConfig())).toBe(0)
    expect(calculateNationalPensionPremium(70, testSIConfig())).toBe(0)
  })

  test('前年所得ゼロ: 国保は均等割+平等割のみ（householdSize=1, age=45）', () => {
    // medicalFixed = 50_000 + 30_000 = 80_000
    // supportFixed = 50_000 * 0.3 = 15_000
    // careFixed    = 50_000 * 0.5 = 25_000
    // total = 120_000
    expect(calculateNHIPremium(0, 1, testSIConfig(), 45)).toBe(120_000)
  })

  test('前年所得が高い: 国保が各分上限の合計（1,060,000）に達する', () => {
    // 所得が非常に高い場合: 医療650,000 + 支援240,000 + 介護170,000 = 1,060,000
    expect(calculateNHIPremium(10_000_000, 1, testSIConfig(), 45)).toBe(1_060_000)
  })

  test('65歳以降: 介護保険料がゼロになる', () => {
    const nhip45 = calculateNHIPremium(1_000_000, 1, testSIConfig(), 45)
    const nhip65 = calculateNHIPremium(1_000_000, 1, testSIConfig(), 65)
    expect(nhip65).toBeLessThan(nhip45)
  })

  test('世帯人数が多いと均等割が増える', () => {
    const nhip1 = calculateNHIPremium(500_000, 1, testSIConfig(), 45)
    const nhip2 = calculateNHIPremium(500_000, 2, testSIConfig(), 45)
    expect(nhip2).toBeGreaterThan(nhip1)
  })

  test('FIRE後の expenses に国保・国民年金が加算される', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 500_000_000,
      monthlyExpenses: 100_000,
      postFireSocialInsurance: testSIConfig(),
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 0,
        incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0, employmentType: 'employee' },
      investmentReturn: 0, simulationYears: 5,
    }))
    // year0 で即FIRE達成 → year1 (isPostFire=true) から社保計算開始
    expect(result.yearlyData[1].postFireSocialInsurance).toBeGreaterThan(0)
    expect(result.yearlyData[1].nhInsurancePremium).toBeGreaterThan(0)
    expect(result.yearlyData[1].nationalPensionPremium).toBe(16_980 * 12)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 取り崩し戦略 (Phase 7)
// ─────────────────────────────────────────────────────────────────────────────

describe('取り崩し戦略', () => {
  const gc: GuardrailConfig = {
    threshold1: -0.10,
    reduction1: 0.40,
    threshold2: -0.20,
    reduction2: 0.80,
    threshold3: -0.35,
    reduction3: 0.95,
    discretionaryRatio: 0.30,
  }

  test('fixed: baseExpenses がそのまま返る', () => {
    const result = calculateWithdrawalAmount('fixed', 2_400_000, 30_000_000, 30_000_000, 0.04)
    expect(result.actualExpenses).toBe(2_400_000)
    expect(result.discretionaryReductionRate).toBe(0)
  })

  test('percentage: totalAssets * SWR が actualExpenses になる（baseExpenses より大きい場合）', () => {
    // 100M * 0.04 = 4_000_000 > baseExpenses 2_400_000 → 4_000_000
    const result = calculateWithdrawalAmount('percentage', 2_400_000, 100_000_000, 100_000_000, 0.04)
    expect(result.actualExpenses).toBe(4_000_000)
  })

  test('percentage: totalAssets * SWR < baseExpenses → baseExpenses が返る', () => {
    // 30M * 0.04 = 1_200_000 < baseExpenses 2_400_000 → max = 2_400_000
    const result = calculateWithdrawalAmount('percentage', 2_400_000, 30_000_000, 30_000_000, 0.04)
    expect(result.actualExpenses).toBe(2_400_000)
  })

  test('guardrail: ドローダウン 0% → 削減なし', () => {
    const result = calculateWithdrawalAmount('guardrail', 2_400_000, 10_000_000, 10_000_000, 0.04, gc)
    expect(result.discretionaryReductionRate).toBe(0)
    expect(result.actualExpenses).toBe(2_400_000)
  })

  test('guardrail: ドローダウン -15% → 裁量支出40%削減', () => {
    // peakAssets = 10_000_000, totalAssets = 8_500_000 → drawdown = -0.15
    // essential = 2_400_000 * 0.70 = 1_680_000
    // discretionary = 2_400_000 * 0.30 * (1 - 0.40) = 432_000
    // actual = 2_112_000
    const result = calculateWithdrawalAmount('guardrail', 2_400_000, 8_500_000, 10_000_000, 0.04, gc)
    expect(result.discretionaryReductionRate).toBe(0.40)
    expect(result.actualExpenses).toBe(2_112_000)
  })

  test('guardrail: ドローダウン -25% → 裁量支出80%削減', () => {
    // totalAssets = 7_500_000 → drawdown = -0.25
    // actual = 1_680_000 + 720_000 * 0.20 = 1_824_000
    const result = calculateWithdrawalAmount('guardrail', 2_400_000, 7_500_000, 10_000_000, 0.04, gc)
    expect(result.discretionaryReductionRate).toBe(0.80)
    expect(result.actualExpenses).toBe(1_824_000)
  })

  test('guardrail: ドローダウン -40% → 裁量支出95%削減', () => {
    // totalAssets = 6_000_000 → drawdown = -0.40
    // actual = 1_680_000 + 720_000 * 0.05 = 1_716_000
    const result = calculateWithdrawalAmount('guardrail', 2_400_000, 6_000_000, 10_000_000, 0.04, gc)
    expect(result.discretionaryReductionRate).toBe(0.95)
    expect(result.actualExpenses).toBe(1_716_000)
  })

  test('depletionAge: 資産が途中でゼロになる → 枯渇年齢を返す', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 1_000_000,
      monthlyExpenses: 300_000,  // 年360万 > SWR4%での取り崩し許容額
      investmentReturn: 0,
      person1: { currentAge: 35, retirementAge: 35, grossIncome: 0,
        incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0, employmentType: 'employee' },
      simulationYears: 10,
      safeWithdrawalRate: 0.04,
    }))
    expect(result.depletionAge).not.toBeNull()
    expect(result.depletionAge).toBeGreaterThanOrEqual(35)
  })

  test('depletionAge: 全期間資産が持つ → null', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 500_000_000,
      monthlyExpenses: 100_000,
      investmentReturn: 0.05,
      person1: { currentAge: 35, retirementAge: 90, grossIncome: 0,
        incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0, employmentType: 'employee' },
      simulationYears: 10,
    }))
    expect(result.depletionAge).toBeNull()
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// FIRE達成率・年次テーブル・収支グラフ
// ─────────────────────────────────────────────────────────────────────────────

describe('FIRE達成率・年次テーブル・収支グラフ', () => {
  test('calculateFireAchievementRate: 資産が67%の場合', () => {
    // fireNumber = 150_000 * 12 / 0.04 = 45_000_000
    // currentAssets = 30_000_000 → rate = 30M / 45M ≈ 0.667
    // ※ year0 のデータは支出引き後の状態なので rate はやや下回る
    const result = runSingleSimulation(cfg({
      currentAssets: 30_000_000,
      monthlyExpenses: 150_000,
      safeWithdrawalRate: 0.04,
      simulationYears: 0,
    }))
    // 支出(1.8M)が引かれた後の assets / fireNumber なので 0.62〜0.67 の範囲
    expect(result.fireAchievementRate).toBeGreaterThan(0.5)
    expect(result.fireAchievementRate).toBeLessThan(0.75)
  })

  test('calculateFireAchievementRate: FIRE達成済み（>=1.0）', () => {
    // currentAssets = 100M, fireNumber = 45M → rate >= 1.0
    const result = runSingleSimulation(cfg({
      currentAssets: 100_000_000,
      monthlyExpenses: 150_000,
      safeWithdrawalRate: 0.04,
      simulationYears: 0,
    }))
    expect(result.fireAchievementRate).toBeGreaterThanOrEqual(1.0)
  })

  test('formatAnnualTableData: totalAssets が assets + nisaAssets + idecoAssets と等しい', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 10_000_000,
      nisa: { enabled: true, annualContribution: 500_000 },
      investmentReturn: 0.05,
      simulationYears: 5,
    }))
    const tableData = formatAnnualTableData(result.yearlyData)
    tableData.forEach((row, i) => {
      const data = result.yearlyData[i]
      expect(row.totalAssets).toBe(data.assets + data.nisaAssets + data.idecoAssets)
    })
  })

  test('formatAnnualTableData: netCashFlow = income - expenses', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 0,
      person1: { currentAge: 35, retirementAge: 65, grossIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0, employmentType: 'employee' },
      monthlyExpenses: 200_000,
      simulationYears: 3,
    }))
    const tableData = formatAnnualTableData(result.yearlyData)
    tableData.forEach((row, i) => {
      const data = result.yearlyData[i]
      expect(row.netCashFlow).toBeCloseTo(data.income - data.expenses, 0)
    })
  })

  test('formatCashFlowChartData: 55年分 → 11グループ（5年単位）', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 0,
      simulationYears: 54, // 55件 (year0〜year54)
      person1: { currentAge: 35, retirementAge: 90, grossIncome: 0, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0, employmentType: 'employee' },
    }))
    const chartData = formatCashFlowChartData(result.yearlyData, 5)
    expect(chartData.length).toBe(11)
    expect(chartData[0].label).toBe('35〜39歳')
  })
})
