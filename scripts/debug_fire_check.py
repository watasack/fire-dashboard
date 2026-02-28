"""
simulate_post_fire_assets() vs _simulate_post_fire_with_random_returns() の差異を調査する診断スクリプト
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from src.data_loader import load_asset_data, load_transaction_data
from src.config import load_config
from src.data_processor import clean_asset_data, clean_transaction_data, calculate_monthly_cashflow
from src.analyzer import analyze_current_status, analyze_income_expense_trends
from src.simulator import (
    simulate_future_assets,
    simulate_post_fire_assets,
    _simulate_post_fire_with_random_returns,
    _initialize_post_fire_simulation,
    _process_post_fire_monthly_cycle,
    _BANKRUPTCY_THRESHOLD,
)

config = load_config('config.yaml')
override_start_ages = {'修平': 75, '桜': 75}

asset_df = load_asset_data(config)
transaction_df = load_transaction_data(config)
asset_df = clean_asset_data(asset_df)
transaction_df = clean_transaction_data(transaction_df)
cashflow_df = calculate_monthly_cashflow(transaction_df)
current_status = analyze_current_status(asset_df)
trends = analyze_income_expense_trends(cashflow_df, transaction_df, config)

monthly_income = config['simulation'].get('initial_labor_income', trends['monthly_avg_income_forecast'])

print("=" * 70)
print("診断: simulate_post_fire_assets vs _simulate_post_fire_with_random_returns")
print("=" * 70)

# Phase 1: FIRE月12の状態を取得
print("\n--- Phase 1: FIRE月12の資産状態を取得 ---")
df = simulate_future_assets(
    current_cash=current_status['cash_deposits'],
    current_stocks=current_status['investment_trusts'],
    monthly_income=monthly_income,
    monthly_expense=trends['monthly_avg_expense'],
    config=config,
    scenario='standard',
    disable_fire_check=True,
    override_start_ages=override_start_ages,
)

row_12 = df[df['month'] == 12].iloc[0]
fire_cash = row_12['cash']
fire_stocks = row_12['stocks']
fire_nisa = row_12['nisa_balance']
fire_nisa_cost = row_12.get('nisa_cost_basis', fire_nisa)
fire_stocks_cost = row_12['stocks_cost_basis']
years_offset = 12 / 12.0

print(f"  FIRE月12の状態:")
print(f"    現金:   {fire_cash:,.0f}")
print(f"    株式:   {fire_stocks:,.0f}")
print(f"    合計:   {fire_cash + fire_stocks:,.0f}")
print(f"    NISA:   {fire_nisa:,.0f}")
print(f"    株式簿価: {fire_stocks_cost:,.0f}")

# --- 関数A: simulate_post_fire_assets (can_retire_now経由) ---
print("\n--- 関数A: simulate_post_fire_assets() ---")
print(f"  破綻閾値: <= {_BANKRUPTCY_THRESHOLD:,.0f}")

result_a = simulate_post_fire_assets(
    current_cash=fire_cash,
    current_stocks=fire_stocks,
    years_offset=years_offset,
    config=config,
    scenario='standard',
    nisa_balance=fire_nisa,
    nisa_cost_basis=fire_nisa_cost,
    stocks_cost_basis=fire_stocks_cost,
    override_start_ages=override_start_ages,
)
print(f"  最終資産: {result_a:,.0f}")
print(f"  can_retire_now判定: {result_a > _BANKRUPTCY_THRESHOLD}")

# --- 関数B: _simulate_post_fire_with_random_returns (固定リターン) ---
print("\n--- 関数B: _simulate_post_fire_with_random_returns() ---")
print(f"  破綻閾値: < 0")

init = _initialize_post_fire_simulation(
    fire_cash, fire_stocks, years_offset, config, 'standard',
    fire_nisa, fire_nisa_cost, fire_stocks_cost
)
remaining_months = init['remaining_months']
params = config['simulation']['standard']
monthly_return_rate = (1 + params['annual_return_rate']) ** (1/12) - 1

fixed_returns = np.full(remaining_months, monthly_return_rate)

from src.simulator import _precompute_monthly_cashflows
post_fire_income = (
    config['simulation'].get('shuhei_post_fire_income', 0)
    + config['simulation'].get('sakura_post_fire_income', 0)
)
pre_exp, pre_inc, pre_base, pre_stage, pre_work = _precompute_monthly_cashflows(
    years_offset, remaining_months, config, post_fire_income,
    override_start_ages=override_start_ages,
)

result_b_ts = _simulate_post_fire_with_random_returns(
    current_cash=fire_cash,
    current_stocks=fire_stocks,
    years_offset=years_offset,
    config=config,
    scenario='standard',
    random_returns=fixed_returns,
    nisa_balance=fire_nisa,
    nisa_cost_basis=fire_nisa_cost,
    stocks_cost_basis=fire_stocks_cost,
    return_timeseries=True,
    precomputed_expenses=pre_exp,
    precomputed_income=pre_inc,
    precomputed_base_expenses=pre_base,
    precomputed_life_stages=pre_stage,
    precomputed_workation_costs=pre_work,
    baseline_assets=None,
    override_start_ages=override_start_ages,
)

result_b_final = result_b_ts[-1] if result_b_ts else 0
min_b = min(result_b_ts) if result_b_ts else 0
min_b_month = result_b_ts.index(min_b)

print(f"  最終資産: {result_b_final:,.0f}")
print(f"  最小資産: {min_b:,.0f} (月{min_b_month}, 年齢{36 + min_b_month/12:.1f}歳)")

# --- 関数Aの月ごとトレース ---
print("\n--- 関数Aの月ごとトレース ---")
init_a = _initialize_post_fire_simulation(
    fire_cash, fire_stocks, years_offset, config, 'standard',
    fire_nisa, fire_nisa_cost, fire_stocks_cost
)

cash_a = init_a['cash']
stocks_a = init_a['stocks']
scb_a = init_a['stocks_cost_basis']
nisa_a = init_a['nisa_balance']
ncb_a = init_a['nisa_cost_basis']
rm_a = init_a['remaining_months']
mrate_a = init_a['monthly_return_rate']
alloc_a = init_a['allocation_enabled']
cgt_a = init_a['capital_gains_tax_rate']
mcb_a = init_a['min_cash_balance']
pfi_a = init_a['post_fire_income']

current_date_a = datetime.now()
current_year_a = (current_date_a + relativedelta(months=int(years_offset * 12))).year
cg_year_a = 0
prev_cg_a = 0
peak_hist_a = []

timeseries_a = []
broke_month = None
for month_a in range(rm_a):
    cr = _process_post_fire_monthly_cycle(
        month_a, cash_a, stocks_a, scb_a, nisa_a, ncb_a,
        current_year_a, cg_year_a, prev_cg_a,
        years_offset, config, current_date_a,
        mrate_a, alloc_a, cgt_a, mcb_a, pfi_a,
        override_start_ages=override_start_ages,
        peak_assets_history=peak_hist_a,
    )
    cash_a = cr['cash']
    stocks_a = cr['stocks']
    scb_a = cr['stocks_cost_basis']
    nisa_a = cr['nisa_balance']
    ncb_a = cr['nisa_cost_basis']
    current_year_a = cr['current_year_post']
    cg_year_a = cr['capital_gains_this_year_post']
    prev_cg_a = cr['prev_year_capital_gains_post']
    total_a = cash_a + stocks_a
    timeseries_a.append(total_a)

    if cr['should_break'] and broke_month is None:
        broke_month = month_a
        print(f"  ★ 破綻! 月{month_a} (年齢{36 + month_a/12:.1f}歳): 資産={total_a:,.0f} <= 閾値{_BANKRUPTCY_THRESHOLD:,.0f}")
        break

if broke_month is None:
    print(f"  破綻せず。最終資産: {timeseries_a[-1]:,.0f}")
    min_a = min(timeseries_a)
    min_a_month = timeseries_a.index(min_a)
    print(f"  最小資産: {min_a:,.0f} (月{min_a_month}, 年齢{36 + min_a_month/12:.1f}歳)")

# --- 比較表 ---
print("\n" + "=" * 70)
print("月ごとの資産比較（関数A vs 関数B）")
print("=" * 70)
print(f"  {'月':>6s}  {'年齢':>6s}  {'関数A':>16s}  {'関数B':>16s}  {'差(A-B)':>16s}")
print(f"  {'----':>6s}  {'----':>6s}  {'----':>16s}  {'----':>16s}  {'----':>16s}")

compare_months = list(range(0, min(len(timeseries_a), len(result_b_ts)), 60))
last_common = min(len(timeseries_a), len(result_b_ts)) - 1
if last_common not in compare_months:
    compare_months.append(last_common)
if broke_month is not None and broke_month not in compare_months:
    compare_months.append(broke_month)
    compare_months.sort()

for m in compare_months:
    if m < len(timeseries_a) and m < len(result_b_ts):
        age = 36 + m / 12
        va = timeseries_a[m]
        vb = result_b_ts[m]
        diff = va - vb
        marker = " ★破綻" if m == broke_month else ""
        print(f"  {m:>6d}  {age:>5.1f}歳  {va:>15,.0f}  {vb:>15,.0f}  {diff:>15,.0f}{marker}")

# 500万以下のポイント
print(f"\n  [関数Bで{_BANKRUPTCY_THRESHOLD/10000:.0f}万円以下になる最初の月]")
first_below = None
for i, v in enumerate(result_b_ts):
    if v <= _BANKRUPTCY_THRESHOLD:
        first_below = (i, v)
        break
if first_below:
    print(f"    月{first_below[0]} (年齢{36+first_below[0]/12:.1f}歳): {first_below[1]:,.0f}")
else:
    print(f"    なし（常に{_BANKRUPTCY_THRESHOLD/10000:.0f}万円超）")
