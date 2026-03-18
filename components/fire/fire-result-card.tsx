"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn, formatCurrency, formatPercent } from "@/lib/utils"
import { SimulationResult, MonteCarloResult } from "@/lib/simulator"
import { TrendingUp, Target, Calendar, Wallet, AlertCircle, CheckCircle2 } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface FireResultCardProps {
  result: SimulationResult | null
  monteCarloResult: MonteCarloResult | null
  currentAge: number
  isCalculating: boolean
}

export function FireResultCard({ result, monteCarloResult, currentAge, isCalculating }: FireResultCardProps) {
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
  const isFireAchievable = fireProbability >= 0.5
  const endAge = currentAge + result.totalYears
  const firePosition = fireAge && result.totalYears > 0
    ? Math.min(100, Math.max(0, ((fireAge - currentAge) / result.totalYears) * 100))
    : null

  return (
    <TooltipProvider>
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
            FIRE達成予測
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            {/* FIRE Age */}
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span>FIRE達成年齢</span>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button className="text-muted-foreground/60 hover:text-muted-foreground">
                      <AlertCircle className="h-3 w-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs text-xs">
                      モンテカルロシミュレーション（1000回）の中央値です。
                      {monteCarloResult && (
                        <>
                          <br />10%ile: {monteCarloResult.percentile10}歳
                          <br />90%ile: {monteCarloResult.percentile90}歳
                        </>
                      )}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <p className={cn(
                "text-3xl font-bold tracking-tight",
                isFireAchievable ? "text-success" : "text-accent"
              )}>
                {fireAge ? `${fireAge}歳` : "達成困難"}
              </p>
              {yearsToFire && (
                <p className="text-sm text-muted-foreground">
                  あと{yearsToFire}年
                </p>
              )}
            </div>

            {/* Success Rate */}
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Target className="h-4 w-4" />
                <span>達成確率</span>
              </div>
              <p className={cn(
                "text-3xl font-bold tracking-tight",
                fireProbability >= 0.8 ? "text-success" :
                fireProbability >= 0.5 ? "text-accent" : "text-destructive"
              )}>
                {formatPercent(fireProbability)}
              </p>
              <p className="text-sm text-muted-foreground">
                {fireProbability >= 0.8 ? "高い確率" :
                 fireProbability >= 0.5 ? "現実的" : "要改善"}
              </p>
            </div>

            {/* FIRE Number */}
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Wallet className="h-4 w-4" />
                <span>必要資産額</span>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button className="text-muted-foreground/60 hover:text-muted-foreground">
                      <AlertCircle className="h-3 w-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs text-xs">
                      年間支出 ÷ 安全引き出し率（4%）で計算されるFIRE達成に必要な資産額
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <p className="text-2xl font-bold tracking-tight">
                {formatCurrency(result.fireNumber, true)}
              </p>
            </div>

            {/* Final Assets */}
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <TrendingUp className="h-4 w-4" />
                <span>最終資産予測</span>
              </div>
              <p className="text-2xl font-bold tracking-tight">
                {formatCurrency(result.finalAssets, true)}
              </p>
              <p className="text-sm text-muted-foreground">
                {result.totalYears}年後
              </p>
            </div>
          </div>

          {/* FIRE Timeline */}
          {firePosition !== null && (
            <div className="mt-4 pt-4 border-t">
              <p className="text-xs text-muted-foreground mb-3">FIREまでの道のり</p>
              <div className="relative">
                {/* Track */}
                <div className="h-1.5 bg-muted rounded-full overflow-visible">
                  {/* Pre-FIRE fill */}
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-500",
                      isFireAchievable ? "bg-success/50" : "bg-accent/50"
                    )}
                    style={{ width: `${firePosition}%` }}
                  />
                </div>
                {/* FIRE marker dot */}
                <div
                  className={cn(
                    "absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3.5 h-3.5 rounded-full border-2 border-card shadow-sm transition-all duration-500",
                    isFireAchievable ? "bg-success" : "bg-accent"
                  )}
                  style={{ left: `${firePosition}%` }}
                />
                {/* Labels */}
                <div className="flex justify-between text-xs text-muted-foreground mt-3">
                  <span>{currentAge}歳（現在）</span>
                  {fireAge && (
                    <span
                      className={cn("font-medium transition-colors", isFireAchievable ? "text-success" : "text-accent")}
                      style={{ marginLeft: `${Math.max(0, firePosition - 15)}%` }}
                    >
                      FIRE {fireAge}歳
                    </span>
                  )}
                  <span>{endAge}歳</span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </TooltipProvider>
  )
}
