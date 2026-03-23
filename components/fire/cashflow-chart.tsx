"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { SimulationResult, formatCashFlowChartData } from "@/lib/simulator"
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
}

export function CashFlowChart({ result }: CashFlowChartProps) {
  if (!result) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>収支グラフ（5年単位）</CardTitle>
        </CardHeader>
        <CardContent className="flex h-[240px] sm:h-[280px] lg:h-[300px] items-center justify-center">
          <p className="text-muted-foreground">データがありません</p>
        </CardContent>
      </Card>
    )
  }

  const chartData = formatCashFlowChartData(result.yearlyData, 5)

  return (
    <Card>
      <CardHeader>
        <CardTitle>収支グラフ（5年単位）</CardTitle>
        <CardDescription>5年ごとの収入・支出・年間収支の合計</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[240px] sm:h-[280px] lg:h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 20, right: 8, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" opacity={0.5} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11 }}
                angle={-30}
                textAnchor="end"
                height={50}
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
              <Legend
                wrapperStyle={{ paddingTop: "8px" }}
                formatter={(value) => <span className="text-sm">{value}</span>}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
