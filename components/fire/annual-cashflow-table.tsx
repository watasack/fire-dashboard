"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { SimulationResult, formatAnnualTableData } from "@/lib/simulator"
import { formatCurrency } from "@/lib/utils"

interface AnnualCashFlowTableProps {
  result: SimulationResult | null
}

export function AnnualCashFlowTable({ result }: AnnualCashFlowTableProps) {
  if (!result) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>年次収支テーブル</CardTitle>
        </CardHeader>
        <CardContent className="flex h-[300px] items-center justify-center">
          <p className="text-muted-foreground">データがありません</p>
        </CardContent>
      </Card>
    )
  }

  const rows = formatAnnualTableData(result.yearlyData)

  return (
    <Card className="overflow-hidden">
      <CardHeader>
        <CardTitle>年次収支テーブル</CardTitle>
        <CardDescription>年齢別の資産・収入・支出・年間収支一覧</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <div className="max-h-96 overflow-x-auto overflow-y-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="sticky top-0 bg-card border-b z-10">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">年齢</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground">西暦</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">総資産(万)</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">手取り(万)</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">支出(万)</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">住居費(万)</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">子育て(万)</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-muted-foreground">収支(万)</th>
                <th className="px-3 py-2 text-center text-xs font-medium text-muted-foreground">FIRE</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const rowBg = row.isFireAchieved
                  ? "bg-green-50 dark:bg-green-950/20"
                  : row.isSemiFire
                  ? "bg-blue-50 dark:bg-blue-950/20"
                  : ""
                const cfColor = row.netCashFlow >= 0 ? "text-green-600" : "text-red-500"
                return (
                  <tr key={`${row.year}-${row.age}`} className={`border-b last:border-0 ${rowBg}`}>
                    <td className="px-3 py-1.5 font-medium">{row.age}歳</td>
                    <td className="px-3 py-1.5 text-muted-foreground">{row.year}</td>
                    <td className="px-3 py-1.5 text-right">{Math.round(row.totalAssets / 10000).toLocaleString()}</td>
                    <td className="px-3 py-1.5 text-right">{Math.round(row.netIncome / 10000).toLocaleString()}</td>
                    <td className="px-3 py-1.5 text-right">{Math.round(row.expenses / 10000).toLocaleString()}</td>
                    <td className="px-3 py-1.5 text-right text-muted-foreground">
                      {row.housingCost > 0 ? Math.round(row.housingCost / 10000).toLocaleString() : "—"}
                    </td>
                    <td className="px-3 py-1.5 text-right text-muted-foreground">
                      {row.childCosts > 0 ? Math.round(row.childCosts / 10000).toLocaleString() : "—"}
                    </td>
                    <td className={`px-3 py-1.5 text-right font-medium ${cfColor}`}>
                      {row.netCashFlow >= 0 ? "+" : ""}{Math.round(row.netCashFlow / 10000).toLocaleString()}
                    </td>
                    <td className="px-3 py-1.5 text-center">
                      {row.isFireAchieved ? (
                        <span className="text-xs font-medium text-green-600">FIRE</span>
                      ) : row.isSemiFire ? (
                        <span className="text-xs font-medium text-blue-600">semi</span>
                      ) : null}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
