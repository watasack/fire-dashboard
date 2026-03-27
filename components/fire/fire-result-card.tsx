"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn, formatCurrency, formatPercent } from "@/lib/utils"
import { SimulationResult, MonteCarloResult } from "@/lib/simulator"
import { TrendingUp, Target, Calendar, AlertCircle, CheckCircle2, Info } from "lucide-react"

interface FireResultCardProps {
  result: SimulationResult | null
  monteCarloResult: MonteCarloResult | null
  currentAge: number
  isCalculating: boolean
}

export function FireResultCard({ result, monteCarloResult, currentAge, isCalculating }: FireResultCardProps) {
  const [fireAgeTooltipOpen, setFireAgeTooltipOpen] = useState(false)

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
  // fireAgeから表示用の年を逆算（MCのmedianFireAgeとresult.fireYearがズレる場合に備える）
  const startYear = result.yearlyData[0]?.year ?? new Date().getFullYear()
  const displayFireYear = fireAge ? startYear + (fireAge - currentAge) : null
  const isFireAchievable = fireProbability >= 0.5
  const endAge = currentAge + result.totalYears
  const firePosition = fireAge && result.totalYears > 0
    ? Math.min(100, Math.max(0, ((fireAge - currentAge) / result.totalYears) * 100))
    : null

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
                 fireProbability >= 0.5 ? "達成圏内" : "改善の余地あり"}
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

          {/* Plain-language narrative */}
          {monteCarloResult && (
            <div className="mt-4 pt-4 border-t">
              <p className="text-xs leading-relaxed text-muted-foreground bg-muted/40 rounded-lg px-3 py-2.5">
                {(() => {
                  const prob = Math.round(fireProbability * 100)
                  if (fireAge && fireProbability >= 0.8) {
                    return `1000通りのシナリオのうち${prob}%で、90歳まで資産が持ちます。現在のプランは堅実です。`
                  } else if (fireAge && fireProbability >= 0.5) {
                    return `1000通りのシナリオのうち${prob}%で成功します。積立額の増加や目標年齢の調整で確率をさらに高められます。`
                  } else {
                    return `現在のプランでは、目標でのFIRE達成が難しい状況です（成功率${prob}%）。積立額の増加、支出の見直し、またはFIRE目標年齢の延長を検討してみましょう。`
                  }
                })()}
              </p>
            </div>
          )}

          {/* FIRE Timeline */}
          {firePosition !== null && (
            <div className="mt-4 pt-4 border-t">
              <p className="text-xs text-muted-foreground mb-3">あと何年でFIREできるか</p>
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
  )
}
