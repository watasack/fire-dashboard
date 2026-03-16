"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { SimulationConfig, SimulationResult, MonteCarloResult, DEFAULT_CONFIG, runSingleSimulation, runMonteCarloSimulation } from "@/lib/simulator"
import { FireResultCard } from "./fire-result-card"
import { ConfigPanel } from "./config-panel"
import { AssetsChart, IncomeExpenseChart } from "./assets-chart"
import { ScenarioComparison } from "./scenario-comparison"
import { MetricsSummary } from "./metrics-summary"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { TooltipProvider } from "@/components/ui/tooltip"
import { BarChart3, Settings, Lightbulb, TrendingUp, Info, ShieldCheck } from "lucide-react"

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
  const [useMonteCarco, setUseMonteCarlo] = useState(true)

  // Debounce config changes for smooth slider interactions
  const debouncedConfig = useDebounce(config, 300)

  // Run simulation when config changes
  useEffect(() => {
    setIsCalculating(true)
    
    // Use setTimeout to prevent UI blocking
    const timer = setTimeout(() => {
      const singleResult = runSingleSimulation(debouncedConfig)
      setResult(singleResult)

      if (useMonteCarco) {
        const mcResult = runMonteCarloSimulation(debouncedConfig, 1000)
        setMonteCarloResult(mcResult)
      } else {
        setMonteCarloResult(null)
      }

      setIsCalculating(false)
    }, 50)

    return () => clearTimeout(timer)
  }, [debouncedConfig, useMonteCarco])

  const handleConfigChange = useCallback((newConfig: SimulationConfig) => {
    setConfig(newConfig)
  }, [])

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
                <h1 className="text-lg font-semibold tracking-tight">FIRE シミュレーター</h1>
                <p className="text-xs text-muted-foreground">経済的自立への道筋を計算</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Switch
                  id="monte-carlo-toggle"
                  checked={useMonteCarco}
                  onCheckedChange={setUseMonteCarlo}
                />
                <Label htmlFor="monte-carlo-toggle" className="text-sm cursor-pointer">
                  モンテカルロ
                </Label>
              </div>
            </div>
          </div>
        </header>

        <main className="container mx-auto px-4 py-6">
          <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
            {/* Left Panel - Configuration */}
            <aside className="space-y-6">
              <ConfigPanel config={config} onConfigChange={handleConfigChange} />
              
              {/* Trust indicators */}
              <Card className="border-primary/20 bg-primary/5">
                <CardContent className="flex items-start gap-3 p-4">
                  <ShieldCheck className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-primary">計算の信頼性</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      モンテカルロ法による1000回のシミュレーションで、市場変動を考慮した現実的な予測を提供します。
                    </p>
                  </div>
                </CardContent>
              </Card>
            </aside>

            {/* Right Panel - Results */}
            <div className="space-y-6">
              {/* Key Metrics Summary */}
              <MetricsSummary config={config} result={result} />
              
              {/* FIRE Result Card */}
              <FireResultCard
                result={result}
                monteCarloResult={monteCarloResult}
                currentAge={config.person1.currentAge}
                isCalculating={isCalculating}
              />

              {/* Charts and Analysis Tabs */}
              <Tabs defaultValue="assets" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="assets" className="flex items-center gap-1.5">
                    <BarChart3 className="h-4 w-4" />
                    <span>資産推移</span>
                  </TabsTrigger>
                  <TabsTrigger value="cashflow" className="flex items-center gap-1.5">
                    <TrendingUp className="h-4 w-4" />
                    <span>収支</span>
                  </TabsTrigger>
                  <TabsTrigger value="scenarios" className="flex items-center gap-1.5">
                    <Lightbulb className="h-4 w-4" />
                    <span>次の一手</span>
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="assets" className="mt-4">
                  <AssetsChart
                    result={result}
                    monteCarloResult={monteCarloResult}
                    showPercentiles={useMonteCarco}
                  />
                </TabsContent>

                <TabsContent value="cashflow" className="mt-4">
                  <IncomeExpenseChart result={result} />
                </TabsContent>

                <TabsContent value="scenarios" className="mt-4">
                  <ScenarioComparison baseConfig={config} baseResult={result} />
                </TabsContent>
              </Tabs>

              {/* Methodology info */}
              <Card>
                <CardContent className="flex items-start gap-3 p-4">
                  <Info className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div className="text-sm text-muted-foreground">
                    <p className="font-medium text-foreground mb-1">計算方法について</p>
                    <ul className="space-y-1 text-xs">
                      <li>FIRE達成条件: 総資産 ≥ 年間支出 ÷ 安全引き出し率（デフォルト4%）</li>
                      <li>モンテカルロ法: 投資リターンの変動を正規分布でモデル化し、1000回シミュレーション</li>
                      <li>NISA/iDeCo: 非課税枠での運用益を別途計算し、総資産に加算</li>
                      <li>教育費: 文部科学省「子供の学習費調査」を参考に年齢別で計算</li>
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t bg-card/50 mt-12">
          <div className="container mx-auto px-4 py-6">
            <p className="text-center text-sm text-muted-foreground">
              このシミュレーターは参考情報であり、投資助言ではありません。実際の投資判断は専門家にご相談ください。
            </p>
          </div>
        </footer>
      </div>
    </TooltipProvider>
  )
}
