#!/usr/bin/env python3
"""
FIRE失敗原因分析スクリプト

最良候補（FIREMonth=48, 年金75/75）でMCシミュレーションを実行し、
失敗するシナリオの特性を分析する。

分析1: 破産タイミングの分布
分析2: 失敗シナリオの特徴（Sequence of Returns Risk）
分析3: 感度分析（パラメータ変更による成功率変化）
"""

import sys
import copy
from pathlib import Path
from datetime import datetime

import numpy as np

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import load_config
from src.data_loader import load_asset_data, load_transaction_data
from src.data_processor import (
    clean_asset_data,
    clean_transaction_data,
    calculate_monthly_cashflow
)
from src.analyzer import (
    analyze_current_status,
    analyze_income_expense_trends,
)
from src.simulator import (
    simulate_future_assets,
    _simulate_post_fire_with_random_returns,
    _precompute_monthly_cashflows,
    generate_random_returns,
    generate_returns_enhanced,
    _BANKRUPTCY_THRESHOLD,
)


def load_data_and_config():
    config = load_config('config.yaml')
    asset_df = load_asset_data(config)
    transaction_df = load_transaction_data(config)
    asset_df = clean_asset_data(asset_df)
    transaction_df = clean_transaction_data(transaction_df)
    cashflow_df = calculate_monthly_cashflow(transaction_df)
    current_status = analyze_current_status(asset_df)
    trends = analyze_income_expense_trends(cashflow_df, transaction_df, config)

    monthly_income = trends['monthly_avg_income_forecast']
    initial_labor_income = config['simulation'].get('initial_labor_income')
    if initial_labor_income is not None:
        monthly_income = initial_labor_income

    return config, current_status, trends, monthly_income


def run_mc_with_trajectories(
    fire_cash, fire_stocks, fire_nisa, fire_nisa_cost, fire_stocks_cost,
    years_offset, remaining_months, config, scenario,
    override_start_ages, iterations, random_seed_offset=0,
    config_overrides=None,
):
    """MCシミュレーションを実行し、全イテレーションの資産推移とリターン系列を返す。"""
    effective_config = config
    if config_overrides:
        effective_config = copy.deepcopy(config)
        for key_path, value in config_overrides.items():
            keys = key_path.split('.')
            d = effective_config
            for k in keys[:-1]:
                d = d[k]
            d[keys[-1]] = value

    params = effective_config['simulation'][scenario]
    mc_config = effective_config['simulation'].get('monte_carlo', {})
    return_std_dev = mc_config.get('return_std_dev', 0.15)
    mean_reversion_speed = mc_config.get('mean_reversion_speed', 0.0)
    enhanced_enabled = mc_config.get('enhanced_model', {}).get('enabled', False)

    post_fire_income = (
        effective_config['simulation'].get('shuhei_post_fire_income', 0)
        + effective_config['simulation'].get('sakura_post_fire_income', 0)
    )

    precomputed = _precompute_monthly_cashflows(
        years_offset, remaining_months, effective_config, post_fire_income,
        override_start_ages=override_start_ages
    )
    precomputed_expenses, precomputed_income, precomputed_base_expenses, \
        precomputed_life_stages, precomputed_workation_costs = precomputed

    monthly_return_rate = (1 + params['annual_return_rate']) ** (1/12) - 1
    baseline_returns = np.full(remaining_months, monthly_return_rate)
    baseline_assets = _simulate_post_fire_with_random_returns(
        current_cash=fire_cash,
        current_stocks=fire_stocks,
        years_offset=years_offset,
        config=effective_config,
        scenario=scenario,
        random_returns=baseline_returns,
        nisa_balance=fire_nisa,
        nisa_cost_basis=fire_nisa_cost,
        stocks_cost_basis=fire_stocks_cost,
        return_timeseries=True,
        precomputed_expenses=precomputed_expenses,
        precomputed_income=precomputed_income,
        precomputed_base_expenses=precomputed_base_expenses,
        precomputed_life_stages=precomputed_life_stages,
        precomputed_workation_costs=precomputed_workation_costs,
        baseline_assets=None,
        override_start_ages=override_start_ages,
    )

    all_timeseries = []
    all_returns = []

    for i in range(iterations):
        seed = i + random_seed_offset
        if enhanced_enabled:
            random_returns = generate_returns_enhanced(
                annual_return_mean=params['annual_return_rate'],
                annual_return_std=return_std_dev,
                total_months=remaining_months,
                config=effective_config,
                random_seed=seed,
            )
        else:
            random_returns = generate_random_returns(
                params['annual_return_rate'],
                return_std_dev,
                remaining_months,
                mean_reversion_speed=mean_reversion_speed,
                random_seed=seed,
            )

        timeseries = _simulate_post_fire_with_random_returns(
            current_cash=fire_cash,
            current_stocks=fire_stocks,
            years_offset=years_offset,
            config=effective_config,
            scenario=scenario,
            random_returns=random_returns,
            nisa_balance=fire_nisa,
            nisa_cost_basis=fire_nisa_cost,
            stocks_cost_basis=fire_stocks_cost,
            return_timeseries=True,
            precomputed_expenses=precomputed_expenses,
            precomputed_income=precomputed_income,
            precomputed_base_expenses=precomputed_base_expenses,
            precomputed_life_stages=precomputed_life_stages,
            precomputed_workation_costs=precomputed_workation_costs,
            baseline_assets=baseline_assets,
            override_start_ages=override_start_ages,
        )

        all_timeseries.append(timeseries)
        all_returns.append(random_returns)

    return np.array(all_timeseries), np.array(all_returns), np.array(baseline_assets)


def find_bankruptcy_month(timeseries_array):
    """各イテレーションの破産月を特定。破産していなければ -1。"""
    n_iter, n_months = timeseries_array.shape
    bankruptcy_months = np.full(n_iter, -1, dtype=int)
    for i in range(n_iter):
        for m in range(n_months):
            if timeseries_array[i, m] <= 0:
                bankruptcy_months[i] = m
                break
    return bankruptcy_months


def analyze_bankruptcy_timing(timeseries_array, years_offset, start_age):
    """分析1: 破産タイミングの分布。"""
    bankruptcy_months = find_bankruptcy_month(timeseries_array)
    n_iter = len(bankruptcy_months)
    failed = bankruptcy_months[bankruptcy_months >= 0]
    succeeded = bankruptcy_months[bankruptcy_months < 0]

    print("\n" + "=" * 60)
    print("分析1: 破産タイミングの分布")
    print("=" * 60)
    print(f"  総イテレーション数: {n_iter}")
    print(f"  成功: {len(succeeded)} ({len(succeeded)/n_iter*100:.1f}%)")
    print(f"  失敗: {len(failed)} ({len(failed)/n_iter*100:.1f}%)")

    if len(failed) == 0:
        print("  破産シナリオなし")
        return bankruptcy_months

    fire_age = start_age + years_offset
    failed_years = failed / 12
    failed_ages = fire_age + failed_years

    print(f"\n  破産タイミング統計:")
    print(f"    最短: FIRE後{failed.min()/12:.1f}年 ({fire_age + failed.min()/12:.1f}歳)")
    print(f"    最長: FIRE後{failed.max()/12:.1f}年 ({fire_age + failed.max()/12:.1f}歳)")
    print(f"    中央値: FIRE後{np.median(failed)/12:.1f}年 ({fire_age + np.median(failed)/12:.1f}歳)")
    print(f"    平均: FIRE後{np.mean(failed)/12:.1f}年 ({fire_age + np.mean(failed)/12:.1f}歳)")

    # 5年区間のヒストグラム
    print(f"\n  破産タイミング分布（FIRE後の年数）:")
    bins = list(range(0, int(failed_years.max()) + 6, 5))
    counts, edges = np.histogram(failed_years, bins=bins)
    for j in range(len(counts)):
        if counts[j] > 0:
            bar = '#' * counts[j]
            age_start = fire_age + edges[j]
            age_end = fire_age + edges[j + 1]
            print(f"    {edges[j]:5.0f}-{edges[j+1]:5.0f}年 ({age_start:.0f}-{age_end:.0f}歳): "
                  f"{counts[j]:3d}件 {bar}")

    # 年金受給前 vs 後
    pension_start_month = int((75 - fire_age) * 12)
    before_pension = failed[failed < pension_start_month]
    after_pension = failed[failed >= pension_start_month]
    print(f"\n  年金受給開始（75歳）との関係:")
    print(f"    受給前に破産: {len(before_pension)}件 ({len(before_pension)/len(failed)*100:.1f}%)")
    print(f"    受給後に破産: {len(after_pension)}件 ({len(after_pension)/len(failed)*100:.1f}%)")

    return bankruptcy_months


def analyze_failure_characteristics(timeseries_array, returns_array, bankruptcy_months, years_offset, start_age):
    """分析2: 失敗シナリオの特徴（Sequence of Returns Risk）。"""
    print("\n" + "=" * 60)
    print("分析2: 失敗シナリオの特徴")
    print("=" * 60)

    failed_mask = bankruptcy_months >= 0
    success_mask = ~failed_mask
    n_failed = failed_mask.sum()
    n_success = success_mask.sum()

    if n_failed == 0:
        print("  失敗シナリオなし")
        return

    # 期間別の累積リターン比較
    periods = [
        ("FIRE後1-3年 (序盤)", 0, 36),
        ("FIRE後4-10年 (中盤)", 36, 120),
        ("FIRE後11-20年 (後半)", 120, 240),
    ]

    print(f"\n  期間別の年率リターン比較:")
    print(f"  {'期間':30s} {'失敗シナリオ':>15s} {'成功シナリオ':>15s} {'差':>10s}")
    print(f"  {'-'*70}")

    for label, start, end in periods:
        end = min(end, returns_array.shape[1])
        if start >= end:
            continue

        failed_returns = returns_array[failed_mask, start:end]
        success_returns = returns_array[success_mask, start:end]

        # 累積リターンから年率換算
        failed_cum = np.prod(1 + failed_returns, axis=1)
        success_cum = np.prod(1 + success_returns, axis=1)

        years = (end - start) / 12
        failed_ann = np.median(failed_cum ** (1 / years) - 1) * 100
        success_ann = np.median(success_cum ** (1 / years) - 1) * 100

        print(f"  {label:30s} {failed_ann:>14.2f}% {success_ann:>14.2f}% {failed_ann - success_ann:>9.2f}pp")

    # FIRE直後のリターン（最初の12ヶ月）の影響
    print(f"\n  Sequence of Returns Risk（FIRE直後12ヶ月の年率リターン）:")
    first_year_returns = returns_array[:, :min(12, returns_array.shape[1])]
    first_year_cum = np.prod(1 + first_year_returns, axis=1)
    first_year_ann = first_year_cum - 1

    failed_fy = first_year_ann[failed_mask]
    success_fy = first_year_ann[success_mask]

    print(f"    失敗シナリオ: 中央値{np.median(failed_fy)*100:+.2f}%, "
          f"P10={np.percentile(failed_fy, 10)*100:+.2f}%, "
          f"P90={np.percentile(failed_fy, 90)*100:+.2f}%")
    print(f"    成功シナリオ: 中央値{np.median(success_fy)*100:+.2f}%, "
          f"P10={np.percentile(success_fy, 10)*100:+.2f}%, "
          f"P90={np.percentile(success_fy, 90)*100:+.2f}%")

    # 最大ドローダウンの比較
    print(f"\n  最大ドローダウン比較:")
    for label, mask, n in [("失敗", failed_mask, n_failed), ("成功", success_mask, n_success)]:
        max_dd_list = []
        for i in np.where(mask)[0]:
            ts = timeseries_array[i]
            ts_nonzero = ts[ts > 0]
            if len(ts_nonzero) < 2:
                max_dd_list.append(-1.0)
                continue
            peak = np.maximum.accumulate(ts_nonzero)
            dd = (ts_nonzero - peak) / peak
            max_dd_list.append(dd.min())
        max_dd = np.array(max_dd_list)
        print(f"    {label}シナリオ: 中央値{np.median(max_dd)*100:.1f}%, "
              f"P10={np.percentile(max_dd, 10)*100:.1f}%, "
              f"最悪={max_dd.min()*100:.1f}%")

    # 資産が最も危険な時期
    print(f"\n  月別の資産中央値（失敗シナリオ vs 成功シナリオ）:")
    fire_age = start_age + years_offset
    milestones = [12, 36, 60, 120, 180, 240, 300]
    print(f"  {'時点':25s} {'失敗シナリオ':>15s} {'成功シナリオ':>15s}")
    print(f"  {'-'*55}")
    for m in milestones:
        if m >= timeseries_array.shape[1]:
            break
        age = fire_age + m / 12
        failed_val = np.median(timeseries_array[failed_mask, m]) / 10000
        success_val = np.median(timeseries_array[success_mask, m]) / 10000
        label = f"FIRE後{m/12:.0f}年 ({age:.0f}歳)"
        print(f"  {label:25s} {failed_val:>12.0f}万円 {success_val:>12.0f}万円")


def run_sensitivity_analysis(
    fire_cash, fire_stocks, fire_nisa, fire_nisa_cost, fire_stocks_cost,
    years_offset, remaining_months, config, scenario,
    override_start_ages, iterations, base_fire_month,
    current_cash_orig, current_stocks_orig, monthly_income, monthly_expense,
):
    """分析3: 感度分析。"""
    print("\n" + "=" * 60)
    print("分析3: 感度分析（パラメータ変更による成功率変化）")
    print("=" * 60)

    start_age = config['simulation'].get('start_age', 35)

    # ベースライン成功率
    base_ts, _, _ = run_mc_with_trajectories(
        fire_cash, fire_stocks, fire_nisa, fire_nisa_cost, fire_stocks_cost,
        years_offset, remaining_months, config, scenario,
        override_start_ages, iterations,
    )
    base_success = np.mean(base_ts[:, -1] > 0) * 100
    print(f"\n  ベースライン（FIRE月{base_fire_month}, 年金75/75）: 成功率{base_success:.1f}%")

    scenarios = []

    # (A) FIRE後の労働収入を増やす
    for extra in [50000, 100000, 150000]:
        label = f"FIRE後収入 +{extra//10000}万円/月"
        overrides = {
            'simulation.shuhei_post_fire_income':
                config['simulation']['shuhei_post_fire_income'] + extra,
        }
        scenarios.append((label, overrides, base_fire_month, override_start_ages))

    for extra in [50000, 100000]:
        label = f"桜の収入 +{extra//10000}万円/月"
        overrides = {
            'simulation.sakura_post_fire_income':
                config['simulation']['sakura_post_fire_income'] + extra,
        }
        scenarios.append((label, overrides, base_fire_month, override_start_ages))

    # (B) empty_nest支出削減
    base_empty_nest = config['fire']['base_expense_by_stage']['empty_nest']
    for pct in [-10, -20]:
        new_val = int(base_empty_nest * (1 + pct / 100))
        label = f"empty_nest支出 {pct}% ({new_val//10000}万円/年)"
        overrides = {
            'fire.base_expense_by_stage.empty_nest': new_val,
        }
        scenarios.append((label, overrides, base_fire_month, override_start_ages))

    # (C) ワーケーション費用削減
    for new_cost in [350000, 0]:
        label = f"ワーケーション {new_cost//10000}万円/年"
        overrides = {
            'workation.annual_cost': new_cost,
        }
        scenarios.append((label, overrides, base_fire_month, override_start_ages))

    # (D) FIRE月を後ろにずらす
    for delta in [6, 12, 24]:
        new_fire_month = base_fire_month + delta
        label = f"FIRE月 +{delta}ヶ月 (月{new_fire_month})"
        scenarios.append((label, {}, new_fire_month, override_start_ages))

    # (E) 年金開始年齢を下げる
    for shuhei_age, sakura_age in [(70, 75), (75, 70), (70, 70), (65, 65)]:
        label = f"年金 修平{shuhei_age}/桜{sakura_age}"
        new_override = {'修平': shuhei_age, '桜': sakura_age}
        scenarios.append((label, {}, base_fire_month, new_override))

    print(f"\n  {'シナリオ':40s} {'成功率':>8s} {'変化':>8s}")
    print(f"  {'-'*60}")
    print(f"  {'[ベースライン]':40s} {base_success:>7.1f}% {'-':>8s}")

    for label, config_overrides, fire_month, pension_override in scenarios:
        if fire_month != base_fire_month:
            fm_fire_state = _get_fire_state(
                fire_month, config, scenario, monthly_income, monthly_expense,
                current_cash_orig, current_stocks_orig,
            )
            if fm_fire_state is None:
                print(f"  {label:40s} {'N/A':>8s} {'N/A':>8s}")
                continue
            fc, fs, fn, fnc, fsc, yo, rm = fm_fire_state
        else:
            fc, fs, fn, fnc, fsc, yo, rm = (
                fire_cash, fire_stocks, fire_nisa, fire_nisa_cost,
                fire_stocks_cost, years_offset, remaining_months
            )

        ts, _, _ = run_mc_with_trajectories(
            fc, fs, fn, fnc, fsc, yo, rm,
            config, scenario, pension_override, iterations,
            config_overrides=config_overrides,
        )
        success_rate = np.mean(ts[:, -1] > 0) * 100
        delta = success_rate - base_success
        print(f"  {label:40s} {success_rate:>7.1f}% {delta:>+7.1f}pp")


def _get_fire_state(fire_month, config, scenario, monthly_income, monthly_expense,
                    current_cash, current_stocks):
    """指定FIRE月における資産状態を取得する。"""
    df = simulate_future_assets(
        current_cash=current_cash,
        current_stocks=current_stocks,
        config=config,
        scenario=scenario,
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        disable_fire_check=True,
    )
    if fire_month >= len(df):
        return None

    row = df.iloc[fire_month]
    start_age = config['simulation'].get('start_age', 35)
    life_expectancy = config['simulation'].get('life_expectancy', 90)
    years_offset = fire_month / 12
    fire_age = start_age + years_offset
    remaining_months = int((life_expectancy - fire_age) * 12)

    if remaining_months <= 0:
        return None

    return (
        row['cash'], row['stocks'], row['nisa_balance'],
        row.get('nisa_cost_basis', row['nisa_balance']),
        row['stocks_cost_basis'], years_offset, remaining_months,
    )


def main():
    print("=" * 60)
    print("FIRE失敗原因分析")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # データ読み込み
    print("[1/5] データ読み込み...")
    config, current_status, trends, monthly_income = load_data_and_config()
    monthly_expense = trends['monthly_avg_expense']
    scenario = 'standard'
    start_age = config['simulation'].get('start_age', 35)
    print("[OK]\n")

    # 分析対象の設定
    fire_month = 48
    override_start_ages = {'修平': 75, '桜': 75}
    iterations = 500

    print(f"[2/5] 分析対象:")
    print(f"  FIRE月: {fire_month} ({start_age + fire_month/12:.1f}歳)")
    print(f"  年金開始年齢: {override_start_ages}")
    print(f"  MCイテレーション: {iterations}")

    # FIRE達成時点の状態を取得
    print("\n[3/5] FIRE達成時点の状態を取得...")
    fire_state = _get_fire_state(
        fire_month, config, scenario, monthly_income, monthly_expense,
        current_status['cash_deposits'], current_status['investment_trusts'],
    )
    if fire_state is None:
        print("  [ERROR] 指定FIRE月が無効")
        return 1

    fire_cash, fire_stocks, fire_nisa, fire_nisa_cost, fire_stocks_cost, \
        years_offset, remaining_months = fire_state

    print(f"  FIRE時資産: JPY{fire_cash + fire_stocks:,.0f}")
    print(f"  (現金: {fire_cash:,.0f}, 株式: {fire_stocks:,.0f})")
    print(f"  残りシミュレーション月数: {remaining_months}")
    print("[OK]\n")

    # MCシミュレーション実行（全軌跡を取得）
    print(f"[4/5] MCシミュレーション実行中 ({iterations}回)...")
    all_timeseries, all_returns, baseline_assets = run_mc_with_trajectories(
        fire_cash, fire_stocks, fire_nisa, fire_nisa_cost, fire_stocks_cost,
        years_offset, remaining_months, config, scenario,
        override_start_ages, iterations,
    )
    print(f"  完了: shape={all_timeseries.shape}")
    print("[OK]\n")

    # 分析1: 破産タイミング
    bankruptcy_months = analyze_bankruptcy_timing(
        all_timeseries, years_offset, start_age
    )

    # 分析2: 失敗シナリオの特徴
    analyze_failure_characteristics(
        all_timeseries, all_returns, bankruptcy_months, years_offset, start_age
    )

    # 分析3: 感度分析
    print("\n[5/5] 感度分析実行中...")
    run_sensitivity_analysis(
        fire_cash, fire_stocks, fire_nisa, fire_nisa_cost, fire_stocks_cost,
        years_offset, remaining_months, config, scenario,
        override_start_ages, iterations, fire_month,
        current_status['cash_deposits'], current_status['investment_trusts'],
        monthly_income, monthly_expense,
    )

    print("\n" + "=" * 60)
    print("分析完了")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
