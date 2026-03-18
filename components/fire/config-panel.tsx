"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip"
import { SimulationConfig, Person, EmploymentType, WithdrawalStrategy, MCReturnModel, PostFireIncomeConfig, LifecycleExpenseConfig } from "@/lib/simulator"
import { formatCurrency, cn } from "@/lib/utils"
import { User, Users, Wallet, TrendingUp, Baby, PiggyBank, Settings2, HelpCircle } from "lucide-react"

interface ConfigPanelProps {
  config: SimulationConfig
  onConfigChange: (config: SimulationConfig) => void
  useMonteCarlo: boolean
  onMonteCarloChange: (value: boolean) => void
}

function FieldLabel({ label, tooltip, className }: { label: string; tooltip: string; className?: string }) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className={cn("flex items-center gap-1 cursor-default", className)}>
            <span className="text-sm font-medium">{label}</span>
            <span className="inline-flex p-2.5 -m-2.5">
              <HelpCircle className="h-4 w-4 text-muted-foreground/60 shrink-0" />
            </span>
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-[240px] text-xs leading-relaxed">
          {tooltip}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

function PersonConfig({
  person,
  label,
  onChange,
  childBirthYears,
}: {
  person: Person
  label: string
  onChange: (person: Person) => void
  childBirthYears?: number[]
}) {
  const isHomemaker = person.employmentType === 'homemaker'

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <FieldLabel label="現在の年齢" tooltip="シミュレーション開始時点の年齢" />
          <span className="text-sm font-mono text-muted-foreground">{person.currentAge}歳</span>
        </div>
        <Slider
          value={[person.currentAge]}
          onValueChange={([value]) => onChange({ ...person, currentAge: value })}
          min={20}
          max={60}
          step={1}
        />
      </div>

      {!isHomemaker && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <FieldLabel label="年収" tooltip="税引き前の年間収入（額面）。給与所得控除・社会保険料・所得税・住民税を自動計算します" />
            <span className="text-sm font-mono text-muted-foreground">{formatCurrency(person.grossIncome, true)}</span>
          </div>
          <Slider
            value={[person.grossIncome]}
            onValueChange={([value]) => onChange({ ...person, grossIncome: value })}
            min={2000000}
            max={20000000}
            step={100000}
          />
        </div>
      )}

      {!isHomemaker && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <FieldLabel label="年収上昇率" tooltip="毎年の年収上昇率の見込み（昇給・昇進など）。0%なら現状維持" />
            <span className="text-sm font-mono text-muted-foreground">{(person.incomeGrowthRate * 100).toFixed(1)}%</span>
          </div>
          <Slider
            value={[person.incomeGrowthRate * 100]}
            onValueChange={([value]) => onChange({ ...person, incomeGrowthRate: value / 100 })}
            min={0}
            max={5}
            step={0.1}
          />
        </div>
      )}

      {isHomemaker && (
        <p className="text-xs text-muted-foreground">専業主婦/夫は年収・社会保険料なし（国民年金第3号）</p>
      )}

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <FieldLabel label="退職年齢" tooltip="FIREまたは定年退職する年齢。この年齢を迎えると給与収入がゼロになります" />
          <span className="text-sm font-mono text-muted-foreground">{person.retirementAge}歳</span>
        </div>
        <Slider
          value={[person.retirementAge]}
          onValueChange={([value]) => onChange({ ...person, retirementAge: value })}
          min={50}
          max={70}
          step={1}
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <FieldLabel label="年金受給額（年間）" tooltip="65歳以降に受け取る公的年金の年額。ねんきんネットやねんきん定期便で確認できます" />
          <span className="text-sm font-mono text-muted-foreground">{formatCurrency(person.pensionAmount ?? 0, true)}</span>
        </div>
        <Slider
          value={[person.pensionAmount ?? 0]}
          onValueChange={([value]) => onChange({ ...person, pensionAmount: value })}
          min={0}
          max={3000000}
          step={50000}
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <FieldLabel label="年金受給開始年齢" tooltip="年金の受け取りを始める年齢。繰り下げると月0.7%増額（最大75歳で84%増）。繰り上げると減額されます" />
          <span className="text-sm font-mono text-muted-foreground">{person.pensionStartAge}歳</span>
        </div>
        <Slider
          value={[person.pensionStartAge]}
          onValueChange={([value]) => onChange({ ...person, pensionStartAge: value })}
          min={60}
          max={75}
          step={1}
        />
      </div>

      <div className="space-y-2">
        <FieldLabel label="雇用形態" tooltip="会社員: 厚生年金・健康保険に加入。自営業: 国民年金・国民健康保険。専業主婦/夫: 配偶者の扶養に入り、年金は第3号被保険者として保険料負担なしで受給資格あり" />
        <select
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
          value={person.employmentType ?? 'employee'}
          onChange={e => onChange({ ...person, employmentType: e.target.value as EmploymentType })}
        >
          <option value="employee">会社員</option>
          <option value="selfEmployed">自営業・フリーランス</option>
          <option value="homemaker">専業主婦/夫</option>
        </select>
      </div>

      {(person.employmentType ?? 'employee') === 'employee' && (
        <div className="space-y-3 rounded-lg bg-muted/50 p-3">
          <div className="flex items-center justify-between">
            <FieldLabel label="時短勤務" tooltip="育休後などに時短勤務する場合に設定。指定した年齢まで収入比率を適用します" />
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                {person.partTimeUntilAge != null ? '設定あり' : '設定なし'}
              </span>
              <Switch
                id={`parttime-${label}`}
                checked={person.partTimeUntilAge != null}
                onCheckedChange={(checked) =>
                  onChange({
                    ...person,
                    partTimeUntilAge: checked ? 40 : null,
                    partTimeIncomeRatio: checked ? (person.partTimeIncomeRatio ?? 0.8) : undefined,
                  })
                }
              />
            </div>
          </div>
          {person.partTimeUntilAge != null && (
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <FieldLabel label="時短終了年齢" tooltip="時短勤務を終了してフルタイムに戻る年齢" className="text-xs" />
                  <span className="text-xs font-mono text-muted-foreground">{person.partTimeUntilAge}歳まで</span>
                </div>
                <Slider
                  value={[person.partTimeUntilAge]}
                  onValueChange={([value]) => onChange({ ...person, partTimeUntilAge: value })}
                  min={person.currentAge + 1}
                  max={person.retirementAge}
                  step={1}
                />
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <FieldLabel label="時短中の収入比率" tooltip="フルタイム年収に対する時短期間中の収入の割合（例: 80%なら年収が80%になる）" className="text-xs" />
                  <span className="text-xs font-mono text-muted-foreground">{((person.partTimeIncomeRatio ?? 0.8) * 100).toFixed(0)}%</span>
                </div>
                <Slider
                  value={[(person.partTimeIncomeRatio ?? 0.8) * 100]}
                  onValueChange={([value]) => onChange({ ...person, partTimeIncomeRatio: value / 100 })}
                  min={50}
                  max={100}
                  step={5}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {childBirthYears && childBirthYears.length > 0 && (
        <div className="space-y-2">
          <FieldLabel label="産休・育休取得" tooltip="取得した年は給与の代わりに育児休業給付金が支給されます（非課税）。産休2ヶ月＋育休1年として年単位で計算します" />
          <p className="text-xs text-muted-foreground">取得する子どもを選択</p>
          {childBirthYears.map((birthYear, index) => {
            const checked = (person.maternityLeaveChildBirthYears ?? []).includes(birthYear)
            return (
              <div key={birthYear} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id={`maternity-${label}-${birthYear}`}
                  checked={checked}
                  onChange={(e) => {
                    const current = person.maternityLeaveChildBirthYears ?? []
                    const updated = e.target.checked
                      ? [...current, birthYear]
                      : current.filter(y => y !== birthYear)
                    onChange({ ...person, maternityLeaveChildBirthYears: updated })
                  }}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <label htmlFor={`maternity-${label}-${birthYear}`} className="text-sm">
                  子ども{index + 1}（{birthYear}年生まれ）
                </label>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function ConfigPanel({ config, onConfigChange, useMonteCarlo, onMonteCarloChange }: ConfigPanelProps) {
  const [showAssetDetail, setShowAssetDetail] = useState(false)

  const defaultGuardrail = {
    threshold1: -0.10, reduction1: 0.40,
    threshold2: -0.20, reduction2: 0.80,
    threshold3: -0.35, reduction3: 0.95,
    discretionaryRatio: 0.30,
  }

  const updatePerson1 = (person: Person) => {
    onConfigChange({ ...config, person1: person })
  }

  const updatePerson2 = (person: Person) => {
    onConfigChange({ ...config, person2: person })
  }

  const togglePerson2 = (enabled: boolean) => {
    if (enabled) {
      onConfigChange({
        ...config,
        person2: {
          currentAge: 33,
          retirementAge: 65,
          grossIncome: 5000000,
          incomeGrowthRate: 0.02,
          pensionStartAge: 65,
          pensionAmount: 1200000,
          employmentType: 'employee',
        },
      })
    } else {
      onConfigChange({ ...config, person2: null })
    }
  }

  return (
    <Tabs defaultValue="basic" className="w-full">
      <TabsList className="grid w-full grid-cols-5">
        <TabsTrigger value="basic" className="flex items-center gap-1.5 text-xs">
          <Wallet className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">基本</span>
        </TabsTrigger>
        <TabsTrigger value="income" className="flex items-center gap-1.5 text-xs">
          <Users className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">収入</span>
        </TabsTrigger>
        <TabsTrigger value="investment" className="flex items-center gap-1.5 text-xs">
          <TrendingUp className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">投資</span>
        </TabsTrigger>
        <TabsTrigger value="life" className="flex items-center gap-1.5 text-xs">
          <Baby className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">ライフ</span>
        </TabsTrigger>
        <TabsTrigger value="advanced" className="flex items-center gap-1.5 text-xs">
          <Settings2 className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">詳細</span>
        </TabsTrigger>
      </TabsList>

      <TabsContent value="basic" className="mt-4 space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">基本設定</CardTitle>
            <CardDescription>現在の資産状況と生活費を設定</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {!showAssetDetail ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <FieldLabel label="現在の資産（現金＋株式）" tooltip="現在保有する資産の合計。NISAは別途設定します。詳細入力で現金・株式を分けると売却時の譲渡税をより正確に計算できます" />
                  <span className="text-sm font-mono text-muted-foreground">{formatCurrency((config.cashAssets ?? 0) + (config.stocks ?? config.currentAssets ?? 0), true)}</span>
                </div>
                <Slider
                  value={[(config.cashAssets ?? 0) + (config.stocks ?? config.currentAssets ?? 0)]}
                  onValueChange={([value]) => onConfigChange({ ...config, cashAssets: 0, stocks: value, stocksCostBasis: value })}
                  min={0}
                  max={100000000}
                  step={1000000}
                />
                <button
                  onClick={() => setShowAssetDetail(true)}
                  className="text-xs text-muted-foreground underline underline-offset-2"
                >
                  詳細入力（現金/株式を分けて入力）
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="現金・預金" tooltip="普通預金・定期預金など。株と異なり投資リターンは発生しません" />
                    <span className="text-sm font-mono text-muted-foreground">{formatCurrency(config.cashAssets ?? 0, true)}</span>
                  </div>
                  <Slider
                    value={[config.cashAssets ?? 0]}
                    onValueChange={([value]) => onConfigChange({ ...config, cashAssets: value })}
                    min={0}
                    max={50000000}
                    step={500000}
                  />
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="株式評価額（課税口座）" tooltip="課税口座（特定口座等）の株式・投資信託の現在の評価額" />
                    <span className="text-sm font-mono text-muted-foreground">{formatCurrency(config.stocks ?? 0, true)}</span>
                  </div>
                  <Slider
                    value={[config.stocks ?? 0]}
                    onValueChange={([newStocksValue]) => onConfigChange({
                      ...config,
                      stocks: newStocksValue,
                      stocksCostBasis: Math.min(config.stocksCostBasis ?? 0, newStocksValue),
                    })}
                    min={0}
                    max={100000000}
                    step={1000000}
                  />
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="株式取得原価" tooltip="株式を購入したときの合計金額。評価額との差が含み益になり、売却時に20.315%の譲渡税がかかります" />
                    <span className="text-sm font-mono text-muted-foreground">{formatCurrency(config.stocksCostBasis ?? 0, true)}</span>
                  </div>
                  <Slider
                    value={[config.stocksCostBasis ?? 0]}
                    onValueChange={([value]) => onConfigChange({ ...config, stocksCostBasis: value })}
                    min={0}
                    max={(config.stocks ?? 0) > 0 ? (config.stocks ?? 0) : 100000000}
                    step={500000}
                  />
                </div>

                {(() => {
                  const unrealizedGain = (config.stocks ?? 0) - (config.stocksCostBasis ?? 0)
                  return (
                    <p className={`text-xs ${unrealizedGain >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                      含み益: {unrealizedGain >= 0 ? '+' : ''}{formatCurrency(unrealizedGain, true)}
                    </p>
                  )
                })()}

                <button
                  onClick={() => setShowAssetDetail(false)}
                  className="text-xs text-muted-foreground underline underline-offset-2"
                >
                  ← 合算表示に戻す
                </button>
              </div>
            )}

            <div className="space-y-2">
              <FieldLabel label="生活費モード" tooltip="固定費: 毎年同額で計算。ライフステージ: 子どもの年齢に連動して自動調整（子育て期は増加、老後は減少）" />
              <div className="flex gap-2">
                {(['fixed', 'lifecycle'] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => onConfigChange({ ...config, expenseMode: mode })}
                    className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                      (config.expenseMode ?? 'fixed') === mode
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted hover:bg-muted/80'
                    }`}
                  >
                    {mode === 'fixed' ? '固定費' : 'ライフステージ'}
                  </button>
                ))}
              </div>
            </div>

            {(config.expenseMode ?? 'fixed') === 'fixed' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <FieldLabel label="月間生活費" tooltip="毎月の基本生活費。住宅ローン返済額・教育費は別途ライフタブで入力します" />
                  <span className="text-sm font-mono text-muted-foreground">{formatCurrency(config.monthlyExpenses)}/月</span>
                </div>
                <Slider
                  value={[config.monthlyExpenses]}
                  onValueChange={([value]) => onConfigChange({ ...config, monthlyExpenses: value })}
                  min={100000}
                  max={1000000}
                  step={10000}
                />
              </div>
            )}

            {(config.expenseMode ?? 'fixed') === 'lifecycle' && (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">年間生活費（万円）</p>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { key: 'withPreschooler', label: '乳幼児期(0-5歳)', defaultVal: 276 },
                    { key: 'withElementaryChild', label: '小学生(6-11歳)', defaultVal: 323 },
                    { key: 'withJuniorHighChild', label: '中学生(12-14歳)', defaultVal: 347 },
                    { key: 'withHighSchoolChild', label: '高校生(15-17歳)', defaultVal: 383 },
                    { key: 'withCollegeChild', label: '大学生(18-21歳)', defaultVal: 396 },
                    { key: 'emptyNestActive', label: '子育て後(-69歳)', defaultVal: 258 },
                    { key: 'emptyNestSenior', label: 'シニア(70-79歳)', defaultVal: 224 },
                    { key: 'emptyNestElderly', label: '高齢期(80歳-)', defaultVal: 193 },
                  ].map(({ key, label, defaultVal }) => (
                    <div key={key} className="space-y-1">
                      <Label className="text-xs text-muted-foreground">{label}</Label>
                      <input
                        type="number"
                        min={0}
                        max={1000}
                        value={Math.round((config.lifecycleExpenses?.[key as keyof LifecycleExpenseConfig] ?? defaultVal * 10000) / 10000)}
                        onChange={(e) => {
                          const val = Number(e.target.value) * 10000
                          onConfigChange({
                            ...config,
                            lifecycleExpenses: {
                              ...config.lifecycleExpenses,
                              [key]: val,
                            },
                          })
                        }}
                        className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm text-right"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <FieldLabel label="生活費上昇率" tooltip="物価上昇や生活水準の向上による年間上昇率。インフレ率と同じ値が一般的です" />
                <span className="text-sm font-mono text-muted-foreground">{(config.expenseGrowthRate * 100).toFixed(1)}%</span>
              </div>
              <Slider
                value={[config.expenseGrowthRate * 100]}
                onValueChange={([value]) => onConfigChange({ ...config, expenseGrowthRate: value / 100 })}
                min={0}
                max={3}
                step={0.1}
              />
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="income" className="mt-4 space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <User className="h-4 w-4" />
              本人
            </CardTitle>
          </CardHeader>
          <CardContent>
            <PersonConfig
              person={config.person1}
              label="本人"
              onChange={updatePerson1}
              childBirthYears={config.children.map(c => c.birthYear)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <Users className="h-4 w-4" />
                配偶者
              </CardTitle>
              <div className="flex items-center gap-2">
                <Label htmlFor="spouse-toggle" className="text-sm">
                  {config.person2 ? "有効" : "無効"}
                </Label>
                <Switch
                  id="spouse-toggle"
                  checked={config.person2 !== null}
                  onCheckedChange={togglePerson2}
                />
              </div>
            </div>
          </CardHeader>
          {config.person2 && (
            <CardContent>
              <PersonConfig
                person={config.person2}
                label="配偶者"
                onChange={updatePerson2}
                childBirthYears={config.children.map(c => c.birthYear)}
              />
            </CardContent>
          )}
        </Card>
      </TabsContent>

      <TabsContent value="investment" className="mt-4 space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">投資設定</CardTitle>
            <CardDescription>運用利回りとリスク設定</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <FieldLabel label="期待リターン" tooltip="年間の投資リターンの期待値（税引き前）。S&P500の歴史的平均は約7%。将来を保証するものではありません" />
                <span className="text-sm font-mono text-muted-foreground">{(config.investmentReturn * 100).toFixed(1)}%</span>
              </div>
              <Slider
                value={[config.investmentReturn * 100]}
                onValueChange={([value]) => onConfigChange({ ...config, investmentReturn: value / 100 })}
                min={1}
                max={10}
                step={0.1}
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <FieldLabel label="リスク（標準偏差）" tooltip="リターンのブレ幅（標準偏差）。大きいほど好不況の振れ幅が増します。S&P500は約15〜20%" />
                <span className="text-sm font-mono text-muted-foreground">{(config.investmentVolatility * 100).toFixed(1)}%</span>
              </div>
              <Slider
                value={[config.investmentVolatility * 100]}
                onValueChange={([value]) => onConfigChange({ ...config, investmentVolatility: value / 100 })}
                min={5}
                max={30}
                step={0.5}
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <FieldLabel label="安全引き出し率（SWR）" tooltip="FIRE後に毎年資産から取り崩す割合。4%ルール（資産×25倍でFIRE）が有名。低いほど資産が長持ちしやすくなります" />
                <span className="text-sm font-mono text-muted-foreground">{(config.safeWithdrawalRate * 100).toFixed(1)}%</span>
              </div>
              <Slider
                value={[config.safeWithdrawalRate * 100]}
                onValueChange={([value]) => onConfigChange({ ...config, safeWithdrawalRate: value / 100 })}
                min={2}
                max={6}
                step={0.1}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <PiggyBank className="h-4 w-4" />
                NISA
              </CardTitle>
              <div className="flex items-center gap-2">
                <Label htmlFor="nisa-toggle" className="text-sm">
                  {config.nisa.enabled ? "有効" : "無効"}
                </Label>
                <Switch
                  id="nisa-toggle"
                  checked={config.nisa.enabled}
                  onCheckedChange={(checked) =>
                    onConfigChange({ ...config, nisa: { ...config.nisa, enabled: checked } })
                  }
                />
              </div>
            </div>
          </CardHeader>
          {config.nisa.enabled && (
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <FieldLabel label="年間投資額" tooltip="新NISAへの年間拠出額。上限は年360万円（成長投資枠240万＋つみたて枠120万）、生涯上限1,800万円。運用益・配当は非課税" />
                  <span className="text-sm font-mono text-muted-foreground">{formatCurrency(config.nisa.annualContribution, true)}</span>
                </div>
                <Slider
                  value={[config.nisa.annualContribution]}
                  onValueChange={([value]) =>
                    onConfigChange({ ...config, nisa: { ...config.nisa, annualContribution: value } })
                  }
                  min={0}
                  max={3600000}
                  step={100000}
                />
              </div>
            </CardContent>
          )}
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <PiggyBank className="h-4 w-4" />
                iDeCo
              </CardTitle>
              <div className="flex items-center gap-2">
                <Label htmlFor="ideco-toggle" className="text-sm">
                  {config.ideco.enabled ? "有効" : "無効"}
                </Label>
                <Switch
                  id="ideco-toggle"
                  checked={config.ideco.enabled}
                  onCheckedChange={(checked) =>
                    onConfigChange({ ...config, ideco: { ...config.ideco, enabled: checked } })
                  }
                />
              </div>
            </div>
          </CardHeader>
          {config.ideco.enabled && (
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <FieldLabel label="月額拠出額" tooltip="iDeCo（個人型確定拠出年金）の月額掛金。掛金は全額所得控除で節税効果あり。60歳まで引き出せません" />
                  <span className="text-sm font-mono text-muted-foreground">{formatCurrency(config.ideco.monthlyContribution)}/月</span>
                </div>
                <Slider
                  value={[config.ideco.monthlyContribution]}
                  onValueChange={([value]) =>
                    onConfigChange({ ...config, ideco: { ...config.ideco, monthlyContribution: value } })
                  }
                  min={5000}
                  max={68000}
                  step={1000}
                />
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <FieldLabel label="受取開始年齢" tooltip="iDeCoの受け取りを開始する年齢（60〜75歳）。受取時に退職所得控除または公的年金等控除が適用されます" />
                  <span className="text-sm font-mono text-muted-foreground">
                    {config.ideco.withdrawalStartAge ?? 60}歳
                  </span>
                </div>
                <Slider
                  value={[config.ideco.withdrawalStartAge ?? 60]}
                  onValueChange={([value]) =>
                    onConfigChange({ ...config, ideco: { ...config.ideco, withdrawalStartAge: value } })
                  }
                  min={60}
                  max={75}
                  step={1}
                />
              </div>
            </CardContent>
          )}
        </Card>
      </TabsContent>

      <TabsContent value="life" className="mt-4 space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Baby className="h-4 w-4" />
              子育て
            </CardTitle>
            <CardDescription>子どもの人数と教育費を設定</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <FieldLabel label="子どもの人数" tooltip="シミュレーションに含める子どもの人数。教育費と児童手当の計算に反映されます" />
                <span className="text-sm font-mono text-muted-foreground">{config.children.length}人</span>
              </div>
              <Slider
                value={[config.children.length]}
                onValueChange={([value]) => {
                  const currentYear = new Date().getFullYear()
                  const children = Array.from({ length: value }, (_, i) => ({
                    birthYear: config.children[i]?.birthYear ?? currentYear + i * 2,
                    educationPath: config.children[i]?.educationPath ?? "mixed" as const,
                  }))
                  onConfigChange({ ...config, children })
                }}
                min={0}
                max={3}
                step={1}
              />
            </div>

            {config.children.map((child, index) => (
              <div key={index} className="space-y-3 rounded-lg bg-muted/50 p-4">
                <p className="text-sm font-medium">子ども {index + 1}</p>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="誕生年" tooltip="子どもの誕生年（西暦）。教育費の発生タイミングと児童手当の計算に使います" />
                    <span className="text-sm font-mono text-muted-foreground">{child.birthYear}年</span>
                  </div>
                  <Slider
                    value={[child.birthYear]}
                    onValueChange={([value]) => {
                      const newChildren = [...config.children]
                      newChildren[index] = { ...child, birthYear: value }
                      onConfigChange({ ...config, children: newChildren })
                    }}
                    min={2020}
                    max={2035}
                    step={1}
                  />
                </div>
                <div className="flex items-center gap-4 pt-2">
                  <FieldLabel label="教育費" tooltip="公立: 小〜大学まで全て公立。私立: 全て私立。混合: 小・中は公立、高・大学は私立" />
                  <div className="flex gap-2">
                    {(["public", "mixed", "private"] as const).map((path) => (
                      <button
                        key={path}
                        onClick={() => {
                          const newChildren = [...config.children]
                          newChildren[index] = { ...child, educationPath: path }
                          onConfigChange({ ...config, children: newChildren })
                        }}
                        className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                          child.educationPath === path
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted hover:bg-muted-foreground/10"
                        }`}
                      >
                        {path === "public" ? "公立" : path === "private" ? "私立" : "混合"}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ))}

            <div className="flex items-center justify-between pt-2 border-t">
              <div>
                <FieldLabel label="児童手当" tooltip="中学校卒業まで支給される児童手当を収入に加算します（第1・2子: 月1万円、第3子以降: 月1.5万円）" />
                <p className="text-xs text-muted-foreground">収入に加算</p>
              </div>
              <Switch
                id="child-allowance-toggle"
                checked={config.childAllowanceEnabled}
                disabled={config.children.length === 0}
                onCheckedChange={(checked) => onConfigChange({ ...config, childAllowanceEnabled: checked })}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">セミFIRE</CardTitle>
                <CardDescription>FIRE後も一定期間、収入を得る場合に設定</CardDescription>
              </div>
              <Switch
                id="semi-fire-toggle"
                checked={config.postFireIncome !== null && config.postFireIncome !== undefined}
                onCheckedChange={(checked) => {
                  if (checked) {
                    onConfigChange({ ...config, postFireIncome: { monthlyAmount: 100000, untilAge: 55 } })
                  } else {
                    onConfigChange({ ...config, postFireIncome: null })
                  }
                }}
              />
            </div>
          </CardHeader>
          {config.postFireIncome !== null && config.postFireIncome !== undefined && (
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <FieldLabel label="月収（税引き前）" tooltip="FIRE後に副業・パート・フリーランス等から得る税引き前の月間収入。社会保険料・税金を自動計算します" />
                  <span className="text-sm font-mono text-muted-foreground">{formatCurrency(config.postFireIncome.monthlyAmount)}/月</span>
                </div>
                <Slider
                  value={[config.postFireIncome.monthlyAmount]}
                  onValueChange={([value]) => onConfigChange({
                    ...config,
                    postFireIncome: { ...(config.postFireIncome as PostFireIncomeConfig), monthlyAmount: value },
                  })}
                  min={0}
                  max={500000}
                  step={10000}
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <FieldLabel label="終了年齢" tooltip="この年齢になるとセミFIREを終了し、完全引退（収入ゼロ）に移行します" />
                  <span className="text-sm font-mono text-muted-foreground">{config.postFireIncome.untilAge}歳まで</span>
                </div>
                <Slider
                  value={[config.postFireIncome.untilAge]}
                  onValueChange={([value]) => onConfigChange({
                    ...config,
                    postFireIncome: { ...(config.postFireIncome as PostFireIncomeConfig), untilAge: value },
                  })}
                  min={40}
                  max={80}
                  step={1}
                />
              </div>
            </CardContent>
          )}
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">住宅ローン</CardTitle>
                <CardDescription>月額返済額をキャッシュフローに反映します</CardDescription>
              </div>
              <Switch
                id="mortgage-toggle"
                checked={config.mortgage !== null && config.mortgage !== undefined}
                onCheckedChange={(checked) => {
                  if (checked) {
                    onConfigChange({ ...config, mortgage: { monthlyPayment: 100000, endYear: 2040 } })
                  } else {
                    onConfigChange({ ...config, mortgage: null })
                  }
                }}
              />
            </div>
          </CardHeader>
          {config.mortgage !== null && config.mortgage !== undefined && (
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <FieldLabel label="月額返済額" tooltip="元利合計の月次返済額。完済年までキャッシュフローから毎月差し引かれます" />
                  <span className="text-sm font-mono text-muted-foreground">{formatCurrency(config.mortgage.monthlyPayment)}/月</span>
                </div>
                <Slider
                  value={[config.mortgage.monthlyPayment]}
                  onValueChange={([value]) => onConfigChange({
                    ...config,
                    mortgage: { ...(config.mortgage!), monthlyPayment: value },
                  })}
                  min={30000}
                  max={300000}
                  step={5000}
                />
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <FieldLabel label="完済年" tooltip="住宅ローンの完済予定年（西暦）。この年以降は返済が発生しません" />
                  <span className="text-sm font-mono text-muted-foreground">{config.mortgage.endYear}年</span>
                </div>
                <Slider
                  value={[config.mortgage.endYear]}
                  onValueChange={([value]) => onConfigChange({
                    ...config,
                    mortgage: { ...(config.mortgage!), endYear: value },
                  })}
                  min={2025}
                  max={2060}
                  step={1}
                />
              </div>
            </CardContent>
          )}
        </Card>
      </TabsContent>

      <TabsContent value="advanced" className="mt-4 space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">シミュレーション設定</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between py-1">
              <FieldLabel
                label="モンテカルロシミュレーション"
                tooltip="1000回のシミュレーションで市場変動を考慮した成功確率を計算します。オフにすると平均シナリオのみ（高速）"
              />
              <Switch
                id="monte-carlo-toggle-panel"
                checked={useMonteCarlo}
                onCheckedChange={onMonteCarloChange}
              />
            </div>
            <div className="h-px bg-border" />
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <FieldLabel label="シミュレーション期間" tooltip="何年後まで資産推移を計算するか。老後の資産状況を把握するため、少なくとも退職後30〜40年分を推奨します" />
                <span className="text-sm font-mono text-muted-foreground">{config.simulationYears}年</span>
              </div>
              <Slider
                value={[config.simulationYears]}
                onValueChange={([value]) => onConfigChange({ ...config, simulationYears: value })}
                min={20}
                max={60}
                step={1}
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <FieldLabel label="インフレ率" tooltip="物価上昇率。生活費がこの割合で毎年増加します。日銀の目標は2%。生活費上昇率と合わせて設定します" />
                <span className="text-sm font-mono text-muted-foreground">{(config.inflationRate * 100).toFixed(1)}%</span>
              </div>
              <Slider
                value={[config.inflationRate * 100]}
                onValueChange={([value]) => onConfigChange({ ...config, inflationRate: value / 100 })}
                min={0}
                max={3}
                step={0.1}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">取り崩し戦略</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex gap-2">
              {([
                { value: 'fixed', label: '固定額' },
                { value: 'percentage', label: '定率' },
                { value: 'guardrail', label: 'ガードレール' },
              ] as { value: WithdrawalStrategy; label: string }[]).map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => onConfigChange({ ...config, withdrawalStrategy: value })}
                  className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                    (config.withdrawalStrategy ?? 'fixed') === value
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted hover:bg-muted-foreground/10"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {(config.withdrawalStrategy ?? 'fixed') === 'guardrail' && (
              <div className="space-y-4">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="裁量支出比率" tooltip="生活費のうち、相場下落時に削減できる裁量的な支出の割合。食費・光熱費などの必須支出以外（旅行・外食・娯楽等）が目安" />
                    <span className="text-sm font-mono text-muted-foreground">{((config.guardrailConfig?.discretionaryRatio ?? 0.3) * 100).toFixed(0)}%</span>
                  </div>
                  <Slider
                    value={[(config.guardrailConfig?.discretionaryRatio ?? 0.3) * 100]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      guardrailConfig: {
                        threshold1: config.guardrailConfig?.threshold1 ?? -0.10,
                        reduction1: config.guardrailConfig?.reduction1 ?? 0.40,
                        threshold2: config.guardrailConfig?.threshold2 ?? -0.20,
                        reduction2: config.guardrailConfig?.reduction2 ?? 0.80,
                        threshold3: config.guardrailConfig?.threshold3 ?? -0.35,
                        reduction3: config.guardrailConfig?.reduction3 ?? 0.95,
                        discretionaryRatio: value / 100,
                      },
                    })}
                    min={10}
                    max={50}
                    step={5}
                  />
                </div>

                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground pt-1">下落閾値と裁量支出削減率</p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="閾値1（軽微な下落）" tooltip="資産がピークからこの割合以上下落するとフェーズ1の削減が発動します" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {((config.guardrailConfig?.threshold1 ?? -0.10) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <Slider
                    value={[(config.guardrailConfig?.threshold1 ?? -0.10) * 100]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      guardrailConfig: { ...defaultGuardrail, ...config.guardrailConfig, threshold1: value / 100 }
                    })}
                    min={-30} max={-5} step={1}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="削減率1" tooltip="フェーズ1発動時に裁量支出を削減する割合（例: 40%削減 = 裁量支出が60%になる）" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {((config.guardrailConfig?.reduction1 ?? 0.40) * 100).toFixed(0)}%削減
                    </span>
                  </div>
                  <Slider
                    value={[(config.guardrailConfig?.reduction1 ?? 0.40) * 100]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      guardrailConfig: { ...defaultGuardrail, ...config.guardrailConfig, reduction1: value / 100 }
                    })}
                    min={10} max={70} step={5}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="閾値2（中程度の下落）" tooltip="資産がピークからこの割合以上下落するとフェーズ2の削減が発動します" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {((config.guardrailConfig?.threshold2 ?? -0.20) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <Slider
                    value={[(config.guardrailConfig?.threshold2 ?? -0.20) * 100]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      guardrailConfig: { ...defaultGuardrail, ...config.guardrailConfig, threshold2: value / 100 }
                    })}
                    min={-40} max={-10} step={1}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="削減率2" tooltip="フェーズ2発動時に裁量支出を削減する割合" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {((config.guardrailConfig?.reduction2 ?? 0.80) * 100).toFixed(0)}%削減
                    </span>
                  </div>
                  <Slider
                    value={[(config.guardrailConfig?.reduction2 ?? 0.80) * 100]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      guardrailConfig: { ...defaultGuardrail, ...config.guardrailConfig, reduction2: value / 100 }
                    })}
                    min={40} max={95} step={5}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="閾値3（深刻な下落）" tooltip="資産がピークからこの割合以上下落するとフェーズ3の削減が発動します。これ以上の下落でも同じ削減率が適用されます" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {((config.guardrailConfig?.threshold3 ?? -0.35) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <Slider
                    value={[(config.guardrailConfig?.threshold3 ?? -0.35) * 100]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      guardrailConfig: { ...defaultGuardrail, ...config.guardrailConfig, threshold3: value / 100 }
                    })}
                    min={-60} max={-20} step={1}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="削減率3" tooltip="フェーズ3発動時の削減率。ほぼ必須支出のみで生活するレベルに設定するのが一般的です" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {((config.guardrailConfig?.reduction3 ?? 0.95) * 100).toFixed(0)}%削減
                    </span>
                  </div>
                  <Slider
                    value={[(config.guardrailConfig?.reduction3 ?? 0.95) * 100]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      guardrailConfig: { ...defaultGuardrail, ...config.guardrailConfig, reduction3: value / 100 }
                    })}
                    min={60} max={100} step={5}
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">MCリターンモデル</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              {([
                { value: 'normal', label: '正規分布' },
                { value: 'meanReversion', label: '平均回帰' },
                { value: 'bootstrap', label: 'ブートストラップ' },
              ] as { value: MCReturnModel; label: string }[]).map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => onConfigChange({ ...config, mcReturnModel: value })}
                  className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                    (config.mcReturnModel ?? 'normal') === value
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted hover:bg-muted-foreground/10"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">FIRE後の社会保険料</CardTitle>
            <CardDescription>国保・国民年金の計算パラメータ（通常は変更不要）</CardDescription>
          </CardHeader>
          <CardContent>
            <details className="group">
              <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground list-none flex items-center gap-1">
                <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
                詳細設定を表示
              </summary>
              <div className="mt-4 space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="医療分所得割率" tooltip="国保の医療分として所得に対して課税される割合。自治体ごとに異なります（全国平均約11%）" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {(config.postFireSocialInsurance.nhisoIncomeRate * 100).toFixed(2)}%
                    </span>
                  </div>
                  <Slider
                    value={[config.postFireSocialInsurance.nhisoIncomeRate * 100]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      postFireSocialInsurance: { ...config.postFireSocialInsurance, nhisoIncomeRate: value / 100 }
                    })}
                    min={5} max={15} step={0.01}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="後期高齢者支援金分所得割率" tooltip="国保のうち後期高齢者医療制度への支援金として所得に対して課税される割合" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {(config.postFireSocialInsurance.nhisoSupportIncomeRate * 100).toFixed(2)}%
                    </span>
                  </div>
                  <Slider
                    value={[config.postFireSocialInsurance.nhisoSupportIncomeRate * 100]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      postFireSocialInsurance: { ...config.postFireSocialInsurance, nhisoSupportIncomeRate: value / 100 }
                    })}
                    min={1} max={5} step={0.01}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="均等割（1人あたり）" tooltip="所得に関わらず加入者1人ごとに定額でかかる国保保険料" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {formatCurrency(config.postFireSocialInsurance.nhisoFixedAmountPerPerson)}
                    </span>
                  </div>
                  <Slider
                    value={[config.postFireSocialInsurance.nhisoFixedAmountPerPerson]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      postFireSocialInsurance: { ...config.postFireSocialInsurance, nhisoFixedAmountPerPerson: value }
                    })}
                    min={10000} max={100000} step={1000}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="平等割（世帯）" tooltip="所得・人数に関わらず世帯単位でかかる定額の国保保険料（自治体によっては0円）" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {formatCurrency(config.postFireSocialInsurance.nhisoHouseholdFixed)}
                    </span>
                  </div>
                  <Slider
                    value={[config.postFireSocialInsurance.nhisoHouseholdFixed]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      postFireSocialInsurance: { ...config.postFireSocialInsurance, nhisoHouseholdFixed: value }
                    })}
                    min={0} max={100000} step={1000}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="国保年間上限額" tooltip="国保保険料の年間上限額。これを超える保険料はかかりません" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {formatCurrency(config.postFireSocialInsurance.nhisoMaxAnnual, true)}
                    </span>
                  </div>
                  <Slider
                    value={[config.postFireSocialInsurance.nhisoMaxAnnual]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      postFireSocialInsurance: { ...config.postFireSocialInsurance, nhisoMaxAnnual: value }
                    })}
                    min={500000} max={2000000} step={10000}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="国民年金月額保険料" tooltip="FIRE後に支払う国民年金の月額保険料（第1号被保険者）。毎年改定されます" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {formatCurrency(config.postFireSocialInsurance.nationalPensionMonthlyPremium)}/月
                    </span>
                  </div>
                  <Slider
                    value={[config.postFireSocialInsurance.nationalPensionMonthlyPremium]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      postFireSocialInsurance: { ...config.postFireSocialInsurance, nationalPensionMonthlyPremium: value }
                    })}
                    min={10000} max={25000} step={100}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="介護分所得割率" tooltip="40〜64歳の第2号被保険者が支払う介護保険料の所得割率" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {(config.postFireSocialInsurance.longTermCareRate * 100).toFixed(2)}%
                    </span>
                  </div>
                  <Slider
                    value={[config.postFireSocialInsurance.longTermCareRate * 100]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      postFireSocialInsurance: { ...config.postFireSocialInsurance, longTermCareRate: value / 100 }
                    })}
                    min={0.5} max={5} step={0.01}
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <FieldLabel label="介護分上限額" tooltip="介護保険料の年間上限額" className="text-xs" />
                    <span className="text-xs font-mono text-muted-foreground">
                      {formatCurrency(config.postFireSocialInsurance.longTermCareMax, true)}
                    </span>
                  </div>
                  <Slider
                    value={[config.postFireSocialInsurance.longTermCareMax]}
                    onValueChange={([value]) => onConfigChange({
                      ...config,
                      postFireSocialInsurance: { ...config.postFireSocialInsurance, longTermCareMax: value }
                    })}
                    min={50000} max={400000} step={10000}
                  />
                </div>

                <button
                  onClick={() => onConfigChange({
                    ...config,
                    postFireSocialInsurance: {
                      nhisoIncomeRate: 0.1100,
                      nhisoSupportIncomeRate: 0.0259,
                      nhisoFixedAmountPerPerson: 50000,
                      nhisoHouseholdFixed: 30000,
                      nhisoMaxAnnual: 1060000,
                      nationalPensionMonthlyPremium: 16980,
                      longTermCareRate: 0.0200,
                      longTermCareMax: 170000,
                    }
                  })}
                  className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted transition-colors"
                >
                  デフォルト値にリセット
                </button>
              </div>
            </details>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  )
}
