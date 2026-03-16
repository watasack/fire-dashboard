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
}

export function AssetsChart({ result, monteCarloResult, showPercentiles = true }: AssetsChartProps) {
  if (!result) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>資産推移</CardTitle>
        </CardHeader>
        <CardContent className="flex h-[400px] items-center justify-center">
          <p className="text-muted-foreground">データがありません</p>
        </CardContent>
      </Card>
    )
  }

  // Prepare chart data
  const chartData = result.yearlyData.map((d, i) => {
    const percentiles = monteCarloResult?.yearlyPercentiles[i]
    return {
      age: d.age,
      year: d.year,
      assets: d.assets + d.nisaAssets + d.idecoAssets,
      fireNumber: d.fireNumber,
      p10: percentiles?.p10,
      p25: percentiles?.p25,
      p50: percentiles?.p50,
      p75: percentiles?.p75,
      p90: percentiles?.p90,
    }
  })

  const fireAge = monteCarloResult?.medianFireAge ?? result.fireAge

  return (
    <Card>
      <CardHeader>
        <CardTitle>資産推移予測</CardTitle>
        <CardDescription>
          {showPercentiles && monteCarloResult
            ? "モンテカルロシミュレーション（1000回）による予測範囲"
            : "単一シナリオでの資産推移"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
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
                width={80}
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
              
              {/* Percentile bands */}
              {showPercentiles && monteCarloResult && (
                <>
                  <Area
                    type="monotone"
                    dataKey="p90"
                    stroke="none"
                    fill="url(#percentileGradient)"
                    name="90%ile"
                  />
                  <Area
                    type="monotone"
                    dataKey="p10"
                    stroke="none"
                    fill="var(--color-background)"
                    name="10%ile"
                  />
                  <Area
                    type="monotone"
                    dataKey="p75"
                    stroke="none"
                    fill="url(#innerPercentileGradient)"
                    name="75%ile"
                  />
                  <Area
                    type="monotone"
                    dataKey="p25"
                    stroke="none"
                    fill="var(--color-background)"
                    name="25%ile"
                  />
                </>
              )}

              {/* Median/Main line */}
              <Line
                type="monotone"
                dataKey={showPercentiles && monteCarloResult ? "p50" : "assets"}
                stroke="var(--chart-primary)"
                strokeWidth={2.5}
                dot={false}
                name="予測資産"
              />

              {/* FIRE number line */}
              <Line
                type="monotone"
                dataKey="fireNumber"
                stroke="var(--chart-secondary)"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
                name="必要資産額"
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

              <Legend
                wrapperStyle={{ paddingTop: "20px" }}
                formatter={(value) => <span className="text-sm">{value}</span>}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}

interface IncomeExpenseChartProps {
  result: SimulationResult | null
}

export function IncomeExpenseChart({ result }: IncomeExpenseChartProps) {
  if (!result) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>収支推移</CardTitle>
        </CardHeader>
        <CardContent className="flex h-[300px] items-center justify-center">
          <p className="text-muted-foreground">データがありません</p>
        </CardContent>
      </Card>
    )
  }

  const chartData = result.yearlyData.map((d) => ({
    age: d.age,
    income: d.income,
    expenses: d.expenses,
    savings: d.savings,
    childCosts: d.childCosts,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>収支推移</CardTitle>
        <CardDescription>年間の収入・支出・貯蓄の推移</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
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
                width={80}
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
              <Bar dataKey="income" fill="var(--chart-success)" name="収入" opacity={0.8} />
              <Bar dataKey="expenses" fill="var(--chart-danger)" name="支出" opacity={0.8} />
              <Line
                type="monotone"
                dataKey="savings"
                stroke="var(--chart-info)"
                strokeWidth={2}
                dot={false}
                name="貯蓄"
              />
              <Legend
                wrapperStyle={{ paddingTop: "20px" }}
                formatter={(value) => <span className="text-sm">{value}</span>}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
