// ============================================================================
// FIRE Simulator - TypeScript Implementation
// ============================================================================

// ----------------------------------------------------------------------------
// Types
// ----------------------------------------------------------------------------

export type EmploymentType = 'employee' | 'selfEmployed' | 'homemaker'

export interface Person {
    currentAge: number
    retirementAge: number
    grossIncome: number          // 税引き前年収（円）
    incomeGrowthRate: number
    pensionStartAge: number
    pensionAmount: number
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
}

export interface IDeCoConfig {
    enabled: boolean
    monthlyContribution: number
}

export interface SimulationConfig {
    // Basic settings
    currentAssets: number
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
    assets: number
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
}

export interface SimulationResult {
    yearlyData: YearlyData[]
    fireAge: number | null
    fireYear: number | null
    fireNumber: number
    finalAssets: number
    totalYears: number
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
    currentAssets: 10000000, // 1000万円
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
    },

    // iDeCo
    ideco: {
        enabled: true,
        monthlyContribution: 23000, // 2.3万円/月
    },

    // Children
    children: [],
    mortgage: null,
    childAllowanceEnabled: true,

    // Simulation settings
    simulationYears: 40,
    inflationRate: 0.01, // 1%
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
        return person.pensionAmount * inflationMultiplier
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
// Single Simulation
// ----------------------------------------------------------------------------

export function runSingleSimulation(
    config: SimulationConfig,
    randomReturns?: number[]
): SimulationResult {
    const currentYear = new Date().getFullYear()
    const yearlyData: YearlyData[] = []

    let assets = config.currentAssets
    let nisaAssets = 0
    let idecoAssets = 0
    let fireAge: number | null = null
    let fireYear: number | null = null

    // Calculate FIRE number based on current expenses
    const annualExpenses = config.monthlyExpenses * 12
    const fireNumber = annualExpenses / config.safeWithdrawalRate

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

        if (isPostFire) {
            // FIRE後: 年金収入のみ（各人個別に計算）
            let p1Income = 0
            let p1Tax = 0
            if (person1Age >= config.person1.pensionStartAge) {
                const inflationMultiplier = Math.pow(1 + config.inflationRate, year)
                const p1Gross = config.person1.pensionAmount * inflationMultiplier
                const p1Breakdown = calculateTaxBreakdown(p1Gross, config.person1.employmentType ?? 'employee', person1Age)
                p1Income = p1Breakdown.netIncome
                p1Tax = p1Breakdown.totalTax
                totalIncome = p1Gross
            } else {
                totalIncome = 0
            }

            let p2Income = 0
            let p2Tax = 0
            if (config.person2 && person2Age >= config.person2.pensionStartAge) {
                const inflationMultiplier = Math.pow(1 + config.inflationRate, year)
                const p2Gross = config.person2.pensionAmount * inflationMultiplier
                const p2Breakdown = calculateTaxBreakdown(p2Gross, config.person2.employmentType ?? 'employee', person2Age)
                p2Income = p2Breakdown.netIncome
                p2Tax = p2Breakdown.totalTax
                totalIncome += p2Gross
            }

            totalNetIncome = p1Income + p2Income
            totalTaxAmount = p1Tax + p2Tax
        } else {
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
        const baseExpenses = annualExpenses * expenseGrowthMultiplier

        // Calculate child costs
        const childCosts = calculateChildCosts(config.children, currentSimYear, config.inflationRate)

        // Calculate mortgage cost
        const mortgageCost = calculateMortgageCost(config.mortgage, currentSimYear)

        // Total expenses
        const totalExpenses = baseExpenses + childCosts + mortgageCost

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

        // Update assets
        assets = assets * (1 + returnRate) + savings

        // NISA contributions and growth (tax-free)
        if (config.nisa.enabled && !isPostFire && person1Age < config.person1.retirementAge) {
            nisaAssets = nisaAssets * (1 + returnRate) + config.nisa.annualContribution
        } else {
            nisaAssets = nisaAssets * (1 + returnRate)
        }

        // iDeCo contributions and growth (tax-deferred)
        if (config.ideco.enabled && !isPostFire && person1Age < config.person1.retirementAge) {
            const annualIdeco = config.ideco.monthlyContribution * 12
            idecoAssets = idecoAssets * (1 + returnRate) + annualIdeco
        } else {
            idecoAssets = idecoAssets * (1 + returnRate)
        }

        // Total assets for FIRE calculation
        const totalAssets = assets + nisaAssets + idecoAssets

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
            assets: Math.max(0, assets),
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
        })
    }

    const finalData = yearlyData[yearlyData.length - 1]

    return {
        yearlyData,
        fireAge,
        fireYear,
        fireNumber,
        finalAssets: finalData.assets + finalData.nisaAssets + finalData.idecoAssets,
        totalYears: config.simulationYears,
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
