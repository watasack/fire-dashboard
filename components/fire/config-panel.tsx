"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { SimulationConfig, Person, EmploymentType, WithdrawalStrategy, MCReturnModel, PostFireIncomeConfig, LifecycleExpenseConfig } from "@/lib/simulator"
import { formatCurrency } from "@/lib/utils"
import { User, Users, Wallet, TrendingUp, Baby, PiggyBank, Settings2 } from "lucide-react"

interface ConfigPanelProps {
  config: SimulationConfig
  onConfigChange: (config: SimulationConfig) => void
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
          <Label className="text-sm font-medium">現在の年齢</Label>
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
            <Label className="text-sm font-medium">年収</Label>
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
            <Label className="text-sm font-medium">年収上昇率</Label>
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
          <Label className="text-sm font-medium">退職年齢</Label>
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
          <Label className="text-sm font-medium">年金受給額（年間）</Label>
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
          <Label className="text-sm font-medium">年金受給開始年齢</Label>
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
        <Label className="text-sm font-medium">雇用形態</Label>
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
            <Label className="text-sm font-medium">時短勤務</Label>
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
                  <Label className="text-xs">時短終了年齢</Label>
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
                  <Label className="text-xs">時短中の収入比率</Label>
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
          <Label className="text-sm font-medium">産休・育休取得</Label>
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

export function ConfigPanel({ config, onConfigChange }: ConfigPanelProps) {
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
                  <Label className="text-sm font-medium">現在の資産（現金＋株式）</Label>
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
                    <Label className="text-sm font-medium">現金・預金</Label>
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
                    <Label className="text-sm font-medium">株式評価額（課税口座）</Label>
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
                    <Label className="text-sm font-medium">株式取得原価</Label>
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
              <Label className="text-sm font-medium">生活費モード</Label>
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
                  <Label className="text-sm font-medium">月間生活費</Label>
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
                <Label className="text-sm font-medium">生活費上昇率</Label>
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
                <Label className="text-sm font-medium">期待リターン</Label>
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
                <Label className="text-sm font-medium">リスク（標準偏差）</Label>
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
                <Label className="text-sm font-medium">安全引き出し率（SWR）</Label>
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
                  <Label className="text-sm font-medium">年間投資額</Label>
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
                  <Label className="text-sm font-medium">月額拠出額</Label>
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
                  <Label className="text-sm font-medium">受取開始年齢</Label>
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
                <Label className="text-sm font-medium">子どもの人数</Label>
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
                    <Label className="text-sm">誕生年</Label>
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
                  <Label className="text-sm">教育費</Label>
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
                <Label className="text-sm font-medium">児童手当</Label>
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
                  <Label className="text-sm font-medium">月収（税引き前）</Label>
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
                  <Label className="text-sm font-medium">終了年齢</Label>
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
                  <Label className="text-sm font-medium">月額返済額</Label>
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
                  <Label className="text-sm font-medium">完済年</Label>
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
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">シミュレーション期間</Label>
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
                <Label className="text-sm font-medium">インフレ率</Label>
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
                    <Label className="text-sm font-medium">裁量支出比率</Label>
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
                    <Label className="text-xs">閾値1（軽微な下落）</Label>
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
                    <Label className="text-xs">削減率1</Label>
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
                    <Label className="text-xs">閾値2（中程度の下落）</Label>
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
                    <Label className="text-xs">削減率2</Label>
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
                    <Label className="text-xs">閾値3（深刻な下落）</Label>
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
                    <Label className="text-xs">削減率3</Label>
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
                    <Label className="text-xs">医療分所得割率</Label>
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
                    <Label className="text-xs">後期高齢者支援金分所得割率</Label>
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
                    <Label className="text-xs">均等割（1人あたり）</Label>
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
                    <Label className="text-xs">平等割（世帯）</Label>
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
                    <Label className="text-xs">国保年間上限額</Label>
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
                    <Label className="text-xs">国民年金月額保険料</Label>
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
                    <Label className="text-xs">介護分所得割率</Label>
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
                    <Label className="text-xs">介護分上限額</Label>
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
