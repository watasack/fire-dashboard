"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion"
import { SimulationConfig, Person, EmploymentType, WithdrawalStrategy, MCReturnModel, PostFireIncomeConfig, LifecycleExpenseConfig, ChildEducationPaths, EDUCATION_PATHS_PRESETS, calcMortgageMonthlyPayment } from "@/lib/simulator"
import { formatCurrency, cn } from "@/lib/utils"
import { User, Users, Wallet, TrendingUp, Baby, PiggyBank, Settings2, Info } from "lucide-react"
import { SliderField } from "@/components/fire/slider-field"

interface ConfigPanelProps {
  config: SimulationConfig
  onConfigChange: (config: SimulationConfig) => void
  useMonteCarlo: boolean
  onMonteCarloChange: (value: boolean) => void
}

function FieldLabel({ label, tooltip, className }: { label: string; tooltip: string; className?: string }) {
  const [open, setOpen] = useState(false)
  return (
    <span className={cn("flex flex-col gap-0", className)}>
      <span className="flex items-center gap-1">
        <span className="text-sm font-medium">{label}</span>
        {tooltip && (
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen((prev) => !prev)}
            className="inline-flex p-2.5 -m-2.5 text-muted-foreground/60 hover:text-muted-foreground transition-colors"
          >
            <Info className="h-4 w-4 shrink-0" />
          </button>
        )}
      </span>
      {open && tooltip && (
        <span className="mt-1 text-xs text-muted-foreground leading-relaxed">
          {tooltip}
        </span>
      )}
    </span>
  )
}

function PersonConfig({
  person,
  label,
  onChange,
}: {
  person: Person
  label: string
  onChange: (person: Person) => void
}) {
  const isHomemaker = person.employmentType === 'homemaker'

  return (
    <div className="space-y-6">
      <SliderField
        label="現在の年齢"
        tooltip="今あなたが何歳かを入力します。ここを起点にFIREまでの年数を計算します"
        value={person.currentAge}
        onChange={(value) => onChange({ ...person, currentAge: value })}
        min={20} max={60} step={1}
        format={(v) => `${v}歳`}
      />

      <div className="space-y-2">
        <FieldLabel label="誕生月" tooltip="誕生月を設定するとFIRE達成時期を「2034年10月」のように月単位で表示できます" />
        <select
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
          value={person.birthMonth ?? ''}
          onChange={e => onChange({ ...person, birthMonth: e.target.value ? Number(e.target.value) : undefined })}
        >
          <option value="">未設定</option>
          {[1,2,3,4,5,6,7,8,9,10,11,12].map(m => (
            <option key={m} value={m}>{m}月</option>
          ))}
        </select>
      </div>

      {!isHomemaker && (
        <SliderField
          label="年収"
          tooltip={
            (person.employmentType ?? 'employee') === 'selfEmployed'
              ? "売上から経費を引いた事業所得を入力してください。手取り計算は自動でやります"
              : "源泉徴収票の一番上の「支払金額」を入力してください。手取り計算は自動でやります"
          }
          value={person.grossIncome}
          onChange={(value) => onChange({ ...person, grossIncome: value })}
          min={2000000} max={20000000} step={100000}
          format={(v) => formatCurrency(v, true)}
        />
      )}

      {!isHomemaker && (
        <SliderField
          label="年収上昇率"
          tooltip="毎年どれくらい年収が上がるか。「あまり変わらない」→1%、「昇進予定あり」→2〜3%が目安です"
          value={person.incomeGrowthRate * 100}
          onChange={(value) => onChange({ ...person, incomeGrowthRate: value / 100 })}
          min={0} max={5} step={0.1}
          format={(v) => `${v.toFixed(1)}%`}
        />
      )}

      {isHomemaker && (
        <p className="text-xs text-muted-foreground">専業主婦/夫は年収・社会保険料なし（国民年金第3号）</p>
      )}

      <SliderField
        label="退職年齢"
        tooltip="「何歳でFIREしたいか」を入力します。まず目標を入れて、後で調整してみてください"
        value={person.retirementAge}
        onChange={(value) => onChange({ ...person, retirementAge: value })}
        min={50} max={70} step={1}
        format={(v) => `${v}歳`}
      />

      <SliderField
        label="年金受給額（年間）"
        tooltip="毎年届く「ねんきん定期便」や「ねんきんネット」で確認できます。会社員は年150〜200万円が目安"
        value={person.pensionAmount ?? 0}
        onChange={(value) => onChange({ ...person, pensionAmount: value })}
        min={0} max={3000000} step={50000}
        format={(v) => formatCurrency(v, true)}
      />

      <SliderField
        label="年金受給開始年齢"
        tooltip="原則65歳ですが、70歳まで遅らせると42%増、75歳まで遅らせると84%増になります"
        value={person.pensionStartAge}
        onChange={(value) => onChange({ ...person, pensionStartAge: value })}
        min={60} max={75} step={1}
        format={(v) => `${v}歳`}
      />

      <div className="space-y-2">
        <FieldLabel label="雇用形態" tooltip="税金や年金の計算が変わります。「会社員」= 会社が社保を半分払ってくれる。「自営業」= 全額自分で支払う" />
        <select
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
          value={person.employmentType ?? 'employee'}
          onChange={e => {
            const employmentType = e.target.value as EmploymentType
            const updates: Partial<typeof person> = { employmentType }
            if (employmentType === 'selfEmployed') updates.incomeGrowthRate = 0
            if (employmentType === 'homemaker') { updates.grossIncome = 0; updates.incomeGrowthRate = 0 }
            onChange({ ...person, ...updates })
          }}
        >
          <option value="employee">会社員</option>
          <option value="selfEmployed">自営業・フリーランス</option>
          <option value="homemaker">専業主婦/夫</option>
        </select>
      </div>

      {(person.employmentType ?? 'employee') === 'employee' && (
        <div className="space-y-3 rounded-lg bg-muted/50 p-3">
          <div className="flex items-center justify-between">
            <FieldLabel label="時短勤務" tooltip="育休後に時短勤務するならONにしてください。年収が下がる期間をFIREの計算に反映します" />
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground whitespace-nowrap">
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
              <SliderField
                label="時短終了年齢"
                tooltip="「何歳でフルタイムに戻るか」を入力します。子どもが小学校入学（6歳）ごろが多いです"
                value={person.partTimeUntilAge}
                onChange={(value) => onChange({ ...person, partTimeUntilAge: value })}
                min={person.currentAge + 1} max={person.retirementAge} step={1}
                format={(v) => `${v}歳まで`}
                small
              />
              <SliderField
                label="時短中の収入比率"
                tooltip="時短でどれくらい収入が減るかです。「7時間→6時間」なら約85%、「週4日」なら80%が目安です"
                value={(person.partTimeIncomeRatio ?? 0.8) * 100}
                onChange={(value) => onChange({ ...person, partTimeIncomeRatio: value / 100 })}
                min={50} max={100} step={5}
                format={(v) => `${v.toFixed(0)}%`}
                small
              />
            </div>
          )}
        </div>
      )}

    </div>
  )
}

const ACCORDION_STORAGE_KEY = "fire_config_accordion"

export function ConfigPanel({ config, onConfigChange, useMonteCarlo, onMonteCarloChange }: ConfigPanelProps) {
  const [accordionValues, setAccordionValues] = useState<string[]>(["basic"])

  useEffect(() => {
    try {
      const stored = localStorage.getItem(ACCORDION_STORAGE_KEY)
      if (stored) setAccordionValues(JSON.parse(stored))
    } catch { /* ignore */ }
  }, [])

  const handleAccordionChange = (values: string[]) => {
    setAccordionValues(values)
    try { localStorage.setItem(ACCORDION_STORAGE_KEY, JSON.stringify(values)) } catch { /* ignore */ }
  }

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

  // ---- inner JSX for each section (shared by accordion and tabs) ----

  const basicInner = (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">基本設定</CardTitle>
          <CardDescription>まずここから。資産・生活費を入力してFIRE時期を計算します</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <SliderField
            label="現金・預金"
            tooltip="銀行口座の合計残高です（普通・定期・財形など）。保険の積立金・外貨預金・金（きん）も現金としてカウントしてください。株式・NISAは投資タブで入力します"
            value={config.cashAssets ?? 0}
            onChange={(value) => onConfigChange({ ...config, cashAssets: value })}
            min={0} max={50000000} step={500000}
            format={(v) => formatCurrency(v, true)}
          />

          <div className="space-y-2">
            <FieldLabel label="生活費の算出方法" tooltip="「固定費」は手軽でシンプル。「ライフステージ」にすると子育て期は生活費が増え、老後は減る現実に近い計算になります" />
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
              <p className="text-xs text-muted-foreground">月間生活費を一定額として計算します。住宅ローン・教育費は別途ライフタブで入力します。</p>
              <SliderField
                label="月間生活費"
                tooltip="食費・光熱費・通信費など毎月かかる生活費の合計。住宅ローンや教育費は後のライフタブで入力します"
                value={config.monthlyExpenses}
                onChange={(value) => onConfigChange({ ...config, monthlyExpenses: value })}
                min={100000} max={1000000} step={10000}
                format={(v) => `${formatCurrency(v)}/月`}
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
                  { key: 'emptyNestActive', label: '独立後(-64歳)', defaultVal: 258 },
                  { key: 'emptyNestSenior', label: 'シニア(65-74歳)', defaultVal: 224 },
                  { key: 'emptyNestElderly', label: '後期高齢(75歳-)', defaultVal: 193 },
                ].map(({ key, label, defaultVal }) => (
                  <div key={key} className="space-y-1">
                    <Label className="text-xs text-muted-foreground">{label}</Label>
                    <input
                      type="number"
                      min={0}
                      max={1000}
                      value={Math.round((config.lifecycleExpenses?.[key as keyof LifecycleExpenseConfig] ?? defaultVal * 10000) / 10000)}
                      onChange={(e) => {
                        const val = Math.max(0, Number(e.target.value)) * 10000
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

        </CardContent>
      </Card>
    </div>
  )

  const incomeInner = (
    <div className="space-y-4">
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
                {config.person2 ? "あり" : "なし"}
              </Label>
              <Switch
                id="spouse-toggle"
                checked={config.person2 != null}
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
            />
          </CardContent>
        )}
      </Card>
    </div>
  )

  const investmentInner = (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">投資設定</CardTitle>
          <CardDescription>資産運用の想定リターンとリスクを設定します</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <SliderField
            label="期待リターン"
            tooltip="毎年平均何%増えると想定するかです。全世界株インデックスなら5〜7%が過去実績です"
            value={config.investmentReturn * 100}
            onChange={(value) => onConfigChange({ ...config, investmentReturn: value / 100 })}
            min={1} max={10} step={0.1}
            format={(v) => `${v.toFixed(1)}%`}
          />

          <SliderField
            label="リスク（標準偏差）"
            tooltip="「当たり年と外れ年の差」です。大きくするほどリーマンショック級の暴落も計算に含まれます。株式なら15〜20%が過去実績"
            value={config.investmentVolatility * 100}
            onChange={(value) => onConfigChange({ ...config, investmentVolatility: value / 100 })}
            min={5} max={30} step={0.5}
            format={(v) => `${v.toFixed(1)}%`}
          />

        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">株式（課税口座）</CardTitle>
          <CardDescription>証券会社の特定口座にある株・投信の現在残高を入力します</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <SliderField
            label="株式評価額"
            tooltip="証券会社の特定口座にある株・投信の今の評価額。NISA口座・iDeCo口座の残高は含めません"
            value={config.stocks ?? 0}
            onChange={(newStocksValue) => onConfigChange({
              ...config,
              stocks: newStocksValue,
              stocksCostBasis: Math.min(config.stocksCostBasis ?? 0, newStocksValue),
            })}
            min={0} max={100000000} step={1000000}
            format={(v) => formatCurrency(v, true)}
          />

          <SliderField
            label="株式取得原価"
            tooltip="株を最初に買ったときの合計金額。「含み益 = 評価額 − 取得原価」の部分に売却時20%の税金がかかります"
            value={config.stocksCostBasis ?? 0}
            onChange={(value) => onConfigChange({ ...config, stocksCostBasis: value })}
            min={0} max={(config.stocks ?? 0) > 0 ? (config.stocks ?? 0) : 100000000} step={500000}
            format={(v) => formatCurrency(v, true)}
          />

          {(() => {
            const unrealizedGain = (config.stocks ?? 0) - (config.stocksCostBasis ?? 0)
            return (
              <p className={`text-xs ${unrealizedGain >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                含み益: {unrealizedGain >= 0 ? '+' : ''}{formatCurrency(unrealizedGain, true)}
              </p>
            )
          })()}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Wallet className="h-4 w-4" />
            その他資産
          </CardTitle>
          <CardDescription>定期預金・外貨預金・金（きん）など、株式以外の運用資産を入力します</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <SliderField
            label="現在評価額"
            tooltip="定期預金・外貨預金・金（きん）など、現金・株式・NISA以外の資産の合計額です"
            value={config.otherAssets ?? 0}
            onChange={(value) => onConfigChange({ ...config, otherAssets: value })}
            min={0} max={50000000} step={500000}
            format={(v) => formatCurrency(v, true)}
          />

          <SliderField
            label="期待リターン"
            tooltip="この資産の年間期待リターンです。定期預金なら0〜1%、外貨預金なら2〜5%、金（きん）なら2〜4%が目安です"
            value={(config.otherAssetsReturn ?? 0.02) * 100}
            onChange={(value) => onConfigChange({ ...config, otherAssetsReturn: value / 100 })}
            min={0} max={8} step={0.1}
            format={(v) => `${v.toFixed(1)}%`}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <PiggyBank className="h-4 w-4" />
              新NISA
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
          <CardDescription>
            {config.nisa.enabled
              ? `年${formatCurrency(config.nisa.annualContribution, true)}を積み立て中。運用益・売却益は非課税・無期限`
              : "運用益・売却益が非課税・無期限。年最大360万円、生涯1800万円まで"}
          </CardDescription>
        </CardHeader>
        {config.nisa.enabled && (
          <CardContent className="space-y-6">
            <SliderField
              label="現在のNISA評価額"
              tooltip="今すでにNISA口座にある資産の評価額を入力してください。証券会社のアプリで確認できます"
              value={config.nisa.balance ?? 0}
              onChange={(value) => onConfigChange({ ...config, nisa: { ...config.nisa, balance: value } })}
              min={0} max={18000000} step={100000}
              format={(v) => formatCurrency(v, true)}
            />
            <SliderField
              label="年間投資額"
              tooltip="つみたて投資枠（年120万円まで）と成長投資枠（年240万円まで）の合計。毎年いくら積み立てているか入力してください"
              value={config.nisa.annualContribution}
              onChange={(value) => onConfigChange({ ...config, nisa: { ...config.nisa, annualContribution: value } })}
              min={0} max={3600000} step={100000}
              format={(v) => formatCurrency(v, true)}
            />
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
          <CardDescription>
            {config.ideco.enabled
              ? `月${formatCurrency(config.ideco.monthlyContribution)}を拠出中。掛金は全額所得控除（${config.ideco.withdrawalStartAge ?? 60}歳から受取）`
              : "掛金が全額所得控除になる老後専用の積立口座。60歳まで引き出し不可"}
          </CardDescription>
        </CardHeader>
        {config.ideco.enabled && (
          <CardContent className="space-y-6">
            <SliderField
              label="月額拠出額"
              tooltip="掛金が全額「所得控除」になるので税金が減ります。ただし60歳まで絶対に引き出せないのが注意点です"
              value={config.ideco.monthlyContribution}
              onChange={(value) => onConfigChange({ ...config, ideco: { ...config.ideco, monthlyContribution: value } })}
              min={5000} max={68000} step={1000}
              format={(v) => `${formatCurrency(v)}/月`}
            />
            <SliderField
              label="受取開始年齢"
              tooltip="FIREが早くても60歳まで受け取れません。受取時に税控除があります"
              value={config.ideco.withdrawalStartAge ?? 60}
              onChange={(value) => onConfigChange({ ...config, ideco: { ...config.ideco, withdrawalStartAge: value } })}
              min={60} max={75} step={1}
              format={(v) => `${v}歳`}
            />
          </CardContent>
        )}
      </Card>
    </div>
  )

  const lifeInner = (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Baby className="h-4 w-4" />
            子育て
          </CardTitle>
          <CardDescription>子どもの人数・誕生年を入力すると、教育費と児童手当を自動計算します</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <SliderField
            label="子どもの人数"
            tooltip="子どもの人数を入力すると、教育費と児童手当が自動でFIRE計算に反映されます"
            value={config.children.length}
            onChange={(value) => {
              const currentYear = new Date().getFullYear()
              const children = Array.from({ length: value }, (_, i) => {
                const existing = config.children[i]
                const educationPath = existing?.educationPath ?? "mixed" as const
                return {
                  birthYear: existing?.birthYear ?? currentYear + i * 2,
                  educationPath,
                  educationPaths: existing?.educationPaths ?? EDUCATION_PATHS_PRESETS[educationPath],
                }
              })
              onConfigChange({ ...config, children })
            }}
            min={0} max={3} step={1}
            format={(v) => `${v}人`}
          />

          {config.children.map((child, index) => (
            <div key={index} className="space-y-3 rounded-lg bg-muted/50 p-4">
              <p className="text-sm font-medium">子ども {index + 1}</p>
              <SliderField
                label="誕生年"
                tooltip="西暦で入力してください（例: 2024年生まれなら2024）。学費の発生タイミングを自動で計算します"
                value={child.birthYear}
                onChange={(value) => {
                  const newChildren = [...config.children]
                  newChildren[index] = { ...child, birthYear: value }
                  onConfigChange({ ...config, children: newChildren })
                }}
                min={2020} max={2035} step={1}
                format={(v) => `${v}年`}
              />
              <div className="space-y-2 pt-2">
                <div className="flex items-center gap-3 flex-wrap">
                  <FieldLabel label="教育費" tooltip="ステージごとに公立・私立を選択できます。プリセットで一括設定も可能です" />
                  <div className="flex gap-1.5">
                    {(["public", "mixed", "private"] as const).map((preset) => (
                      <button
                        key={preset}
                        onClick={() => {
                          const newChildren = [...config.children]
                          newChildren[index] = {
                            ...child,
                            educationPath: preset,
                            educationPaths: EDUCATION_PATHS_PRESETS[preset],
                          }
                          onConfigChange({ ...config, children: newChildren })
                        }}
                        className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                          !child.educationPaths && child.educationPath === preset
                            ? "bg-primary text-primary-foreground"
                            : JSON.stringify(child.educationPaths) === JSON.stringify(EDUCATION_PATHS_PRESETS[preset])
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted hover:bg-muted-foreground/10"
                        }`}
                      >
                        {preset === "public" ? "全公立" : preset === "private" ? "全私立" : "混合"}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-5 gap-1 text-xs">
                  {([
                    { key: "kindergarten" as keyof ChildEducationPaths, label: "幼稚園" },
                    { key: "elementary"   as keyof ChildEducationPaths, label: "小学校" },
                    { key: "juniorHigh"   as keyof ChildEducationPaths, label: "中学校" },
                    { key: "highSchool"   as keyof ChildEducationPaths, label: "高校" },
                    { key: "university"   as keyof ChildEducationPaths, label: "大学" },
                  ] as const).map(({ key, label }) => {
                    const paths = child.educationPaths ?? EDUCATION_PATHS_PRESETS[child.educationPath]
                    const current = paths[key]
                    return (
                      <div key={key} className="space-y-0.5 text-center">
                        <p className="text-muted-foreground text-[10px]">{label}</p>
                        <div className="flex flex-col gap-0.5">
                          {(["public", "private"] as const).map((v) => (
                            <button
                              key={v}
                              onClick={() => {
                                const newPaths: ChildEducationPaths = {
                                  ...(child.educationPaths ?? EDUCATION_PATHS_PRESETS[child.educationPath]),
                                  [key]: v,
                                }
                                const newChildren = [...config.children]
                                newChildren[index] = { ...child, educationPaths: newPaths }
                                onConfigChange({ ...config, children: newChildren })
                              }}
                              className={`rounded px-1 py-0.5 text-[10px] font-medium transition-colors ${
                                current === v
                                  ? "bg-primary text-primary-foreground"
                                  : "bg-muted hover:bg-muted-foreground/10"
                              }`}
                            >
                              {v === "public" ? "公立" : "私立"}
                            </button>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
              <div className="pt-2">
                <SliderField
                  label="保育料（0〜2歳）"
                  tooltip="認可保育園の年額費用です。認可外は高くなります。0歳児クラスは月5〜6万円が目安"
                  value={child.daycareAnnualCost ?? 360_000}
                  onChange={(value) => {
                    const newChildren = [...config.children]
                    newChildren[index] = { ...child, daycareAnnualCost: value }
                    onConfigChange({ ...config, children: newChildren })
                  }}
                  min={0} max={1_200_000} step={10_000}
                  format={(v) => `${(v / 10_000).toFixed(0)}万円/年`}
                />
              </div>
            </div>
          ))}

          {config.children.length > 0 && (
            <div className="space-y-3 rounded-lg border border-accent/30 bg-accent/5 p-3">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-medium text-accent-foreground/80 bg-accent/20 px-1.5 py-0.5 rounded-full">このツールの強み</span>
              </div>
              <FieldLabel label="産休・育休取得" tooltip="育休を取る場合、給与の代わりに育児休業給付金が支給されます" />
              <p className="text-xs text-muted-foreground">育休を取る子どもを全て選択</p>
              {config.children.map((child, index) => (
                <div key={child.birthYear} className="space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">子ども{index + 1}（{child.birthYear}年生まれ）</p>
                  <div className="flex gap-4 pl-2">
                    {[
                      { personKey: 'person1' as const, personLabel: '本人', person: config.person1, update: updatePerson1 },
                      ...(config.person2 ? [{ personKey: 'person2' as const, personLabel: '配偶者', person: config.person2, update: updatePerson2 }] : []),
                    ].map(({ personKey, personLabel, person, update }) => {
                      const checked = (person.maternityLeaveChildBirthYears ?? []).includes(child.birthYear)
                      return (
                        <div key={personKey} className="flex items-center gap-1.5">
                          <input
                            type="checkbox"
                            id={`maternity-${personKey}-${child.birthYear}`}
                            checked={checked}
                            onChange={(e) => {
                              const current = person.maternityLeaveChildBirthYears ?? []
                              const updated = e.target.checked
                                ? [...current, child.birthYear]
                                : current.filter(y => y !== child.birthYear)
                              update({ ...person, maternityLeaveChildBirthYears: updated })
                            }}
                            className="h-4 w-4 rounded border-gray-300"
                          />
                          <label htmlFor={`maternity-${personKey}-${child.birthYear}`} className="text-sm">{personLabel}</label>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center justify-between pt-2 border-t">
            <div>
              <FieldLabel label="児童手当" tooltip="2024年10月〜の制度。0〜2歳は1.5万円/月、3〜17歳は1万円/月（第3子以降は全年齢3万円/月）。所得制限なし。第3子のカウントは22歳未満のきょうだいを含む" />
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
              <CardDescription>
                {config.postFireIncome
                  ? `月${formatCurrency(config.postFireIncome.monthlyAmount)}を${config.postFireIncome.untilAge}歳まで稼ぐ設定でシミュレーション中`
                  : "完全にやめるのではなく、パートや仕事を続けながらFIREするシナリオです"}
              </CardDescription>
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
            <SliderField
              label="月収（税引き前）"
              tooltip="FIRE後も少し働いて得る月収を入力します。月10万円でも計算が大きく変わります"
              value={config.postFireIncome.monthlyAmount}
              onChange={(value) => onConfigChange({
                ...config,
                postFireIncome: { ...(config.postFireIncome as PostFireIncomeConfig), monthlyAmount: value },
              })}
              min={0} max={500000} step={10000}
              format={(v) => `${formatCurrency(v)}/月`}
            />

            <SliderField
              label="終了年齢"
              tooltip="ここまでは働いて、それ以降は年金生活に切り替えるイメージです"
              value={config.postFireIncome.untilAge}
              onChange={(value) => onConfigChange({
                ...config,
                postFireIncome: { ...(config.postFireIncome as PostFireIncomeConfig), untilAge: value },
              })}
              min={40} max={80} step={1}
              format={(v) => `${v}歳まで`}
            />
          </CardContent>
        )}
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">住居</CardTitle>
          <CardDescription>
            {config.rentToPurchaseYear !== undefined
              ? `賃貸中→${config.rentToPurchaseYear}年に購入予定（月${formatCurrency(config.monthlyRent ?? 0)}の家賃をそれまで計上）`
              : (config.monthlyRent ?? 0) > 0
              ? `賃貸 — 月${formatCurrency(config.monthlyRent ?? 0)}を毎年の支出に計上中`
              : "持ち家（または住居費を生活費に含める場合）"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            {(['owned', 'rented', 'future'] as const).map(type => {
              const active =
                type === 'future'  ? config.rentToPurchaseYear !== undefined :
                type === 'rented'  ? config.rentToPurchaseYear === undefined && (config.monthlyRent ?? 0) > 0 :
                                     config.rentToPurchaseYear === undefined && (config.monthlyRent ?? 0) === 0
              return (
                <button
                  key={type}
                  onClick={() => {
                    const currentYear = new Date().getFullYear()
                    if (type === 'owned') {
                      onConfigChange({ ...config, monthlyRent: 0, rentToPurchaseYear: undefined, purchaseDownPayment: undefined })
                    } else if (type === 'rented') {
                      onConfigChange({ ...config, monthlyRent: (config.monthlyRent && config.monthlyRent > 0) ? config.monthlyRent : 100_000, rentToPurchaseYear: undefined, purchaseDownPayment: undefined })
                    } else {
                      onConfigChange({ ...config, monthlyRent: (config.monthlyRent && config.monthlyRent > 0) ? config.monthlyRent : 100_000, rentToPurchaseYear: currentYear + 5, purchaseDownPayment: 5_000_000 })
                    }
                  }}
                  className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                    active ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/80'
                  }`}
                >
                  {type === 'owned' ? '持ち家' : type === 'rented' ? '賃貸' : '将来購入'}
                </button>
              )
            })}
          </div>

          {/* 賃貸 or 将来購入: 月額家賃 */}
          {((config.monthlyRent ?? 0) > 0 || config.rentToPurchaseYear !== undefined) && (
            <SliderField
              label="現在の月額家賃"
              tooltip="管理費・駐車場代など毎月かかる住居費の合計。更新料は生活費に含めてください"
              value={config.monthlyRent ?? 0}
              onChange={(value) => onConfigChange({ ...config, monthlyRent: value })}
              min={30_000} max={500_000} step={5_000}
              format={(v) => `${formatCurrency(v)}/月`}
            />
          )}

          {/* 将来購入モード専用 */}
          {config.rentToPurchaseYear !== undefined && (
            <>
              <SliderField
                label="購入予定年"
                tooltip="この年に持ち家に切り替わります。それ以前は家賃を、この年に頭金を一括計上します。購入後はローンカードの設定が適用されます"
                value={config.rentToPurchaseYear}
                onChange={(value) => onConfigChange({ ...config, rentToPurchaseYear: value })}
                min={new Date().getFullYear()} max={2050} step={1}
                format={(v) => `${v}年`}
              />
              <SliderField
                label="頭金"
                tooltip="購入時に一括で払う自己資金です。購入予定年の支出として計上されます"
                value={config.purchaseDownPayment ?? 5_000_000}
                onChange={(value) => onConfigChange({ ...config, purchaseDownPayment: value })}
                min={0} max={30_000_000} step={500_000}
                format={(v) => `${(v / 10_000).toFixed(0)}万円`}
              />
              <p className="text-xs text-muted-foreground">
                購入後のローン返済は「住宅ローン」カードで設定してください
              </p>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">住宅ローン</CardTitle>
              <CardDescription>
                {config.mortgage
                  ? `月${formatCurrency(config.mortgage.monthlyPayment)}を${config.mortgage.endYear}年まで返済する設定でシミュレーション中`
                  : "ローン返済額をFIRE計算に含めます。完済後はキャッシュフローが改善します"}
              </CardDescription>
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
        {config.mortgage !== null && config.mortgage !== undefined && (() => {
          const m = config.mortgage!
          const isDetail = m.loanAmount !== undefined
          const currentYear = new Date().getFullYear()
          const loanAmount    = m.loanAmount    ?? 30_000_000
          const interestRate  = m.interestRate  ?? 0.005
          const loanTermYears = m.loanTermYears ?? 35
          const loanStartYear = m.loanStartYear ?? currentYear
          const loanType      = m.loanType      ?? "variable"
          const variableRateForecast = m.variableRateForecast ?? 0.02

          function applyDetail(updates: Partial<typeof m>) {
            const next = { ...m, ...updates }
            // 詳細入力時は月額・完済年を自動計算
            if (next.loanAmount !== undefined && next.interestRate !== undefined && next.loanTermYears !== undefined && next.loanStartYear !== undefined) {
              next.monthlyPayment = Math.round(calcMortgageMonthlyPayment(next.loanAmount, next.interestRate, next.loanTermYears))
              next.endYear = next.loanStartYear + next.loanTermYears
            }
            onConfigChange({ ...config, mortgage: next })
          }

          return (
            <CardContent className="space-y-5">
              {/* モード切替 */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">借入条件から計算</span>
                <Switch
                  checked={isDetail}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      applyDetail({ loanAmount, interestRate, loanTermYears, loanStartYear, loanType })
                    } else {
                      const { loanAmount: _a, interestRate: _r, loanTermYears: _t, loanStartYear: _s, loanType: _l, variableRateForecast: _v, ...simple } = m
                      onConfigChange({ ...config, mortgage: simple })
                    }
                  }}
                />
              </div>

              {!isDetail ? (
                <>
                  <SliderField
                    label="月額返済額"
                    tooltip="毎月の住宅ローン返済額です。完済年まで支出として計算されます"
                    value={m.monthlyPayment}
                    onChange={(value) => onConfigChange({ ...config, mortgage: { ...m, monthlyPayment: value } })}
                    min={30000} max={300000} step={5000}
                    format={(v) => `${formatCurrency(v)}/月`}
                  />
                  <SliderField
                    label="完済年"
                    tooltip="ローンが終わる予定の西暦年。完済後は月々の支出が減るので、FIREが近づきます"
                    value={m.endYear}
                    onChange={(value) => onConfigChange({ ...config, mortgage: { ...m, endYear: value } })}
                    min={2025} max={2060} step={1}
                    format={(v) => `${v}年`}
                  />
                </>
              ) : (
                <>
                  {/* 借入額 */}
                  <SliderField
                    label="借入額"
                    tooltip="銀行から借りる金額です。物件価格から頭金を引いた額を入力します"
                    value={loanAmount}
                    onChange={(value) => applyDetail({ loanAmount: value })}
                    min={1_000_000} max={80_000_000} step={500_000}
                    format={(v) => `${(v / 10_000).toFixed(0)}万円`}
                  />
                  {/* 借入開始年 */}
                  <SliderField
                    label="借入開始年"
                    tooltip="ローン開始の年です。変動金利の場合、5年後の金利見直しタイミングを計算するために使います"
                    value={loanStartYear}
                    onChange={(value) => applyDetail({ loanStartYear: value })}
                    min={2020} max={2035} step={1}
                    format={(v) => `${v}年`}
                  />
                  {/* 返済期間 */}
                  <SliderField
                    label="返済期間"
                    tooltip="ローンの借入期間です。一般的には35年が最長です"
                    value={loanTermYears}
                    onChange={(value) => applyDetail({ loanTermYears: value })}
                    min={5} max={35} step={1}
                    format={(v) => `${v}年（${loanStartYear + v}年完済）`}
                  />
                  {/* 金利タイプ */}
                  <div className="space-y-2">
                    <FieldLabel label="金利タイプ" tooltip="固定金利は返済期間中ずっと同じ金利。変動金利は市場によって変わります。日本の住宅ローンの約7割は変動金利です" />
                    <div className="flex gap-2">
                      {(["variable", "fixed"] as const).map((t) => (
                        <button
                          key={t}
                          onClick={() => applyDetail({ loanType: t })}
                          className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                            loanType === t ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted-foreground/10"
                          }`}
                        >
                          {t === "fixed" ? "固定金利" : "変動金利"}
                        </button>
                      ))}
                    </div>
                  </div>
                  {/* 現在の金利 */}
                  <SliderField
                    label={loanType === "fixed" ? "適用金利" : "現在の金利（変動）"}
                    tooltip={loanType === "fixed" ? "ローン期間中ずっと適用される金利です" : "現在の適用金利です。変動金利の目安は0.3〜1.0%程度（2024年時点）"}
                    value={Math.round(interestRate * 10000)}
                    onChange={(value) => applyDetail({ interestRate: value / 10000 })}
                    min={10} max={400} step={5}
                    format={(v) => `${(v / 100).toFixed(2)}%`}
                  />
                  {/* 変動金利: 将来想定金利 */}
                  {loanType === "variable" && (
                    <SliderField
                      label="将来想定金利"
                      tooltip="借入5年後の金利見直し時に、この金利に上昇したと仮定してシミュレーションします。最悪シナリオの確認に使えます"
                      value={Math.round(variableRateForecast * 10000)}
                      onChange={(value) => applyDetail({ variableRateForecast: value / 10000 })}
                      min={10} max={500} step={5}
                      format={(v) => `${(v / 100).toFixed(2)}%`}
                    />
                  )}
                  {/* 自動計算結果 */}
                  <div className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground space-y-1">
                    <p>月額返済: <span className="font-mono font-medium text-foreground">{formatCurrency(m.monthlyPayment)}/月</span></p>
                    {loanType === "variable" && (
                      <p>5年後（金利{(variableRateForecast * 100).toFixed(2)}%）の月額: <span className="font-mono font-medium text-foreground">
                        {formatCurrency(Math.round((() => {
                          const elapsed = 5 * 12
                          const remaining = Math.max(0, loanAmount * Math.pow(1 + interestRate / 12, elapsed)
                            - m.monthlyPayment * (Math.pow(1 + interestRate / 12, elapsed) - 1) / (interestRate / 12))
                          return calcMortgageMonthlyPayment(remaining, variableRateForecast, loanTermYears - 5)
                        })()))}/月
                      </span></p>
                    )}
                  </div>
                </>
              )}
            </CardContent>
          )
        })()}
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">固定資産税</CardTitle>
          <CardDescription>持ち家の場合に毎年かかる税金です。戸建ては年10〜20万円、マンションは5〜15万円が目安</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <SliderField
            label="年額"
            tooltip="固定資産税＋都市計画税の合計額を入力してください。市区町村から毎年5月ごろに通知が届きます"
            value={config.propertyTaxAnnual ?? 0}
            onChange={(value) => onConfigChange({ ...config, propertyTaxAnnual: value })}
            min={0} max={500000} step={10000}
            format={(v) => `${(v / 10_000).toFixed(0)}万円/年`}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">大規模修繕費</CardTitle>
              <CardDescription>
                {(config.maintenanceCosts ?? []).length > 0
                  ? `${((config.maintenanceCosts ?? [])[0].amount / 10_000).toFixed(0)}万円を${(config.maintenanceCosts ?? [])[0].intervalYears}年ごとに計上中`
                  : "外壁・屋根などの大型修繕費を周期的に計上します"}
              </CardDescription>
            </div>
            <Switch
              id="maintenance-toggle"
              checked={(config.maintenanceCosts ?? []).length > 0}
              onCheckedChange={(checked) => {
                if (checked) {
                  onConfigChange({ ...config, maintenanceCosts: [{ amount: 1_500_000, intervalYears: 15, firstYear: new Date().getFullYear() + 10, label: '大規模修繕' }] })
                } else {
                  onConfigChange({ ...config, maintenanceCosts: [] })
                }
              }}
            />
          </div>
        </CardHeader>
        {(config.maintenanceCosts ?? []).length > 0 && (() => {
          const mc = config.maintenanceCosts![0]
          return (
            <CardContent className="space-y-4">
              <SliderField
                label="1回あたりの費用"
                tooltip="外壁塗装・屋根補修・給湯器交換など大型修繕の合計費用。戸建ては100〜200万円が目安"
                value={mc.amount}
                onChange={(value) => onConfigChange({ ...config, maintenanceCosts: [{ ...mc, amount: value }] })}
                min={500_000} max={5_000_000} step={100_000}
                format={(v) => `${(v / 10_000).toFixed(0)}万円`}
              />
              <SliderField
                label="修繕サイクル"
                tooltip="何年ごとに大規模修繕が必要か。外壁・屋根は15〜20年が一般的です"
                value={mc.intervalYears}
                onChange={(value) => onConfigChange({ ...config, maintenanceCosts: [{ ...mc, intervalYears: value }] })}
                min={5} max={30} step={1}
                format={(v) => `${v}年ごと`}
              />
              <SliderField
                label="初回発生年"
                tooltip="最初に大規模修繕が発生する予定の西暦年"
                value={mc.firstYear}
                onChange={(value) => onConfigChange({ ...config, maintenanceCosts: [{ ...mc, firstYear: value }] })}
                min={new Date().getFullYear()} max={2060} step={1}
                format={(v) => `${v}年`}
              />
            </CardContent>
          )
        })()}
      </Card>
    </div>
  )

  const advancedInner = (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">シミュレーション設定</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between py-1">
            <FieldLabel
              label="モンテカルロシミュレーション"
              tooltip="1000通りの市場シナリオでFIRE成功確率を計算します。OFFにすると平均シナリオのみ（計算が速くなります）"
            />
            <Switch
              id="monte-carlo-toggle-panel"
              checked={useMonteCarlo}
              onCheckedChange={onMonteCarloChange}
            />
          </div>
          <SliderField
            label="インフレ率"
            tooltip="年金・教育費・住宅ローンなどの計算に使う物価上昇率です。日銀目標の2%が一般的です"
            value={config.inflationRate * 100}
            onChange={(value) => onConfigChange({ ...config, inflationRate: value / 100 })}
            min={0} max={3} step={0.1}
            format={(v) => `${v.toFixed(1)}%`}
          />
          <SliderField
            label="生活費上昇率"
            tooltip="食費・日用品など毎月の生活費が毎年どれくらい上がるかです。インフレ率と独立して設定でき、1〜2%が目安です"
            value={config.expenseGrowthRate * 100}
            onChange={(value) => onConfigChange({ ...config, expenseGrowthRate: value / 100 })}
            min={0} max={3} step={0.1}
            format={(v) => `${v.toFixed(1)}%`}
          />
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
              { value: 'guardrail', label: '暴落時支出抑制' },
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
          <p className="text-xs text-muted-foreground">
            {(config.withdrawalStrategy ?? 'fixed') === 'fixed' && '毎年一定額を取り崩します。生活水準が安定しますが、相場が悪い年も同額を引き出します。'}
            {(config.withdrawalStrategy ?? 'fixed') === 'percentage' && '毎年資産残高の一定割合を取り崩します。資産が増えれば支出も増え、減れば自然に支出も減ります。'}
            {(config.withdrawalStrategy ?? 'fixed') === 'guardrail' && '資産が大幅に下落した際に支出を自動削減します。暴落時のリスクを抑えつつ、好況時は支出を維持します。'}
          </p>

          {(config.withdrawalStrategy ?? 'fixed') === 'guardrail' && (
            <div className="space-y-4">
              <SliderField
                label="裁量支出比率"
                tooltip="生活費の中で「暴落時に削れる部分」の割合。旅行・外食・服などが対象。30%が一般的な想定です"
                value={(config.guardrailConfig?.discretionaryRatio ?? 0.3) * 100}
                onChange={(value) => onConfigChange({
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
                min={10} max={50} step={5}
                format={(v) => `${v.toFixed(0)}%`}
              />

              <p className="text-xs font-medium text-muted-foreground pt-1">下落閾値と裁量支出削減率</p>

              <SliderField
                label="閾値1（軽微な下落）"
                tooltip="資産がピークからこの割合以上下落するとフェーズ1の削減が発動します"
                value={(config.guardrailConfig?.threshold1 ?? -0.10) * 100}
                onChange={(value) => onConfigChange({
                  ...config,
                  guardrailConfig: { ...defaultGuardrail, ...config.guardrailConfig, threshold1: value / 100 }
                })}
                min={-30} max={-5} step={1}
                format={(v) => `${v.toFixed(0)}%`}
                small
              />
              <SliderField
                label="削減率1"
                tooltip="フェーズ1発動時に裁量支出を削減する割合（例: 40%削減 = 裁量支出が60%になる）"
                value={(config.guardrailConfig?.reduction1 ?? 0.40) * 100}
                onChange={(value) => onConfigChange({
                  ...config,
                  guardrailConfig: { ...defaultGuardrail, ...config.guardrailConfig, reduction1: value / 100 }
                })}
                min={10} max={70} step={5}
                format={(v) => `${v.toFixed(0)}%削減`}
                small
              />

              <SliderField
                label="閾値2（中程度の下落）"
                tooltip="資産がピークからこの割合以上下落するとフェーズ2の削減が発動します"
                value={(config.guardrailConfig?.threshold2 ?? -0.20) * 100}
                onChange={(value) => onConfigChange({
                  ...config,
                  guardrailConfig: { ...defaultGuardrail, ...config.guardrailConfig, threshold2: value / 100 }
                })}
                min={-40} max={-10} step={1}
                format={(v) => `${v.toFixed(0)}%`}
                small
              />
              <SliderField
                label="削減率2"
                tooltip="フェーズ2発動時に裁量支出を削減する割合"
                value={(config.guardrailConfig?.reduction2 ?? 0.80) * 100}
                onChange={(value) => onConfigChange({
                  ...config,
                  guardrailConfig: { ...defaultGuardrail, ...config.guardrailConfig, reduction2: value / 100 }
                })}
                min={40} max={95} step={5}
                format={(v) => `${v.toFixed(0)}%削減`}
                small
              />

              <SliderField
                label="閾値3（深刻な下落）"
                tooltip="資産がピークからこの割合以上下落するとフェーズ3の削減が発動します。これ以上の下落でも同じ削減率が適用されます"
                value={(config.guardrailConfig?.threshold3 ?? -0.35) * 100}
                onChange={(value) => onConfigChange({
                  ...config,
                  guardrailConfig: { ...defaultGuardrail, ...config.guardrailConfig, threshold3: value / 100 }
                })}
                min={-60} max={-20} step={1}
                format={(v) => `${v.toFixed(0)}%`}
                small
              />
              <SliderField
                label="削減率3"
                tooltip="フェーズ3発動時の削減率。ほぼ必須支出のみで生活するレベルに設定するのが一般的です"
                value={(config.guardrailConfig?.reduction3 ?? 0.95) * 100}
                onChange={(value) => onConfigChange({
                  ...config,
                  guardrailConfig: { ...defaultGuardrail, ...config.guardrailConfig, reduction3: value / 100 }
                })}
                min={60} max={100} step={5}
                format={(v) => `${v.toFixed(0)}%削減`}
                small
              />
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">FIRE後の社会保険料</CardTitle>
          <CardDescription>FIREした後に自分で支払う社会保険料の計算設定です。通常は変更不要です</CardDescription>
        </CardHeader>
        <CardContent>
          <details className="group">
            <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground list-none flex items-center gap-1">
              <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
              詳細設定を表示
            </summary>
            <div className="mt-4 space-y-4">
              <SliderField
                label="医療分所得割率"
                tooltip="国保の医療費分として収入に対してかかる率。自治体で異なりますが全国平均は約11%です"
                value={config.postFireSocialInsurance.nhisoIncomeRate * 100}
                onChange={(value) => onConfigChange({
                  ...config,
                  postFireSocialInsurance: { ...config.postFireSocialInsurance, nhisoIncomeRate: value / 100 }
                })}
                min={5} max={15} step={0.01}
                format={(v) => `${v.toFixed(2)}%`}
                small
              />

              <SliderField
                label="後期高齢者支援金分所得割率"
                tooltip="国保保険料のうち「高齢者支援のための上乗せ分」の料率（全国平均約2.6%）です"
                value={config.postFireSocialInsurance.nhisoSupportIncomeRate * 100}
                onChange={(value) => onConfigChange({
                  ...config,
                  postFireSocialInsurance: { ...config.postFireSocialInsurance, nhisoSupportIncomeRate: value / 100 }
                })}
                min={1} max={5} step={0.01}
                format={(v) => `${v.toFixed(2)}%`}
                small
              />

              <SliderField
                label="均等割（1人あたり）"
                tooltip="収入がゼロでも1人あたり年約5万円かかる定額の国保保険料です"
                value={config.postFireSocialInsurance.nhisoFixedAmountPerPerson}
                onChange={(value) => onConfigChange({
                  ...config,
                  postFireSocialInsurance: { ...config.postFireSocialInsurance, nhisoFixedAmountPerPerson: value }
                })}
                min={10000} max={100000} step={1000}
                format={(v) => formatCurrency(v)}
                small
              />

              <SliderField
                label="平等割（世帯）"
                tooltip="世帯に1つかかる定額料金です。自治体によっては「均等割のみ」でここは0円の場合もあります"
                value={config.postFireSocialInsurance.nhisoHouseholdFixed}
                onChange={(value) => onConfigChange({
                  ...config,
                  postFireSocialInsurance: { ...config.postFireSocialInsurance, nhisoHouseholdFixed: value }
                })}
                min={0} max={100000} step={1000}
                format={(v) => formatCurrency(v)}
                small
              />

              <SliderField
                label="国保年間上限額"
                tooltip="国保には上限があります。高収入でもここまでしかかかりません（現在の上限: 約106万円/年）"
                value={config.postFireSocialInsurance.nhisoMaxAnnual}
                onChange={(value) => onConfigChange({
                  ...config,
                  postFireSocialInsurance: { ...config.postFireSocialInsurance, nhisoMaxAnnual: value }
                })}
                min={500000} max={2000000} step={10000}
                format={(v) => formatCurrency(v, true)}
                small
              />

              <SliderField
                label="国民年金月額保険料"
                tooltip="FIREすると年金を自分で払います。今は月約17,000円。夫婦2人なら月約34,000円です"
                value={config.postFireSocialInsurance.nationalPensionMonthlyPremium}
                onChange={(value) => onConfigChange({
                  ...config,
                  postFireSocialInsurance: { ...config.postFireSocialInsurance, nationalPensionMonthlyPremium: value }
                })}
                min={10000} max={25000} step={100}
                format={(v) => `${formatCurrency(v)}/月`}
                small
              />

              <SliderField
                label="介護分所得割率"
                tooltip="40〜64歳は介護保険料が国保に追加されます（収入の約2%）。65歳以降は年金から天引きになります"
                value={config.postFireSocialInsurance.longTermCareRate * 100}
                onChange={(value) => onConfigChange({
                  ...config,
                  postFireSocialInsurance: { ...config.postFireSocialInsurance, longTermCareRate: value / 100 }
                })}
                min={0.5} max={5} step={0.01}
                format={(v) => `${v.toFixed(2)}%`}
                small
              />

              <SliderField
                label="介護分上限額"
                tooltip="介護保険料にも上限があります（年約17万円）。高収入でもここを超えません"
                value={config.postFireSocialInsurance.longTermCareMax}
                onChange={(value) => onConfigChange({
                  ...config,
                  postFireSocialInsurance: { ...config.postFireSocialInsurance, longTermCareMax: value }
                })}
                min={50000} max={400000} step={10000}
                format={(v) => formatCurrency(v, true)}
                small
              />

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
    </div>
  )

  return (
    <>
      {/* モバイル (lg未満): アコーディオン */}
      <div className="lg:hidden">
        <Accordion type="multiple" value={accordionValues} onValueChange={handleAccordionChange}>
          <AccordionItem value="basic" id="config-basic">
            <AccordionTrigger>
              <span className="flex items-center gap-2"><Wallet className="h-4 w-4" />基本設定</span>
            </AccordionTrigger>
            <AccordionContent>
              {basicInner}
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="income" id="config-income">
            <AccordionTrigger>
              <span className="flex items-center gap-2"><Users className="h-4 w-4" />収入</span>
            </AccordionTrigger>
            <AccordionContent>
              {incomeInner}
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="investment" id="config-invest">
            <AccordionTrigger>
              <span className="flex items-center gap-2"><TrendingUp className="h-4 w-4" />投資</span>
            </AccordionTrigger>
            <AccordionContent>
              {investmentInner}
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="life" id="config-life">
            <AccordionTrigger>
              <span className="flex items-center gap-2"><Baby className="h-4 w-4" />ライフ</span>
            </AccordionTrigger>
            <AccordionContent>
              {lifeInner}
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="advanced" id="config-detail">
            <AccordionTrigger>
              <span className="flex items-center gap-2"><Settings2 className="h-4 w-4" />詳細設定</span>
            </AccordionTrigger>
            <AccordionContent>
              {advancedInner}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>

      {/* PC (lg以上): 既存のタブ */}
      <div className="not-lg:hidden">
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

          <TabsContent value="basic" className="mt-4">
            {basicInner}
          </TabsContent>
          <TabsContent value="income" className="mt-4">
            {incomeInner}
          </TabsContent>
          <TabsContent value="investment" className="mt-4">
            {investmentInner}
          </TabsContent>
          <TabsContent value="life" className="mt-4">
            {lifeInner}
          </TabsContent>
          <TabsContent value="advanced" className="mt-4">
            {advancedInner}
          </TabsContent>
        </Tabs>
      </div>
    </>
  )
}
