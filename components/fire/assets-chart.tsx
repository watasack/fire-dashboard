"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { SimulationResult, MonteCarloResult } from "@/lib/simulator"
import { formatCurrency } from "@/lib/utils"
import {
  Area,
  AreaChart,
  Line,
  LineChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
  ComposedChart,
  Bar,
} from "recharts"

interface AssetsChartProps {
  result: SimulationResult | null
  monteCarloResult: MonteCarloResult | null
  showPercentiles?: boolean
  compact?: boolean
  /** モバイルでグラフを全画面展開するとき true */
  expanded?: boolean
}

export function AssetsChart({ result, monteCarloResult, showPercentiles = true, compact = false, expanded = false }: AssetsChartProps) {
  const chartHeight = expanded ? "h-full" : compact ? "h-[240px]" : "h-[260px] sm:h-[360px] lg:h-[400px]"
  const showHeader = !compact && !expanded
  const showLegend = !compact && !expanded
  const chartMargin = (compact || expanded)
    ? { top: 16, right: 8, bottom: 4, left: 20 }
    : { top: 20, right: 8, bottom: 20, left: 20 }

  if (!result) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>資産推移</CardTitle>
        </CardHeader>
        <CardContent className={`flex ${chartHeight} items-center justify-center`}>
          <p className="text-muted-foreground">データがありません</p>
        </CardContent>
      </Card>
    )
  }

  // Prepare chart data
  const chartData = result.yearlyData.map((d, i) => {
    const pct = monteCarloResult?.yearlyPercentiles[i]
    return {
      age: d.age,
      year: d.year,
      assets: d.assets + d.nisaAssets + d.idecoAssets + d.otherAssets,
      fireNumber: d.fireNumber,
      // Stacked band segments (each is the *difference* between adjacent percentiles)
      // stackId="band": base(p10) → seg1(p25-p10) → seg2(p75-p25) → seg3(p90-p75)
      bandBase:  pct ? pct.p10 : undefined,
      bandLow:   pct ? pct.p25 - pct.p10 : undefined,
      bandMid:   pct ? pct.p75 - pct.p25 : undefined,
      bandHigh:  pct ? pct.p90 - pct.p75 : undefined,
      p50: pct?.p50,
    }
  })

  const fireAge = monteCarloResult?.medianFireAge ?? result.fireAge

  const chartInner = (
    <div className={chartHeight}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={chartMargin}>
              <defs>
                <linearGradient id="percentileGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-primary)" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="var(--chart-primary)" stopOpacity={0.05} />
                </linearGradient>
                <linearGradient id="innerPercentileGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-primary)" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="var(--chart-primary)" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.5} />
              <XAxis
                dataKey="age"
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => `${value}歳`}
                stroke="var(--color-muted-foreground)"
              />
              <YAxis
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => formatCurrency(value, true)}
                stroke="var(--color-muted-foreground)"
                width={60}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null
                  return (
                    <div className="rounded-lg border bg-background p-3 shadow-lg">
                      <p className="mb-2 font-medium">{label}歳</p>
                      {payload.map((entry, index) => (
                        <p key={index} className="text-sm" style={{ color: entry.color }}>
                          {entry.name}: {formatCurrency(entry.value as number, true)}
                        </p>
                      ))}
                    </div>
                  )
                }}
              />

              {/* Percentile bands — stacked difference approach (no masking needed).
                  Each Area must be a direct child of ComposedChart (no fragment wrapper)
                  due to React 19 / Recharts 2.x incompatibility with react-is@16. */}
              {/* Base: transparent floor at p10 */}
              {showPercentiles && monteCarloResult ? (
                <Area
                  type="monotone"
                  dataKey="bandBase"
                  stackId="band"
                  stroke="none"
                  fill="#1a365d"
                  fillOpacity={0}
                  legendType="none"
                  tooltipType="none"
                  isAnimationActive={false}
                />
              ) : null}
              {/* p10→p25: outer low segment */}
              {showPercentiles && monteCarloResult ? (
                <Area
                  type="monotone"
                  dataKey="bandLow"
                  stackId="band"
                  stroke="none"
                  fill="#1a365d"
                  fillOpacity={0.15}
                  name="10〜90%の範囲"
                  legendType="square"
                  isAnimationActive={false}
                />
              ) : null}
              {/* p25→p75: inner mid segment */}
              {showPercentiles && monteCarloResult ? (
                <Area
                  type="monotone"
                  dataKey="bandMid"
                  stackId="band"
                  stroke="none"
                  fill="#1a365d"
                  fillOpacity={0.3}
                  name="25〜75パーセンタイル（中央50%の確率範囲）"
                  legendType="square"
                  isAnimationActive={false}
                />
              ) : null}
              {/* p75→p90: outer high segment */}
              {showPercentiles && monteCarloResult ? (
                <Area
                  type="monotone"
                  dataKey="bandHigh"
                  stackId="band"
                  stroke="none"
                  fill="#1a365d"
                  fillOpacity={0.15}
                  legendType="none"
                  tooltipType="none"
                  isAnimationActive={false}
                />
              ) : null}

              {/* Median/Main line */}
              <Line
                type="monotone"
                dataKey={showPercentiles && monteCarloResult ? "p50" : "assets"}
                stroke="var(--chart-primary)"
                strokeWidth={2.5}
                dot={false}
                name="中央値シナリオ"
              />

              {/* FIRE age reference line */}
              {fireAge && (
                <ReferenceLine
                  x={fireAge}
                  stroke="var(--chart-success)"
                  strokeWidth={2}
                  strokeDasharray="3 3"
                  label={{
                    value: `FIRE ${fireAge}歳`,
                    position: "top",
                    fill: "var(--chart-success)",
                    fontSize: 12,
                  }}
                />
              )}

              {showLegend ? (
                <Legend
                  wrapperStyle={{ paddingTop: "20px" }}
                  formatter={(value) => <span className="text-sm">{value}</span>}
                />
              ) : null}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
  )

  if (expanded) {
    return <div className="h-full px-2 pb-2">{chartInner}</div>
  }

  return (
    <Card>
      {showHeader && (
        <CardHeader>
          <CardTitle>資産推移予測</CardTitle>
          <CardDescription>
            {showPercentiles && monteCarloResult
              ? "1000通りのシミュレーション結果。濃い帯ほど「よくある結果」を示します"
              : "平均的なシナリオでの資産推移"}
          </CardDescription>
        </CardHeader>
      )}
      <CardContent className={showHeader ? "" : "pt-3"}>
        {chartInner}
      </CardContent>
    </Card>
  )
}

interface IncomeExpenseChartProps {
  result: SimulationResult | null
  compact?: boolean
  expanded?: boolean
}

export function IncomeExpenseChart({ result, compact = false, expanded = false }: IncomeExpenseChartProps) {
  const chartHeight = expanded ? "h-full" : compact ? "h-[200px]" : "h-[240px] sm:h-[280px] lg:h-[300px]"
  const showHeader = !compact && !expanded
  const showLegend = !compact && !expanded
  const chartMargin = (compact || expanded)
    ? { top: 16, right: 8, bottom: 4, left: 20 }
    : { top: 20, right: 8, bottom: 20, left: 20 }
  if (!result) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>収支推移</CardTitle>
        </CardHeader>
        <CardContent className={`flex ${chartHeight} items-center justify-center`}>
          <p className="text-muted-foreground">データがありません</p>
        </CardContent>
      </Card>
    )
  }

  const chartData = result.yearlyData.map((d) => ({
    age: d.age,
    income: d.income,
    expenses: d.expenses,
    netCF: d.income - d.expenses,
    childCosts: d.childCosts,
  }))

  const cashflowInner = (
    <div className={chartHeight}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={chartMargin}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.5} />
          <XAxis
            dataKey="age"
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => `${value}歳`}
            stroke="var(--color-muted-foreground)"
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => formatCurrency(value, true)}
            stroke="var(--color-muted-foreground)"
            width={60}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null
              return (
                <div className="rounded-lg border bg-background p-3 shadow-lg">
                  <p className="mb-2 font-medium">{label}歳</p>
                  {payload.map((entry, index) => (
                    <p key={index} className="text-sm" style={{ color: entry.color }}>
                      {entry.name}: {formatCurrency(entry.value as number, true)}
                    </p>
                  ))}
                </div>
              )
            }}
          />
          {true ? <Bar dataKey="income" fill="#3B82F6" name="収入" opacity={0.85} /> : null}
          {true ? <Bar dataKey="expenses" fill="#EF4444" name="支出" opacity={0.85} /> : null}
          {true ? <Line type="monotone" dataKey="netCF" stroke="#10B981" strokeWidth={3} dot={false} name="年間収支" /> : null}
          {showLegend ? (
            <Legend
              wrapperStyle={{ paddingTop: "20px" }}
              formatter={(value) => <span className="text-sm">{value}</span>}
            />
          ) : null}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )

  if (expanded) {
    return <div className="h-full px-2 pb-2">{cashflowInner}</div>
  }

  return (
    <Card>
      {showHeader && (
        <CardHeader>
          <CardTitle>収支推移</CardTitle>
          <CardDescription>年間の収入・支出・貯蓄の推移</CardDescription>
        </CardHeader>
      )}
      <CardContent className={showHeader ? "" : "pt-3"}>
        {cashflowInner}
      </CardContent>
    </Card>
  )
}
