"""
年金受給開始年齢の最適化モジュール

FIRE達成時期と年金受給開始年齢を同時に最適化する。

定式化:
    minimize   m*  (FIRE達成月)
    subject to f(m*, a_修平, a_桜) >= 0.95  (MC成功率)
    where      a_修平, a_桜 ∈ {62, 63, ..., 75}

解法:
    Phase 1: FIRE前シミュレーション（FIRE判定なし、全月の状態記録）
    Phase 2: 確定的スクリーニング（全候補を高速評価、上位K件を選出）
    Phase 3: MC精密評価（上位候補のみ、成功率≥αで最小FIRE月を選択）
"""

import copy
import multiprocessing
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from itertools import product

_PROJECT_ROOT = str(Path(__file__).parent.parent)

from src.simulator import (
    simulate_future_assets,
    simulate_post_fire_assets,
    _simulate_post_fire_with_random_returns,
    _simulate_post_fire_mc_vectorized,
    _precompute_monthly_cashflows,
    _initialize_post_fire_simulation,
    generate_random_returns,
    generate_returns_enhanced,
    generate_random_returns_batch,
    generate_returns_enhanced_batch,
)


PENSION_AGE_MIN = 62
PENSION_AGE_MAX = 75
DEFAULT_MIN_SUCCESS_RATE = 0.95
DEFAULT_TOP_K = 30
DEFAULT_MC_ITERATIONS = 500

_CASH_STRATEGY_COLS = ['cash_safety_margin', 'cash_crash_threshold']
_EXPENSE_REDUCTION_COLS = ['er_level1', 'er_level2', 'er_level3']


def _apply_cash_strategy(config: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
    """現金管理戦略のオーバーライドを適用した config のコピーを返す。"""
    cfg = copy.copy(config)
    base = config.get('post_fire_cash_strategy', {})
    cfg['post_fire_cash_strategy'] = {**base, **strategy}
    return cfg


def _apply_expense_reduction(config: Dict[str, Any], rates: Dict[str, float]) -> Dict[str, Any]:
    """動的支出削減率のオーバーライドを適用した config のコピーを返す。"""
    cfg = copy.copy(config)
    fire_cfg = copy.copy(config.get('fire', {}))
    der_cfg = copy.copy(fire_cfg.get('dynamic_expense_reduction', {}))
    base_rates = der_cfg.get('reduction_rates', {})
    der_cfg['reduction_rates'] = {**base_rates, **rates}
    fire_cfg['dynamic_expense_reduction'] = der_cfg
    cfg['fire'] = fire_cfg
    return cfg


def optimize_pension_start_ages(
    current_cash: float,
    current_stocks: float,
    config: Dict[str, Any],
    scenario: str = 'standard',
    monthly_income: float = 0,
    monthly_expense: float = 0,
    min_success_rate: float = DEFAULT_MIN_SUCCESS_RATE,
    top_k: int = DEFAULT_TOP_K,
    mc_iterations: int = DEFAULT_MC_ITERATIONS,
    fire_month_search_range: int = 36,
    fire_month_step: int = 12,
    extra_budget_candidates: List[float] = None,
    cash_strategy_candidates: List[Dict[str, Any]] = None,
    expense_reduction_candidates: List[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    FIRE達成時期・年金受給開始年齢・FIRE後追加予算・現金管理戦略・動的支出削減を同時に最適化する。

    Args:
        current_cash: 現在の現金残高
        current_stocks: 現在の株式残高
        config: 設定辞書
        scenario: シナリオ名
        monthly_income: 月次労働収入
        monthly_expense: 月次支出
        min_success_rate: 許容最低成功率（デフォルト: 0.95）
        top_k: MC評価する上位候補数
        mc_iterations: MCイテレーション数
        fire_month_search_range: 基準FIRE月 ± この月数を探索
        fire_month_step: FIRE候補月の刻み幅
        extra_budget_candidates: FIRE後追加月額予算の候補リスト（円）
        cash_strategy_candidates: 現金管理戦略の候補リスト
        expense_reduction_candidates: 動的支出削減率の候補リスト
            各要素は {'level_1_warning': float, 'level_2_concern': float, 'level_3_crisis': float}

    Returns:
        最適化結果の辞書
    """
    if extra_budget_candidates is None:
        extra_budget_candidates = [0]
    if cash_strategy_candidates is None:
        cash_strategy_candidates = [{}]
    if expense_reduction_candidates is None:
        expense_reduction_candidates = [{}]
    print("=" * 60)
    print("年金受給開始年齢の最適化")
    print("=" * 60)

    people = config.get('pension', {}).get('people', [])
    person_names = [p.get('name', f'person_{i}') for i, p in enumerate(people)]

    # Phase 1
    print("\nPhase 1: FIRE前シミュレーション（FIRE判定なし）...")
    pre_fire_df = _simulate_pre_fire_trajectory(
        current_cash, current_stocks, config, scenario,
        monthly_income, monthly_expense
    )
    print(f"  全{len(pre_fire_df)}ヶ月の状態を記録 [OK]")

    # 基準FIRE月を取得（通常のFIRE判定つきシミュレーション）
    print("\n  基準FIRE月を取得中...")
    baseline_df = simulate_future_assets(
        current_cash=current_cash,
        current_stocks=current_stocks,
        config=config,
        scenario=scenario,
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
    )
    fire_rows = baseline_df[baseline_df['fire_achieved'] == True]
    if len(fire_rows) == 0:
        print("  [ERROR] 基準シミュレーションでFIRE達成不可")
        return {'error': 'FIRE not achievable in baseline simulation'}

    baseline_fire_month = int(fire_rows.iloc[0]['fire_month'])
    start_age = config['simulation'].get('start_age', 35)
    baseline_fire_age = start_age + baseline_fire_month / 12
    print(f"  基準FIRE月: {baseline_fire_month}（{baseline_fire_age:.1f}歳）")

    # Phase 2
    fire_month_min = max(1, baseline_fire_month - fire_month_search_range)
    fire_month_max = baseline_fire_month + fire_month_search_range
    max_month = len(pre_fire_df) - 1
    fire_month_max = min(fire_month_max, max_month)

    fire_month_candidates = list(range(fire_month_min, fire_month_max + 1, fire_month_step))
    if baseline_fire_month not in fire_month_candidates:
        fire_month_candidates.append(baseline_fire_month)
        fire_month_candidates.sort()

    # Phase 2a: 粗いグリッド（3年刻み）で高速スクリーニング
    coarse_ages = list(range(PENSION_AGE_MIN, PENSION_AGE_MAX + 1, 3))
    if PENSION_AGE_MAX not in coarse_ages:
        coarse_ages.append(PENSION_AGE_MAX)

    coarse_combos = len(coarse_ages) ** len(person_names)
    total_coarse = (len(fire_month_candidates) * coarse_combos
                    * len(extra_budget_candidates) * len(cash_strategy_candidates))

    print(f"\nPhase 2: 確定的スクリーニング")
    print(f"  FIRE候補月: {fire_month_candidates}")
    print(f"  年金開始年齢（粗いグリッド）: {coarse_ages} × {len(person_names)}人 = {coarse_combos}通り")
    if len(extra_budget_candidates) > 1:
        budget_str = ', '.join(f'{b/10000:.0f}万' for b in extra_budget_candidates)
        print(f"  追加予算候補: [{budget_str}]/月 ({len(extra_budget_candidates)}通り)")
    if len(cash_strategy_candidates) > 1:
        print(f"  現金管理戦略候補: {len(cash_strategy_candidates)}通り")
    if len(expense_reduction_candidates) > 1:
        print(f"  動的支出削減候補: {len(expense_reduction_candidates)}通り（Phase 3で評価）")
    print(f"  合計候補数: {total_coarse}")

    screening_results = _run_deterministic_screening(
        pre_fire_df, config, scenario,
        fire_month_candidates, coarse_ages, person_names,
        extra_budget_candidates=extra_budget_candidates,
        cash_strategy_candidates=cash_strategy_candidates,
    )

    feasible = screening_results[screening_results['final_assets'] > 0]
    print(f"  実行可能な候補: {len(feasible)}/{len(screening_results)}通り [OK]")

    if len(feasible) == 0:
        print("  [ERROR] 実行可能な候補なし")
        return {'error': 'No feasible candidates found'}

    feasible_sorted = feasible.sort_values(
        ['fire_month', 'extra_budget', 'final_assets'],
        ascending=[True, False, False]
    )

    coarse_top = _select_diverse_top_k(feasible_sorted, min(top_k, len(feasible_sorted)), person_names)

    # Phase 2b: 有望な候補の近傍で細かいグリッド（1年刻み）にリファイン
    fine_fire_months = sorted(set(int(r['fire_month']) for _, r in coarse_top.iterrows()))
    fine_age_centers = set()
    for _, r in coarse_top.iterrows():
        for name in person_names:
            fine_age_centers.add(int(r[f'age_{name}']))

    fine_ages = set()
    for center in fine_age_centers:
        for delta in range(-2, 3):
            age = center + delta
            if PENSION_AGE_MIN <= age <= PENSION_AGE_MAX:
                fine_ages.add(age)
    fine_ages = sorted(fine_ages)

    fine_combos = len(fine_ages) ** len(person_names)
    total_fine = (len(fine_fire_months) * fine_combos * len(extra_budget_candidates)
                  * len(cash_strategy_candidates))
    print(f"\n  リファイン（1年刻み）: FIRE月{fine_fire_months}, 年金{fine_ages}")
    print(f"  リファイン候補数: {total_fine}")

    fine_results = _run_deterministic_screening(
        pre_fire_df, config, scenario,
        fine_fire_months, fine_ages, person_names,
        extra_budget_candidates=extra_budget_candidates,
        cash_strategy_candidates=cash_strategy_candidates,
    )

    all_screening = pd.concat([screening_results, fine_results], ignore_index=True)
    dedup_cols = (['fire_month', 'extra_budget']
                  + _CASH_STRATEGY_COLS
                  + [f'age_{n}' for n in person_names])
    all_screening = all_screening.drop_duplicates(subset=dedup_cols)
    feasible_all = all_screening[all_screening['final_assets'] > 0]
    feasible_all_sorted = feasible_all.sort_values(
        ['fire_month', 'extra_budget', 'final_assets'],
        ascending=[True, False, False]
    )

    top_candidates = _select_diverse_top_k(feasible_all_sorted, top_k, person_names)
    print(f"  MC評価対象: {len(top_candidates)}候補を選出")

    # Phase 3
    total_mc = len(top_candidates) * len(expense_reduction_candidates)
    print(f"\nPhase 3: MC精密評価（各{mc_iterations}回 × {len(expense_reduction_candidates)}削減戦略 = {total_mc}評価）")
    mc_results = _run_mc_evaluation(
        top_candidates, pre_fire_df, config, scenario,
        mc_iterations, person_names,
        expense_reduction_candidates=expense_reduction_candidates,
    )
    print("  [OK]")

    # 最適解を選出
    optimal, pareto_info = _find_optimal_solution(
        mc_results, min_success_rate, person_names
    )

    # 基準解との比較情報を構築
    baseline_info = _get_baseline_info(
        baseline_fire_month, pre_fire_df, config, scenario,
        mc_iterations, person_names
    )

    result = {
        'optimal': optimal,
        'baseline': baseline_info,
        'pareto_info': pareto_info,
        'all_mc_results': mc_results,
        'min_success_rate': min_success_rate,
        'person_names': person_names,
    }

    _print_result(result)

    return result


def _simulate_pre_fire_trajectory(
    current_cash: float,
    current_stocks: float,
    config: Dict[str, Any],
    scenario: str,
    monthly_income: float,
    monthly_expense: float
) -> pd.DataFrame:
    """Phase 1: FIRE判定なしで全期間の月次状態を記録する。"""
    df = simulate_future_assets(
        current_cash=current_cash,
        current_stocks=current_stocks,
        config=config,
        scenario=scenario,
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        disable_fire_check=True,
    )
    return df


def _compute_pension_income_array(
    years_offset: float,
    remaining_months: int,
    config: Dict[str, Any],
    post_fire_income: float,
    override_start_ages: Dict[str, int],
) -> np.ndarray:
    """年金開始年齢に依存する月次収入配列を計算する。"""
    from src.simulator import (
        calculate_pension_income, calculate_child_allowance
    )
    income = np.zeros(remaining_months)
    for month_idx in range(remaining_months):
        years = years_offset + month_idx / 12
        annual_pension = calculate_pension_income(
            years, config, fire_achieved=True, fire_year_offset=years_offset,
            current_assets=None, fire_target_assets=None,
            override_start_ages=override_start_ages
        )
        monthly_pension = annual_pension / 12
        effective_labor = 0 if monthly_pension > 0 else post_fire_income
        annual_child = calculate_child_allowance(years, config)
        income[month_idx] = effective_labor + monthly_pension + annual_child / 12
    return income


def _run_deterministic_screening(
    pre_fire_df: pd.DataFrame,
    config: Dict[str, Any],
    scenario: str,
    fire_month_candidates: List[int],
    pension_ages: List[int],
    person_names: List[str],
    extra_budget_candidates: List[float] = None,
    cash_strategy_candidates: List[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Phase 2: 全候補を確定的シミュレーションで高速評価する。

    同じFIRE月の支出配列を共有し、年金収入のみ差し替えることで高速化。
    """
    if extra_budget_candidates is None:
        extra_budget_candidates = [0]
    if cash_strategy_candidates is None:
        cash_strategy_candidates = [{}]

    default_strategy = config.get('post_fire_cash_strategy', {})
    default_safety = default_strategy.get('safety_margin', 5_000_000)
    default_crash = default_strategy.get('market_crash_threshold', -0.20)

    strategy_configs = [
        (cs, _apply_cash_strategy(config, cs))
        for cs in cash_strategy_candidates
    ]

    results = []
    age_combos = list(product(pension_ages, repeat=len(person_names)))
    total = (len(fire_month_candidates) * len(age_combos)
             * len(extra_budget_candidates) * len(cash_strategy_candidates))
    done = 0

    params = config['simulation'][scenario]
    monthly_return_rate = (1 + params['annual_return_rate']) ** (1/12) - 1

    life_expectancy = config['simulation'].get('life_expectancy', 90)
    start_age = config['simulation'].get('start_age', 35)

    post_fire_income = (
        config['simulation'].get('shuhei_post_fire_income', 0)
        + config['simulation'].get('sakura_post_fire_income', 0)
    )

    for fire_month in fire_month_candidates:
        if fire_month >= len(pre_fire_df):
            continue

        row = pre_fire_df.iloc[fire_month]
        fire_cash = row['cash']
        fire_stocks = row['stocks']
        fire_nisa = row['nisa_balance']
        fire_nisa_cost = row.get('nisa_cost_basis', fire_nisa)
        fire_stocks_cost = row['stocks_cost_basis']
        years_offset = fire_month / 12

        fire_age = start_age + years_offset
        remaining_years = life_expectancy - fire_age
        remaining_months = int(remaining_years * 12)
        if remaining_months <= 0:
            continue

        fixed_returns = np.full(remaining_months, monthly_return_rate)

        base_precomputed = _precompute_monthly_cashflows(
            years_offset, remaining_months, config, post_fire_income,
            override_start_ages=None
        )
        shared_expenses = base_precomputed[0]
        shared_base_expenses = base_precomputed[2]
        shared_life_stages = base_precomputed[3]
        shared_workation_costs = base_precomputed[4]

        for ages in age_combos:
            override = dict(zip(person_names, ages))

            income_array = _compute_pension_income_array(
                years_offset, remaining_months, config,
                post_fire_income, override
            )

            for extra_budget in extra_budget_candidates:
                for cs, cfg in strategy_configs:
                    final = _simulate_post_fire_with_random_returns(
                        current_cash=fire_cash,
                        current_stocks=fire_stocks,
                        years_offset=years_offset,
                        config=cfg,
                        scenario=scenario,
                        random_returns=fixed_returns,
                        nisa_balance=fire_nisa,
                        nisa_cost_basis=fire_nisa_cost,
                        stocks_cost_basis=fire_stocks_cost,
                        return_timeseries=False,
                        precomputed_expenses=shared_expenses,
                        precomputed_income=income_array,
                        precomputed_base_expenses=shared_base_expenses,
                        precomputed_life_stages=shared_life_stages,
                        precomputed_workation_costs=shared_workation_costs,
                        baseline_assets=None,
                        override_start_ages=override,
                        extra_monthly_budget=extra_budget,
                    )

                    entry = {
                        'fire_month': fire_month,
                        'extra_budget': extra_budget,
                        'cash_safety_margin': cs.get('safety_margin', default_safety),
                        'cash_crash_threshold': cs.get('market_crash_threshold', default_crash),
                        'final_assets': final,
                    }
                    for i, name in enumerate(person_names):
                        entry[f'age_{name}'] = ages[i]

                    results.append(entry)

                    done += 1
                    if done % 500 == 0:
                        print(f"  Progress: {done}/{total} ({done*100/total:.0f}%)")

    return pd.DataFrame(results)


def _select_diverse_top_k(
    feasible_sorted: pd.DataFrame,
    top_k: int,
    person_names: List[str]
) -> pd.DataFrame:
    """FIRE月×現金管理戦略の多様性を確保しつつ上位K件を選出する。

    (FIRE月, cash_safety_margin) の各グループからラウンドロビンで選出し、
    特定のFIRE月や特定の現金管理戦略に偏ることを防ぐ。
    """
    by_group = {}
    seen_combos = set()

    for _, row in feasible_sorted.iterrows():
        fm = int(row['fire_month'])
        ages = tuple(row[f'age_{name}'] for name in person_names)
        eb = row.get('extra_budget', 0)
        cs_margin = row.get('cash_safety_margin', 0)
        cs_crash = row.get('cash_crash_threshold', 0)
        key = (fm, ages, eb, cs_margin, cs_crash)
        if key in seen_combos:
            continue
        seen_combos.add(key)
        group_key = (fm, cs_margin)
        by_group.setdefault(group_key, []).append(row)

    selected = []
    groups_sorted = sorted(by_group.keys())
    slot = 0
    while len(selected) < top_k:
        added = False
        for gk in groups_sorted:
            candidates = by_group[gk]
            if slot < len(candidates):
                selected.append(candidates[slot])
                added = True
                if len(selected) >= top_k:
                    break
        if not added:
            break
        slot += 1

    return pd.DataFrame(selected)



def _init_worker(project_root: str) -> None:
    """ワーカープロセスの sys.path を設定する（Windows spawn 対応）。"""
    import sys
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def _evaluate_single_candidate(args: dict) -> List[dict]:
    """
    単一候補のMC評価（並列ワーカー関数）。

    候補 1 件に対してすべての expense_reduction_candidates を評価し、
    結果リスト（len = len(expense_reduction_candidates)）を返す。
    """
    import numpy as np
    from src.simulator import (
        _simulate_post_fire_with_random_returns,
        _simulate_post_fire_mc_vectorized,
        _precompute_monthly_cashflows,
        generate_returns_enhanced_batch,
        generate_random_returns_batch,
    )

    cand                        = args['cand']
    pre_fire_row                = args['pre_fire_row']
    config                      = args['config']
    scenario                    = args['scenario']
    iterations                  = args['iterations']
    person_names                = args['person_names']
    expense_reduction_candidates = args['expense_reduction_candidates']
    enhanced_enabled            = args['enhanced_enabled']
    return_std_dev              = args['return_std_dev']
    mean_reversion_speed        = args['mean_reversion_speed']
    life_expectancy             = args['life_expectancy']
    start_age                   = args['start_age']
    post_fire_income            = args['post_fire_income']
    params                      = args['params']
    default_safety              = args['default_safety']
    default_crash               = args['default_crash']
    default_l1                  = args['default_l1']
    default_l2                  = args['default_l2']
    default_l3                  = args['default_l3']

    fire_month   = int(cand['fire_month'])
    override     = {name: int(cand[f'age_{name}']) for name in person_names}
    extra_budget = float(cand.get('extra_budget', 0))

    cash_strategy = {}
    cand_safety = cand.get('cash_safety_margin')
    cand_crash  = cand.get('cash_crash_threshold')
    if cand_safety is not None and float(cand_safety) != default_safety:
        cash_strategy['safety_margin'] = float(cand_safety)
    if cand_crash is not None and float(cand_crash) != default_crash:
        cash_strategy['market_crash_threshold'] = float(cand_crash)

    fire_cash        = pre_fire_row['cash']
    fire_stocks      = pre_fire_row['stocks']
    fire_nisa        = pre_fire_row['nisa_balance']
    fire_nisa_cost   = pre_fire_row.get('nisa_cost_basis', fire_nisa)
    fire_stocks_cost = pre_fire_row['stocks_cost_basis']
    years_offset     = fire_month / 12

    fire_age         = start_age + years_offset
    remaining_years  = life_expectancy - fire_age
    remaining_months = int(remaining_years * 12)
    if remaining_months <= 0:
        return []

    precomputed = _precompute_monthly_cashflows(
        years_offset, remaining_months, config, post_fire_income,
        override_start_ages=override,
    )
    precomputed_expenses, precomputed_income, precomputed_base_expenses, \
        precomputed_life_stages, precomputed_workation_costs = precomputed

    monthly_return_rate = (1 + params['annual_return_rate']) ** (1 / 12) - 1

    if enhanced_enabled:
        random_returns_matrix = generate_returns_enhanced_batch(
            annual_return_mean=params['annual_return_rate'],
            annual_return_std=return_std_dev,
            total_months=remaining_months,
            n_paths=iterations,
            config=config,
            random_seed=0,
        )
    else:
        random_returns_matrix = generate_random_returns_batch(
            annual_return_mean=params['annual_return_rate'],
            annual_return_std=return_std_dev,
            total_months=remaining_months,
            n_paths=iterations,
            mean_reversion_speed=mean_reversion_speed,
            random_seed=0,
        )

    results = []
    for er in expense_reduction_candidates:
        cfg = config
        if cash_strategy:
            cfg = _apply_cash_strategy(cfg, cash_strategy)
        if er:
            cfg = _apply_expense_reduction(cfg, er)

        baseline_returns = np.full(remaining_months, monthly_return_rate)
        baseline_assets = _simulate_post_fire_with_random_returns(
            current_cash=fire_cash,
            current_stocks=fire_stocks,
            years_offset=years_offset,
            config=cfg,
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
            override_start_ages=override,
            extra_monthly_budget=extra_budget,
        )

        final_assets_arr = _simulate_post_fire_mc_vectorized(
            fire_cash=fire_cash,
            fire_stocks=fire_stocks,
            years_offset=years_offset,
            config=cfg,
            scenario=scenario,
            random_returns_matrix=random_returns_matrix,
            nisa_balance=fire_nisa,
            nisa_cost_basis=fire_nisa_cost,
            stocks_cost_basis=fire_stocks_cost,
            precomputed_expenses=precomputed_expenses,
            precomputed_income=precomputed_income,
            precomputed_base_expenses=precomputed_base_expenses,
            precomputed_life_stages=precomputed_life_stages,
            precomputed_workation_costs=precomputed_workation_costs,
            baseline_assets=baseline_assets,
            override_start_ages=override,
            extra_monthly_budget=extra_budget,
        )

        success_rate = int((final_assets_arr > 0).sum()) / iterations
        er_l1 = er.get('level_1_warning', default_l1)
        er_l2 = er.get('level_2_concern', default_l2)
        er_l3 = er.get('level_3_crisis', default_l3)

        entry = {
            'fire_month':           fire_month,
            'extra_budget':         extra_budget,
            'cash_safety_margin':   float(cand.get('cash_safety_margin', default_safety)),
            'cash_crash_threshold': float(cand.get('cash_crash_threshold', default_crash)),
            'er_level1':            er_l1,
            'er_level2':            er_l2,
            'er_level3':            er_l3,
            'success_rate':         success_rate,
            'p10_assets':           float(np.percentile(final_assets_arr, 10)),
            'median_assets':        float(np.median(final_assets_arr)),
            'mean_assets':          float(np.mean(final_assets_arr)),
        }
        for name in person_names:
            entry[f'age_{name}'] = override[name]
        results.append(entry)

    return results

def _run_mc_evaluation(
    candidates: pd.DataFrame,
    pre_fire_df: pd.DataFrame,
    config: Dict[str, Any],
    scenario: str,
    iterations: int,
    person_names: List[str],
    expense_reduction_candidates: List[Dict[str, float]] = None,
) -> pd.DataFrame:
    """Phase 3: 上位候補に対してMCシミュレーションを並列実行する。"""
    if expense_reduction_candidates is None:
        expense_reduction_candidates = [{}]

    params    = config['simulation'][scenario]
    mc_config = config['simulation'].get('monte_carlo', {})
    return_std_dev       = mc_config.get('return_std_dev', 0.15)
    mean_reversion_speed = mc_config.get('mean_reversion_speed', 0.0)
    enhanced_enabled     = mc_config.get('enhanced_model', {}).get('enabled', False)

    life_expectancy = config['simulation'].get('life_expectancy', 90)
    start_age       = config['simulation'].get('start_age', 35)

    default_strategy = config.get('post_fire_cash_strategy', {})
    default_safety   = default_strategy.get('safety_margin', 5_000_000)
    default_crash    = default_strategy.get('market_crash_threshold', -0.20)

    default_der = config.get('fire', {}).get('dynamic_expense_reduction', {}).get('reduction_rates', {})
    default_l1  = default_der.get('level_1_warning', 0.0)
    default_l2  = default_der.get('level_2_concern', 0.0)
    default_l3  = default_der.get('level_3_crisis', 0.0)

    post_fire_income = (
        config['simulation'].get('shuhei_post_fire_income', 0)
        + config['simulation'].get('sakura_post_fire_income', 0)
    )

    # 候補ごとに評価引数を準備
    all_args = []
    for _, cand in candidates.iterrows():
        fire_month = int(cand['fire_month'])
        if fire_month >= len(pre_fire_df):
            continue
        all_args.append({
            'cand':                       cand.to_dict(),
            'pre_fire_row':               pre_fire_df.iloc[fire_month].to_dict(),
            'config':                     config,
            'scenario':                   scenario,
            'iterations':                 iterations,
            'person_names':               person_names,
            'expense_reduction_candidates': expense_reduction_candidates,
            'enhanced_enabled':           enhanced_enabled,
            'return_std_dev':             return_std_dev,
            'mean_reversion_speed':       mean_reversion_speed,
            'life_expectancy':            life_expectancy,
            'start_age':                  start_age,
            'post_fire_income':           post_fire_income,
            'params':                     params,
            'default_safety':             default_safety,
            'default_crash':              default_crash,
            'default_l1':                 default_l1,
            'default_l2':                 default_l2,
            'default_l3':                 default_l3,
        })

    n_cands   = len(all_args)
    n_er      = len(expense_reduction_candidates)
    n_workers = min(multiprocessing.cpu_count(), n_cands)
    print(f"  並列評価: {n_cands}候補 × {n_er}削減戦略 = {n_cands * n_er}評価 ({n_workers}プロセス)")

    all_results: List[dict] = []
    completed = 0

    with ProcessPoolExecutor(
        max_workers=n_workers,
        initializer=_init_worker,
        initargs=(_PROJECT_ROOT,),
    ) as executor:
        futures = {
            executor.submit(_evaluate_single_candidate, args): i
            for i, args in enumerate(all_args)
        }
        for future in as_completed(futures):
            cand_results = future.result()
            all_results.extend(cand_results)
            completed += 1
            if completed % 10 == 0 or completed == n_cands:
                print(f"  [{completed}/{n_cands}] 候補評価完了")

    # 評価結果をサマリー表示（ソート済み）
    result_df = pd.DataFrame(all_results)
    if not result_df.empty:
        top_rows = result_df.nlargest(min(5, len(result_df)), 'success_rate')
        for _, r in top_rows.iterrows():
            ages_str = '/'.join(f"{int(r[f'age_{n}'])}歳" for n in person_names)
            er_str = (f", 削減{r['er_level1']*100:.0f}/{r['er_level2']*100:.0f}/{r['er_level3']*100:.0f}%"
                      if r['er_level1'] > 0 or r['er_level2'] > 0 or r['er_level3'] > 0 else "")
            print(f"  FIRE月{int(r['fire_month'])} ({ages_str}{er_str}): "
                  f"成功率{r['success_rate']*100:.1f}%, P10={r['p10_assets']/10000:.0f}万円")

    return result_df


def _find_optimal_solution(
    mc_results: pd.DataFrame,
    min_success_rate: float,
    person_names: List[str]
) -> Tuple[Optional[Dict[str, Any]], pd.DataFrame]:
    """成功率≥αで、FIRE月最小・追加予算最大の解を選出する。"""
    feasible = mc_results[mc_results['success_rate'] >= min_success_rate]

    pareto_candidates = []
    for fm in sorted(mc_results['fire_month'].unique()):
        fm_rows = mc_results[mc_results['fire_month'] == fm]
        best = fm_rows.loc[fm_rows['success_rate'].idxmax()]
        pareto_candidates.append(best)

    pareto_df = pd.DataFrame(pareto_candidates)

    if len(feasible) == 0:
        return None, pareto_df

    feasible_sorted = feasible.sort_values(
        ['fire_month', 'extra_budget', 'success_rate'],
        ascending=[True, False, False]
    )
    best = feasible_sorted.iloc[0]

    optimal = {
        'fire_month': int(best['fire_month']),
        'extra_monthly_budget': float(best.get('extra_budget', 0)),
        'cash_strategy': {
            'safety_margin': float(best.get('cash_safety_margin', 5_000_000)),
            'market_crash_threshold': float(best.get('cash_crash_threshold', -0.20)),
        },
        'reduction_rates': {
            'level_1_warning': float(best.get('er_level1', 0.0)),
            'level_2_concern': float(best.get('er_level2', 0.0)),
            'level_3_crisis': float(best.get('er_level3', 0.0)),
        },
        'success_rate': best['success_rate'],
        'p10_assets': best['p10_assets'],
        'median_assets': best['median_assets'],
        'mean_assets': best['mean_assets'],
        'pension_ages': {name: int(best[f'age_{name}']) for name in person_names},
    }
    return optimal, pareto_df


def _get_baseline_info(
    baseline_fire_month: int,
    pre_fire_df: pd.DataFrame,
    config: Dict[str, Any],
    scenario: str,
    mc_iterations: int,
    person_names: List[str]
) -> Dict[str, Any]:
    """現在のルールベースの結果を返す（比較用）。"""
    default_start_age = config.get('pension', {}).get('start_age', 65)
    return {
        'fire_month': baseline_fire_month,
        'pension_ages': {name: default_start_age for name in person_names},
    }


def _print_result(result: Dict[str, Any]) -> None:
    """最適化結果を整形して出力する。"""
    config_start_age = 35  # TODO: result から取得すべきだが、表示用には十分

    print("\n" + "=" * 60)
    print("最適化結果")
    print("=" * 60)

    optimal = result.get('optimal')
    baseline = result.get('baseline')
    person_names = result.get('person_names', [])

    if optimal is None:
        min_rate = result.get('min_success_rate', DEFAULT_MIN_SUCCESS_RATE)
        print(f"\n  成功率 ≥ {min_rate*100:.0f}% を満たす解が見つかりませんでした。")
        print("  許容成功率を下げるか、探索範囲を広げてください。")
    else:
        fire_age = config_start_age + optimal['fire_month'] / 12
        extra_budget = optimal.get('extra_monthly_budget', 0)
        cs = optimal.get('cash_strategy', {})
        print(f"\n  最適解:")
        print(f"    FIRE達成月:         月{optimal['fire_month']}（{fire_age:.1f}歳）")
        for name in person_names:
            age = optimal['pension_ages'][name]
            default_age = 65
            diff = age - default_age
            if diff > 0:
                adj_str = f"+{diff*8.4:.1f}%増額"
            elif diff < 0:
                adj_str = f"{diff*4.8:.1f}%減額"
            else:
                adj_str = "増減なし"
            print(f"    {name}の受給開始年齢:  {age}歳（{adj_str}）")
        if extra_budget > 0:
            print(f"    FIRE後追加予算:     月{extra_budget/10000:.0f}万円（年{extra_budget*12/10000:.0f}万円）")
        if cs:
            print(f"    現金安全マージン:    {cs.get('safety_margin', 5_000_000)/10000:.0f}万円")
            print(f"    暴落判定閾値:       {cs.get('market_crash_threshold', -0.20)*100:.0f}%")
        rr = optimal.get('reduction_rates', {})
        if rr.get('level_1_warning', 0) > 0 or rr.get('level_2_concern', 0) > 0 or rr.get('level_3_crisis', 0) > 0:
            print(f"    動的支出削減率:")
            print(f"      警戒（L1）:       {rr.get('level_1_warning', 0)*100:.0f}%")
            print(f"      懸念（L2）:       {rr.get('level_2_concern', 0)*100:.0f}%")
            print(f"      危機（L3）:       {rr.get('level_3_crisis', 0)*100:.0f}%")
        print(f"    FIRE成功率:         {optimal['success_rate']*100:.1f}%")
        print(f"    P10最終資産:        {optimal['p10_assets']/10000:.0f}万円")
        print(f"    中央値最終資産:      {optimal['median_assets']/10000:.0f}万円")

        if baseline:
            bl_fire_age = config_start_age + baseline['fire_month'] / 12
            month_diff = baseline['fire_month'] - optimal['fire_month']
            print(f"\n  現在のルールベースとの比較:")
            print(f"    ルールベースFIRE月:  月{baseline['fire_month']}（{bl_fire_age:.1f}歳）")
            for name in person_names:
                print(f"    ルールベース年金({name}): {baseline['pension_ages'][name]}歳")
            if month_diff > 0:
                print(f"    → 最適化により FIRE時期を {month_diff}ヶ月前倒し")
            elif month_diff < 0:
                print(f"    → 最適化後のFIRE時期は {-month_diff}ヶ月後ろ倒し（成功率制約のため）")
            else:
                print(f"    → FIRE時期は同一（年金戦略の最適化のみ）")

    # パレート参考情報
    pareto = result.get('pareto_info')
    if pareto is not None and len(pareto) > 0:
        print(f"\n" + "=" * 60)
        print("パレート参考情報（FIRE月 vs 成功率）")
        print("=" * 60)

        min_rate = result.get('min_success_rate', DEFAULT_MIN_SUCCESS_RATE)
        ages_header = '/'.join(person_names)
        print(f"\n  {'FIRE月':>6} | {'年齢':>5} | {f'年金({ages_header})':>16} | {'追加予算':>8} | {'安全証拠金':>10} | {'暴落閾値':>8} | {'削減L1/L2/L3':>14} | {'成功率':>7} | {'P10資産':>10}")
        print(f"  {'-'*6} | {'-'*5} | {'-'*16} | {'-'*8} | {'-'*10} | {'-'*8} | {'-'*14} | {'-'*7} | {'-'*10}")

        for _, row in pareto.iterrows():
            fm = int(row['fire_month'])
            age = config_start_age + fm / 12
            ages_str = '/'.join(f"{int(row[f'age_{n}'])}歳" for n in person_names)
            eb = float(row.get('extra_budget', 0))
            eb_str = f"{eb/10000:.0f}万/月" if eb > 0 else "-"
            sm = float(row.get('cash_safety_margin', 5_000_000))
            ct = float(row.get('cash_crash_threshold', -0.20))
            sm_str = f"{sm/10000:.0f}万"
            ct_str = f"{ct*100:.0f}%"
            er_l1 = float(row.get('er_level1', 0))
            er_l2 = float(row.get('er_level2', 0))
            er_l3 = float(row.get('er_level3', 0))
            er_str = f"{er_l1*100:.0f}/{er_l2*100:.0f}/{er_l3*100:.0f}%"
            sr = row['success_rate']
            p10 = row['p10_assets']
            opt_rr = optimal.get('reduction_rates', {}) if optimal else {}
            is_optimal = (optimal
                          and fm == optimal['fire_month']
                          and eb == optimal.get('extra_monthly_budget', 0)
                          and sm == optimal.get('cash_strategy', {}).get('safety_margin', 5_000_000)
                          and ct == optimal.get('cash_strategy', {}).get('market_crash_threshold', -0.20)
                          and er_l1 == opt_rr.get('level_1_warning', 0.0)
                          and er_l2 == opt_rr.get('level_2_concern', 0.0)
                          and er_l3 == opt_rr.get('level_3_crisis', 0.0))
            marker = " ★" if is_optimal else ""
            meets = "  " if sr >= min_rate else "x "
            print(f"  {meets}月{fm:>3} | {age:>4.1f}歳 | {ages_str:>16} | {eb_str:>8} | {sm_str:>10} | {ct_str:>8} | {er_str:>14} | {sr*100:>5.1f}% | {p10/10000:>8.0f}万円{marker}")
