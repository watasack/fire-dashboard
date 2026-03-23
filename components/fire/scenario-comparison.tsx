"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { SimulationConfig, runSingleSimulation, generateScenarios, SimulationResult } from "@/lib/simulator"
import { cn } from "@/lib/utils"
import { useMemo } from "react"
import { ArrowDown, ArrowUp, Minus, Lightbulb, TrendingUp, Wallet, Briefcase, Calendar } from "lucide-react"

interface ScenarioComparisonProps {
  baseConfig: SimulationConfig
  baseResult: SimulationResult | null
  onConfigChange?: (config: SimulationConfig) => void
}

const SCENARIO_ICONS = {
  "FIRE目標を5年早める": Calendar,
  "支出を月3万円削減": Wallet,
  "NISAを上限まで投資": TrendingUp,
  "副業で月10万円追加": Briefcase,
}

export function ScenarioComparison({ baseConfig, baseResult, onConfigChange }: ScenarioComparisonProps) {
  const scenarios = useMemo(() => {
    if (!baseResult) return []

    const scenarioConfigs = generateScenarios(baseConfig)
    
    return scenarioConfigs.map((scenario) => {
      const mergedConfig = { ...baseConfig, ...scenario.changes } as import('@/lib/simulator').SimulationConfig
      
      // Handle nested objects
      if (scenario.changes.person1) {
        mergedConfig.person1 = { ...baseConfig.person1, ...scenario.changes.person1 }
      }
      if (scenario.changes.person2 && baseConfig.person2) {
        mergedConfig.person2 = { ...baseConfig.person2, ...scenario.changes.person2 }
      }
      if (scenario.changes.nisa) {
        mergedConfig.nisa = { ...baseConfig.nisa, ...scenario.changes.nisa }
      }
      if (scenario.changes.ideco) {
        mergedConfig.ideco = { ...baseConfig.ideco, ...scenario.changes.ideco }
      }

      const result = runSingleSimulation(mergedConfig)
      const baseFireAge = baseResult.fireAge
      const scenarioFireAge = result.fireAge

      let fireAgeDelta: number | null = null
      if (baseFireAge && scenarioFireAge) {
        fireAgeDelta = scenarioFireAge - baseFireAge
      } else if (!baseFireAge && scenarioFireAge) {
        fireAgeDelta = -100 // Indicates improvement from impossible to possible
      } else if (baseFireAge && !scenarioFireAge) {
        fireAgeDelta = 100 // Indicates worsening from possible to impossible
      }

      return {
        name: scenario.name,
        description: scenario.description,
        result,
        mergedConfig,
        fireAgeDelta,
        finalAssetsDelta: result.finalAssets - baseResult.finalAssets,
      }
    })
  }, [baseConfig, baseResult])

  if (!baseResult) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5" />
            次の一手
          </CardTitle>
        </CardHeader>
        <CardContent className="flex h-48 items-center justify-center">
          <p className="text-muted-foreground">基本シミュレーションを実行してください</p>
        </CardContent>
      </Card>
    )
  }

  // Sort scenarios by impact (best first)
  const sortedScenarios = [...scenarios].sort((a, b) => {
    if (a.fireAgeDelta === null) return 1
    if (b.fireAgeDelta === null) return -1
    return a.fireAgeDelta - b.fireAgeDelta
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5 text-accent" />
          次の一手 - シナリオ比較
        </CardTitle>
        <CardDescription>
          少し設定を変えるだけでFIRE確率が大幅に変化します。試してみましょう
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3">
          {sortedScenarios.map((scenario, index) => {
            const Icon = SCENARIO_ICONS[scenario.name as keyof typeof SCENARIO_ICONS] || TrendingUp
            const isImprovement = scenario.fireAgeDelta !== null && scenario.fireAgeDelta < 0
            const isBest = index === 0 && isImprovement

            return (
              <div
                key={scenario.name}
                className={cn(
                  "relative rounded-lg border p-4 transition-all hover:shadow-md",
                  isBest && "border-success/50 bg-success/5",
                  isImprovement && !isBest && "border-accent/30 bg-accent/5"
                )}
              >
                {isBest && (
                  <div className="absolute -top-2 right-3 rounded-full bg-success px-2 py-0.5 text-xs font-medium text-success-foreground">
                    最も効果的
                  </div>
                )}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      "rounded-lg p-2",
                      isBest ? "bg-success/20" : "bg-muted"
                    )}>
                      <Icon className={cn(
                        "h-4 w-4",
                        isBest ? "text-success" : "text-muted-foreground"
                      )} />
                    </div>
                    <div>
                      <p className="font-medium">{scenario.name}</p>
                      <p className="text-sm text-muted-foreground">{scenario.description}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-1">
                      {scenario.fireAgeDelta !== null && scenario.fireAgeDelta !== 0 ? (
                        <>
                          {scenario.fireAgeDelta < 0 ? (
                            <ArrowDown className="h-4 w-4 text-success" />
                          ) : (
                            <ArrowUp className="h-4 w-4 text-destructive" />
                          )}
                          <span className={cn(
                            "text-lg font-bold",
                            scenario.fireAgeDelta < 0 ? "text-success" : "text-destructive"
                          )}>
                            {Math.abs(scenario.fireAgeDelta)}年
                          </span>
                        </>
                      ) : (
                        <>
                          <Minus className="h-4 w-4 text-muted-foreground" />
                          <span className="text-lg font-bold text-muted-foreground">変化なし</span>
                        </>
                      )}
                    </div>
                    {scenario.result.fireAge && (
                      <p className="text-sm text-muted-foreground">
                        {scenario.result.fireAge}歳でFIRE
                      </p>
                    )}
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full mt-3 text-xs"
                  onClick={() => onConfigChange?.(scenario.mergedConfig)}
                >
                  この設定を試す →<span className="block text-[10px] opacity-60 font-normal">即時反映</span>
                </Button>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
