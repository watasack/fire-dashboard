"""
クロスバリデーション: Python 独立実装

TypeScript の計算ロジックを Python で独立に再実装し、
同じ入力に対する出力を突き合わせて計算の正確性を検証する。

検証対象:
1. 給与所得控除
2. 所得税（累進課税 + 復興特別所得税）
3. 住民税
4. 社会保険料
5. 年金計算
6. 課税口座売却（税計算）
7. 国保保険料

使い方:
  python -X utf8 tools/cross_validate.py
"""

import subprocess
import json
import math
import sys


# =============================================================================
# 1. 給与所得控除（給与所得計算）
# =============================================================================

def calculate_employment_income(gross: float, emp_type: str) -> float:
    """給与所得（給与所得控除後）"""
    if emp_type != "employee":
        return gross  # 個人事業主・専業主婦はそのまま
    if gross <= 1_628_000:
        return max(0, gross - 550_000)
    if gross <= 1_800_000:
        return max(0, gross - max(550_000, gross * 0.4 - 100_000))
    if gross <= 3_600_000:
        return gross - (gross * 0.3 + 80_000)
    if gross <= 6_600_000:
        return gross - (gross * 0.2 + 440_000)
    if gross <= 8_500_000:
        return gross - (gross * 0.1 + 1_100_000)
    return gross - 1_950_000


# =============================================================================
# 2. 社会保険料
# =============================================================================

def calculate_social_insurance(gross: float, emp_type: str, age: int) -> float:
    """社会保険料合計"""
    if emp_type == "employee":
        health_standard = min(gross / 12, 1_390_000)
        health_rate = 0.1182 if age >= 40 else 0.0998
        health_ins = health_standard * health_rate / 2 * 12

        pension_standard = min(gross / 12, 635_000)
        pension_ins = pension_standard * 0.183 / 2 * 12

        employment_ins = gross * 0.006
        return health_ins + pension_ins + employment_ins
    elif emp_type == "selfEmployed":
        nhi = gross * 0.10
        national_pension = 20_520 * 12
        return nhi + national_pension
    else:  # homemaker
        return 0


# =============================================================================
# 3. 所得税（累進課税 + 復興特別所得税）
# =============================================================================

def calculate_income_tax(taxable_income: float) -> float:
    """所得税（復興特別所得税 2.1% 込み）"""
    if taxable_income <= 1_950_000:
        base = taxable_income * 0.05
    elif taxable_income <= 3_300_000:
        base = 97_500 + (taxable_income - 1_950_000) * 0.10
    elif taxable_income <= 6_950_000:
        base = 232_500 + (taxable_income - 3_300_000) * 0.20
    elif taxable_income <= 9_000_000:
        base = 962_500 + (taxable_income - 6_950_000) * 0.23
    elif taxable_income <= 18_000_000:
        base = 1_434_000 + (taxable_income - 9_000_000) * 0.33
    elif taxable_income <= 40_000_000:
        base = 4_404_000 + (taxable_income - 18_000_000) * 0.40
    else:
        base = 13_204_000 + (taxable_income - 40_000_000) * 0.45
    return base * 1.021


# =============================================================================
# 4. 住民税
# =============================================================================

def calculate_resident_tax(taxable_income: float) -> float:
    """住民税（所得割10% + 均等割5,000円）"""
    if taxable_income <= 0:
        return 0
    return taxable_income * 0.10 + 5_000


# =============================================================================
# 5. 税額の一括計算
# =============================================================================

def calculate_tax_breakdown(gross: float, emp_type: str, age: int) -> dict:
    """TypeScript の calculateTaxBreakdown に対応"""
    employment_income = max(0, calculate_employment_income(gross, emp_type))
    social_insurance = calculate_social_insurance(gross, emp_type, age)
    basic_deduction = 480_000
    taxable_income = max(0, employment_income - social_insurance - basic_deduction)
    income_tax = calculate_income_tax(taxable_income)
    resident_tax = calculate_resident_tax(taxable_income)
    total_tax = social_insurance + income_tax + resident_tax
    net_income = max(0, gross - total_tax)
    return {
        "grossIncome": gross,
        "employmentIncome": employment_income,
        "socialInsurance": social_insurance,
        "taxableIncome": taxable_income,
        "incomeTax": income_tax,
        "residentTax": resident_tax,
        "totalTax": total_tax,
        "netIncome": net_income,
    }


# =============================================================================
# 6. 年金計算
# =============================================================================

def calculate_pension(emp_type: str, past_months: int, past_avg_remuneration: float,
                      past_national_months: int, future_months: int,
                      future_avg_remuneration: float) -> dict:
    """TypeScript の calculatePensionAmount (pensionConfig モード) に対応"""
    if emp_type == "employee":
        past_ep = past_avg_remuneration * past_months * 0.005481
        future_ep = future_avg_remuneration * future_months * 0.005481
        total_ep = past_ep + future_ep
        total_pension_months = past_national_months + past_months + future_months
        capped = min(total_pension_months, 480)
        national = round(816_000 * capped / 480)
        return {
            "employeePension": round(total_ep),
            "nationalPension": national,
            "totalAnnualPension": round(total_ep) + national,
        }
    elif emp_type == "selfEmployed":
        total_pension_months = past_national_months + future_months
        capped = min(total_pension_months, 480)
        national = round(816_000 * capped / 480)
        return {
            "employeePension": 0,
            "nationalPension": national,
            "totalAnnualPension": national,
        }
    else:
        capped = min(past_national_months, 480)
        national = round(816_000 * capped / 480)
        return {
            "employeePension": 0,
            "nationalPension": national,
            "totalAnnualPension": national,
        }


# =============================================================================
# 7. 課税口座売却
# =============================================================================

def withdraw_from_taxable(target: float, stock_value: float, cost_basis: float) -> dict:
    """TypeScript の withdrawFromTaxableAccount に対応"""
    TAX_RATE = 0.20315
    if stock_value <= 0 or target <= 0:
        return {
            "sellAmount": 0, "realizedGains": 0, "capitalGainsTax": 0,
            "netProceeds": 0, "remainingValue": stock_value, "remainingCostBasis": cost_basis,
        }
    gain_ratio = max(0, (stock_value - cost_basis) / stock_value)
    gross_sell = target / (1 - gain_ratio * TAX_RATE)
    sell_amount = min(gross_sell, stock_value)
    cost_basis_sold = sell_amount * (cost_basis / stock_value)
    realized_gains = sell_amount - cost_basis_sold
    capital_gains_tax = realized_gains * TAX_RATE
    net_proceeds = sell_amount - capital_gains_tax
    return {
        "sellAmount": sell_amount,
        "realizedGains": realized_gains,
        "capitalGainsTax": capital_gains_tax,
        "netProceeds": net_proceeds,
        "remainingValue": stock_value - sell_amount,
        "remainingCostBasis": cost_basis - cost_basis_sold,
    }


# =============================================================================
# 8. 国保保険料
# =============================================================================

def calculate_nhi_premium(last_year_income: float, household_size: int,
                          age: int) -> float:
    """TypeScript の calculateNHIPremium に対応（デフォルトパラメータ）"""
    deducted = max(0, last_year_income - 430_000)

    # 医療分
    medical_income = deducted * 0.1100
    medical_fixed = 50_000 * household_size + 30_000
    medical = min(medical_income + medical_fixed, 650_000)

    # 後期高齢者支援金分
    support_income = deducted * 0.0259
    support_fixed = 50_000 * 0.3 * household_size
    support = min(support_income + support_fixed, 240_000)

    # 介護分（40-64歳）
    care = 0.0
    if 40 <= age < 65:
        care_income = deducted * 0.0200
        care_fixed = 50_000 * 0.5 * household_size
        care = min(care_income + care_fixed, 170_000)

    return medical + support + care


# =============================================================================
# テストランナー
# =============================================================================

def close_enough(a: float, b: float, tolerance: float = 2.0) -> bool:
    """丸め誤差を考慮した比較"""
    return abs(a - b) <= tolerance


def run_tests() -> tuple[int, int]:
    passed = 0
    failed = 0

    def check(label: str, py_val: float, ts_val: float, tol: float = 2.0):
        nonlocal passed, failed
        if close_enough(py_val, ts_val, tol):
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {label}: Python={py_val:.2f}, TS={ts_val:.2f}, diff={abs(py_val-ts_val):.2f}")

    # ----- 税計算テスト -----
    print("=" * 60)
    print("1. 税計算クロスバリデーション")
    print("=" * 60)

    tax_cases = [
        (5_000_000, "employee", 35),
        (7_000_000, "employee", 35),
        (10_000_000, "employee", 45),
        (3_000_000, "employee", 25),
        (15_000_000, "employee", 50),
        (5_000_000, "selfEmployed", 35),
        (8_000_000, "selfEmployed", 42),
        (0, "employee", 35),
        (0, "homemaker", 30),
        (20_000_000, "employee", 55),
    ]

    # TypeScript の結果を取得
    ts_code = """
const { calculateTaxBreakdown } = require('./lib/simulator');
const cases = %s;
const results = cases.map(([g, e, a]) => calculateTaxBreakdown(g, e, a));
console.log(JSON.stringify(results));
""" % json.dumps(tax_cases)

    ts_results = run_ts(ts_code)

    for i, (gross, emp_type, age) in enumerate(tax_cases):
        py = calculate_tax_breakdown(gross, emp_type, age)
        ts = ts_results[i]
        label = f"gross={gross:,}, type={emp_type}, age={age}"
        print(f"\n  Case: {label}")
        check(f"  netIncome", py["netIncome"], ts["netIncome"])
        check(f"  incomeTax", py["incomeTax"], ts["incomeTax"])
        check(f"  residentTax", py["residentTax"], ts["residentTax"])
        check(f"  socialInsurance", py["socialInsurance"], ts["socialInsurance"])
        check(f"  employmentIncome", py["employmentIncome"], ts["employmentIncome"])

    # ----- 年金��算テスト -----
    print("\n" + "=" * 60)
    print("2. 年金計算クロスバリ��ーション")
    print("=" * 60)

    pension_cases = [
        ("employee", 120, 350_000, 120, 180, 400_000),
        ("employee", 0, 0, 0, 360, 500_000),
        ("selfEmployed", 0, 0, 240, 120, 0),
        ("homemaker", 0, 0, 360, 0, 0),
    ]

    ts_pension_code = """
const { calculatePensionAmount } = require('./lib/simulator');
const cases = %s;
const results = cases.map(([empType, pastMonths, pastAvg, pastNatl, futureMonths, futureAvg]) => {
    const person = {
        currentAge: 35, retirementAge: 65, grossIncome: 5000000,
        incomeGrowthRate: 0.02, pensionStartAge: 65, pensionAmount: null,
        employmentType: empType,
        pensionConfig: {
            pastEmployeeMonths: pastMonths,
            pastAverageMonthlyRemuneration: pastAvg,
            pastNationalPensionMonths: pastNatl,
            pensionGrowthRate: 0.01,
        },
    };
    return calculatePensionAmount(person, futureMonths / 12, futureAvg);
});
console.log(JSON.stringify(results));
""" % json.dumps(pension_cases)

    ts_pension = run_ts(ts_pension_code)

    for i, (emp_type, past_months, past_avg, past_natl, future_months, future_avg) in enumerate(pension_cases):
        py = calculate_pension(emp_type, past_months, past_avg, past_natl, future_months, future_avg)
        ts = ts_pension[i]
        label = f"type={emp_type}, pastM={past_months}, futM={future_months}"
        print(f"\n  Case: {label}")
        check(f"  employeePension", py["employeePension"], ts["employeePension"])
        check(f"  nationalPension", py["nationalPension"], ts["nationalPension"])
        check(f"  totalAnnualPension", py["totalAnnualPension"], ts["totalAnnualPension"])

    # ----- 課税口座売却テスト -----
    print("\n" + "=" * 60)
    print("3. 課税口座売却クロスバリデーション")
    print("=" * 60)

    withdrawal_cases = [
        (1_000_000, 10_000_000, 7_000_000),
        (5_000_000, 10_000_000, 5_000_000),
        (500_000, 3_000_000, 3_000_000),  # 含み益なし
        (0, 10_000_000, 5_000_000),       # 引き出し0
        (1_000_000, 0, 0),                # 資産0
    ]

    ts_withdrawal_code = """
const { withdrawFromTaxableAccount } = require('./lib/simulator');
const cases = %s;
const results = cases.map(([t, s, c]) => withdrawFromTaxableAccount(t, s, c));
console.log(JSON.stringify(results));
""" % json.dumps(withdrawal_cases)

    ts_withdrawal = run_ts(ts_withdrawal_code)

    for i, (target, stock, cost) in enumerate(withdrawal_cases):
        py = withdraw_from_taxable(target, stock, cost)
        ts = ts_withdrawal[i]
        label = f"target={target:,}, stock={stock:,}, cost={cost:,}"
        print(f"\n  Case: {label}")
        check(f"  sellAmount", py["sellAmount"], ts["sellAmount"])
        check(f"  capitalGainsTax", py["capitalGainsTax"], ts["capitalGainsTax"])
        check(f"  netProceeds", py["netProceeds"], ts["netProceeds"])

    # ----- 国保保��料テスト -----
    print("\n" + "=" * 60)
    print("4. 国保保険料クロスバリデーション")
    print("=" * 60)

    nhi_cases = [
        (3_000_000, 1, 35),
        (5_000_000, 2, 45),
        (1_000_000, 1, 55),
        (10_000_000, 3, 42),
        (0, 1, 35),
    ]

    ts_nhi_code = """
const { calculateNHIPremium } = require('./lib/simulator');
const config = {
    nhisoIncomeRate: 0.1100,
    nhisoSupportIncomeRate: 0.0259,
    nhisoFixedAmountPerPerson: 50000,
    nhisoHouseholdFixed: 30000,
    nhisoMaxAnnual: 1060000,
    nationalPensionMonthlyPremium: 16980,
    longTermCareRate: 0.0200,
    longTermCareMax: 170000,
};
const cases = %s;
const results = cases.map(([income, size, age]) => calculateNHIPremium(income, size, config, age));
console.log(JSON.stringify(results));
""" % json.dumps(nhi_cases)

    ts_nhi = run_ts(ts_nhi_code)

    for i, (income, size, age) in enumerate(nhi_cases):
        py = calculate_nhi_premium(income, size, age)
        ts = ts_nhi[i]
        label = f"income={income:,}, size={size}, age={age}"
        print(f"\n  Case: {label}")
        check(f"  nhipremium", py, ts)

    # ----- 一次資料ベース検証 -----
    print("\n" + "=" * 60)
    print("5. 一次資料ベース検証（国税庁・厚労省の公開情報と照合）")
    print("=" * 60)

    # === 5-1. 給与所得控除（国税庁 No.1410） ===
    # https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/1410.htm
    # 年収660万以下: 年収×20%+44万, 年収850万超: 195万（上限）
    print("\n  --- 給与所得控除（国税庁 No.1410）---")
    employment_deduction_cases = [
        # (年収, 期待される給与所得控除額, 根拠)
        (3_000_000, 3_000_000 * 0.3 + 80_000, "300万×30%+8万=98万"),
        (5_000_000, 5_000_000 * 0.2 + 440_000, "500万×20%+44万=144万"),
        (8_500_000, 8_500_000 * 0.1 + 1_100_000, "850万×10%+110万=195万"),
        (10_000_000, 1_950_000, "850万超は一律195万円"),
    ]
    for gross, expected_deduction, reason in employment_deduction_cases:
        actual_income = calculate_employment_income(gross, "employee")
        actual_deduction = gross - actual_income
        print(f"  年収{gross/10000:.0f}万: 控除={actual_deduction:,.0f}円 (期待値={expected_deduction:,.0f}円) [{reason}]")
        check(f"  給与所得控除 年収{gross/10000:.0f}万", actual_deduction, expected_deduction)

    # === 5-2. 所得税率（国税庁 No.2260） ===
    # https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/2260.htm
    print("\n  --- 所得税率（国税庁 No.2260）---")
    income_tax_cases = [
        # (課税所得, 期待される所得税（復興税抜き）, 税率と控除額)
        (1_000_000, 1_000_000 * 0.05, "5%"),
        (3_000_000, 97_500 + (3_000_000 - 1_950_000) * 0.10, "10%, 控除97,500円"),
        (5_000_000, 232_500 + (5_000_000 - 3_300_000) * 0.20, "20%, 控除232,500円"),
        (8_000_000, 962_500 + (8_000_000 - 6_950_000) * 0.23, "23%, 控除962,500円"),
    ]
    for taxable, expected_base, reason in income_tax_cases:
        actual = calculate_income_tax(taxable)
        expected_with_surtax = expected_base * 1.021  # 復興特別所得税
        print(f"  課税所得{taxable/10000:.0f}万: 税額={actual:,.0f}円 (期待値={expected_with_surtax:,.0f}円) [{reason}]")
        check(f"  所得税 課税所得{taxable/10000:.0f}万", actual, expected_with_surtax)

    # === 5-3. 厚生年金（日本年金機構の報酬比例部分計算式） ===
    # 報酬比例部分 = 平均標準報酬月額 × 5.481/1000 × 被保険者月数
    # 国民年金（老齢基礎年金）= 816,000円 × 納付月数/480
    print("\n  --- 年金計算（日本年金機構）---")
    # 例: 平均月収40万で30年（360月）加入の会社員
    avg_monthly = 400_000
    months = 360
    expected_employee_pension = round(avg_monthly * months * 0.005481)
    expected_national_pension = round(816_000 * min(months, 480) / 480)
    py_pension = calculate_pension("employee", months, avg_monthly, 0, 0, 0)
    print(f"  報酬比例: {py_pension['employeePension']:,}円 (期待値={expected_employee_pension:,}円)")
    print(f"  基礎年金: {py_pension['nationalPension']:,}円 (期待値={expected_national_pension:,}円)")
    check("  報酬比例（平均40万×30年）", py_pension["employeePension"], expected_employee_pension)
    check("  基礎年金（360月）", py_pension["nationalPension"], expected_national_pension)

    # === 5-4. 譲渡所得税率 20.315%（所得税15.315% + 住民税5%） ===
    print("\n  --- 譲渡所得税（20.315%）---")
    # 1000万で買って1500万で売る → 含み益500万 → 税 = 500万 × 20.315%
    stock_val = 15_000_000
    cost = 10_000_000
    gains = stock_val - cost
    expected_tax = gains * 0.20315
    # 全額売却の場合を検証
    py_withdrawal = withdraw_from_taxable(stock_val, stock_val, cost)
    print(f"  売却益{gains/10000:.0f}万: 税={py_withdrawal['capitalGainsTax']:,.0f}円 (期待値={expected_tax:,.0f}円)")
    check("  譲渡所得税", py_withdrawal["capitalGainsTax"], expected_tax)

    return passed, failed


def run_ts(code: str) -> list:
    """Node.js で TypeScript コードを実行して JSON を返す"""
    # ESM import に変換
    code = code.replace("require('./lib/simulator')", "await import('./lib/simulator.ts')")
    # 一時ファイルに書き出して tsx で実行（-e はエスケープ問題が起きやすいため）
    tmp_path = os.path.join(os.getcwd(), "_cross_validate_tmp.mjs")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(code)
        result = subprocess.run(
            ["npx", "tsx", tmp_path],
            capture_output=True, text=True, cwd=os.getcwd(),
            encoding="utf-8", shell=True,
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    if result.returncode != 0:
        print(f"TS Error: {result.stderr}")
        sys.exit(1)
    return json.loads(result.stdout.strip())


if __name__ == "__main__":
    import os
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))

    print("FIRE Simulator クロスバリデーション")
    print("Python 独立実装 vs TypeScript 実装")
    print()

    passed, failed = run_tests()

    print("\n" + "=" * 60)
    print(f"結果: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        print("\n⚠️  一致しないケースがあります。実装を確認してください。")
        sys.exit(1)
    else:
        print("\n✅ 全ケースで Python と TypeScript の計算結果が一致しました。")
        sys.exit(0)
