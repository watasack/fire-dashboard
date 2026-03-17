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
}

export interface Child {
    birthYear: number
    educationPath: "public" | "private" | "mixed"
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

    // Simulation settings
    simulationYears: number
    inflationRate: number
}

export interface YearlyData {
    year: number
    age: number
    assets: number
    nisaAssets: number
    idecoAssets: number
    income: number
    expenses: number
    savings: number
    childCosts: number
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
// Tax Calculator (Simplified)
// ----------------------------------------------------------------------------

function calculateTax(income: number): number {
    // Simplified progressive tax calculation for Japan
    // Including social insurance (~15%)
    const socialInsurance = income * 0.15
    const taxableIncome = Math.max(0, income - 480000) // Basic deduction

    let incomeTax = 0
    if (taxableIncome > 0) {
        if (taxableIncome <= 1950000) {
            incomeTax = taxableIncome * 0.05
        } else if (taxableIncome <= 3300000) {
            incomeTax = 97500 + (taxableIncome - 1950000) * 0.10
        } else if (taxableIncome <= 6950000) {
            incomeTax = 232500 + (taxableIncome - 3300000) * 0.20
        } else if (taxableIncome <= 9000000) {
            incomeTax = 962500 + (taxableIncome - 6950000) * 0.23
        } else if (taxableIncome <= 18000000) {
            incomeTax = 1434000 + (taxableIncome - 9000000) * 0.33
        } else {
            incomeTax = 4404000 + (taxableIncome - 18000000) * 0.40
        }
    }

    // Resident tax (~10%)
    const residentTax = taxableIncome * 0.10

    return socialInsurance + incomeTax + residentTax
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

        // Calculate income
        let totalIncome: number
        if (isPostFire) {
            totalIncome = 0
            if (person1Age >= config.person1.pensionStartAge) {
                const inflationMultiplier = Math.pow(1 + config.inflationRate, year)
                totalIncome += config.person1.pensionAmount * inflationMultiplier
            }
            if (config.person2 && person2Age >= config.person2.pensionStartAge) {
                const inflationMultiplier = Math.pow(1 + config.inflationRate, year)
                totalIncome += config.person2.pensionAmount * inflationMultiplier
            }
        } else {
            totalIncome = calculateIncome(config.person1, person1Age, config.inflationRate, year)
            if (config.person2) {
                totalIncome += calculateIncome(config.person2, person2Age, config.inflationRate, year)
            }
        }

        // Calculate taxes
        const totalTax = calculateTax(totalIncome)
        const netIncome = totalIncome - totalTax

        // Calculate expenses with growth
        const expenseGrowthMultiplier = Math.pow(1 + config.expenseGrowthRate, year)
        const baseExpenses = annualExpenses * expenseGrowthMultiplier

        // Calculate child costs
        const childCosts = calculateChildCosts(config.children, currentSimYear, config.inflationRate)

        // Total expenses
        const totalExpenses = baseExpenses + childCosts

        // Calculate savings
        const savings = netIncome - totalExpenses

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
            income: netIncome,
            expenses: totalExpenses,
            savings,
            childCosts,
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
