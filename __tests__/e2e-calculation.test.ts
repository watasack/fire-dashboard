/**
 * E2E 計算一致テスト
 *
 * UI表示層で使われるフォーマット関数（formatAnnualTableData, formatCashFlowChartData）の
 * 出力が、runSingleSimulation の生データと数学的に一致するかを検証する。
 *
 * UI のバインディングバグや丸め誤差の蓄積を検知するためのテスト。
 */

import { describe, test, expect } from 'vitest'
import {
  runSingleSimulation,
  formatAnnualTableData,
  formatCashFlowChartData,
  calculateFireAchievementRate,
  findEarliestFireAge,
  runMonteCarloSimulation,
  SimulationConfig,
  DEFAULT_CONFIG,
} from '../lib/simulator'

// ─────────────────────────────────────────────────────────────────────────────
// 1. formatAnnualTableData と yearlyData の一致
// ─────────────────────────────────────────────────────────────────────────────

describe('E2E: formatAnnualTableData と yearlyData の一致', () => {
  // findEarliestFireAge 経由で FIRE を発動させた結果に対して検証する。
  // runSingleSimulation 直接呼びでは fireAtAge が未指定で FIRE が発動せず、
  // FIRE 後の取り崩し・社保などの重要ロジックが検証対象から漏れる。

  test('全行の totalAssets が yearlyData の合算と一致する', () => {
    const result = findEarliestFireAge(DEFAULT_CONFIG)
    const table = formatAnnualTableData(result.yearlyData)

    for (let i = 0; i < table.length; i++) {
      const row = table[i]
      const yd = result.yearlyData[i]
      const expected = yd.cashAssets + yd.stocks + yd.nisaAssets + yd.idecoAssets + yd.otherAssets
      expect(Math.abs(row.totalAssets - expected)).toBeLessThan(2)
    }
  })

  test('全行の netCashFlow = netIncome - expenses', () => {
    const result = findEarliestFireAge(DEFAULT_CONFIG)
    const table = formatAnnualTableData(result.yearlyData)

    for (const row of table) {
      expect(Math.abs(row.netCashFlow - (row.netIncome - row.expenses))).toBeLessThan(2)
    }
  })

  test('全行の isFireAchieved / isSemiFire が yearlyData と一致', () => {
    const result = findEarliestFireAge(DEFAULT_CONFIG)
    const table = formatAnnualTableData(result.yearlyData)

    for (let i = 0; i < table.length; i++) {
      expect(table[i].isFireAchieved).toBe(result.yearlyData[i].isFireAchieved)
      expect(table[i].isSemiFire).toBe(result.yearlyData[i].isSemiFire)
    }
  })

  test('年齢・年が yearlyData と一致', () => {
    const result = findEarliestFireAge(DEFAULT_CONFIG)
    const table = formatAnnualTableData(result.yearlyData)

    for (let i = 0; i < table.length; i++) {
      expect(table[i].age).toBe(result.yearlyData[i].age)
      expect(table[i].year).toBe(result.yearlyData[i].year)
    }
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 2. formatCashFlowChartData の集計検証
// ─────────────────────────────────────────────────────────────────────────────

describe('E2E: formatCashFlowChartData の集計が yearlyData と一致', () => {

  test('全グループの income/expenses 合計が yearlyData の合計と一致', () => {
    const result = findEarliestFireAge(DEFAULT_CONFIG)
    const groups = formatCashFlowChartData(result.yearlyData, DEFAULT_CONFIG.person1.currentAge)

    const groupTotalIncome = groups.reduce((s, g) => s + g.income, 0)
    const groupTotalExpenses = groups.reduce((s, g) => s + g.expenses, 0)

    const ydTotalIncome = result.yearlyData.reduce((s, y) => s + y.income, 0)
    const ydTotalExpenses = result.yearlyData.reduce((s, y) => s + y.expenses, 0)

    expect(Math.abs(groupTotalIncome - ydTotalIncome)).toBeLessThan(100)
    expect(Math.abs(groupTotalExpenses - ydTotalExpenses)).toBeLessThan(100)
  })

  test('各グループの netCF = income - expenses', () => {
    const result = findEarliestFireAge(DEFAULT_CONFIG)
    const groups = formatCashFlowChartData(result.yearlyData, DEFAULT_CONFIG.person1.currentAge)

    for (const g of groups) {
      expect(Math.abs(g.netCF - (g.income - g.expenses))).toBeLessThan(2)
    }
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 3. calculateFireAchievementRate の整合性
// ─────────────────────────────────────────────────────────────────────────────

describe('E2E: FIRE 達成率の一貫性', () => {

  test('findEarliestFireAge で FIRE 達成 → fireAge が存在する', () => {
    // DEFAULT_CONFIG は FIRE 可能な設定なので、必ず fireAge が返るはず
    const result = findEarliestFireAge(DEFAULT_CONFIG)
    expect(result.fireAge).not.toBeNull()
    // fireAchievementRate は year0 時点の比率（開始時資産 / fireNumber）。
    // FIRE 年齢に到達するまで蓄積するので、year0 では 1.0 未満でも正常。
    // ただし 0 より大きいはず（初期資産が存在するため）
    expect(result.fireAchievementRate).toBeGreaterThan(0)
  })

  test('calculateFireAchievementRate と result.fireAchievementRate が一致', () => {
    const result = findEarliestFireAge(DEFAULT_CONFIG)
    const recalculated = calculateFireAchievementRate(result.yearlyData, result.fireNumber)
    expect(Math.abs(result.fireAchievementRate - recalculated)).toBeLessThan(0.01)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 4. findEarliestFireAge の妥当性
// ─────────────────────────────────────────────────────────────────────────────

describe('E2E: findEarliestFireAge の妥当性', () => {

  test('FIRE 年齢で FIRE し、1年早いと資産が枯渇する', () => {
    // findEarliestFireAge が返した年齢が「最早」であることを検証する。
    // fireAge - 1 歳で FIRE すると資産が枯渇するはず。
    const result = findEarliestFireAge(DEFAULT_CONFIG)
    expect(result.fireAge).not.toBeNull()

    if (result.fireAge !== null && result.fireAge > DEFAULT_CONFIG.person1.currentAge) {
      const tooEarly = runSingleSimulation(DEFAULT_CONFIG, undefined, result.fireAge - 1)
      // 1年早いと枯渇する（= depletionAge が非null）
      expect(tooEarly.depletionAge).not.toBeNull()
    }
  })

  test('FIRE 年齢で FIRE すると資産が枯渇しない', () => {
    const result = findEarliestFireAge(DEFAULT_CONFIG)
    expect(result.depletionAge).toBeNull()
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 5. MC 中央値と標準シミュレーションの近似一致
// ─────────────────────────────────────────────────────────────────────────────

describe('E2E: モンテカルロと標準シミュレーションの整合性', () => {

  test('MC: ボラティリティ≒0 なら標準シミュレーションと近似一致する', () => {
    // MC は findEarliestFireAge 経由で FIRE を自動判定するため、
    // 「FIRE しない設定」を作るのが困難。
    // ボラティリティをほぼゼロにすれば MC のランダムリターンが平均値に集中し、
    // 標準シミュレーション（= findEarliestFireAge の決定論的結果）と近い結果になるはず。
    const config: SimulationConfig = {
      ...DEFAULT_CONFIG,
      simulationYears: 20,
      investmentVolatility: 0.001,  // ほぼゼロ
    }
    // 標準も findEarliestFireAge 経由で
    const standard = findEarliestFireAge(config)
    const mc = runMonteCarloSimulation(config, 100)

    const finalYd = standard.yearlyData[standard.yearlyData.length - 1]
    const standardTotal = finalYd.cashAssets + finalYd.stocks +
      finalYd.nisaAssets + finalYd.idecoAssets + finalYd.otherAssets

    const mcP50Final = mc.yearlyPercentiles[mc.yearlyPercentiles.length - 1].p50

    if (standardTotal > 0) {
      const ratio = mcP50Final / standardTotal
      expect(ratio).toBeGreaterThan(0.7)
      expect(ratio).toBeLessThan(1.3)
    }
  })

  test('MC の successRate が 0〜1 の範囲', () => {
    const mc = runMonteCarloSimulation({ ...DEFAULT_CONFIG, simulationYears: 20 }, 100)
    expect(mc.successRate).toBeGreaterThanOrEqual(0)
    expect(mc.successRate).toBeLessThanOrEqual(1)
  })

  test('MC の yearlyPercentiles の順序: p10 ≤ p25 ≤ p50 ≤ p75 ≤ p90', () => {
    const mc = runMonteCarloSimulation({ ...DEFAULT_CONFIG, simulationYears: 20 }, 200)
    for (const yp of mc.yearlyPercentiles) {
      expect(yp.p10).toBeLessThanOrEqual(yp.p25 + 1)
      expect(yp.p25).toBeLessThanOrEqual(yp.p50 + 1)
      expect(yp.p50).toBeLessThanOrEqual(yp.p75 + 1)
      expect(yp.p75).toBeLessThanOrEqual(yp.p90 + 1)
    }
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// 6. 複数設定での端から端までの一貫性
// ─────────────────────────────────────────────────────────────────────────────

describe('E2E: 各種設定変更時の一貫性', () => {

  test('支出を増やすと FIRE 年齢が遅くなる（または達成しない）', () => {
    const resultLow = findEarliestFireAge({ ...DEFAULT_CONFIG, monthlyExpenses: 200_000 })
    const resultHigh = findEarliestFireAge({ ...DEFAULT_CONFIG, monthlyExpenses: 500_000 })

    // 低支出なら FIRE できるはず
    expect(resultLow.fireAge).not.toBeNull()

    if (resultHigh.fireAge !== null) {
      // 両方 FIRE 可能なら、高支出の方が遅い
      expect(resultHigh.fireAge).toBeGreaterThanOrEqual(resultLow.fireAge!)
    }
    // resultHigh.fireAge === null なら高支出で FIRE 不可能 → 単調性は成立
  })

  test('投資リターンを増やすと最終資産が増える', () => {
    // FIRE が発動すると取り崩しが始まり非線形になるため、
    // FIRE しない設定（高支出）で純粋な蓄積の差を検証
    const base = {
      ...DEFAULT_CONFIG,
      simulationYears: 20,
      monthlyExpenses: 1_000_000,  // 高支出で FIRE させない
    }
    const resultLow = findEarliestFireAge({ ...base, investmentReturn: 0.03 })
    const resultHigh = findEarliestFireAge({ ...base, investmentReturn: 0.07 })

    const finalLow = resultLow.yearlyData[resultLow.yearlyData.length - 1]
    const finalHigh = resultHigh.yearlyData[resultHigh.yearlyData.length - 1]

    const totalLow = finalLow.cashAssets + finalLow.stocks + finalLow.nisaAssets + finalLow.idecoAssets + finalLow.otherAssets
    const totalHigh = finalHigh.cashAssets + finalHigh.stocks + finalHigh.nisaAssets + finalHigh.idecoAssets + finalHigh.otherAssets
    expect(totalHigh).toBeGreaterThan(totalLow)
  })

  test('年収を増やすと FIRE が早まる', () => {
    const resultLow = findEarliestFireAge({
      ...DEFAULT_CONFIG,
      person1: { ...DEFAULT_CONFIG.person1, grossIncome: 5_000_000 },
    })
    const resultHigh = findEarliestFireAge({
      ...DEFAULT_CONFIG,
      person1: { ...DEFAULT_CONFIG.person1, grossIncome: 15_000_000 },
    })

    // 高年収なら必ず FIRE できる
    expect(resultHigh.fireAge).not.toBeNull()

    if (resultLow.fireAge !== null) {
      expect(resultHigh.fireAge!).toBeLessThanOrEqual(resultLow.fireAge)
    }
    // resultLow.fireAge === null なら低年収で FIRE 不可能 → 高年収の方が有利は自明
  })
})
