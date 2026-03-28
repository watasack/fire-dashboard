"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn, formatPercent } from "@/lib/utils"
import { SimulationResult, MonteCarloResult } from "@/lib/simulator"
import { Target, Calendar, AlertCircle, CheckCircle2, Info } from "lucide-react"

interface FireResultCardProps {
  result: SimulationResult | null
  monteCarloResult: MonteCarloResult | null
  currentAge: number
  isCalculating: boolean
}

export function FireResultCard({ result, monteCarloResult, currentAge, isCalculating }: FireResultCardProps) {
  const [fireAgeTooltipOpen, setFireAgeTooltipOpen] = useState(false)
  const [probabilityTooltipOpen, setProbabilityTooltipOpen] = useState(false)

  if (!result) {
    return (
      <Card className="border-2 border-dashed border-muted-foreground/20">
        <CardContent className="flex items-center justify-center h-48">
          <p className="text-sm text-muted-foreground">パラメータを入力してください</p>
        </CardContent>
      </Card>
    )
  }

  const fireAge = monteCarloResult?.medianFireAge ?? result.fireAge
  const fireProbability = monteCarloResult?.successRate ?? (result.fireAge ? 1 : 0)
  const yearsToFire = fireAge ? fireAge - currentAge : null
  const startYear = result.yearlyData[0]?.year ?? new Date().getFullYear()
  const displayFireYear = fireAge ? startYear + (fireAge - currentAge) : null
  const isFireAchievable = fireProbability >= 0.5

  return (
    <Card className={cn(
        "border-2 transition-all duration-500",
        isCalculating ? "opacity-70" : "",
        isFireAchievable ? "border-success/50 bg-success/5" : "border-accent/50 bg-accent/5"
      )}>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            {isFireAchievable ? (
              <CheckCircle2 className="h-5 w-5 text-success" />
            ) : (
              <AlertCircle className="h-5 w-5 text-accent" />
            )}
            FIRE達成シミュレーション
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            {/* FIRE Age */}
            <div className="space-y-1">
              <span className="flex flex-col gap-0">
                <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  <span>FIRE達成年齢</span>
                  <button
                    type="button"
                    onClick={() => setFireAgeTooltipOpen(p => !p)}
                    className="inline-flex p-2.5 -m-2.5 text-muted-foreground/60 hover:text-muted-foreground transition-colors"
                  >
                    <Info className="h-4 w-4 shrink-0" />
                  </button>
                </span>
                {fireAgeTooltipOpen && (
                  <span className="mt-1 text-xs text-muted-foreground leading-relaxed">
                    1000通りのシナリオでの中央値（ちょうど真ん中のシナリオ）です。
                  </span>
                )}
              </span>
              <p className={cn(
                "text-3xl font-bold tracking-tight",
                isFireAchievable ? "text-success" : "text-accent"
              )}>
                {fireAge ? `${fireAge}歳` : "達成困難"}
              </p>
              {yearsToFire && (
                <p className="text-sm text-muted-foreground">
                  あと{yearsToFire}年
                  {displayFireYear ? `（${displayFireYear}年）` : ""}
                </p>
              )}
            </div>

            {/* Success Rate */}
            <div className="space-y-1">
              <span className="flex flex-col gap-0">
                <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Target className="h-4 w-4" />
                  <span>達成確率</span>
                  <button
                    type="button"
                    onClick={() => setProbabilityTooltipOpen(p => !p)}
                    className="inline-flex p-2.5 -m-2.5 text-muted-foreground/60 hover:text-muted-foreground transition-colors"
                  >
                    <Info className="h-4 w-4 shrink-0" />
                  </button>
                </span>
                {probabilityTooltipOpen && (
                  <span className="mt-1 text-xs text-muted-foreground leading-relaxed">
                    1000通りの市場シナリオで、90歳まで資産が持つ確率です。
                  </span>
                )}
              </span>
              <p className={cn(
                "text-3xl font-bold tracking-tight",
                fireProbability >= 0.8 ? "text-success" :
                fireProbability >= 0.5 ? "text-accent" : "text-destructive"
              )}>
                {formatPercent(fireProbability)}
              </p>
              <p className="text-sm text-muted-foreground">
                {fireProbability >= 0.8 ? "高い確率" :
                 fireProbability >= 0.5 ? "達成圏内" : "改善の余地あり"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
  )
}
