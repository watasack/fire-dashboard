// ============================================================================
// FIRE Simulator - TypeScript Implementation
// ============================================================================

// ----------------------------------------------------------------------------
// Types
// ----------------------------------------------------------------------------

export type EmploymentType = 'employee' | 'selfEmployed' | 'homemaker'

export type WithdrawalStrategy = 'fixed' | 'percentage' | 'guardrail'

export interface GuardrailConfig {
    threshold1: number       // デフォルト: -0.10
    reduction1: number       // デフォルト: 0.40
    threshold2: number       // デフォルト: -0.20
    reduction2: number       // デフォルト: 0.80
    threshold3: number       // デフォルト: -0.35
    reduction3: number       // デフォルト: 0.95
    discretionaryRatio: number  // デフォルト: 0.30
}

export interface PensionConfig {
    pastEmployeeMonths: number
    pastAverageMonthlyRemuneration: number
    pastNationalPensionMonths: number
    pensionGrowthRate: number
}

export interface PensionBreakdown {
    employeePension: number
    nationalPension: number
    totalAnnualPension: number
    source: 'calculated' | 'fixed'
}

export interface Person {
    currentAge: number
    retirementAge: number
    grossIncome: number          // 税引き前年収（円）
    incomeGrowthRate: number
    pensionStartAge: number
    pensionAmount?: number
    pensionConfig?: PensionConfig
    employmentType?: EmploymentType  // 雇用形態（省略時は 'employee'）
    /** @deprecated grossIncome を使うこと */
    currentIncome?: number
    maternityLeaveChildBirthYears?: number[]  // 産休・育休を取る子の出生年（年単位近似）
    partTimeUntilAge?: number | null          // 時短勤務終了年齢（この年齢になるまで時短）
    partTimeIncomeRatio?: number              // 時短中の収入比率（例: 0.7 = フル収入の70%）
}

export interface Child {
    birthYear: number
    birthDate?: string          // 追加: 'YYYY-MM-DD' 形式（optional）
    educationPath: "public" | "private" | "mixed"
}

export interface MortgageConfig {
    monthlyPayment: number   // 月次返済額（元利合計・円）
    endYear: number          // 完済年（西暦）
}

export interface NISAConfig {
    enabled: boolean
    annualContribution: number
    annualLimit?: number          // 年間上限（デフォルト: 3_600_000）
    lifetimeLimit?: number        // 生涯限度額（デフォルト: 18_000_000）
    totalContributed?: number     // シミュレーション開始時の累積拠出額（デフォルト: 0）
}

export interface IDeCoConfig {
    enabled: boolean
    monthlyContribution: number
    withdrawalStartAge?: number  // 受取開始年齢（デフォルト: 60）
}

export interface LifecycleExpenseConfig {
    withPreschooler?: number        // 0〜5歳: デフォルト 2,760,000
    withElementaryChild?: number    // 6〜11歳: デフォルト 3,232,000
    withJuniorHighChild?: number    // 12〜14歳: デフォルト 3,468,000
    withHighSchoolChild?: number    // 15〜17歳: デフォルト 3,830,000
    withCollegeChild?: number       // 18〜21歳: デフォルト 3,957,000
    emptyNestActive?: number        // 子なし〜69歳: デフォルト 2,581,000
    emptyNestSenior?: number        // 70〜79歳: デフォルト 2,243,000
    emptyNestElderly?: number       // 80歳〜: デフォルト 1,931,000
}

export interface PostFireIncomeConfig {
    monthlyAmount: number    // 月次収入（円）
    untilAge: number         // セミFIRE終了年齢（この年齢になったら収入ゼロ）
}

export interface PostFireSocialInsuranceConfig {
    nhisoIncomeRate: number        // 医療分所得割率（デフォルト: 0.1100）
    nhisoSupportIncomeRate: number // 後期高齢者支援金分所得割率（デフォルト: 0.0259）
    nhisoFixedAmountPerPerson: number  // 均等割/人（デフォルト: 50_000）
    nhisoHouseholdFixed: number    // 平等割（デフォルト: 30_000）
    nhisoMaxAnnual: number         // 参考値（デフォルト: 1_060_000）
    nationalPensionMonthlyPremium: number  // 国民年金月額（デフォルト: 16_980）
    longTermCareRate: number       // 介護分所得割（デフォルト: 0.0200）
    longTermCareMax: number        // 介護分上限（デフォルト: 170_000）
}

export interface SimulationConfig {
    // Basic settings
    /** @deprecated cashAssets / stocks を使うこと（後方互換のみ） */
    currentAssets?: number
    cashAssets?: number             // 現金・普通預金（投資リターンなし）
    stocks?: number                 // 課税口座の株式評価額
    stocksCostBasis?: number        // 課税口座取得原価（税計算用）
    monthlyExpenses: number
    expenseGrowthRate: number

    // Investment settings
    investmentReturn: number
    investmentVolatility: number
    safeWithdrawalRate: number

    // People
    person1: Person
    person2: Person | null

    // Tax-advantaged accounts
    nisa: NISAConfig
    ideco: IDeCoConfig

    // Life events
    children: Child[]
    mortgage: MortgageConfig | null
    childAllowanceEnabled: boolean

    // Simulation settings
    simulationYears: number
    inflationRate: number

    // Lifecycle expense mode
    expenseMode: 'fixed' | 'lifecycle'
    lifecycleExpenses?: LifecycleExpenseConfig

    // Semi-FIRE / Post-FIRE income
    postFireIncome?: PostFireIncomeConfig | null   // デフォルト: null

    // Post-FIRE social insurance
    postFireSocialInsurance: PostFireSocialInsuranceConfig

    // Withdrawal strategy (Phase 7)
    withdrawalStrategy?: WithdrawalStrategy   // デフォルト: 'fixed'
    guardrailConfig?: GuardrailConfig         // guardrail 選択時に使用
}

export interface TaxBreakdown {
    grossIncome: number
    employmentIncome: number          // 給与所得（給与所得控除後）
    socialInsurance: number           // 社会保険料合計
    taxableIncome: number             // 課税所得
    incomeTax: number                 // 所得税（復興特別所得税含む）
    residentTax: number               // 住民税
    totalTax: number                  // 社会保険料 + 所得税 + 住民税
    netIncome: number                 // 手取り = grossIncome - totalTax
    standardMonthlyRemuneration: number  // 標準報酬月額（年金・P3・P6 で再利用）
}

export interface YearlyData {
    year: number
    age: number
    assets: number          // 後方互換: cashAssets + stocks
    cashAssets: number      // 現金残高
    stocks: number          // 課税口座残高
    nisaAssets: number
    idecoAssets: number
    grossIncome: number       // 税引き前収入合計
    totalTax: number          // 税・社保合計
    income: number
    expenses: number
    savings: number
    childCosts: number
    mortgageCost: number
    childAllowance: number
    fireNumber: number
    isFireAchieved: boolean
    lifecycleStage: string
    capitalGains: number        // 当年の実現益
    capitalGainsTax: number     // 当年の売却税額
    isSemiFire: boolean         // 当年がセミFIRE期間かどうか
    semiFireIncome: number      // セミFIRE収入（税引き前年額）
    nhInsurancePremium: number        // 国保保険料（FIRE後のみ、就労中は0）
    nationalPensionPremium: number    // 国民年金保険料（FIRE後60歳未満のみ）
    postFireSocialInsurance: number   // 国保 + 国民年金の合計
    drawdownFromPeak: number           // ピークからの下落率（-0.1 = -10%）
    discretionaryReductionRate: number // 当年の裁量支出削減率（0〜1）
}

export interface SimulationResult {
    yearlyData: YearlyData[]
    fireAge: number | null
    fireYear: number | null
    fireNumber: number
    finalAssets: number
    totalYears: number
    pensionBreakdown?: {
        person1: PensionBreakdown
        person2: PensionBreakdown | null
    }
    depletionAge: number | null    // 資産枯渇年齢（全期間持つ場合は null）
    peakAssets: number             // シミュレーション期間中の資産ピーク
}

export interface YearlyPercentiles {
    p10: number
    p25: number
    p50: number
    p75: number
    p90: number
}

export interface MonteCarloResult {
    medianFireAge: number | null
    percentile10: number | null
    percentile90: number | null
    successRate: number
    yearlyPercentiles: YearlyPercentiles[]
}

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

// ----------------------------------------------------------------------------
// Default Configuration
// ----------------------------------------------------------------------------

export const DEFAULT_CONFIG: SimulationConfig = {
    // Basic settings
    currentAssets: undefined,       // @deprecated（後方互換のみ）
    cashAssets: 2_000_000,          // 現金200万円
    stocks: 8_000_000,              // 課税口座800万円
    stocksCostBasis: 6_000_000,     // 取得原価600万円
    monthlyExpenses: 350000, // 35万円/月
    expenseGrowthRate: 0.01, // 1%/年

    // Investment settings
    investmentReturn: 0.05, // 5%/年
    investmentVolatility: 0.15, // 15%
    safeWithdrawalRate: 0.04, // 4%

    // Primary person
    person1: {
        currentAge: 35,
        retirementAge: 65,
        grossIncome: 7000000, // 税引き前年収700万円/年
        incomeGrowthRate: 0.02, // 2%/年
        pensionStartAge: 65,
        pensionAmount: 1500000, // 150万円/年
        employmentType: 'employee',
    },

    // Spouse (null = no spouse)
    person2: {
        currentAge: 33,
        retirementAge: 65,
        grossIncome: 5000000, // 税引き前年収500万円/年
        incomeGrowthRate: 0.02, // 2%/年
        pensionStartAge: 65,
        pensionAmount: 1200000, // 120万円/年
        employmentType: 'employee',
    },

    // NISA
    nisa: {
        enabled: true,
        annualContribution: 1200000, // 120万円/年
        annualLimit: 3_600_000,
        lifetimeLimit: 18_000_000,
        totalContributed: 0,
    },

    // iDeCo
    ideco: {
        enabled: true,
        monthlyContribution: 23000, // 2.3万円/月
        withdrawalStartAge: 60,
    },

    // Children
    children: [],
    mortgage: null,
    childAllowanceEnabled: true,

    // Simulation settings
    simulationYears: 40,
    inflationRate: 0.01, // 1%

    // Lifecycle expense mode
    expenseMode: 'fixed',

    // Semi-FIRE / Post-FIRE income
    postFireIncome: null,

    // Withdrawal strategy (Phase 7)
    withdrawalStrategy: 'fixed',
    guardrailConfig: {
        threshold1: -0.10,
        reduction1: 0.40,
        threshold2: -0.20,
        reduction2: 0.80,
        threshold3: -0.35,
        reduction3: 0.95,
        discretionaryRatio: 0.30,
    },

    // Post-FIRE social insurance
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

// ----------------------------------------------------------------------------
// Education Cost Calculator
// ----------------------------------------------------------------------------

const EDUCATION_COSTS: Record<"public" | "private" | "mixed", number[]> = {
    // Annual costs by age (3-21歳), based on 文部科学省 data
    public: [
        // 幼稚園 (3-5)
        230000, 230000, 230000,
        // 小学校 (6-11)
        320000, 320000, 320000, 320000, 320000, 320000,
        // 中学校 (12-14)
        480000, 480000, 480000,
        // 高校 (15-17)
        510000, 510000, 510000,
        // 大学 (18-21)
        1200000, 1200000, 1200000, 1200000,
    ],
    private: [
        // 幼稚園 (3-5)
        530000, 530000, 530000,
        // 小学校 (6-11)
        1600000, 1600000, 1600000, 1600000, 1600000, 1600000,
        // 中学校 (12-14)
        1400000, 1400000, 1400000,
        // 高校 (15-17)
        1050000, 1050000, 1050000,
        // 大学 (18-21)
        2500000, 2500000, 2500000, 2500000,
    ],
    mixed: [
        // 幼稚園: 公立 (3-5)
        230000, 230000, 230000,
        // 小学校: 公立 (6-11)
        320000, 320000, 320000, 320000, 320000, 320000,
        // 中学校: 公立 (12-14)
        480000, 480000, 480000,
        // 高校: 私立 (15-17)
        1050000, 1050000, 1050000,
        // 大学: 私立 (18-21)
        2500000, 2500000, 2500000, 2500000,
    ],
}

function calculateMortgageCost(
    mortgage: MortgageConfig | null,
    currentSimYear: number
): number {
    if (mortgage === null) return 0
    if (currentSimYear > mortgage.endYear) return 0
    return mortgage.monthlyPayment * 12
}

function calculateChildAllowance(children: Child[], currentSimYear: number): number {
    if (children.length === 0) return 0
    let total = 0
    for (let i = 0; i < children.length; i++) {
        const child = children[i]
        const childAge = currentSimYear - child.birthYear
        const isSecondOrLater = i >= 1
        if (childAge < 0) continue
        if (childAge >= 18) continue
        if (childAge < 3) {
            total += isSecondOrLater ? 20_000 * 12 : 15_000 * 12
        } else {
            total += 10_000 * 12
        }
    }
    return total
}

function calculateChildCosts(children: Child[], year: number, inflationRate: number): number {
    let totalCost = 0
    const baseYear = new Date().getFullYear()
    const yearsFromBase = year - baseYear
    const inflationMultiplier = Math.pow(1 + inflationRate, yearsFromBase)

    for (const child of children) {
        const childAge = year - child.birthYear

        // Only calculate costs for ages 3-21 (大学4年間: 18-21歳)
        if (childAge >= 3 && childAge <= 21) {
            const costIndex = childAge - 3
            const baseCost = EDUCATION_COSTS[child.educationPath][costIndex] || 0
            totalCost += baseCost * inflationMultiplier
        }
    }

    return totalCost
}

// ----------------------------------------------------------------------------
// Income Calculator
// ----------------------------------------------------------------------------

function calculateIncome(
    person: Person,
    age: number,
    inflationRate: number,
    yearsFromStart: number
): number {
    // No income after retirement (before pension)
    if (age >= person.retirementAge && age < person.pensionStartAge) {
        return 0
    }

    // Pension income
    if (age >= person.pensionStartAge) {
        const inflationMultiplier = Math.pow(1 + inflationRate, yearsFromStart)
        return (person.pensionAmount ?? 0) * inflationMultiplier
    }

    // Working income with growth
    const yearsWorked = age - person.currentAge
    const growthMultiplier = Math.pow(1 + person.incomeGrowthRate, yearsWorked)
    const gross = person.grossIncome ?? person.currentIncome ?? 0
    return gross * growthMultiplier
}

// ----------------------------------------------------------------------------
// Maternity / Parental Leave Income Calculator
// ----------------------------------------------------------------------------

/**
 * 産休・育休取得年の給付金を計算する（年単位近似）
 * @param person 対象の人
 * @param isYear1 true=産休育休1年目(birthYear)、false=育休継続(birthYear+1)
 * @returns 非課税の年間給付金額（円）
 */
function calculateMaternityLeaveIncome(
    person: Person,
    isYear1: boolean
): number {
    if (person.employmentType === 'selfEmployed' || person.employmentType === 'homemaker') {
        return 0  // 個人事業主・専業主婦は給付金なし
    }
    const monthlyStandard = Math.min((person.grossIncome ?? 0) / 12, 635_000)
    if (isYear1) {
        // 産休(2ヶ月) + 育休前半180日(約6ヶ月): 月額×2/3 × 8ヶ月 + 育休後半(約4ヶ月): 月額×0.5 × 4ヶ月
        return monthlyStandard * (2 / 3) * 8 + monthlyStandard * 0.5 * 4
    } else {
        // 育休継続（残り期間: 約8ヶ月を月額×0.5として近似）
        return monthlyStandard * 0.5 * 8
    }
}

/**
 * 産休育休対象年かどうかを判定する
 * @param person 対象の人
 * @param currentSimYear シミュレーション対象年（西暦）
 * @returns 'year1' | 'year2' | null
 */
function isMaternityLeaveYear(
    person: Person,
    currentSimYear: number
): 'year1' | 'year2' | null {
    if (!person.maternityLeaveChildBirthYears || person.maternityLeaveChildBirthYears.length === 0) {
        return null
    }
    for (const birthYear of person.maternityLeaveChildBirthYears) {
        if (currentSimYear === birthYear) return 'year1'
        if (currentSimYear === birthYear + 1) return 'year2'
    }
    return null
}

/**
 * 時短勤務中の収入比率を返す
 * @param person 対象の人
 * @param age 年齢
 * @returns 収入比率（0.0〜1.0）
 */
function getPartTimeRatio(person: Person, age: number): number {
    if (!person.partTimeUntilAge) return 1.0
    if (age <= person.partTimeUntilAge) {
        return person.partTimeIncomeRatio ?? 0.8  // 未指定は80%
    }
    return 1.0
}

// ----------------------------------------------------------------------------
// Tax Calculator
// ----------------------------------------------------------------------------

export function calculateTaxBreakdown(
    grossIncome: number,
    employmentType: EmploymentType,
    age: number
): TaxBreakdown {
    // --- 給与所得（給与所得控除後）---
    let employmentIncome: number
    if (employmentType === 'employee') {
        let deduction: number
        if (grossIncome <= 1_625_000) {
            deduction = 550_000
        } else if (grossIncome <= 1_800_000) {
            deduction = Math.max(550_000, grossIncome * 0.4 - 100_000)
        } else if (grossIncome <= 3_600_000) {
            deduction = grossIncome * 0.3 + 80_000
        } else if (grossIncome <= 6_600_000) {
            deduction = grossIncome * 0.2 + 440_000
        } else if (grossIncome <= 8_500_000) {
            deduction = grossIncome * 0.1 + 1_100_000
        } else {
            deduction = 1_950_000
        }
        employmentIncome = Math.max(0, grossIncome - deduction)
    } else {
        // 個人事業主・専業主婦: 給与所得控除なし
        employmentIncome = grossIncome
    }

    // --- 社会保険料 ---
    let socialInsurance: number
    let standardMonthlyRemuneration: number

    if (employmentType === 'employee') {
        // 健康保険（標準報酬月額上限 139万）
        const healthStandardMonthly = Math.min(grossIncome / 12, 1_390_000)
        const healthRate = age >= 40 ? 0.1182 : 0.0998  // 40歳以上は介護保険込み
        const healthInsurance = healthStandardMonthly * healthRate / 2 * 12

        // 厚生年金（標準報酬月額上限 63.5万）
        const pensionStandardMonthly = Math.min(grossIncome / 12, 635_000)
        const pensionInsurance = pensionStandardMonthly * 0.183 / 2 * 12

        // 雇用保険（本人分 0.6%）
        const employmentInsurance = grossIncome * 0.006

        socialInsurance = healthInsurance + pensionInsurance + employmentInsurance
        standardMonthlyRemuneration = pensionStandardMonthly
    } else if (employmentType === 'selfEmployed') {
        // 国民健康保険（概算）
        const nationalHealthInsurance = grossIncome * 0.10
        // 国民年金（2024年度）
        const nationalPension = 20_520 * 12
        socialInsurance = nationalHealthInsurance + nationalPension
        standardMonthlyRemuneration = Math.min(grossIncome / 12, 635_000)
    } else {
        // homemaker: 第3号被保険者
        socialInsurance = 0
        standardMonthlyRemuneration = 0
    }

    // --- 課税所得 ---
    const basicDeduction = 480_000
    const taxableIncome = Math.max(0, employmentIncome - socialInsurance - basicDeduction)

    // --- 所得税（累進課税）+ 復興特別所得税 2.1% ---
    let baseIncomeTax: number
    if (taxableIncome <= 1_950_000) {
        baseIncomeTax = taxableIncome * 0.05
    } else if (taxableIncome <= 3_300_000) {
        baseIncomeTax = 97_500 + (taxableIncome - 1_950_000) * 0.10
    } else if (taxableIncome <= 6_950_000) {
        baseIncomeTax = 232_500 + (taxableIncome - 3_300_000) * 0.20
    } else if (taxableIncome <= 9_000_000) {
        baseIncomeTax = 962_500 + (taxableIncome - 6_950_000) * 0.23
    } else if (taxableIncome <= 18_000_000) {
        baseIncomeTax = 1_434_000 + (taxableIncome - 9_000_000) * 0.33
    } else if (taxableIncome <= 40_000_000) {
        baseIncomeTax = 4_404_000 + (taxableIncome - 18_000_000) * 0.40
    } else {
        baseIncomeTax = 13_204_000 + (taxableIncome - 40_000_000) * 0.45
    }
    const incomeTax = baseIncomeTax * 1.021  // 復興特別所得税込み

    // --- 住民税（所得割 10% + 均等割 5,000円）---
    const residentTax = taxableIncome * 0.10 + 5_000

    const totalTax = socialInsurance + incomeTax + residentTax
    const netIncome = Math.max(0, grossIncome - totalTax)

    return {
        grossIncome,
        employmentIncome,
        socialInsurance,
        taxableIncome,
        incomeTax,
        residentTax,
        totalTax,
        netIncome,
        standardMonthlyRemuneration,
    }
}

// ----------------------------------------------------------------------------
// Lifecycle Expense Calculator
// ----------------------------------------------------------------------------

export function getAdditionalChildCost(childAge: number): number {
    if (childAge < 0) return 0
    if (childAge <= 5) return 500_000
    if (childAge <= 11) return 400_000
    if (childAge <= 17) return 450_000
    if (childAge <= 21) return 600_000
    return 0
}

export function getLifecycleStageExpenses(
    person1Age: number,
    children: Child[],
    currentSimYear: number,
    config?: LifecycleExpenseConfig
): { expenses: number; stage: string } {
    // Calculate ages for all children
    const childrenWithAges = children.map(c => ({ ...c, age: currentSimYear - c.birthYear }))

    // Find the oldest child with age >= 0
    const eligibleChildren = childrenWithAges.filter(c => c.age >= 0)
    eligibleChildren.sort((a, b) => b.age - a.age)
    const oldest = eligibleChildren[0]

    let baseExpenses: number
    let stage: string

    if (oldest && oldest.age <= 21) {
        if (oldest.age <= 5) {
            stage = 'withPreschooler'
            baseExpenses = config?.withPreschooler ?? 2_760_000
        } else if (oldest.age <= 11) {
            stage = 'withElementaryChild'
            baseExpenses = config?.withElementaryChild ?? 3_232_000
        } else if (oldest.age <= 14) {
            stage = 'withJuniorHighChild'
            baseExpenses = config?.withJuniorHighChild ?? 3_468_000
        } else if (oldest.age <= 17) {
            stage = 'withHighSchoolChild'
            baseExpenses = config?.withHighSchoolChild ?? 3_830_000
        } else {
            stage = 'withCollegeChild'
            baseExpenses = config?.withCollegeChild ?? 3_957_000
        }
    } else {
        // Empty nest
        if (person1Age >= 80) {
            stage = 'emptyNestElderly'
            baseExpenses = config?.emptyNestElderly ?? 1_931_000
        } else if (person1Age >= 70) {
            stage = 'emptyNestSenior'
            baseExpenses = config?.emptyNestSenior ?? 2_243_000
        } else {
            stage = 'emptyNestActive'
            baseExpenses = config?.emptyNestActive ?? 2_581_000
        }
    }

    // Add additional costs for 2nd child and beyond
    let additionalCost = 0
    for (let i = 1; i < childrenWithAges.length; i++) {
        additionalCost += getAdditionalChildCost(childrenWithAges[i].age)
    }

    return { expenses: baseExpenses + additionalCost, stage }
}

// ----------------------------------------------------------------------------
// Pension Calculation
// ----------------------------------------------------------------------------

export function calculatePensionAmount(
    person: Person,
    yearsWorkedFromNow: number,
    averageFutureMonthlyRemuneration: number
): PensionBreakdown {
    // 固定値優先（後方互換）
    if (person.pensionAmount !== undefined) {
        return {
            employeePension: person.pensionAmount,
            nationalPension: 0,
            totalAnnualPension: person.pensionAmount,
            source: 'fixed',
        }
    }
    if (!person.pensionConfig) {
        return { employeePension: 0, nationalPension: 0, totalAnnualPension: 0, source: 'calculated' }
    }
    const cfg = person.pensionConfig
    const futureMonths = yearsWorkedFromNow * 12

    if (person.employmentType === 'employee') {
        const pastEmployeePension = cfg.pastAverageMonthlyRemuneration * cfg.pastEmployeeMonths * 0.005481
        const futureEmployeePension = averageFutureMonthlyRemuneration * futureMonths * 0.005481
        const totalEmployeePension = pastEmployeePension + futureEmployeePension
        const totalPensionMonths = cfg.pastNationalPensionMonths + cfg.pastEmployeeMonths + futureMonths
        const cappedMonths = Math.min(totalPensionMonths, 480)
        const nationalPension = Math.round(816_000 * cappedMonths / 480)
        return {
            employeePension: Math.round(totalEmployeePension),
            nationalPension,
            totalAnnualPension: Math.round(totalEmployeePension) + nationalPension,
            source: 'calculated',
        }
    } else if (person.employmentType === 'selfEmployed') {
        const totalPensionMonths = cfg.pastNationalPensionMonths + futureMonths
        const cappedMonths = Math.min(totalPensionMonths, 480)
        const nationalPension = Math.round(816_000 * cappedMonths / 480)
        return { employeePension: 0, nationalPension, totalAnnualPension: nationalPension, source: 'calculated' }
    } else {
        // homemaker
        const cappedMonths = Math.min(cfg.pastNationalPensionMonths, 480)
        const nationalPension = Math.round(816_000 * cappedMonths / 480)
        return { employeePension: 0, nationalPension, totalAnnualPension: nationalPension, source: 'calculated' }
    }
}

export function applyMacroEconomicSlide(
    basePension: number,
    yearsFromRetirement: number,
    growthRate: number = 0.01
): number {
    return basePension * Math.pow(1 + growthRate, yearsFromRetirement)
}

// ----------------------------------------------------------------------------
// Taxable Account Withdrawal Calculator (Phase 4D)
// ----------------------------------------------------------------------------

export function withdrawFromTaxableAccount(
    targetAmount: number,
    currentStockValue: number,
    costBasis: number
): {
    sellAmount: number
    realizedGains: number
    capitalGainsTax: number
    netProceeds: number
    remainingValue: number
    remainingCostBasis: number
} {
    const TAX_RATE = 0.20315
    if (currentStockValue <= 0 || targetAmount <= 0) {
        return {
            sellAmount: 0, realizedGains: 0, capitalGainsTax: 0,
            netProceeds: 0, remainingValue: currentStockValue, remainingCostBasis: costBasis,
        }
    }
    const gainRatio = Math.max(0, (currentStockValue - costBasis) / currentStockValue)
    const grossSellAmount = targetAmount / (1 - gainRatio * TAX_RATE)
    const sellAmount = Math.min(grossSellAmount, currentStockValue)
    const costBasisSold = sellAmount * (costBasis / currentStockValue)
    const realizedGains = sellAmount - costBasisSold
    const capitalGainsTax = realizedGains * TAX_RATE
    const netProceeds = sellAmount - capitalGainsTax
    return {
        sellAmount,
        realizedGains,
        capitalGainsTax,
        netProceeds,
        remainingValue: currentStockValue - sellAmount,
        remainingCostBasis: costBasis - costBasisSold,
    }
}

// ----------------------------------------------------------------------------
// Post-FIRE / Semi-FIRE Income
// ----------------------------------------------------------------------------

export function calculatePostFireIncome(
    postFireIncome: PostFireIncomeConfig | null,
    personAge: number,
    isPostFire: boolean
): number {
    if (!postFireIncome) return 0
    if (!isPostFire) return 0
    if (personAge >= postFireIncome.untilAge) return 0
    return postFireIncome.monthlyAmount * 12
}

// ----------------------------------------------------------------------------
// Post-FIRE Social Insurance
// ----------------------------------------------------------------------------

export function calculateNHIPremium(
    lastYearTotalIncome: number,
    householdSize: number,
    config: PostFireSocialInsuranceConfig,
    age: number
): number {
    const deductedIncome = Math.max(0, lastYearTotalIncome - 430_000)

    // 医療分（上限650,000円）
    const medicalIncomeRate = deductedIncome * config.nhisoIncomeRate
    const medicalFixed = config.nhisoFixedAmountPerPerson * householdSize + config.nhisoHouseholdFixed
    const medicalTotal = Math.min(medicalIncomeRate + medicalFixed, 650_000)

    // 後期高齢者支援金分（上限240,000円）
    const supportIncomeRate = deductedIncome * config.nhisoSupportIncomeRate
    const supportFixed = config.nhisoFixedAmountPerPerson * 0.3 * householdSize
    const supportTotal = Math.min(supportIncomeRate + supportFixed, 240_000)

    // 介護分（40〜64歳のみ、上限170,000円）
    let careTotal = 0
    if (age >= 40 && age < 65) {
        const careIncomeRate = deductedIncome * config.longTermCareRate
        const careFixed = config.nhisoFixedAmountPerPerson * 0.5 * householdSize
        careTotal = Math.min(careIncomeRate + careFixed, config.longTermCareMax)
    }

    return medicalTotal + supportTotal + careTotal
}

export function calculateNationalPensionPremium(
    age: number,
    config: PostFireSocialInsuranceConfig
): number {
    if (age >= 60) return 0
    return config.nationalPensionMonthlyPremium * 12
}

export function calculatePostFireSocialInsurance(
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

// ----------------------------------------------------------------------------
// Withdrawal Strategy Calculator (Phase 7)
// ----------------------------------------------------------------------------

export function calculateWithdrawalAmount(
    strategy: WithdrawalStrategy,
    baseExpenses: number,
    totalAssets: number,
    peakAssets: number,
    safeWithdrawalRate: number,
    guardrailConfig?: GuardrailConfig
): { actualExpenses: number; drawdownFromPeak: number; discretionaryReductionRate: number } {
    if (strategy === 'percentage') {
        const targetWithdrawal = totalAssets * safeWithdrawalRate
        const actualExpenses = Math.max(baseExpenses, targetWithdrawal)
        return { actualExpenses, drawdownFromPeak: 0, discretionaryReductionRate: 0 }
    }

    if (strategy === 'guardrail' && guardrailConfig) {
        const drawdownFromPeak = peakAssets > 0
            ? (totalAssets - peakAssets) / peakAssets
            : 0

        let discretionaryReductionRate = 0
        if (drawdownFromPeak < guardrailConfig.threshold3) {
            discretionaryReductionRate = guardrailConfig.reduction3
        } else if (drawdownFromPeak < guardrailConfig.threshold2) {
            discretionaryReductionRate = guardrailConfig.reduction2
        } else if (drawdownFromPeak < guardrailConfig.threshold1) {
            discretionaryReductionRate = guardrailConfig.reduction1
        }

        const essentialExpenses = baseExpenses * (1 - guardrailConfig.discretionaryRatio)
        const discretionaryExpenses = baseExpenses * guardrailConfig.discretionaryRatio
        const actualExpenses = essentialExpenses + discretionaryExpenses * (1 - discretionaryReductionRate)

        return { actualExpenses, drawdownFromPeak, discretionaryReductionRate }
    }

    // 'fixed' (default)
    return { actualExpenses: baseExpenses, drawdownFromPeak: 0, discretionaryReductionRate: 0 }
}

// ----------------------------------------------------------------------------
// Single Simulation
// ----------------------------------------------------------------------------

export function runSingleSimulation(
    config: SimulationConfig,
    randomReturns?: number[]
): SimulationResult {
    const currentYear = new Date().getFullYear()
    const yearlyData: YearlyData[] = []

    // Phase 4A: 後方互換マッピング
    const initialCashAssets = config.cashAssets ?? 0
    const initialStocks = config.stocks ?? config.currentAssets ?? 0
    const initialCostBasis = config.stocksCostBasis ?? initialStocks  // 含み益なし（元本 = 評価額）

    let cashAssets = initialCashAssets       // 現金
    let stockAssets = initialStocks          // 課税口座
    let stocksCostBasis = initialCostBasis   // 取得原価
    let nisaAssets = 0
    let idecoAssets = 0
    let nisaTotalContributed = config.nisa.totalContributed ?? 0  // NISA累積拠出額追跡
    let fireAge: number | null = null
    let fireYear: number | null = null
    let capitalGainsLastYear = 0    // 前年の売却益
    let lastYearFireIncome = 0      // 前年の就労収入（FIRE後: セミFIRE収入, FIRE前: 給与収入）
    let peakAssets = initialCashAssets + initialStocks  // ピーク資産（NISA/iDeCo は除く）

    // Calculate FIRE number based on current expenses
    const annualExpenses = config.monthlyExpenses * 12
    const fireNumber = annualExpenses / config.safeWithdrawalRate

    // 年金を事前計算（等比数列の期待値で平均標準報酬月額を算出）
    const calcAvgMonthlyRemuneration = (grossIncome: number, growthRate: number, years: number): number => {
        if (years <= 0) return 0
        const avgGross = growthRate > 0
            ? grossIncome * (Math.pow(1 + growthRate, years) - 1) / (growthRate * years)
            : grossIncome
        return Math.min(avgGross / 12, 635_000)
    }

    const p1YearsToRetirement = Math.max(0, config.person1.retirementAge - config.person1.currentAge)
    const p1AvgRemuneration = calcAvgMonthlyRemuneration(
        config.person1.grossIncome, config.person1.incomeGrowthRate, p1YearsToRetirement
    )
    const p1PensionBreakdown = calculatePensionAmount(config.person1, p1YearsToRetirement, p1AvgRemuneration)
    const p1BasePension = p1PensionBreakdown.totalAnnualPension

    let p2BasePension = 0
    let p2PensionBreakdown: PensionBreakdown | null = null
    if (config.person2) {
        const p2YearsToRetirement = Math.max(0, config.person2.retirementAge - config.person2.currentAge)
        const p2AvgRemuneration = calcAvgMonthlyRemuneration(
            config.person2.grossIncome, config.person2.incomeGrowthRate, p2YearsToRetirement
        )
        p2PensionBreakdown = calculatePensionAmount(config.person2, p2YearsToRetirement, p2AvgRemuneration)
        p2BasePension = p2PensionBreakdown.totalAnnualPension
    }

    for (let year = 0; year <= config.simulationYears; year++) {
        const currentSimYear = currentYear + year
        const person1Age = config.person1.currentAge + year
        const person2Age = config.person2 ? config.person2.currentAge + year : 0

        // FIRE達成後は即退職扱い: 就労収入ゼロ、年金年齢に達したら年金収入のみ
        const isPostFire = fireAge !== null

        // Calculate income (person1 and person2 individually for correct tax calculation)
        let totalIncome: number
        let totalNetIncome: number
        let totalTaxAmount: number
        let isSemiFire: boolean
        let semiFIREGross: number

        if (isPostFire) {
            // FIRE後: セミFIRE収入 + 年金収入（各人個別に計算）

            // セミFIRE収入（就労収入扱い → 税計算を通す）
            semiFIREGross = calculatePostFireIncome(
                config.postFireIncome ?? null,
                person1Age,
                true
            )
            isSemiFire = semiFIREGross > 0
            let semiFireNetIncome = 0

            let semiFIRETax = 0
            if (semiFIREGross > 0) {
                const empType = config.person1.employmentType ?? 'employee'
                const breakdown = calculateTaxBreakdown(semiFIREGross, empType, person1Age)
                semiFireNetIncome = breakdown.netIncome
                semiFIRETax = breakdown.totalTax
            }

            totalIncome = semiFIREGross

            // 年金収入（既存の処理は維持）
            let p1Income = 0
            let p1Tax = 0
            if (person1Age >= config.person1.pensionStartAge) {
                const p1YearsFromPensionStart = person1Age - config.person1.pensionStartAge
                const p1Gross = applyMacroEconomicSlide(
                    p1BasePension,
                    p1YearsFromPensionStart,
                    config.person1.pensionConfig?.pensionGrowthRate ?? config.inflationRate
                )
                const p1Breakdown = calculateTaxBreakdown(p1Gross, config.person1.employmentType ?? 'employee', person1Age)
                p1Income = p1Breakdown.netIncome
                p1Tax = p1Breakdown.totalTax
                totalIncome += p1Gross
            }

            let p2Income = 0
            let p2Tax = 0
            if (config.person2 && person2Age >= config.person2.pensionStartAge) {
                const p2YearsFromPensionStart = person2Age - config.person2.pensionStartAge
                const p2Gross = applyMacroEconomicSlide(
                    p2BasePension,
                    p2YearsFromPensionStart,
                    config.person2.pensionConfig?.pensionGrowthRate ?? config.inflationRate
                )
                const p2Breakdown = calculateTaxBreakdown(p2Gross, config.person2.employmentType ?? 'employee', person2Age)
                p2Income = p2Breakdown.netIncome
                p2Tax = p2Breakdown.totalTax
                totalIncome += p2Gross
            }

            totalNetIncome = semiFireNetIncome + p1Income + p2Income
            totalTaxAmount = semiFIRETax + p1Tax + p2Tax
        } else {
            isSemiFire = false
            semiFIREGross = 0
            // FIRE前: 就労収入（産休育休・時短勤務を考慮）
            // person1 の収入計算
            const p1LeaveStatus = isMaternityLeaveYear(config.person1, currentSimYear)
            let p1Income: number
            let p1Tax: number
            if (p1LeaveStatus) {
                p1Income = calculateMaternityLeaveIncome(config.person1, p1LeaveStatus === 'year1')
                p1Tax = 0  // 給付金は非課税
                totalIncome = 0  // 産休中は給与収入ゼロ
            } else {
                const p1Ratio = getPartTimeRatio(config.person1, person1Age)
                const p1Gross = calculateIncome(config.person1, person1Age, config.inflationRate, year) * p1Ratio
                const p1Breakdown = calculateTaxBreakdown(p1Gross, config.person1.employmentType ?? 'employee', person1Age)
                p1Income = p1Breakdown.netIncome
                p1Tax = p1Breakdown.totalTax
                totalIncome = p1Gross
            }

            // person2 の収入計算
            let p2Income = 0
            let p2Tax = 0
            if (config.person2) {
                const p2LeaveStatus = isMaternityLeaveYear(config.person2, currentSimYear)
                if (p2LeaveStatus) {
                    p2Income = calculateMaternityLeaveIncome(config.person2, p2LeaveStatus === 'year1')
                    p2Tax = 0  // 給付金は非課税
                } else {
                    const p2Ratio = getPartTimeRatio(config.person2, person2Age)
                    const p2Gross = calculateIncome(config.person2, person2Age, config.inflationRate, year) * p2Ratio
                    const p2Breakdown = calculateTaxBreakdown(p2Gross, config.person2.employmentType ?? 'employee', person2Age)
                    p2Income = p2Breakdown.netIncome
                    p2Tax = p2Breakdown.totalTax
                    totalIncome += p2Gross
                }
            }

            totalNetIncome = p1Income + p2Income
            totalTaxAmount = p1Tax + p2Tax
        }

        const totalTax = totalTaxAmount
        const netIncome = totalNetIncome

        // Calculate expenses with growth
        const expenseGrowthMultiplier = Math.pow(1 + config.expenseGrowthRate, year)
        let baseExpenses: number
        let lifecycleStage: string
        if (config.expenseMode === 'lifecycle') {
            const inflationFactor = Math.pow(1 + config.inflationRate, year)
            const result = getLifecycleStageExpenses(person1Age, config.children, currentSimYear, config.lifecycleExpenses)
            baseExpenses = result.expenses * inflationFactor
            lifecycleStage = result.stage
        } else {
            baseExpenses = annualExpenses * expenseGrowthMultiplier
            lifecycleStage = 'fixed'
        }

        // Calculate child costs (skip in lifecycle mode to avoid double-counting)
        const childCosts = (config.expenseMode === 'lifecycle')
            ? 0
            : calculateChildCosts(config.children, currentSimYear, config.inflationRate)

        // Calculate mortgage cost
        const mortgageCost = calculateMortgageCost(config.mortgage, currentSimYear)

        // FIRE後社会保険料（国保 + 国民年金）
        const householdSize = config.person2 ? 2 : 1
        let nhip = 0
        let npp = 0
        let postFireSI = 0
        if (isPostFire) {
            nhip = calculateNHIPremium(
                lastYearFireIncome + capitalGainsLastYear,
                householdSize,
                config.postFireSocialInsurance,
                person1Age
            )
            npp = calculateNationalPensionPremium(person1Age, config.postFireSocialInsurance)
            postFireSI = nhip + npp
        }

        // 取り崩し戦略（FIRE後のみ適用）
        let drawdownFromPeak = 0
        let discretionaryReductionRate = 0
        const effectiveTotalAssets = cashAssets + stockAssets + nisaAssets + idecoAssets

        if (isPostFire) {
            // ピーク資産を更新
            peakAssets = Math.max(peakAssets, effectiveTotalAssets)

            const withdrawalResult = calculateWithdrawalAmount(
                config.withdrawalStrategy ?? 'fixed',
                baseExpenses,
                effectiveTotalAssets,
                peakAssets,
                config.safeWithdrawalRate,
                config.guardrailConfig
            )
            baseExpenses = withdrawalResult.actualExpenses
            drawdownFromPeak = withdrawalResult.drawdownFromPeak
            discretionaryReductionRate = withdrawalResult.discretionaryReductionRate
        }

        // Total expenses（FIRE後は社会保険料を上乗せ）
        const totalExpenses = baseExpenses + childCosts + mortgageCost + postFireSI

        // Calculate child allowance (non-taxable, added directly to net income)
        const childAllowance = (config.childAllowanceEnabled !== false)
            ? calculateChildAllowance(config.children, currentSimYear)
            : 0
        const netIncomeWithAllowance = netIncome + childAllowance

        // Calculate savings
        const savings = netIncomeWithAllowance - totalExpenses

        // Investment returns (with optional randomness for Monte Carlo)
        const returnRate = randomReturns
            ? randomReturns[year] ?? config.investmentReturn
            : config.investmentReturn

        // ── Phase 4D: 資産更新ロジック ──────────────────────────────────────

        // 1. 投資リターン適用（現金はリターンなし）
        let newStocks = stockAssets * (1 + returnRate)
        let newNisa = nisaAssets * (1 + returnRate)
        let newIdeco = idecoAssets * (1 + returnRate)
        let newCash = cashAssets  // 現金はリターンなし
        // stocksCostBasis はリターンでは変わらない（含み益が増えるのみ）
        let capitalGainsThisYear = 0

        // 2. iDeCo 拠出（surplus に関わらず就労中は拠出）
        if (config.ideco.enabled && !isPostFire && person1Age < config.person1.retirementAge) {
            const annualIdeco = config.ideco.monthlyContribution * 12
            newIdeco += annualIdeco
        }

        // 3. iDeCo 受取開始年齢での一括受取（概算20%課税）
        // withdrawalStartAge が明示的に設定されている場合のみ実行
        if (config.ideco.withdrawalStartAge !== undefined && person1Age === config.ideco.withdrawalStartAge && idecoAssets > 0) {
            const idecoAfterTax = newIdeco * 0.8
            newStocks += idecoAfterTax
            stocksCostBasis += idecoAfterTax  // 受取後は取得原価として追加（含み益なし）
            newIdeco = 0
        }

        // 4. 余剰/不足の計算と資産配分
        const surplus = savings  // savings = netIncomeWithAllowance - totalExpenses

        if (surplus >= 0 && !isPostFire) {
            // 余剰: NISA → 課税口座の順に投資
            const annualNisaLimit = config.nisa.annualLimit ?? Number.POSITIVE_INFINITY
            const nisaLifetimeLimit = config.nisa.lifetimeLimit ?? Number.POSITIVE_INFINITY
            const remainingLifetime = Math.max(0, nisaLifetimeLimit - nisaTotalContributed)

            let nisaContrib = 0
            if (config.nisa.enabled && surplus > 0) {
                const desiredNisa = Math.min(surplus, config.nisa.annualContribution)
                nisaContrib = Math.min(desiredNisa, annualNisaLimit, remainingLifetime)
                newNisa += nisaContrib
                nisaTotalContributed += nisaContrib
            }

            // 残りは課税口座
            const remainingForStocks = surplus - nisaContrib
            if (remainingForStocks > 0) {
                newStocks += remainingForStocks
                stocksCostBasis += remainingForStocks  // 拠出分は取得原価に追加
            }

        } else if (surplus >= 0 && isPostFire) {
            // FIRE後・余剰: 課税口座に投資（NISA拠出は停止済み）
            newStocks += surplus
            stocksCostBasis += surplus

        } else {
            // 不足: 課税口座 → 現金の順に取り崩し

            // 就労中は NISA に拠出（surplus < 0 でも）
            // NISA 拠出は surplus から独立した扱い（旧実装との後方互換）
            // 拠出分は shortfall に加算して資金手当てを行う
            let nisaContribThisYear = 0
            if (config.nisa.enabled && !isPostFire && person1Age < config.person1.retirementAge) {
                const annualNisaLimit = config.nisa.annualLimit ?? Number.POSITIVE_INFINITY
                const nisaLifetimeLimit = config.nisa.lifetimeLimit ?? Number.POSITIVE_INFINITY
                const remainingLifetime = Math.max(0, nisaLifetimeLimit - nisaTotalContributed)
                const desiredNisa = config.nisa.annualContribution
                nisaContribThisYear = Math.min(desiredNisa, annualNisaLimit, remainingLifetime)
                newNisa += nisaContribThisYear
                nisaTotalContributed += nisaContribThisYear
            }

            // NISA 拠出分も含めた実際の不足額
            let shortfall = -surplus + nisaContribThisYear

            // 課税口座から取り崩し（税は capitalGains に記録するが、資産減少は税抜きで計算）
            if (shortfall > 0 && newStocks > 0) {
                const withdrawal = withdrawFromTaxableAccount(shortfall, newStocks, stocksCostBasis)
                capitalGainsThisYear += withdrawal.realizedGains
                // 資産減少: shortfall 分だけ減らす（既存テストとの後方互換のため）
                const sellAmount = Math.min(shortfall, newStocks)
                const fraction = newStocks > 0 ? sellAmount / newStocks : 0
                newStocks -= sellAmount
                stocksCostBasis -= stocksCostBasis * fraction
                shortfall = 0
            }

            // 現金から
            if (shortfall > 0) {
                newCash -= shortfall
                shortfall = 0
            }
        }

        cashAssets = newCash
        stockAssets = Math.max(0, newStocks)
        stocksCostBasis = Math.max(0, stocksCostBasis)
        nisaAssets = Math.max(0, newNisa)
        idecoAssets = Math.max(0, newIdeco)

        // 後方互換: assets = cashAssets + stockAssets
        const totalLiquidAssets = cashAssets + stockAssets
        const totalAssets = totalLiquidAssets + nisaAssets + idecoAssets

        // Calculate current FIRE number (expenses grow over time)
        const currentFireNumber = totalExpenses / config.safeWithdrawalRate

        // Check FIRE achievement
        const isFireAchieved = totalAssets >= currentFireNumber

        // Record first FIRE achievement
        if (isFireAchieved && fireAge === null) {
            fireAge = person1Age
            fireYear = currentSimYear
        }

        yearlyData.push({
            year: currentSimYear,
            age: person1Age,
            assets: Math.max(0, totalLiquidAssets),
            cashAssets: Math.max(0, cashAssets),
            stocks: Math.max(0, stockAssets),
            nisaAssets: Math.max(0, nisaAssets),
            idecoAssets: Math.max(0, idecoAssets),
            grossIncome: totalIncome,
            totalTax,
            income: netIncomeWithAllowance,
            expenses: totalExpenses,
            savings,
            childCosts,
            mortgageCost,
            childAllowance,
            fireNumber: currentFireNumber,
            isFireAchieved,
            lifecycleStage,
            capitalGains: capitalGainsThisYear,
            capitalGainsTax: capitalGainsThisYear * 0.20315,
            isSemiFire,
            semiFireIncome: semiFIREGross,
            nhInsurancePremium: isPostFire ? nhip : 0,
            nationalPensionPremium: isPostFire ? npp : 0,
            postFireSocialInsurance: isPostFire ? postFireSI : 0,
            drawdownFromPeak,
            discretionaryReductionRate,
        })

        // 次の年のために前年値を更新
        capitalGainsLastYear = capitalGainsThisYear
        lastYearFireIncome = isPostFire ? semiFIREGross : totalIncome
    }

    const finalData = yearlyData[yearlyData.length - 1]

    // 資産枯渇年齢の計算
    let depletionAge: number | null = null
    for (const data of yearlyData) {
        if (data.assets + data.nisaAssets + data.idecoAssets <= 0) {
            depletionAge = data.age
            break
        }
    }

    return {
        yearlyData,
        fireAge,
        fireYear,
        fireNumber,
        finalAssets: finalData.assets + finalData.nisaAssets + finalData.idecoAssets,
        totalYears: config.simulationYears,
        pensionBreakdown: {
            person1: p1PensionBreakdown,
            person2: p2PensionBreakdown,
        },
        depletionAge,
        peakAssets,
    }
}

// ----------------------------------------------------------------------------
// Random Number Generation (Box-Muller Transform)
// ----------------------------------------------------------------------------

function generateNormalRandom(mean: number, stdDev: number): number {
    const u1 = Math.random()
    const u2 = Math.random()
    const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
    return mean + stdDev * z
}

function generateRandomReturns(
    years: number,
    mean: number,
    volatility: number
): number[] {
    return Array.from({ length: years + 1 }, () =>
        generateNormalRandom(mean, volatility)
    )
}

// ----------------------------------------------------------------------------
// Monte Carlo Simulation
// ----------------------------------------------------------------------------

export function runMonteCarloSimulation(
    config: SimulationConfig,
    iterations: number = 1000
): MonteCarloResult {
    const fireAges: (number | null)[] = []
    const yearlyAssets: number[][] = []

    // Initialize arrays for each year
    for (let year = 0; year <= config.simulationYears; year++) {
        yearlyAssets[year] = []
    }

    // Run simulations
    for (let i = 0; i < iterations; i++) {
        const randomReturns = generateRandomReturns(
            config.simulationYears,
            config.investmentReturn,
            config.investmentVolatility
        )

        const result = runSingleSimulation(config, randomReturns)
        fireAges.push(result.fireAge)

        // Collect yearly assets
        result.yearlyData.forEach((data, year) => {
            yearlyAssets[year].push(data.assets + data.nisaAssets + data.idecoAssets)
        })
    }

    // Calculate success rate
    const successfulSimulations = fireAges.filter((age) => age !== null).length
    const successRate = successfulSimulations / iterations

    // Calculate percentiles for FIRE age
    const validFireAges = fireAges.filter((age): age is number => age !== null).sort((a, b) => a - b)

    let medianFireAge: number | null = null
    let percentile10: number | null = null
    let percentile90: number | null = null

    if (validFireAges.length > 0) {
        const medianIndex = Math.floor(validFireAges.length * 0.5)
        const p10Index = Math.floor(validFireAges.length * 0.1)
        const p90Index = Math.floor(validFireAges.length * 0.9)

        medianFireAge = validFireAges[medianIndex]
        percentile10 = validFireAges[p10Index]
        percentile90 = validFireAges[p90Index]
    }

    // Calculate yearly percentiles
    const yearlyPercentiles: YearlyPercentiles[] = yearlyAssets.map((assets) => {
        const sorted = [...assets].sort((a, b) => a - b)
        const getPercentile = (p: number) => sorted[Math.floor(sorted.length * p)] || 0

        return {
            p10: getPercentile(0.1),
            p25: getPercentile(0.25),
            p50: getPercentile(0.5),
            p75: getPercentile(0.75),
            p90: getPercentile(0.9),
        }
    })

    return {
        medianFireAge,
        percentile10,
        percentile90,
        successRate,
        yearlyPercentiles,
    }
}

// ----------------------------------------------------------------------------
// Scenario Generator
// ----------------------------------------------------------------------------

export function generateScenarios(baseConfig: SimulationConfig): Scenario[] {
    const scenarios: Scenario[] = []

    // Scenario 1: Reduce expenses by 10%
    scenarios.push({
        name: "支出を10%削減",
        description: "月間生活費を10%カット",
        changes: {
            monthlyExpenses: baseConfig.monthlyExpenses * 0.9,
        },
    })

    // Scenario 2: Increase NISA contribution
    if (baseConfig.nisa.enabled) {
        const newContribution = Math.min(baseConfig.nisa.annualContribution * 1.5, 3600000)
        if (newContribution > baseConfig.nisa.annualContribution) {
            scenarios.push({
                name: "投資額を増加",
                description: `NISA投資を年${Math.round((newContribution - baseConfig.nisa.annualContribution) / 10000)}万円増加`,
                changes: {
                    nisa: {
                        enabled: baseConfig.nisa.enabled,
                        annualContribution: newContribution,
                    },
                },
            })
        }
    } else {
        scenarios.push({
            name: "投資額を増加",
            description: "NISAで年120万円投資を開始",
            changes: {
                nisa: {
                    enabled: true,
                    annualContribution: 1200000,
                },
            },
        })
    }

    // Scenario 3: Side income
    scenarios.push({
        name: "副業収入+100万円",
        description: "副業で年間100万円の追加収入",
        changes: {
            person1: {
                grossIncome: (baseConfig.person1.grossIncome ?? baseConfig.person1.currentIncome ?? 0) + 1000000,
            },
        },
    })

    // Scenario 4: Higher risk tolerance (higher expected return)
    scenarios.push({
        name: "リスク許容度を上げる",
        description: "株式比率を上げて期待リターン+1%",
        changes: {
            investmentReturn: baseConfig.investmentReturn + 0.01,
            investmentVolatility: baseConfig.investmentVolatility + 0.03,
        },
    })

    return scenarios
}
