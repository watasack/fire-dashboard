"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { SimulationResult } from "@/lib/simulator"
import { formatCurrency } from "@/lib/utils"
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"

interface CashFlowChartProps {
  result: SimulationResult | null
  compact?: boolean
  expanded?: boolean
}

export function CashFlowChart({ result, compact = false, expanded = false }: CashFlowChartProps) {
  const chartHeight = expanded ? "h-full" : compact ? "h-[200px]" : "h-[240px] sm:h-[280px] lg:h-[300px]"
  const showHeader = !compact && !expanded
  const showLegend = !compact && !expanded
  const chartMargin = (compact || expanded)
    ? { top: 16, right: 8, bottom: 4, left: 20 }
    : { top: 20, right: 8, bottom: 40, left: 20 }

  if (!result) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>収支グラフ</CardTitle>
        </CardHeader>
        <CardContent className={`flex ${chartHeight} items-center justify-center`}>
          <p className="text-muted-foreground">データがありません</p>
        </CardContent>
      </Card>
    )
  }

  const chartData = result.yearlyData.map((d) => ({
    label: `${d.age}歳`,
    income: d.income,
    expenses: d.expenses,
    netCF: d.income - d.expenses,
  }))

  const chartInner = (
    <div className={chartHeight}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={chartMargin}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.5} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11 }}
            angle={-30}
            textAnchor="end"
            height={showLegend ? 50 : 30}
            stroke="var(--color-muted-foreground)"
            interval={4}
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
                  <p className="mb-2 font-medium">{label}</p>
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
          {true ? <Bar dataKey="netCF" fill="#10B981" name="収支" opacity={0.85} /> : null}
          <ReferenceLine y={0} stroke="#888" strokeWidth={1} />
          {showLegend ? (
            <Legend
              wrapperStyle={{ paddingTop: "8px" }}
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
          <CardTitle>収支グラフ</CardTitle>
          <CardDescription>年齢別の収入・支出・年間収支</CardDescription>
        </CardHeader>
      )}
      <CardContent className={showHeader ? "" : "pt-3"}>
        {chartInner}
      </CardContent>
    </Card>
  )
}
