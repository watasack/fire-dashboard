"use client"

import { Card, CardContent } from "@/components/ui/card"
import { SimulationConfig, SimulationResult, MonteCarloResult } from "@/lib/simulator"
import { formatCurrency } from "@/lib/utils"
import { Target } from "lucide-react"

interface MetricsSummaryProps {
  config: SimulationConfig
  result: SimulationResult | null
  mcResult?: MonteCarloResult | null
  isCalculating?: boolean
}

export function MetricsSummary({ config, result, mcResult, isCalculating }: MetricsSummaryProps) {
  // FIRE達成率
  const achievementPercent = result ? Math.round(result.fireAchievementRate * 100) : 0
  const achievementColor = achievementPercent >= 100 ? "text-green-600" : "text-blue-600"

  return (
    <Card className={`transition-opacity duration-200 ${isCalculating ? 'opacity-60' : ''}`}>
      <CardContent className="p-4">
        {/* FIRE達成率 */}
        {result && (
          <div className="rounded-lg bg-muted/50 p-3">
            <div className="flex items-center gap-2 mb-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-background">
                <Target className="h-4 w-4 text-primary" />
              </div>
              <p className="text-xs text-muted-foreground">目標達成率（現在）</p>
            </div>
            <p className={`font-semibold text-lg ${achievementColor}`}>{achievementPercent}%</p>
            <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${achievementPercent >= 100 ? "bg-green-500" : "bg-blue-500"}`}
                style={{ width: `${Math.min(achievementPercent, 100)}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              必要資産: {formatCurrency(result.fireNumber, true)}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
