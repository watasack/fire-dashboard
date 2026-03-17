/**
 * FIRE Simulator — 計算整合性テスト
 *
 * 方針: カバレッジ目的ではなく「計算結果が数学的に正しいか」を検証する。
 * - 各パターンについて手計算した期待値をコードで明示し、シミュレーター出力と照合する
 * - 90歳時点（simulationYears=55, currentAge=35 の場合）の最終資産を中心に検証
 * - 各テストは独立して実行できるよう最小限の設定を注入する
 */

import { describe, test, expect } from 'vitest'
import { runSingleSimulation, SimulationConfig } from '../lib/simulator'

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
    currentAssets: 0,
    monthlyExpenses: 0,
    expenseGrowthRate: 0,
    investmentReturn: 0,
    investmentVolatility: 0.15,
    safeWithdrawalRate: 0.04,
    person1: {
      currentAge: 35,
      retirementAge: 90,
      currentIncome: 0,
      incomeGrowthRate: 0,
      pensionStartAge: 90,
      pensionAmount: 0,
    },
    person2: null,
    nisa: { enabled: false, annualContribution: 0 },
    ideco: { enabled: false, monthlyContribution: 0 },
    children: [],
    simulationYears: 1,
    inflationRate: 0,
  }
  // person1/person2/nisa/ideco はネストしているので個別マージ
  const { person1, person2, nisa, ideco, ...rest } = overrides
  return {
    ...base,
    ...rest,
    person1: person1 ? { ...base.person1, ...person1 } : base.person1,
    person2: person2 !== undefined ? person2 : base.person2,
    nisa: nisa ? { ...base.nisa, ...nisa } : base.nisa,
    ideco: ideco ? { ...base.ideco, ...ideco } : base.ideco,
  }
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
      person1: { currentAge: 35, retirementAge: 65, currentIncome: 5_000_000, incomeGrowthRate: 0.02, pensionStartAge: 65, pensionAmount: 0 },
      monthlyExpenses: 500_000, // fireNumber = 150M → テスト期間中に FIRE しない
      simulationYears: 4,
    }))
    expect(result.yearlyData[4].income).toBeGreaterThan(result.yearlyData[0].income)
  })

  test('就労フェーズ year0: 税引き後収入が手計算と一致する', () => {
    // gross = 5,000,000
    // 社会保険料 = 750,000 (15%)
    // 課税所得 = 4,520,000
    // 所得税 = 232,500 + (4,520,000 - 3,300,000) * 0.20 = 476,500
    // 住民税 = 452,000
    // 合計税 = 1,678,500
    // 手取り = 3,321,500
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 65, currentIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 0 },
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].income).toBeCloseTo(3_321_500, -1)
  })

  test('退職ギャップ: retirementAge <= age < pensionStartAge は収入 0', () => {
    // currentAge=60, retirementAge=60, pensionStartAge=65
    // year0(age60)〜year4(age64): 退職ギャップ → 収入ゼロ
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 60, retirementAge: 60, currentIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 1_200_000 },
      simulationYears: 5,
    }))
    expect(result.yearlyData[0].income).toBe(0)
    expect(result.yearlyData[4].income).toBe(0)
  })

  test('年金フェーズ: pensionStartAge に達したら年金収入が始まる', () => {
    // currentAge=60, retirementAge=60, pensionStartAge=65
    // year5(age65): 年金開始 → 収入 > 0
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 60, retirementAge: 60, currentIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 1_200_000 },
      simulationYears: 5,
    }))
    expect(result.yearlyData[5].income).toBeGreaterThan(0)
  })

  test('年金フェーズ year0: inflationRate でインフレ調整される', () => {
    // currentAge=65, pensionStartAge=65, pension=1,200,000, inflation=0
    // gross = 1,200,000, 社会保険=180,000, 課税所得=720,000
    // 所得税 = 720,000*0.05=36,000, 住民税=72,000 → 税288,000
    // 手取り = 912,000
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 65, retirementAge: 65, currentIncome: 0, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 1_200_000 },
      inflationRate: 0,
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].income).toBeCloseTo(912_000, -1)
  })

  test('年金: inflationRate > 0 のとき経年で収入が増える', () => {
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 65, retirementAge: 65, currentIncome: 0, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 1_200_000 },
      inflationRate: 0.02,
      simulationYears: 10,
    }))
    // 年金額 = 1,200,000 * 1.02^year → 増加する
    expect(result.yearlyData[10].income).toBeGreaterThan(result.yearlyData[0].income)
  })

  test('配偶者あり: 収入が2人分合算される', () => {
    const noSpouse = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 90, currentIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      simulationYears: 0,
    }))
    const withSpouse = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 90, currentIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      person2: { currentAge: 33, retirementAge: 90, currentIncome: 3_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      simulationYears: 0,
    }))
    expect(withSpouse.yearlyData[0].income).toBeGreaterThan(noSpouse.yearlyData[0].income)
  })

  test('person2=null: 配偶者なしで収入は person1 のみ', () => {
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 90, currentIncome: 5_000_000, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      person2: null,
      simulationYears: 0,
    }))
    // person2 がいる場合より少ない（= person1 税引き後のみ）
    expect(result.yearlyData[0].income).toBeCloseTo(3_321_500, -1)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 2. 税計算（各ブラケット）
// ─────────────────────────────────────────────────────────────────────────────

describe('税計算ブラケット', () => {
  /** 年収 annualIncome に対する手取りを返す */
  function netAt(annualIncome: number): number {
    return runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 90, currentIncome: annualIncome, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
      simulationYears: 0,
    })).yearlyData[0].income
  }

  test('収入ゼロ → 税ゼロ、手取りゼロ', () => {
    expect(netAt(0)).toBe(0)
  })

  test('5% ブラケット (課税所得 ≤ 1,950,000): 年収 2,000,000', () => {
    // 社会保険 = 300,000 / 課税所得 = 1,520,000
    // 所得税 = 1,520,000 * 0.05 = 76,000 / 住民税 = 152,000
    // 税計 = 528,000 / 手取り = 1,472,000
    expect(netAt(2_000_000)).toBeCloseTo(1_472_000, -1)
  })

  test('10% ブラケット (1,950,000 < 課税所得 ≤ 3,300,000): 年収 3,000,000', () => {
    // 社会保険 = 450,000 / 課税所得 = 2,520,000
    // 所得税 = 97,500 + (2,520,000 - 1,950,000) * 0.10 = 154,500 / 住民税 = 252,000
    // 税計 = 856,500 / 手取り = 2,143,500
    expect(netAt(3_000_000)).toBeCloseTo(2_143_500, -1)
  })

  test('20% ブラケット (3,300,000 < 課税所得 ≤ 6,950,000): 年収 7,000,000', () => {
    // 社会保険 = 1,050,000 / 課税所得 = 6,520,000
    // 所得税 = 232,500 + (6,520,000 - 3,300,000) * 0.20 = 876,500 / 住民税 = 652,000
    // 税計 = 2,578,500 / 手取り = 4,421,500
    expect(netAt(7_000_000)).toBeCloseTo(4_421_500, -1)
  })

  test('23% ブラケット (6,950,000 < 課税所得 ≤ 9,000,000): 年収 9,000,000', () => {
    // 社会保険 = 1,350,000 / 課税所得 = 8,520,000
    // 所得税 = 962,500 + (8,520,000 - 6,950,000) * 0.23 = 1,323,600 / 住民税 = 852,000
    // 税計 = 3,525,600 / 手取り = 5,474,400
    expect(netAt(9_000_000)).toBeCloseTo(5_474_400, -1)
  })

  test('33% ブラケット (9,000,000 < 課税所得 ≤ 18,000,000): 年収 12,000,000', () => {
    // 社会保険 = 1,800,000 / 課税所得 = 11,520,000
    // 所得税 = 1,434,000 + (11,520,000 - 9,000,000) * 0.33 = 2,265,600 / 住民税 = 1,152,000
    // 税計 = 5,217,600 / 手取り = 6,782,400
    expect(netAt(12_000_000)).toBeCloseTo(6_782_400, -1)
  })

  test('40% ブラケット (課税所得 > 18,000,000): 年収 20,000,000', () => {
    // 社会保険 = 3,000,000 / 課税所得 = 19,520,000
    // 所得税 = 4,404,000 + (19,520,000 - 18,000,000) * 0.40 = 5,012,000 / 住民税 = 1,952,000
    // 税計 = 9,964,000 / 手取り = 10,036,000
    expect(netAt(20_000_000)).toBeCloseTo(10_036_000, -1)
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
      person1: { currentAge: 35, retirementAge: 65, currentIncome: 0, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 0 },
      nisa: { enabled: true, annualContribution: 1_200_000 },
      monthlyExpenses: 500_000,
      simulationYears: 9,
    }))
    expect(result.yearlyData[9].nisaAssets).toBeCloseTo(10 * 1_200_000, -1)
  })

  test('退職年 (age=retirementAge) から拠出停止: 残高は伸びない(リターン0)', () => {
    // retirementAge=37 → year0(age35),year1(age36)まで拠出、year2(age37)から停止
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 37, currentIncome: 0, incomeGrowthRate: 0, pensionStartAge: 37, pensionAmount: 0 },
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
      person1: { currentAge: 35, retirementAge: 37, currentIncome: 0, incomeGrowthRate: 0, pensionStartAge: 37, pensionAmount: 0 },
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
      person1: { currentAge: 35, retirementAge: 65, currentIncome: 0, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 0 },
      ideco: { enabled: true, monthlyContribution: monthly },
      simulationYears: 0,
    }))
    expect(result.yearlyData[0].idecoAssets).toBeCloseTo(monthly * 12, -1)
  })

  test('3年拠出(リターン 0): 3回分の年間拠出が累積する', () => {
    const monthly = 23_000
    const annual = monthly * 12 // 276,000
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 65, currentIncome: 0, incomeGrowthRate: 0, pensionStartAge: 65, pensionAmount: 0 },
      ideco: { enabled: true, monthlyContribution: monthly },
      monthlyExpenses: 500_000, // FIRE しないようにする
      simulationYears: 2, // year0,1,2 → 3 回
    }))
    expect(result.yearlyData[2].idecoAssets).toBeCloseTo(3 * annual, -1)
  })

  test('退職後は拠出停止: 残高が増えなくなる(リターン 0)', () => {
    const monthly = 23_000
    const result = runSingleSimulation(cfg({
      person1: { currentAge: 35, retirementAge: 37, currentIncome: 0, incomeGrowthRate: 0, pensionStartAge: 37, pensionAmount: 0 },
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
   * リターン 0 で手計算可能:
   *   就労貯蓄: 3,321,500 - 2,400,000 = 921,500 × 30年
   *   年金貯蓄: 912,000 - 2,400,000 = -1,488,000 × 26年
   *   最終: 20,000,000 + 30*921,500 + 26*(-1,488,000) = 8,957,000
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
        currentIncome: 5_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 65,
        pensionAmount: 1_200_000,
      },
      simulationYears: 55,
    }))

    // 手計算:
    // 就労: net=3,321,500, savings=921,500, 30年 (year 0..29, age 35..64)
    // 年金: net=912,000, savings=-1,488,000, 26年 (year 30..55, age 65..90)
    const workSavings = 3_321_500 - 2_400_000   // 921,500
    const pensionSavings = 912_000 - 2_400_000  // -1,488,000
    const afterWork = 20_000_000 + 30 * workSavings
    const expected = afterWork + 26 * pensionSavings

    expect(result.finalAssets).toBeCloseTo(expected, -1) // 10円以内
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
        currentIncome: 0,
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
   * 手計算:
   *   year31: gross=1.2M → tax(1.2M)=288K → net=912K
   *   year32: gross=2.0M → tax(2.0M)=528K → net=1,472K
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
        currentIncome: 5_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 65,
        pensionAmount: 1_200_000,
      },
      person2: {
        currentAge: 33,
        retirementAge: 60,   // 60歳退職 → ギャップ 60〜64
        currentIncome: 3_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 65,
        pensionAmount: 800_000,
      },
      simulationYears: 55,
    }))

    // year31: p1=age66(年金), p2=age64(ギャップ) → gross=1.2M → net=912,000
    expect(result.yearlyData[31].income).toBeCloseTo(912_000, -1)
    // year32: p1=age67(年金), p2=age65(年金開始) → gross=2.0M → net=1,472,000
    expect(result.yearlyData[32].income).toBeCloseTo(1_472_000, -1)
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
        currentIncome: 8_000_000,
        incomeGrowthRate: 0.02,
        pensionStartAge: 65,
        pensionAmount: 1_500_000,
      },
      person2: {
        currentAge: 33,
        retirementAge: 60,
        currentIncome: 5_000_000,
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
      person1: { currentAge: 40, retirementAge: 90, currentIncome: 0, incomeGrowthRate: 0, pensionStartAge: 90, pensionAmount: 0 },
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
   *   year0: isPostFire=false → 就労収入あり (netIncome ≈ 4,421,500)
   *   year1: isPostFire=true  → 就労収入ゼロ (age36 < pensionStartAge 65)
   *   year30 (age65): pension 開始 → 収入 = 年金手取り (912,000)
   */
  test('FIRE 翌年から就労収入ゼロ・年金年齢で年金開始', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 500_000_000, // year0 で即 FIRE (500M >> 30M)
      monthlyExpenses: 100_000,   // fireNumber = 30M
      person1: {
        currentAge: 35,
        retirementAge: 65,
        currentIncome: 7_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 65,
        pensionAmount: 1_200_000,
      },
      investmentReturn: 0,
      inflationRate: 0,
      simulationYears: 55,
    }))

    // year0: FIRE未設定 → 就労収入あり
    expect(result.yearlyData[0].income).toBeCloseTo(4_421_500, -1)
    // year1: FIRE済 → 就労収入ゼロ（年金未満の年齢）
    expect(result.yearlyData[1].income).toBe(0)
    // year20 (age55): まだ年金年齢未満 → ゼロのまま
    expect(result.yearlyData[20].income).toBe(0)
    // year30 (age65): 年金開始 → 手取り = 912,000
    expect(result.yearlyData[30].income).toBeCloseTo(912_000, -1)
  })

  /**
   * FIRE 達成後に資産が取り崩しで減少することを確認する。
   *
   * 設定:
   *   currentAssets = 500M, investmentReturn = 0, income = 7M
   *   FIRE at year0 → 翌年から収入ゼロ
   *
   * year0: savings = 4,421,500 - 1,200,000 = +3,221,500 → 503.2M (就労収入あり)
   * year1〜: savings = 0 - 1,200,000 = -1,200,000 → 毎年 1.2M 減少
   */
  test('FIRE 後は資産が毎年 (expenses - pension) ずつ減少する', () => {
    const result = runSingleSimulation(cfg({
      currentAssets: 500_000_000,
      monthlyExpenses: 100_000, // 1.2M/year
      person1: {
        currentAge: 35,
        retirementAge: 65,
        currentIncome: 7_000_000,
        incomeGrowthRate: 0,
        pensionStartAge: 90, // 年金なし（テスト期間中）
        pensionAmount: 0,
      },
      investmentReturn: 0,
      inflationRate: 0,
      simulationYears: 10,
    }))

    // year0 後の資産 (就労収入あり): 500M + (4,421,500 - 1,200,000) = 503,221,500
    expect(result.yearlyData[0].assets).toBeCloseTo(503_221_500, -1)
    // year1〜: 毎年 1.2M 減少
    expect(result.yearlyData[1].assets).toBeCloseTo(503_221_500 - 1_200_000, -1)
    expect(result.yearlyData[2].assets).toBeCloseTo(503_221_500 - 2 * 1_200_000, -1)
    expect(result.yearlyData[10].assets).toBeCloseTo(503_221_500 - 10 * 1_200_000, -1)
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
        currentIncome: 0,
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
        currentIncome: 7_000_000,
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
