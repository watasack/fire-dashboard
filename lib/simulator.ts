// ============================================================================
// FIRE Simulator - TypeScript Implementation
// ============================================================================

// ----------------------------------------------------------------------------
// Internal constants
// ----------------------------------------------------------------------------

/** SWRは内部定数として固定（ユーザーには非公開）。FIRE達成判定・定率引き出し戦略で使用 */
const INTERNAL_SWR = 0.04

// ----------------------------------------------------------------------------
// Types
// ----------------------------------------------------------------------------

export type EmploymentType = 'employee' | 'selfEmployed' | 'homemaker'

export type WithdrawalStrategy = 'fixed' | 'percentage' | 'guardrail'

export type MCReturnModel = 'normal' | 'meanReversion' | 'bootstrap'

export interface MeanReversionConfig {
    speed: number    // 平均回帰速度（0.0〜1.0、推奨: 0.3）
}

export interface BootstrapConfig {
    historicalReturns: number[]    // 過去の年次リターンデータ（小数: 0.10 = 10%）
    blockSize?: number             // ブロックサイズ（デフォルト: 1）
}

export interface GuardrailConfig {
    threshold1: number       // デフォルト: -0.10
    reduction1: number       // デフォルト: 0.40
    threshold2: number       // デフォルト: -0.20
    reduction2: number       // デフォルト: 0.80
    threshold3: number       // デフォルト: -0.35
    reduction3: number       // デフォルト: 0.95
    discretionaryRatio: number           // 後方互換: useLifecycleDiscretionary が false の時のみ使用
    useLifecycleDiscretionary?: boolean  // true=ライフステージ別（家計調査ベース）, false=discretionaryRatio固定
}

/** 産休・育休設定（子ごと・週数・月数を詳細指定） */
export interface MaternityLeaveEntry {
    childBirthDate: string    // 'YYYY-MM' 形式（例: '2027-04'）
    prenatalWeeks?: number    // 産前休暇週数（デフォルト: 6）
    postnatalWeeks?: number   // 産後休暇週数（デフォルト: 8、法定最低）
    childcareMonths?: number  // 産後休暇終了後の育休月数（デフォルト: 10）
}

/** 住宅メンテナンス費用（周期型） */
export interface MaintenanceCost {
    amount: number            // 1回あたりの費用（円）
    intervalYears: number     // 周期（年）
    firstYear: number         // 初回発生年（西暦）
    label?: string            // 表示名（例: '外壁補修'）
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
    birthMonth?: number          // 誕生月（1-12）。FIRE達成月の表示精度向上に使用
    retirementAge: number
    grossIncome: number          // 税引き前年収（円）
    incomeGrowthRate: number
    pensionStartAge: number
    pensionAmount?: number | null
    pensionConfig?: PensionConfig
    employmentType?: EmploymentType  // 雇用形態（省略時は 'employee'）
    /** @deprecated grossIncome を使うこと */
    currentIncome?: number
    /** @deprecated maternityLeaveConfig を使うこと */
    maternityLeaveChildBirthYears?: number[]  // 産休・育休を取る子の出生年（年単位近似・後方互換）
    maternityLeaveConfig?: MaternityLeaveEntry[]  // 産休・育休の詳細設定（月単位精度）
    partTimeUntilAge?: number | null          // 時短勤務終了年齢（この年齢になるまで時短）
    partTimeIncomeRatio?: number              // 時短中の収入比率（例: 0.7 = フル収入の70%）
}

export interface ChildEducationPaths {
    kindergarten: "public" | "private"   // 幼稚園 3-5歳
    elementary:   "public" | "private"   // 小学校 6-11歳
    juniorHigh:   "public" | "private"   // 中学校 12-14歳
    highSchool:   "public" | "private"   // 高校 15-17歳
    university:   "public" | "private"   // 大学 18-21歳
}

export const EDUCATION_PATHS_PRESETS: Record<"public" | "private" | "mixed", ChildEducationPaths> = {
    public:  { kindergarten: "public",  elementary: "public",  juniorHigh: "public",  highSchool: "public",  university: "public"  },
    private: { kindergarten: "private", elementary: "private", juniorHigh: "private", highSchool: "private", university: "private" },
    mixed:   { kindergarten: "public",  elementary: "public",  juniorHigh: "public",  highSchool: "private", university: "private" },
}

export interface Child {
    birthYear: number
    birthDate?: string              // 'YYYY-MM-DD' 形式（optional）
    educationPath: "public" | "private" | "mixed"
    educationPaths?: ChildEducationPaths  // ステージ別設定（設定時はこちらが優先）
    daycareAnnualCost?: number      // 0〜2歳の保育園年額（デフォルト: 360,000円）
}

export interface MortgageConfig {
    monthlyPayment: number   // 月次返済額（元利合計・円）
    endYear: number          // 完済年（西暦）
    // 詳細入力モード（任意）
    loanAmount?: number          // 借入額（円）
    interestRate?: number        // 現在の年利率（例: 0.005 = 0.5%）
    loanTermYears?: number       // 返済期間（年）
    loanStartYear?: number       // 借入開始年
    loanType?: "fixed" | "variable"
    variableRateForecast?: number  // 変動金利の将来想定年利（例: 0.02）
}

export interface NISAConfig {
    enabled: boolean
    annualContribution: number
    balance?: number              // 現在のNISA評価額（デフォルト: 0）
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
    emptyNestActive?: number        // 子なし〜64歳: デフォルト 2,581,000
    emptyNestSenior?: number        // 65〜74歳: デフォルト 2,243,000
    emptyNestElderly?: number       // 75歳〜: デフォルト 1,931,000
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
    otherAssets?: number            // その他資産（定期預金・外貨預金・金など）
    otherAssetsReturn?: number      // その他資産の期待リターン（デフォルト2%）
    monthlyExpenses: number
    expenseGrowthRate: number

    // Investment settings
    investmentReturn: number
    investmentVolatility: number

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

    // 住居
    monthlyRent?: number        // 賃貸の場合の月額家賃（持ち家の場合は0またはundefined）
    rentToPurchaseYear?: number  // 賃貸→持ち家への切り替え年（将来購入モード）
    purchaseDownPayment?: number // 購入時の頭金（切り替え年に一括計上）

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

    // 住宅メンテナンス費用（周期型）
    maintenanceCosts?: MaintenanceCost[]

    // 固定資産税（年額）
    propertyTaxAnnual?: number

    // Withdrawal strategy (Phase 7)
    withdrawalStrategy?: WithdrawalStrategy   // デフォルト: 'fixed'
    guardrailConfig?: GuardrailConfig         // guardrail 選択時に使用

    // MC return model (Phase 9)
    mcReturnModel?: MCReturnModel             // デフォルト: 'normal'
    meanReversionConfig?: MeanReversionConfig
    bootstrapConfig?: BootstrapConfig
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
    otherAssets: number       // その他資産（定期預金・外貨預金・金など）
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
    maintenanceCost: number            // 住宅メンテナンス費用（周期的大型出費）
    rentCost: number                   // 家賃または頭金（将来購入モードの購入年は頭金）
    propertyTax: number                // 固定資産税
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
    fireAchievementRate: number    // FIRE達成率（0.0〜1.0以上、year0 資産 / fireNumber）
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
    depletionAgeP10: number | null      // 下位10%シナリオの枯渇年齢
    depletionAgeP50: number | null      // 中央値シナリオの枯渇年齢
    successCountFormatted: string       // 例: "1000通りのうち800通りで90歳まで資産が持ちました"
    mcModel: MCReturnModel              // 使用したMCモデル
}

export interface AnnualTableRow {
    year: number
    age: number
    totalAssets: number
    grossIncome: number
    netIncome: number
    expenses: number
    netCashFlow: number
    isFireAchieved: boolean
    isSemiFire: boolean
    fireNumber: number
    housingCost: number   // 家賃 + ローン返済 + 固定資産税 + 大規模修繕費の合計
    childCosts: number
}

export interface CashFlowChartGroup {
    label: string     // 例: "35〜39歳"
    income: number    // 期間合計収入
    expenses: number  // 期間合計支出
    netCF: number     // 期間合計純CF
}

export function calculateFireAchievementRate(
    yearlyData: YearlyData[],
    fireNumber: number
): number {
    if (yearlyData.length === 0 || fireNumber <= 0) return 0
    const year0 = yearlyData[0]
    const totalCurrentAssets = year0.assets + year0.nisaAssets + year0.idecoAssets
    return totalCurrentAssets / fireNumber
}

export function formatAnnualTableData(yearlyData: YearlyData[]): AnnualTableRow[] {
    return yearlyData.map(data => ({
        year: data.year,
        age: data.age,
        totalAssets: data.assets + data.nisaAssets + data.idecoAssets + data.otherAssets,
        grossIncome: data.grossIncome,
        netIncome: data.income,
        expenses: data.expenses,
        netCashFlow: data.income - data.expenses,
        isFireAchieved: data.isFireAchieved,
        isSemiFire: data.isSemiFire,
        fireNumber: data.fireNumber,
        housingCost: data.rentCost + data.mortgageCost + data.propertyTax + data.maintenanceCost,
        childCosts: data.childCosts,
    }))
}

export function formatCashFlowChartData(
    yearlyData: YearlyData[],
    groupByYears: number = 5
): CashFlowChartGroup[] {
    const groups: CashFlowChartGroup[] = []
    for (let i = 0; i < yearlyData.length; i += groupByYears) {
        const group = yearlyData.slice(i, i + groupByYears)
        const startAge = group[0].age
        const endAge = group[group.length - 1].age
        groups.push({
            label: `${startAge}〜${endAge}歳`,
            income: group.reduce((sum, d) => sum + d.income, 0),
            expenses: group.reduce((sum, d) => sum + d.expenses, 0),
            netCF: group.reduce((sum, d) => sum + d.income - d.expenses, 0),
        })
    }
    return groups
}

export interface Scenario {
    name: string
    description: string
    changes: Omit<Partial<SimulationConfig>, 'person1' | 'person2' | 'nisa' | 'ideco'> & {
        person1?: Partial<Person>
        person2?: Partial<Person> | null
        nisa?: Partial<NISAConfig>
        ideco?: Partial<IDeCoConfig>
    }
    id?: string          // identifier (localStorage key)
    savedAt?: number     // save time (epoch ms)
}

export interface ScenarioComparisonResult {
    planA: SimulationResult
    planB: SimulationResult
    planAConfig: SimulationConfig
    planBConfig: SimulationConfig
    diffSummary: ScenarioDiffSummary
}

export interface ScenarioDiffSummary {
    fireAgeDiff: number | null       // B.fireAge - A.fireAge (negative = B fires earlier)
                                     // null if either plan doesn't fire
    finalAssetsDiff: number          // B.finalAssets - A.finalAssets
    fireAchievementRateDiff: number  // B.achievementRate - A.achievementRate
    planAFiresOnly: boolean          // Only plan A fires within simulationYears
    planBFiresOnly: boolean          // Only plan B fires within simulationYears
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
    otherAssets: 0,                 // その他資産（定期預金・外貨預金・金など）
    otherAssetsReturn: 0.02,        // 2%/年
    monthlyExpenses: 350000, // 35万円/月
    expenseGrowthRate: 0.01, // 1%/年

    // Investment settings
    investmentReturn: 0.05, // 5%/年
    investmentVolatility: 0.15, // 15%

    // Primary person
    person1: {
        currentAge: 35,
        retirementAge: 50,
        grossIncome: 7000000, // 税引き前年収700万円/年
        incomeGrowthRate: 0.02, // 2%/年
        pensionStartAge: 65,
        pensionAmount: 1500000, // 150万円/年
        employmentType: 'employee',
        birthMonth: undefined,
    },

    // Spouse (null = no spouse)
    person2: {
        currentAge: 33,
        retirementAge: 50,
        grossIncome: 5000000, // 税引き前年収500万円/年
        incomeGrowthRate: 0.02, // 2%/年
        pensionStartAge: 65,
        pensionAmount: 1200000, // 120万円/年
        employmentType: 'employee',
        birthMonth: undefined,
        maternityLeaveConfig: [
            {
                childBirthDate: '2022-07',  // 産休・育休を取る子の出生年月
                prenatalWeeks: 6,
                postnatalWeeks: 8,
                childcareMonths: 10,
            }
        ],
        partTimeUntilAge: 38,
        partTimeIncomeRatio: 0.7,
    },

    // NISA
    nisa: {
        enabled: true,
        annualContribution: 1200000, // 120万円/年
        annualLimit: 3_600_000,
        lifetimeLimit: 18_000_000,
        totalContributed: 0,
        balance: 0,
    },

    // iDeCo
    ideco: {
        enabled: true,
        monthlyContribution: 23000, // 2.3万円/月
        withdrawalStartAge: 60,
    },

    // Children
    children: [
        {
            birthYear: 2022,
            educationPath: "public" as const,
            educationPaths: {
                kindergarten: "public", elementary: "public", juniorHigh: "public",
                highSchool: "public", university: "public",
            },
            daycareAnnualCost: 360_000,
        }
    ],
    mortgage: null,
    childAllowanceEnabled: true,

    // 住居
    monthlyRent: 0,
    rentToPurchaseYear: undefined,
    purchaseDownPayment: undefined,

    // 固定資産税
    propertyTaxAnnual: 0,

    // Simulation settings
    simulationYears: 50,
    inflationRate: 0.01, // 1%

    // Lifecycle expense mode
    expenseMode: 'fixed',

    // Semi-FIRE / Post-FIRE income
    postFireIncome: null,

    // Withdrawal strategy (Phase 7)
    withdrawalStrategy: 'fixed',
    mcReturnModel: 'normal',
    guardrailConfig: {
        threshold1: -0.10,
        reduction1: 0.40,
        threshold2: -0.20,
        reduction2: 0.80,
        threshold3: -0.35,
        reduction3: 0.95,
        discretionaryRatio: 0.30,
        useLifecycleDiscretionary: true,  // ライフステージ別裁量支出比率（家計調査ベース）
    },

    // 住宅メンテナンス費用（周期型・任意）
    maintenanceCosts: [],

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

// 文部科学省「子供の学習費調査」令和3年度データ準拠
// 大学は国公立・私立の学納金（授業料等）のみ。生活費は基本生活費に含まれる。
const EDUCATION_COSTS: Record<"public" | "private" | "mixed", number[]> = {
    // Annual costs by age (3-21歳)
    public: [
        // 幼稚園 (3-5): 222,264円/年→無償化後実費 約220,000円
        220000, 220000, 220000,
        // 小学校 (6-11): 321,281円/年
        320000, 320000, 320000, 320000, 320000, 320000,
        // 中学校 (12-14): 488,397円/年
        490000, 490000, 490000,
        // 高校 (15-17): 457,380円/年
        460000, 460000, 460000,
        // 大学 国公立 (18-21): 授業料535,800円+入学金282,000円÷4年≒606,300→年約540,000円
        540000, 540000, 540000, 540000,
    ],
    private: [
        // 幼稚園 (3-5): 527,916円/年
        530000, 530000, 530000,
        // 小学校 (6-11): 1,592,985円/年
        1600000, 1600000, 1600000, 1600000, 1600000, 1600000,
        // 中学校 (12-14): 1,406,433円/年
        1400000, 1400000, 1400000,
        // 高校 (15-17): 969,911円/年→100万
        1000000, 1000000, 1000000,
        // 大学 私立文系 (18-21): 授業料約800,000円+入学金250,000円÷4年≒1,062,500→年約1,300,000円
        1300000, 1300000, 1300000, 1300000,
    ],
    mixed: [
        // 幼稚園: 公立 (3-5)
        220000, 220000, 220000,
        // 小学校: 公立 (6-11)
        320000, 320000, 320000, 320000, 320000, 320000,
        // 中学校: 公立 (12-14)
        490000, 490000, 490000,
        // 高校: 私立 (15-17)
        1000000, 1000000, 1000000,
        // 大学: 私立 (18-21)
        1300000, 1300000, 1300000, 1300000,
    ],
}

function calculateMaintenanceCost(
    costs: MaintenanceCost[] | undefined,
    currentSimYear: number
): number {
    if (!costs || costs.length === 0) return 0
    let total = 0
    for (const cost of costs) {
        if (currentSimYear < cost.firstYear) continue
        const yearsSinceFirst = currentSimYear - cost.firstYear
        if (yearsSinceFirst % cost.intervalYears === 0) {
            total += cost.amount
        }
    }
    return total
}

// 元利均等返済の月次返済額を計算
export function calcMortgageMonthlyPayment(principal: number, annualRate: number, termYears: number): number {
    if (termYears <= 0 || principal <= 0) return 0
    if (annualRate === 0) return principal / (termYears * 12)
    const r = annualRate / 12
    const n = termYears * 12
    return principal * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1)
}

function calcRemainingBalance(principal: number, annualRate: number, termYears: number, elapsedMonths: number): number {
    const monthly = calcMortgageMonthlyPayment(principal, annualRate, termYears)
    if (annualRate === 0) return Math.max(0, principal - monthly * elapsedMonths)
    const r = annualRate / 12
    return Math.max(0, principal * Math.pow(1 + r, elapsedMonths) - monthly * (Math.pow(1 + r, elapsedMonths) - 1) / r)
}

function calculateMortgageCost(
    mortgage: MortgageConfig | null,
    currentSimYear: number
): number {
    if (mortgage === null) return 0
    if (currentSimYear > mortgage.endYear) return 0

    // 変動金利: 借入5年後の金利見直し時点でもう一度計算
    if (
        mortgage.loanType === "variable" &&
        mortgage.variableRateForecast !== undefined &&
        mortgage.loanAmount !== undefined &&
        mortgage.interestRate !== undefined &&
        mortgage.loanStartYear !== undefined &&
        mortgage.loanTermYears !== undefined
    ) {
        const reviewYear = mortgage.loanStartYear + 5
        if (currentSimYear >= reviewYear) {
            const elapsedMonths = (reviewYear - mortgage.loanStartYear) * 12
            const remaining = calcRemainingBalance(
                mortgage.loanAmount, mortgage.interestRate, mortgage.loanTermYears, elapsedMonths
            )
            const remainingTermYears = mortgage.loanTermYears - 5
            if (remaining > 0 && remainingTermYears > 0) {
                const newMonthly = calcMortgageMonthlyPayment(remaining, mortgage.variableRateForecast, remainingTermYears)
                return newMonthly * 12
            }
        }
    }

    return mortgage.monthlyPayment * 12
}

// 2024年10月改正後の児童手当
// 所得制限撤廃・高校生（18歳）まで延長・第3子以降30,000円/月に増額
// 第3子カウントは22歳未満の子を全員含む（大学生も上の子としてカウント）
function calculateChildAllowance(children: Child[], currentSimYear: number): number {
    if (children.length === 0) return 0
    // 子どもを年齢順（誕生年の古い順）にソート
    const sorted = [...children].sort((a, b) => a.birthYear - b.birthYear)
    let total = 0
    for (const child of sorted) {
        const childAge = currentSimYear - child.birthYear
        if (childAge < 0 || childAge >= 18) continue
        // 第3子かどうか: 自分より年上で22歳未満の子の数を数える
        const olderUnder22 = sorted.filter(c => c.birthYear < child.birthYear && (currentSimYear - c.birthYear) < 22).length
        const isThirdOrLater = olderUnder22 >= 2
        if (isThirdOrLater) {
            // 第3子以降: 全年齢 30,000円/月
            total += 30_000 * 12
        } else if (childAge < 3) {
            // 第1・2子, 0〜2歳: 15,000円/月（2024年改正: 第1子・第2子は同額）
            total += 15_000 * 12
        } else {
            // 第1・2子, 3〜17歳: 10,000円/月
            total += 10_000 * 12
        }
    }
    return total
}

function calculateChildCosts(children: Child[], year: number, inflationRate: number, baseYear: number): number {
    let totalCost = 0
    const yearsFromBase = year - baseYear
    const inflationMultiplier = Math.pow(1 + inflationRate, yearsFromBase)

    for (const child of children) {
        const childAge = year - child.birthYear

        // 0〜2歳: 保育園費用（認可保育園は所得連動のためインフレ調整なし）
        if (childAge >= 0 && childAge <= 2) {
            totalCost += child.daycareAnnualCost ?? 360_000
        }

        // 3〜21歳: 学校教育費（文科省データ準拠）
        if (childAge >= 3 && childAge <= 21) {
            const costIndex = childAge - 3
            let baseCost: number
            if (child.educationPaths) {
                // ステージ別設定が優先
                const ep = child.educationPaths
                const stageKey: "public" | "private" =
                    childAge <= 5  ? ep.kindergarten :
                    childAge <= 11 ? ep.elementary :
                    childAge <= 14 ? ep.juniorHigh :
                    childAge <= 17 ? ep.highSchool :
                    ep.university
                baseCost = EDUCATION_COSTS[stageKey][costIndex] || 0
            } else {
                baseCost = EDUCATION_COSTS[child.educationPath][costIndex] || 0
            }
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

    // Working income with growth (homemaker has no earned income)
    if ((person.employmentType ?? 'employee') === 'homemaker') return 0
    const yearsWorked = age - person.currentAge
    const growthMultiplier = Math.pow(1 + person.incomeGrowthRate, yearsWorked)
    const gross = person.grossIncome ?? person.currentIncome ?? 0
    return gross * growthMultiplier
}

// ----------------------------------------------------------------------------
// Maternity / Parental Leave Income Calculator
// ----------------------------------------------------------------------------

// ----------------------------------------------------------------------------
// Maternity / Parental Leave - Month-precision calculation
// ----------------------------------------------------------------------------

/**
 * 指定した暦年の中で、特定の期間に含まれる月数を数える
 * @param simYear 対象年（西暦）
 * @param birthYear 出生年
 * @param birthMonth 出生月（1-12）
 * @param startMonthOffset 期間開始（出生月を0とした月オフセット、産前は負値）
 * @param endMonthOffset 期間終了（出生月を0とした月オフセット、以上未満）
 */
function countLeaveMonthsInYear(
    simYear: number,
    birthYear: number,
    birthMonth: number,
    startMonthOffset: number,
    endMonthOffset: number
): number {
    let count = 0
    for (let m = 1; m <= 12; m++) {
        // 各月の中旬（0.5）を基準に判定
        const monthsFromBirth = (simYear - birthYear) * 12 + (m - birthMonth) + 0.5
        if (monthsFromBirth >= startMonthOffset && monthsFromBirth < endMonthOffset) {
            count++
        }
    }
    return count
}

/**
 * 産休・育休対象年かどうか判定する（後方互換用 + maternityLeaveConfig 両対応）
 * maternityLeaveConfig が設定されていれば true/false を返す（詳細計算は別関数）
 */
function getMaternityLeaveStatus(
    person: Person,
    currentSimYear: number
): boolean {
    // 新設定（月単位精度）
    if (person.maternityLeaveConfig && person.maternityLeaveConfig.length > 0) {
        for (const entry of person.maternityLeaveConfig) {
            const [birthYear, birthMonth] = entry.childBirthDate.split('-').map(Number)
            const prenatalWeeks = entry.prenatalWeeks ?? 6
            const postnatalWeeks = entry.postnatalWeeks ?? 8
            const childcareMonths = entry.childcareMonths ?? 10
            const prenatalMonths = prenatalWeeks * 7 / 30.44
            const postnatalMonths = postnatalWeeks * 7 / 30.44
            const leaveEnd = postnatalMonths + childcareMonths

            // 産前〜育休終了の期間に currentSimYear の月が1つでも含まれれば対象年
            const months = countLeaveMonthsInYear(currentSimYear, birthYear, birthMonth, -prenatalMonths, leaveEnd)
            if (months > 0) return true
        }
        return false
    }
    // 後方互換（年単位近似）
    if (person.maternityLeaveChildBirthYears && person.maternityLeaveChildBirthYears.length > 0) {
        for (const by of person.maternityLeaveChildBirthYears) {
            if (currentSimYear === by || currentSimYear === by + 1) return true
        }
    }
    return false
}

/**
 * 産休・育休期間の年間収入を計算する（月単位精度）
 * 給付金月は非課税、就労月は課税対象として分離して返す。
 * @returns { leaveIncome: 給付金合計（非課税）, workGross: 就労月の総支給（課税対象） }
 */
function calculateMaternityLeaveIncomeForYear(
    person: Person,
    currentSimYear: number
): { leaveIncome: number; workGross: number } {
    const hasInsurance = person.employmentType === 'employee'
    const monthlyStandard = Math.min((person.grossIncome ?? 0) / 12, 635_000)
    const regularMonthlyGross = (person.grossIncome ?? 0) / 12

    type Phase = 'prenatalPostnatal' | 'half1' | 'half2' | 'work'
    const monthPhases = new Array(12).fill('work') as Phase[]

    // 後方互換: maternityLeaveChildBirthYears は年単位近似（月単位変換しない）
    if (!person.maternityLeaveConfig || person.maternityLeaveConfig.length === 0) {
        for (const by of (person.maternityLeaveChildBirthYears ?? [])) {
            if (currentSimYear === by) {
                // 出生年: 産前産後8週+育休前半(6ヶ月) = 8ヶ月 @ 2/3, 育休後半(4ヶ月) @ 50%
                const leaveIncomeLegacy = hasInsurance
                    ? monthlyStandard * (2 / 3) * 8 + monthlyStandard * 0.5 * 4
                    : 0
                return { leaveIncome: leaveIncomeLegacy, workGross: 0 }
            } else if (currentSimYear === by + 1) {
                // 翌年: 育休後半(8ヶ月) @ 50%, 残り4ヶ月は就労ゼロ（年単位近似）
                const leaveIncomeLegacy = hasInsurance ? monthlyStandard * 0.5 * 8 : 0
                return { leaveIncome: leaveIncomeLegacy, workGross: 0 }
            }
        }
        return { leaveIncome: 0, workGross: 0 }
    }

    const entries = person.maternityLeaveConfig

    for (const entry of entries) {
        const [birthYear, birthMonth] = entry.childBirthDate.split('-').map(Number)
        const prenatalMonths = (entry.prenatalWeeks ?? 6) * 7 / 30.44
        const postnatalMonths = (entry.postnatalWeeks ?? 8) * 7 / 30.44
        const half1End = postnatalMonths + Math.min(6, entry.childcareMonths ?? 10)
        const half2End = postnatalMonths + (entry.childcareMonths ?? 10)

        for (let m = 1; m <= 12; m++) {
            const mfb = (currentSimYear - birthYear) * 12 + (m - birthMonth) + 0.5
            if (mfb >= -prenatalMonths && mfb < postnatalMonths) {
                monthPhases[m - 1] = 'prenatalPostnatal'
            } else if (mfb >= postnatalMonths && mfb < half1End) {
                monthPhases[m - 1] = 'half1'
            } else if (mfb >= half1End && mfb < half2End) {
                monthPhases[m - 1] = 'half2'
            }
        }
    }

    let leaveIncome = 0
    let workGross = 0
    for (const phase of monthPhases) {
        if (phase === 'prenatalPostnatal') {
            leaveIncome += hasInsurance ? monthlyStandard * (2 / 3) : 0
        } else if (phase === 'half1') {
            leaveIncome += hasInsurance ? monthlyStandard * 0.67 : 0
        } else if (phase === 'half2') {
            leaveIncome += hasInsurance ? monthlyStandard * 0.50 : 0
        } else {
            workGross += regularMonthlyGross
        }
    }

    return { leaveIncome, workGross }
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

/**
 * 給与所得（給与所得控除後）を計算する
 * calculateTaxBreakdown と配偶者控除の両方から利用する共通ロジック
 */
function calculateEmploymentIncome(grossIncome: number, employmentType: EmploymentType): number {
    if (employmentType !== 'employee') return grossIncome  // 個人事業主・専業主婦はそのまま
    if (grossIncome <= 1_628_000) return Math.max(0, grossIncome - 550_000)
    if (grossIncome <= 1_800_000) return Math.max(0, grossIncome - Math.max(550_000, grossIncome * 0.4 - 100_000))
    if (grossIncome <= 3_600_000) return grossIncome - (grossIncome * 0.3 + 80_000)
    if (grossIncome <= 6_600_000) return grossIncome - (grossIncome * 0.2 + 440_000)
    if (grossIncome <= 8_500_000) return grossIncome - (grossIncome * 0.1 + 1_100_000)
    return grossIncome - 1_950_000
}

/**
 * 配偶者控除・配偶者特別控除額を計算する（2024年度）
 * @param ownEmploymentIncome 申告者の給与所得（給与所得控除後）
 * @param spouseEmploymentIncome 配偶者の給与所得（給与所得控除後）
 * @returns 控除額（円）
 */
function calculateSpouseDeduction(
    ownEmploymentIncome: number,
    spouseEmploymentIncome: number
): number {
    // 申告者の合計所得が1,000万超 → 控除なし
    if (ownEmploymentIncome > 10_000_000) return 0
    // 配偶者の合計所得が133万超 → 控除なし
    if (spouseEmploymentIncome > 1_330_000) return 0

    // 申告者の所得階層で控除逓減率を決定
    const ownTierMultiplier =
        ownEmploymentIncome <= 9_000_000 ? 1.0 :
        ownEmploymentIncome <= 9_500_000 ? 2/3 :
        1/3

    // 配偶者の合計所得 ≤ 480,000 → 配偶者控除（満額38万）
    if (spouseEmploymentIncome <= 480_000) {
        return Math.round(380_000 * ownTierMultiplier)
    }

    // 配偶者特別控除（48万超〜133万以下）: 国税庁テーブル準拠
    const baseDeduction =
        spouseEmploymentIncome <= 950_000  ? 380_000 :
        spouseEmploymentIncome <= 1_000_000 ? 360_000 :
        spouseEmploymentIncome <= 1_050_000 ? 310_000 :
        spouseEmploymentIncome <= 1_100_000 ? 260_000 :
        spouseEmploymentIncome <= 1_150_000 ? 210_000 :
        spouseEmploymentIncome <= 1_200_000 ? 160_000 :
        spouseEmploymentIncome <= 1_250_000 ? 110_000 :
        spouseEmploymentIncome <= 1_300_000 ?  60_000 :
        spouseEmploymentIncome <= 1_330_000 ?  30_000 :
        0
    return Math.round(baseDeduction * ownTierMultiplier)
}

export function calculateTaxBreakdown(
    grossIncome: number,
    employmentType: EmploymentType,
    age: number,
    spouseEmploymentIncome?: number   // 配偶者控除計算用（配偶者の給与所得）
): TaxBreakdown {
    // --- 給与所得（給与所得控除後）---
    const employmentIncome = Math.max(0, calculateEmploymentIncome(grossIncome, employmentType))

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
    const spouseDeduction = spouseEmploymentIncome !== undefined
        ? calculateSpouseDeduction(employmentIncome, spouseEmploymentIncome)
        : 0
    const taxableIncome = Math.max(0, employmentIncome - socialInsurance - basicDeduction - spouseDeduction)

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
    // 課税所得ゼロ（専業主婦・無職等）は均等割も含め非課税（申告不要で自治体が自動判定）
    const residentTax = taxableIncome > 0 ? taxableIncome * 0.10 + 5_000 : 0

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
        if (person1Age >= 75) {
            stage = 'emptyNestElderly'
            baseExpenses = config?.emptyNestElderly ?? 1_931_000
        } else if (person1Age >= 65) {
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
    // 固定値優先: null/undefined → pensionConfig で自動計算、0 → 年金なし固定、正数 → 固定額
    if (person.pensionAmount != null) {
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

/**
 * ライフステージ別の裁量支出比率（総務省家計調査2023年ベース）
 * 裁量支出 = 外食・被服・教養娯楽・旅行・美容・趣味等、暴落時に削減可能な支出
 */
const LIFECYCLE_DISCRETIONARY_RATIOS: Record<string, number> = {
    withPreschooler:      0.30,  // 未就学: 子育て期は外食・旅行が制限される
    withElementaryChild:  0.34,  // 小学生: 習い事・レジャーが増える
    withJuniorHighChild:  0.37,  // 中学生: 部活・塾が増えるが旅行も増加
    withHighSchoolChild:  0.39,  // 高校生: 旅行・外食が増える
    withCollegeChild:     0.40,  // 大学生: 旅行・趣味に充てやすくなる
    emptyNestActive:      0.42,  // 独立後〜64歳: 旅行・趣味が最大化
    emptyNestSenior:      0.35,  // 65〜74歳: 医療費増加で裁量比率が低下
    emptyNestElderly:     0.28,  // 75歳〜: 介護・医療費が大半を占める
    fixed:                0.32,  // 固定支出モード時のフォールバック
}

function getLifecycleDiscretionaryRatio(lifecycleStage: string | undefined): number {
    if (!lifecycleStage) return 0.32
    return LIFECYCLE_DISCRETIONARY_RATIOS[lifecycleStage] ?? 0.32
}

export function calculateWithdrawalAmount(
    strategy: WithdrawalStrategy,
    baseExpenses: number,
    totalAssets: number,
    peakAssets: number,
    safeWithdrawalRate: number,
    guardrailConfig?: GuardrailConfig,
    lifecycleStage?: string   // ライフステージ別裁量比率の算出に使用
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

        const effectiveDiscretionaryRatio = (guardrailConfig.useLifecycleDiscretionary ?? false)
            ? getLifecycleDiscretionaryRatio(lifecycleStage)
            : guardrailConfig.discretionaryRatio
        const essentialExpenses = baseExpenses * (1 - effectiveDiscretionaryRatio)
        const discretionaryExpenses = baseExpenses * effectiveDiscretionaryRatio
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
    let nisaAssets = config.nisa.balance ?? 0
    let idecoAssets = 0
    let otherAssets = config.otherAssets ?? 0
    let nisaTotalContributed = config.nisa.totalContributed ?? 0  // NISA累積拠出額追跡
    let fireAge: number | null = null
    let fireYear: number | null = null
    let capitalGainsLastYear = 0    // 前年の売却益
    let lastYearFireIncome = 0      // 前年の就労収入（FIRE後: セミFIRE収入, FIRE前: 給与収入）
    let peakAssets = initialCashAssets + initialStocks + (config.nisa.balance ?? 0) + otherAssets  // ピーク資産

    // Calculate FIRE number based on current expenses
    const annualExpenses = config.monthlyExpenses * 12
    const fireNumber = annualExpenses / INTERNAL_SWR

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
            if (config.person2) {
                // Person2 独自の退職年齢まで就労収入を継続計算（person1 の FIRE に左右されない）
                if (person2Age < config.person2.retirementAge) {
                    const p2Ratio = getPartTimeRatio(config.person2, person2Age)
                    const p2RawGross = calculateIncome(config.person2, person2Age, config.inflationRate, year) * p2Ratio
                    const p2Breakdown = calculateTaxBreakdown(p2RawGross, config.person2.employmentType ?? 'employee', person2Age)
                    p2Income = p2Breakdown.netIncome
                    p2Tax = p2Breakdown.totalTax
                    totalIncome += p2RawGross
                } else if (person2Age >= config.person2.pensionStartAge) {
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
            }

            totalNetIncome = semiFireNetIncome + p1Income + p2Income
            totalTaxAmount = semiFIRETax + p1Tax + p2Tax
        } else {
            isSemiFire = false
            semiFIREGross = 0
            // FIRE前: 就労収入（産休育休・時短勤務を考慮）

            // --- Step1: 各人の総支給額と「給与所得（控除後）」を先算出（配偶者控除の相互参照に使う）---
            const p1LeaveStatus = getMaternityLeaveStatus(config.person1, currentSimYear)
            const p1Ratio = getPartTimeRatio(config.person1, person1Age)
            // 産休育休中でも就労月の給与は課税対象 → 配偶者控除の判定に使う就労月分を取得
            const p1RawGross = p1LeaveStatus
                ? calculateMaternityLeaveIncomeForYear(config.person1, currentSimYear).workGross
                : calculateIncome(config.person1, person1Age, config.inflationRate, year) * p1Ratio
            const p1EmpIncome = calculateEmploymentIncome(p1RawGross, config.person1.employmentType ?? 'employee')

            let p2RawGross = 0
            let p2EmpIncome = 0
            if (config.person2) {
                const p2LeaveStatus = getMaternityLeaveStatus(config.person2, currentSimYear)
                const p2Ratio = getPartTimeRatio(config.person2, person2Age)
                p2RawGross = p2LeaveStatus
                    ? calculateMaternityLeaveIncomeForYear(config.person2, currentSimYear).workGross
                    : calculateIncome(config.person2, person2Age, config.inflationRate, year) * p2Ratio
                p2EmpIncome = calculateEmploymentIncome(p2RawGross, config.person2.employmentType ?? 'employee')
            }

            // --- Step2: 配偶者控除を反映してそれぞれ税計算 ---
            let p1Income: number
            let p1Tax: number
            if (p1LeaveStatus) {
                // 産休育休年: 就労月（課税）+ 給付金月（非課税）を分離して計算
                const { leaveIncome: p1Leave, workGross: p1WorkGross } =
                    calculateMaternityLeaveIncomeForYear(config.person1, currentSimYear)
                const p1WorkEmpIncome = calculateEmploymentIncome(p1WorkGross, config.person1.employmentType ?? 'employee')
                let p1WorkNet = p1WorkGross
                p1Tax = 0
                if (p1WorkGross > 0) {
                    const p1Bd = calculateTaxBreakdown(
                        p1WorkGross,
                        config.person1.employmentType ?? 'employee',
                        person1Age,
                        config.person2 ? p2EmpIncome : undefined
                    )
                    p1WorkNet = p1Bd.netIncome
                    p1Tax = p1Bd.totalTax
                }
                p1Income = p1WorkNet + p1Leave  // 手取り就労収入 + 非課税給付金
                totalIncome = p1WorkGross        // gross は課税分のみ記録
            } else {
                const p1Breakdown = calculateTaxBreakdown(
                    p1RawGross,
                    config.person1.employmentType ?? 'employee',
                    person1Age,
                    config.person2 ? p2EmpIncome : undefined  // 配偶者控除
                )
                p1Income = p1Breakdown.netIncome
                p1Tax = p1Breakdown.totalTax
                totalIncome = p1RawGross
            }

            let p2Income = 0
            let p2Tax = 0
            if (config.person2) {
                const p2LeaveStatus = getMaternityLeaveStatus(config.person2, currentSimYear)
                if (p2LeaveStatus) {
                    const { leaveIncome: p2Leave, workGross: p2WorkGross } =
                        calculateMaternityLeaveIncomeForYear(config.person2, currentSimYear)
                    let p2WorkNet = p2WorkGross
                    p2Tax = 0
                    if (p2WorkGross > 0) {
                        const p2Bd = calculateTaxBreakdown(
                            p2WorkGross,
                            config.person2.employmentType ?? 'employee',
                            person2Age,
                            p1EmpIncome
                        )
                        p2WorkNet = p2Bd.netIncome
                        p2Tax = p2Bd.totalTax
                    }
                    p2Income = p2WorkNet + p2Leave
                    totalIncome += p2WorkGross
                } else {
                    const p2Breakdown = calculateTaxBreakdown(
                        p2RawGross,
                        config.person2.employmentType ?? 'employee',
                        person2Age,
                        p1EmpIncome  // 配偶者控除
                    )
                    p2Income = p2Breakdown.netIncome
                    p2Tax = p2Breakdown.totalTax
                    totalIncome += p2RawGross
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
            : calculateChildCosts(config.children, currentSimYear, config.inflationRate, currentYear)

        // Calculate mortgage cost
        const mortgageCost = calculateMortgageCost(config.mortgage, currentSimYear)

        // Calculate maintenance cost (周期的大型出費)
        const maintenanceCost = calculateMaintenanceCost(config.maintenanceCosts, currentSimYear)

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
        const effectiveTotalAssets = cashAssets + stockAssets + nisaAssets + idecoAssets + otherAssets

        if (isPostFire) {
            // ピーク資産を更新
            peakAssets = Math.max(peakAssets, effectiveTotalAssets)

            const withdrawalResult = calculateWithdrawalAmount(
                config.withdrawalStrategy ?? 'fixed',
                baseExpenses,
                effectiveTotalAssets,
                peakAssets,
                INTERNAL_SWR,
                config.guardrailConfig,
                lifecycleStage
            )
            baseExpenses = withdrawalResult.actualExpenses
            drawdownFromPeak = withdrawalResult.drawdownFromPeak
            discretionaryReductionRate = withdrawalResult.discretionaryReductionRate
        }

        // Total expenses（FIRE後は社会保険料を上乗せ）
        // 将来購入モードの場合は購入年以降のみ固定資産税を課税
        const propertyTax = config.rentToPurchaseYear !== undefined
            ? (currentSimYear >= config.rentToPurchaseYear ? (config.propertyTaxAnnual ?? 0) : 0)
            : (config.propertyTaxAnnual ?? 0)
        let rentCost = 0
        if (config.rentToPurchaseYear !== undefined) {
            // 将来購入モード: 購入年より前は家賃、購入年に頭金を一括計上
            if (currentSimYear < config.rentToPurchaseYear) {
                rentCost = (config.monthlyRent ?? 0) * 12
            } else if (currentSimYear === config.rentToPurchaseYear) {
                rentCost = config.purchaseDownPayment ?? 0
            }
        } else {
            rentCost = (config.monthlyRent ?? 0) * 12
        }
        const totalExpenses = baseExpenses + childCosts + mortgageCost + maintenanceCost + postFireSI + propertyTax + rentCost

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
        const otherAssetsReturnRate = config.otherAssetsReturn ?? 0.02
        let newOtherAssets = otherAssets * (1 + otherAssetsReturnRate)
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
                // 税込みの gross 売却額を資産から控除し、手取りで shortfall を充当
                newStocks = withdrawal.remainingValue
                stocksCostBasis = withdrawal.remainingCostBasis
                shortfall = Math.max(0, shortfall - withdrawal.netProceeds)
            }

            // 現金から
            if (shortfall > 0) {
                newCash -= shortfall
                shortfall = 0
            }

            // その他資産から（現金も枯渇した場合）
            if (shortfall > 0 && newOtherAssets > 0) {
                const sellAmount = Math.min(shortfall, newOtherAssets)
                newOtherAssets -= sellAmount
                shortfall -= sellAmount
            }
        }

        cashAssets = Math.max(0, newCash)
        stockAssets = Math.max(0, newStocks)
        stocksCostBasis = Math.max(0, stocksCostBasis)
        nisaAssets = Math.max(0, newNisa)
        idecoAssets = Math.max(0, newIdeco)
        otherAssets = Math.max(0, newOtherAssets)

        // 後方互換: assets = cashAssets + stockAssets
        const totalLiquidAssets = cashAssets + stockAssets
        const totalAssets = totalLiquidAssets + nisaAssets + idecoAssets + otherAssets

        // Calculate current FIRE number (expenses grow over time)
        const currentFireNumber = totalExpenses / INTERNAL_SWR

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
            otherAssets: Math.max(0, otherAssets),
            grossIncome: totalIncome,
            totalTax,
            income: netIncomeWithAllowance,
            expenses: totalExpenses,
            savings,
            childCosts,
            mortgageCost,
            maintenanceCost,
            rentCost,
            propertyTax,
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
        if (data.assets + data.nisaAssets + data.idecoAssets + data.otherAssets <= 0) {
            depletionAge = data.age
            break
        }
    }

    const fireAchievementRate = calculateFireAchievementRate(yearlyData, fireNumber)

    return {
        yearlyData,
        fireAge,
        fireYear,
        fireNumber,
        finalAssets: finalData.assets + finalData.nisaAssets + finalData.idecoAssets + finalData.otherAssets,
        totalYears: config.simulationYears,
        pensionBreakdown: {
            person1: p1PensionBreakdown,
            person2: p2PensionBreakdown,
        },
        depletionAge,
        peakAssets,
        fireAchievementRate,
    }
}

// ----------------------------------------------------------------------------
// Historical Return Data
// ----------------------------------------------------------------------------

// S&P500の年次リターン（1970〜2024年の概算値, 50年分）
export const DEFAULT_SP500_RETURNS: number[] = [
    0.040, -0.146, 0.187, -0.145, -0.262,
    0.371, 0.238, -0.071, 0.065, 0.184,
    0.321, -0.049, 0.215, 0.223, 0.062,
    0.316, 0.185, 0.052, 0.166, 0.315,
    0.026, 0.076, 0.099, 0.013, 0.379,
    0.228, 0.333, 0.285, 0.210, -0.091,
    -0.119, -0.221, 0.287, 0.108, 0.048,
    0.158, 0.057, -0.370, 0.264, 0.152,
    0.021, 0.160, 0.323, 0.135, 0.014,
    0.119, 0.218, -0.044, 0.314, 0.245,
]

// ----------------------------------------------------------------------------
// Random Number Generation (Box-Muller Transform)
// ----------------------------------------------------------------------------

export function generateMeanReversionReturns(
    years: number,
    mean: number,
    volatility: number,
    speed: number
): number[] {
    const returns: number[] = []
    let prevReturn = mean  // 初期値: 期待値から開始

    for (let t = 0; t <= years; t++) {
        const u1 = Math.random() || Number.EPSILON
        const u2 = Math.random()
        const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
        const epsilon = volatility * z
        const r_t = mean + speed * (mean - prevReturn) + epsilon
        returns.push(r_t)
        prevReturn = r_t
    }

    return returns
}

export function generateBootstrapReturns(
    years: number,
    historicalReturns: number[],
    blockSize: number = 1
): number[] {
    const returns: number[] = []

    if (blockSize <= 1) {
        // 単純ブートストラップ
        for (let t = 0; t <= years; t++) {
            const idx = Math.floor(Math.random() * historicalReturns.length)
            returns.push(historicalReturns[idx])
        }
    } else {
        // ブロックブートストラップ
        while (returns.length <= years) {
            const maxStart = Math.max(1, historicalReturns.length - blockSize)
            const startIdx = Math.floor(Math.random() * maxStart)
            const block = historicalReturns.slice(startIdx, startIdx + blockSize)
            returns.push(...block)
        }
        returns.splice(years + 1)  // 必要な長さにトリム
    }

    return returns
}

function generateRandomReturns(years: number, config: SimulationConfig): number[] {
    const model = config.mcReturnModel ?? 'normal'

    if (model === 'meanReversion') {
        return generateMeanReversionReturns(
            years,
            config.investmentReturn,
            config.investmentVolatility,
            config.meanReversionConfig?.speed ?? 0.3
        )
    }

    if (model === 'bootstrap') {
        const historicalReturns = config.bootstrapConfig?.historicalReturns
        if (!historicalReturns || historicalReturns.length === 0) {
            // フォールバック: 正規分布
            return Array.from({ length: years + 1 }, () => {
                const u1 = Math.random() || Number.EPSILON
                const u2 = Math.random()
                const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
                return config.investmentReturn + config.investmentVolatility * z
            })
        }
        return generateBootstrapReturns(
            years,
            historicalReturns,
            config.bootstrapConfig?.blockSize ?? 1
        )
    }

    // 'normal' (デフォルト)
    return Array.from({ length: years + 1 }, () => {
        const u1 = Math.random() || Number.EPSILON
        const u2 = Math.random()
        const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
        return config.investmentReturn + config.investmentVolatility * z
    })
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
    const depletionAges: (number | null)[] = []

    // Initialize arrays for each year
    for (let year = 0; year <= config.simulationYears; year++) {
        yearlyAssets[year] = []
    }

    // Run simulations
    for (let i = 0; i < iterations; i++) {
        const randomReturns = generateRandomReturns(
            config.simulationYears,
            config
        )

        const result = runSingleSimulation(config, randomReturns)
        fireAges.push(result.fireAge)
        depletionAges.push(result.depletionAge)

        // Collect yearly assets
        result.yearlyData.forEach((data, year) => {
            yearlyAssets[year].push(data.assets + data.nisaAssets + data.idecoAssets + data.otherAssets)
        })
    }


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

    // Calculate depletion age percentiles
    const sortedDepletionAges = depletionAges
        .filter((a): a is number => a !== null)
        .sort((a, b) => a - b)

    const depletionAgeP10 = sortedDepletionAges.length > 0
        ? sortedDepletionAges[Math.floor(sortedDepletionAges.length * 0.10)]
        : null
    const depletionAgeP50 = sortedDepletionAges.length > 0
        ? sortedDepletionAges[Math.floor(sortedDepletionAges.length * 0.50)]
        : null

    // 成功率: シミュレーション期間（100歳まで）資産が枯渇しない確率
    const targetAge = config.person1.currentAge + config.simulationYears
    const successCount = depletionAges.filter(a => a === null || a > targetAge).length
    const mcSuccessRate = successCount / iterations
    const successCountFormatted = `${iterations}通りのうち${successCount}通りで${targetAge}歳まで資産が持ちました`

    return {
        medianFireAge,
        percentile10,
        percentile90,
        successRate: mcSuccessRate,
        yearlyPercentiles,
        depletionAgeP10,
        depletionAgeP50,
        successCountFormatted,
        mcModel: config.mcReturnModel ?? 'normal',
    }
}

// ----------------------------------------------------------------------------
// Scenario Generator
// ----------------------------------------------------------------------------

export function generateScenarios(baseConfig: SimulationConfig): Scenario[] {
    const scenarios: Scenario[] = []

    // Scenario 1: Retire 5 years earlier
    const p1EarlyRetirement = Math.max(baseConfig.person1.currentAge + 1, baseConfig.person1.retirementAge - 5)
    const p2EarlyRetirement = baseConfig.person2
        ? Math.max(baseConfig.person2.currentAge + 1, baseConfig.person2.retirementAge - 5)
        : undefined
    scenarios.push({
        name: "FIRE目標を5年早める",
        description: "退職年齢を5年前倒しにした場合のFIRE成功確率への影響",
        changes: {
            person1: {
                retirementAge: p1EarlyRetirement,
            },
            ...(baseConfig.person2 && p2EarlyRetirement !== undefined
                ? { person2: { retirementAge: p2EarlyRetirement } }
                : {}),
        },
    })

    // Scenario 2: Reduce monthly expenses by 30,000 yen
    scenarios.push({
        name: "支出を月3万円削減",
        description: "毎月の生活費を3万円削減した場合（外食・娯楽費の見直し）",
        changes: {
            monthlyExpenses: Math.max(0, baseConfig.monthlyExpenses - 30000),
        },
    })

    // Scenario 3: Max out NISA contribution (3.6M/year)
    scenarios.push({
        name: "NISAを上限まで投資",
        description: "NISAの年間上限（360万円）まで投資額を増やした場合",
        changes: {
            nisa: {
                enabled: true,
                annualContribution: 3_600_000,
            },
        },
    })

    // Scenario 4: Side hustle / career growth (pre-FIRE income boost via growth rate)
    scenarios.push({
        name: "副業で月10万円追加",
        description: "FIREまでの期間、副業・フリーランスで月10万円の収入を追加した場合",
        changes: {
            person1: {
                grossIncome: (baseConfig.person1.grossIncome ?? baseConfig.person1.currentIncome ?? 0) + 1_200_000,
            },
        },
    })

    return scenarios
}

// ----------------------------------------------------------------------------
// Scenario Comparison (Phase 10)
// ----------------------------------------------------------------------------

function getDefaultPerson2(): Person {
    return {
        currentAge: 33,
        retirementAge: 65,
        grossIncome: 5000000,
        incomeGrowthRate: 0.02,
        pensionStartAge: 65,
        pensionAmount: 1200000,
        employmentType: 'employee',
    }
}

export function runScenarioComparison(
    planAConfig: SimulationConfig,
    planBConfig: SimulationConfig
): ScenarioComparisonResult {
    const planA = runSingleSimulation(planAConfig)
    const planB = runSingleSimulation(planBConfig)

    const fireAgeDiff = (planB.fireAge !== null && planA.fireAge !== null)
        ? planB.fireAge - planA.fireAge
        : null

    const planAFiresOnly = planA.fireAge !== null && planB.fireAge === null
    const planBFiresOnly = planB.fireAge !== null && planA.fireAge === null

    return {
        planA,
        planB,
        planAConfig,
        planBConfig,
        diffSummary: {
            fireAgeDiff,
            finalAssetsDiff: planB.finalAssets - planA.finalAssets,
            fireAchievementRateDiff: planB.fireAchievementRate - planA.fireAchievementRate,
            planAFiresOnly,
            planBFiresOnly,
        },
    }
}

export function applyScenarioChanges(
    baseConfig: SimulationConfig,
    scenario: Scenario
): SimulationConfig {
    const changes = scenario.changes
    return {
        ...baseConfig,
        ...Object.fromEntries(
            Object.entries(changes).filter(([key]) =>
                !['person1', 'person2', 'nisa', 'ideco'].includes(key)
            )
        ),
        person1: changes.person1
            ? { ...baseConfig.person1, ...changes.person1 }
            : baseConfig.person1,
        person2: changes.person2 !== undefined
            ? (changes.person2 === null
                ? null
                : { ...(baseConfig.person2 ?? getDefaultPerson2()), ...changes.person2 })
            : baseConfig.person2,
        nisa: changes.nisa ? { ...baseConfig.nisa, ...changes.nisa } : baseConfig.nisa,
        ideco: changes.ideco ? { ...baseConfig.ideco, ...changes.ideco } : baseConfig.ideco,
    }
}
