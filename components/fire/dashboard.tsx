"use client"

import { useState, useEffect, useCallback } from "react"
import { SimulationConfig, SimulationResult, MonteCarloResult, DEFAULT_CONFIG, runSingleSimulation, runMonteCarloSimulation } from "@/lib/simulator"
import { FireResultCard } from "./fire-result-card"
import { ConfigPanel } from "./config-panel"
import { AssetsChart, IncomeExpenseChart } from "./assets-chart"
import { ScenarioComparison } from "./scenario-comparison"
import { MetricsSummary } from "./metrics-summary"
import { AnnualCashFlowTable } from "./annual-cashflow-table"
import { CashFlowChart } from "./cashflow-chart"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent } from "@/components/ui/card"
import { TooltipProvider } from "@/components/ui/tooltip"
import { BarChart3, Lightbulb, TrendingUp, Info, ShieldCheck, Table2, Lock, Share2, Home, Wallet, Baby, Settings2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { encodeConfig, decodeConfig } from "@/lib/url-state"

// Helper: determine which sections have meaningful input
function getSectionCompletion(config: SimulationConfig) {
  return {
    basic: config.monthlyExpenses > 0,
    income: config.person1.grossIncome > 0,
    invest: (config.cashAssets ?? config.currentAssets ?? 0) > 0 || (config.stocks ?? 0) > 0 || config.nisa.enabled,
    life: config.children.length > 0 || config.mortgage !== null || (config.postFireIncome != null),
    detail: true, // always consider configured
  }
}

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(timer)
    }
  }, [value, delay])

  return debouncedValue
}

export function FireDashboard() {
  const [config, setConfig] = useState<SimulationConfig>(DEFAULT_CONFIG)
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [monteCarloResult, setMonteCarloResult] = useState<MonteCarloResult | null>(null)
  const [isCalculating, setIsCalculating] = useState(false)
  const [useMonteCarlo, setUseMonteCarlo] = useState(true)
  const [copied, setCopied] = useState(false)
  const [activeSection, setActiveSection] = useState<string>("config-basic")

  // Read config from URL hash on mount
  useEffect(() => {
    if (typeof window === 'undefined') return
    const hash = window.location.hash
    if (hash.startsWith('#config=')) {
      const encoded = hash.slice('#config='.length)
      const decoded = decodeConfig(encoded)
      if (decoded !== null) {
        setConfig(decoded)
      }
    }
  }, [])

  // Debounce config changes for smooth slider interactions
  const debouncedConfig = useDebounce(config, 300)

  // Run simulation when config changes
  useEffect(() => {
    setIsCalculating(true)
    
    // Use setTimeout to prevent UI blocking
    const timer = setTimeout(() => {
      const singleResult = runSingleSimulation(debouncedConfig)
      setResult(singleResult)

      if (useMonteCarlo) {
        const mcResult = runMonteCarloSimulation(debouncedConfig, 1000)
        setMonteCarloResult(mcResult)
      } else {
        setMonteCarloResult(null)
      }

      setIsCalculating(false)
    }, 50)

    return () => clearTimeout(timer)
  }, [debouncedConfig, useMonteCarlo])

  // IntersectionObserver: track which accordion section is in view (mobile only)
  useEffect(() => {
    const sectionIds = ["config-basic", "config-income", "config-invest", "config-life", "config-detail"]
    const observers: IntersectionObserver[] = []

    sectionIds.forEach((id) => {
      const el = document.getElementById(id)
      if (!el) return
      const obs = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              setActiveSection(id)
            }
          })
        },
        { threshold: 0.3 }
      )
      obs.observe(el)
      observers.push(obs)
    })

    return () => {
      observers.forEach((obs) => obs.disconnect())
    }
  }, [])

  const handleConfigChange = useCallback((newConfig: SimulationConfig) => {
    setConfig({ ...newConfig, simulationYears: 100 - newConfig.person1.currentAge })
  }, [])

  const handleShare = useCallback(() => {
    const encoded = encodeConfig(config)
    window.location.hash = 'config=' + encoded
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [config])

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background">
        {/* Header */}
        <header className="sticky top-0 z-50 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
          <div className="container mx-auto flex h-16 items-center justify-between px-4">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
                <TrendingUp className="h-5 w-5 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-lg font-semibold tracking-tight hidden lg:block">FIRE シミュレーター</h1>
                <p className="text-xs text-muted-foreground">育休や時短の影響も含めて、あなたのFIRE時期を計算します</p>
              </div>
            </div>
            </div>
        </header>

        {/* KPI Banner */}
        <div className="sticky top-16 z-40 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60 relative overflow-hidden">
          <div className="container mx-auto px-4 h-12 flex items-center justify-center gap-6">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">FIRE達成</span>
              <span className={`text-sm font-semibold tabular-nums transition-opacity duration-200 ${isCalculating ? 'opacity-40' : ''}`}>
                {(() => { const age = monteCarloResult?.medianFireAge ?? result?.fireAge; return age != null ? `${age}歳` : '—' })()}
              </span>
            </div>
            <div className="w-px h-4 bg-border" />
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">
                {monteCarloResult ? '成功率' : '達成率'}
              </span>
              {(() => {
                const rate = monteCarloResult ? monteCarloResult.successRate : (result?.fireAchievementRate ?? 0)
                const colorClass = rate >= 0.8
                  ? 'text-success bg-success/10'
                  : rate >= 0.5
                  ? 'text-accent bg-accent/10'
                  : result ? 'text-destructive bg-destructive/10' : 'text-muted-foreground'
                return (
                  <span className={`text-sm font-semibold tabular-nums px-2 py-0.5 rounded-full transition-all duration-200 ${isCalculating ? 'opacity-40' : ''} ${colorClass}`}>
                    {monteCarloResult
                      ? `${Math.round(monteCarloResult.successRate * 100)}%`
                      : `${Math.round((result?.fireAchievementRate ?? 0) * 100)}%`}
                  </span>
                )
              })()}
            </div>
            <div className="w-px h-4 bg-border" />
            <Button variant="ghost" size="sm" className="h-7 px-2 text-xs gap-1" onClick={handleShare}>
              <Share2 className="h-3.5 w-3.5" />
              {copied ? 'コピーしました！' : 'リンクをコピー'}
            </Button>
          </div>
          {/* Calculating progress indicator */}
          <div className="absolute bottom-0 left-0 right-0 h-0.5">
            {isCalculating && (
              <div className="absolute h-full w-1/4 bg-primary/60 rounded-full animate-slide-right" />
            )}
          </div>
        </div>

        <main className="container mx-auto px-4 py-6 pb-24 lg:pb-6">
          <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
            {/* Left Panel - Configuration */}
            <aside className="space-y-6 order-2 lg:order-1">
              <ConfigPanel config={config} onConfigChange={handleConfigChange} useMonteCarlo={useMonteCarlo} onMonteCarloChange={setUseMonteCarlo} />
              
              {/* Trust indicators */}
              <Card className="border-primary/20 bg-primary/5">
                <CardContent className="flex items-start gap-3 p-4">
                  <ShieldCheck className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-primary">計算方法</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      株価は毎年ランダムに動きます。1000通りの未来を一気に計算して「だいたい何%の確率でFIREできるか」を算出しています。
                    </p>
                    <p className="text-xs text-muted-foreground flex items-center gap-1.5 pt-1 border-t border-primary/10">
                      <Lock className="h-3 w-3 shrink-0 text-primary/70" />
                      <span>入力データはこのブラウザ内にのみ保存。サーバーには送信されません。</span>
                    </p>
                  </div>
                </CardContent>
              </Card>
            </aside>

            {/* Right Panel - Results */}
            <div className="space-y-6 order-1 lg:order-2 min-w-0">
              {/* Key Metrics Summary */}
              <MetricsSummary config={config} result={result} mcResult={monteCarloResult} isCalculating={isCalculating} />
              
              {/* FIRE Result Card */}
              <FireResultCard
                result={result}
                monteCarloResult={monteCarloResult}
                currentAge={config.person1.currentAge}
                isCalculating={isCalculating}
                swr={config.safeWithdrawalRate}
              />

              {/* Charts and Analysis Tabs */}
              <Tabs defaultValue="assets" className="w-full">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="assets" className="flex items-center gap-1 text-xs sm:gap-1.5">
                    <BarChart3 className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">資産推移</span>
                  </TabsTrigger>
                  <TabsTrigger value="cashflow" className="flex items-center gap-1 text-xs sm:gap-1.5">
                    <TrendingUp className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">収支</span>
                  </TabsTrigger>
                  <TabsTrigger value="annual" className="flex items-center gap-1 text-xs sm:gap-1.5">
                    <Table2 className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">年次表</span>
                  </TabsTrigger>
                  <TabsTrigger value="scenarios" className="flex items-center gap-1 text-xs sm:gap-1.5">
                    <Lightbulb className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">次の一手</span>
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="assets" className="mt-4">
                  <AssetsChart
                    result={result}
                    monteCarloResult={monteCarloResult}
                    showPercentiles={false}
                  />
                </TabsContent>

                <TabsContent value="cashflow" className="mt-4 space-y-4">
                  <CashFlowChart result={result} />
                  <IncomeExpenseChart result={result} />
                </TabsContent>

                <TabsContent value="annual" className="mt-4">
                  <AnnualCashFlowTable result={result} />
                </TabsContent>

                <TabsContent value="scenarios" className="mt-4">
                  <ScenarioComparison baseConfig={config} baseResult={result} onConfigChange={handleConfigChange} />
                </TabsContent>
              </Tabs>

              {/* Methodology info */}
              <Card>
                <CardContent className="flex items-start gap-3 p-4">
                  <Info className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div className="text-sm text-muted-foreground">
                    <p className="font-medium text-foreground mb-1">計算方法について</p>
                    <ul className="space-y-1 text-xs">
                      <li>FIRE達成: 資産が「年間支出 × 25倍」以上になった時点（4%ルール）</li>
                      <li>市場変動: 株価のランダムな動きを1000通りシミュレーション（悪い年が続いた場合も含む）</li>
                      <li>NISA/iDeCo: 非課税口座の運用益は税金なしで計算</li>
                      <li>教育費: 文部科学省データをもとに、子どもの年齢に合わせて自動計算</li>
                      <li>プライバシー: 計算はすべてブラウザ内で完結。入力データは外部に送信されません</li>
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </main>

        {/* Mobile Bottom Navigation */}
        {(() => {
          const completion = getSectionCompletion(config)
          const navItems = [
            { id: "config-basic",  label: "基本",   icon: Home,      done: completion.basic },
            { id: "config-income", label: "収入",   icon: Wallet,    done: completion.income },
            { id: "config-invest", label: "投資",   icon: TrendingUp, done: completion.invest },
            { id: "config-life",   label: "ライフ", icon: Baby,      done: completion.life },
            { id: "config-detail", label: "詳細",   icon: Settings2, done: completion.detail },
          ]
          return (
            <nav className="fixed bottom-0 inset-x-0 z-50 lg:hidden border-t bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/60">
              <div className="flex">
                {navItems.map(({ id, label, icon: Icon, done }) => {
                  const isActive = activeSection === id
                  return (
                    <button
                      key={id}
                      type="button"
                      onClick={() => {
                        const el = document.getElementById(id)
                        if (el) {
                          el.scrollIntoView({ behavior: "smooth", block: "start" })
                          setActiveSection(id)
                        }
                      }}
                      className={`flex flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[10px] font-medium transition-colors ${
                        isActive
                          ? "text-primary"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <span className="relative">
                        <Icon className="h-5 w-5" />
                        {done && (
                          <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-primary border border-background" />
                        )}
                      </span>
                      <span>{label}</span>
                    </button>
                  )
                })}
              </div>
            </nav>
          )
        })()}

        {/* Footer */}
        <footer className="border-t bg-card/50 mt-12">
          <div className="container mx-auto px-4 py-6">
            <p className="text-center text-sm text-muted-foreground">
              あくまでも試算です。投資の最終判断はご自身でお願いします。
            </p>
          </div>
        </footer>
      </div>
    </TooltipProvider>
  )
}
