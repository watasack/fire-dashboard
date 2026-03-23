"use client"

import { Card, CardContent } from "@/components/ui/card"
import { SimulationConfig, SimulationResult, MonteCarloResult } from "@/lib/simulator"
import { formatCurrency, formatPercent } from "@/lib/utils"
import { TrendingUp, TrendingDown, Wallet, PiggyBank, Baby, Calendar, Target, ShieldAlert } from "lucide-react"

interface MetricsSummaryProps {
  config: SimulationConfig
  result: SimulationResult | null
  mcResult?: MonteCarloResult | null
  isCalculating?: boolean
}

interface MetricCardProps {
  icon: React.ReactNode
  label: string
  value: string
  subValue?: string
  trend?: "up" | "down" | "neutral"
}

function MetricCard({ icon, label, value, subValue, trend }: MetricCardProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg bg-muted/50 p-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-background">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground truncate">{label}</p>
        <p className="font-semibold">{value}</p>
        {subValue && (
          <p className="text-xs text-muted-foreground">{subValue}</p>
        )}
      </div>
      {trend && trend !== "neutral" && (
        <div className={trend === "up" ? "text-success" : "text-destructive"}>
          {trend === "up" ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
        </div>
      )}
    </div>
  )
}

export function MetricsSummary({ config, result, mcResult, isCalculating }: MetricsSummaryProps) {
  const totalIncome = config.person1.grossIncome + (config.person2?.grossIncome ?? 0)
  const annualExpenses = config.monthlyExpenses * 12
  const savingsRate = (totalIncome - annualExpenses) / totalIncome
  const childCount = config.children.length

  // Calculate total child education costs over time
  const totalChildCosts = result?.yearlyData.reduce((sum, d) => sum + d.childCosts, 0) ?? 0

  // FIRE達成率
  const achievementPercent = result ? Math.round(result.fireAchievementRate * 100) : 0
  const achievementColor = achievementPercent >= 100 ? "text-green-600" : "text-blue-600"

  return (
    <Card className={`transition-opacity duration-200 ${isCalculating ? 'opacity-60' : ''}`}>
      <CardContent className="p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        </div>

        {/* FIRE達成率・枯渇年齢 */}
        {result && (
          <div className="grid gap-3 sm:grid-cols-2 mt-3">
            {/* FIRE達成率カード */}
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

            {/* 枯渇年齢カード（モンテカルロ時のみ） */}
            {mcResult ? (
              <div className="rounded-lg bg-muted/50 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-background">
                    <ShieldAlert className="h-4 w-4 text-primary" />
                  </div>
                  <p className="text-xs text-muted-foreground">FIRE成功確率（1000通り）</p>
                </div>
                <p className="font-semibold text-lg">{formatPercent(mcResult.successRate)}</p>
                {mcResult.depletionAgeP10 !== null && (
                  <p className="text-xs text-muted-foreground mt-1">
                    最悪シナリオ（下位10%）: {mcResult.depletionAgeP10}歳まで資産が持ちます
                  </p>
                )}
                {mcResult.depletionAgeP10 === null && (
                  <p className="text-xs text-green-600 mt-1">
                    1000通り全てで90歳まで資産が持続しました
                  </p>
                )}
              </div>
            ) : (
              <MetricCard
                icon={<Calendar className="h-5 w-5 text-primary" />}
                label="シミュレーション期間"
                value={`${config.simulationYears}年`}
                subValue={`${config.person1.currentAge}〜${config.person1.currentAge + config.simulationYears}歳`}
              />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
