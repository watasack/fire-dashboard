/**
 * Issue #16 reproduction: 低資産・高支出条件で MC が NaN/エラーになる
 */
import { describe, test, expect } from 'vitest'
import { runMonteCarloSimulation, runSingleSimulation, findEarliestFireAge, SimulationConfig, DEFAULT_CONFIG } from '../lib/simulator'

function buildIssueConfig(monthlyExpenses: number): SimulationConfig {
  return {
    ...DEFAULT_CONFIG,
    cashAssets: 1_000_000,    // 100万円
    stocks: 0,
    stocksCostBasis: 0,
    otherAssets: 0,
    monthlyExpenses,
    person1: {
      ...DEFAULT_CONFIG.person1,
      currentAge: 35,
      grossIncome: 6_000_000,
    },
    person2: {
      ...(DEFAULT_CONFIG.person2!),
      currentAge: 35,
      grossIncome: 5_500_000,
      maternityLeaveConfig: [],
      partTimeUntilAge: null,
    },
    children: [],
    mortgage: { monthlyPayment: 100_000, endYear: new Date().getFullYear() + 30 },
    simulationYears: 50,
  }
}

describe('Issue #16: 低資産・高支出条件のクラッシュ再現', () => {
  test('月支出 50万・資産 100万 で runMonteCarloSimulation がエラーを投げない', () => {
    const config = buildIssueConfig(500_000)
    expect(() => runMonteCarloSimulation(config, 100)).not.toThrow()
  })

  test('月支出 50万・資産 100万 で MC 結果に NaN/Infinity が含まれない', () => {
    const config = buildIssueConfig(500_000)
    const result = runMonteCarloSimulation(config, 100)
    result.yearlyPercentiles.forEach((yp) => {
      expect(Number.isFinite(yp.p10)).toBe(true)
      expect(Number.isFinite(yp.p25)).toBe(true)
      expect(Number.isFinite(yp.p50)).toBe(true)
      expect(Number.isFinite(yp.p75)).toBe(true)
      expect(Number.isFinite(yp.p90)).toBe(true)
    })
    expect(Number.isFinite(result.successRate)).toBe(true)
  })

  test('月支出 150万・資産 100万 で runMonteCarloSimulation がエラーを投げない', () => {
    const config = buildIssueConfig(1_500_000)
    expect(() => runMonteCarloSimulation(config, 100)).not.toThrow()
  })

  test('月支出 150万・資産 100万 で MC 結果に NaN/Infinity が含まれない', () => {
    const config = buildIssueConfig(1_500_000)
    const result = runMonteCarloSimulation(config, 100)
    result.yearlyPercentiles.forEach((yp) => {
      expect(Number.isFinite(yp.p10)).toBe(true)
      expect(Number.isFinite(yp.p50)).toBe(true)
      expect(Number.isFinite(yp.p90)).toBe(true)
    })
    expect(Number.isFinite(result.successRate)).toBe(true)
  })

  test('単発シミュレーション: 極端な負のリターンでも資産値が有限値', () => {
    const config = buildIssueConfig(500_000)
    // 強制的に -100% のリターン（破綻シナリオ）
    const extremeReturns = new Array(config.simulationYears + 1).fill(-1.1)
    expect(() => runSingleSimulation(config, extremeReturns)).not.toThrow()
    const result = runSingleSimulation(config, extremeReturns)
    result.yearlyData.forEach((d) => {
      expect(Number.isFinite(d.assets)).toBe(true)
      expect(Number.isFinite(d.cashAssets)).toBe(true)
      expect(Number.isFinite(d.stocks)).toBe(true)
      expect(Number.isFinite(d.nisaAssets)).toBe(true)
      expect(Number.isFinite(d.idecoAssets)).toBe(true)
    })
  })
})
