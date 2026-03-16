"use client"

import { Card, CardContent } from "@/components/ui/card"
import { SimulationConfig, SimulationResult } from "@/lib/simulator"
import { formatCurrency, formatPercent } from "@/lib/utils"
import { TrendingUp, TrendingDown, Wallet, PiggyBank, Baby, Calendar } from "lucide-react"

interface MetricsSummaryProps {
  config: SimulationConfig
  result: SimulationResult | null
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

export function MetricsSummary({ config, result }: MetricsSummaryProps) {
  const totalIncome = config.person1.currentIncome + (config.person2?.currentIncome ?? 0)
  const annualExpenses = config.monthlyExpenses * 12
  const savingsRate = (totalIncome - annualExpenses) / totalIncome
  const childCount = config.children.length

  // Calculate total child education costs over time
  const totalChildCosts = result?.yearlyData.reduce((sum, d) => sum + d.childCosts, 0) ?? 0

  return (
    <Card>
      <CardContent className="p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            icon={<Wallet className="h-5 w-5 text-primary" />}
            label="世帯年収"
            value={formatCurrency(totalIncome, true)}
            subValue={config.person2 ? "共働き" : "単独"}
          />
          <MetricCard
            icon={<PiggyBank className="h-5 w-5 text-success" />}
            label="貯蓄率"
            value={formatPercent(Math.max(0, savingsRate))}
            subValue={`年間 ${formatCurrency(Math.max(0, totalIncome - annualExpenses), true)}`}
            trend={savingsRate > 0.3 ? "up" : savingsRate > 0.15 ? "neutral" : "down"}
          />
          <MetricCard
            icon={<Baby className="h-5 w-5 text-accent" />}
            label="子育て費用（総額）"
            value={formatCurrency(totalChildCosts, true)}
            subValue={`${childCount}人`}
          />
          <MetricCard
            icon={<Calendar className="h-5 w-5 text-primary" />}
            label="シミュレーション期間"
            value={`${config.simulationYears}年`}
            subValue={`${config.person1.currentAge}〜${config.person1.currentAge + config.simulationYears}歳`}
          />
        </div>
      </CardContent>
    </Card>
  )
}
