"""
シミュレーターモジュール
将来の資産推移を予測
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, NamedTuple
from dateutil.relativedelta import relativedelta

# 年金・資産計算用定数
_NATIONAL_PENSION_FULL_AMOUNT = 816_000       # 国民年金満額（2024年度, 円/年）
_EMPLOYEE_PENSION_MULTIPLIER = 0.005481        # 厚生年金乗率（給付乗率）
_PENSION_MAX_CONTRIBUTION_YEARS = 40           # 国民年金最大加入年数
_BANKRUPTCY_THRESHOLD = 5_000_000              # 破綻ライン（円）


class _StockSaleResult(NamedTuple):
    """_sell_stocks_with_tax() の戻り値。"""
    stocks: float            # 更新後の株式残高
    nisa_balance: float      # 更新後のNISA残高
    nisa_cost_basis: float   # 更新後のNISA簿価
    stocks_cost_basis: float # 更新後の株式簿価
    nisa_sold: float         # NISA売却額（非課税）
    cash_from_taxable: float # 課税口座売却後の現金（税引後）
    capital_gain: float      # 実現益（capital_gains_this_year に加算する値）
    total_sold: float        # 総売却額（nisa_sold + 課税口座売却額）


def _get_age_at_offset(birthdate_str: str, year_offset: float) -> float:
    """
    生年月日文字列とシミュレーション経過年数から、その時点での年齢を返す。

    Args:
        birthdate_str: 生年月日（'YYYY/MM/DD'形式）
        year_offset: シミュレーション開始からの経過年数

    Returns:
        シミュレーション時点での年齢（歳）
    """
    birthdate = datetime.strptime(birthdate_str, '%Y/%m/%d')
    current_age = (datetime.now() - birthdate).days / 365.25
    return current_age + year_offset


def _get_life_stage(child_age: float) -> str:
    """
    子供の年齢からライフステージキーを返す。

    Returns:
        'young_child' | 'elementary' | 'junior_high' | 'high_school' | 'university' | 'empty_nest'
    """
    if child_age < 6:
        return 'young_child'
    elif child_age < 12:
        return 'elementary'
    elif child_age < 15:
        return 'junior_high'
    elif child_age < 18:
        return 'high_school'
    elif child_age < 22:
        return 'university'
    else:
        return 'empty_nest'


def _is_enabled(config: Dict, section: str) -> bool:
    """設定セクションの enabled フラグを返す。"""
    return config.get(section, {}).get('enabled', False)


def _advance_year(
    date_year: int,
    current_year: int,
    capital_gains_this_year: float,
) -> tuple:
    """
    月次ループで年が変わった場合に年次カウンターをリセットする。

    Returns:
        (new_current_year, new_capital_gains_this_year, year_advanced: bool)
        year_advanced=True の場合、呼び出し側で capital_gains_this_year の元の値を
        prev_year_capital_gains として保存すること。
    """
    if date_year > current_year:
        return date_year, 0.0, True
    return current_year, capital_gains_this_year, False


def calculate_education_expense(year_offset: float, config: Dict[str, Any]) -> float:
    """
    指定年における教育費を計算

    Args:
        year_offset: シミュレーション開始からの経過年数
        config: 設定辞書

    Returns:
        年間教育費（円）
    """
    if not _is_enabled(config, 'education'):
        return 0

    children = config['education'].get('children', [])
    costs = config['education']['costs']

    total_education_expense = 0

    for child in children:
        # 生年月日から現在の年齢を計算
        birthdate_str = child.get('birthdate')
        if not birthdate_str:
            continue

        child_age = _get_age_at_offset(birthdate_str, year_offset)

        # 年齢に応じた教育段階と費用を計算
        if 0 <= child_age < 3:
            # 保育園（0-2歳）
            nursery_type = child.get('nursery', 'none')
            if nursery_type != 'none':
                annual_cost = costs.get('nursery', {}).get(nursery_type, 0)
                total_education_expense += annual_cost

        elif 3 <= child_age < 6:
            # 幼稚園（3-5歳）
            stage_type = child.get('kindergarten', 'public')
            annual_cost = costs['kindergarten'][stage_type]
            total_education_expense += annual_cost

        elif 6 <= child_age < 12:
            # 小学校（6-11歳）
            stage_type = child.get('elementary', 'public')
            annual_cost = costs['elementary'][stage_type]
            total_education_expense += annual_cost

        elif 12 <= child_age < 15:
            # 中学校（12-14歳）
            stage_type = child.get('junior_high', 'public')
            annual_cost = costs['junior_high'][stage_type]
            total_education_expense += annual_cost

        elif 15 <= child_age < 18:
            # 高校（15-17歳）
            stage_type = child.get('high', 'public')
            annual_cost = costs['high'][stage_type]
            total_education_expense += annual_cost

        elif 18 <= child_age < 22:
            # 大学（18-21歳）
            stage_type = child.get('university', 'national')
            annual_cost = costs['university'][stage_type]
            total_education_expense += annual_cost

    return total_education_expense


def _calculate_national_pension_amount(contribution_years: float) -> float:
    """
    国民年金の年間受給額を計算

    Args:
        contribution_years: 加入年数（最大40年）

    Returns:
        年間年金額（円）
    """
    # 加入年数に応じた按分（最大加入年数で満額）
    contribution_years = min(contribution_years, _PENSION_MAX_CONTRIBUTION_YEARS)
    annual_pension = _NATIONAL_PENSION_FULL_AMOUNT * (contribution_years / _PENSION_MAX_CONTRIBUTION_YEARS)

    return annual_pension


def _calculate_employees_pension_amount(avg_monthly_salary: float, contribution_months: int) -> float:
    """
    厚生年金の年間受給額を計算（簡易版）

    Args:
        avg_monthly_salary: 平均月収（円）- 厚生年金加入期間中の平均
        contribution_months: 加入月数

    Returns:
        年間年金額（円）
    """
    # 厚生年金（報酬比例部分）= 平均月収 × 加入月数 × 給付乗率
    # 2003年4月以降の乗率（平成15年3月以前と以降で異なるが、簡略化のため統一）
    annual_pension = avg_monthly_salary * contribution_months * _EMPLOYEE_PENSION_MULTIPLIER

    return annual_pension


def calculate_pension_income(
    year_offset: float,
    config: Dict[str, Any],
    fire_achieved: bool = False,
    fire_year_offset: float = None
) -> float:
    """
    指定年における年金収入を計算（FIRE対応・動的計算）

    FIRE達成時点で厚生年金の加入を停止し、その時点までの加入期間で年金額を計算する。
    国民年金は20歳から60歳まで（最大40年）加入すると仮定。

    Args:
        year_offset: シミュレーション開始からの経過年数
        config: 設定辞書
        fire_achieved: FIRE達成フラグ
        fire_year_offset: FIRE達成時点の経過年数（年）

    Returns:
        年間年金収入（円）
    """
    if not _is_enabled(config, 'pension'):
        return 0

    people = config['pension'].get('people', [])
    start_age = config['pension'].get('start_age', 65)

    total_pension_income = 0

    for person in people:
        # 生年月日から現在の年齢を計算
        birthdate_str = person.get('birthdate')
        if not birthdate_str:
            continue

        person_age = _get_age_at_offset(birthdate_str, year_offset)

        # 年金受給開始年齢に達していなければスキップ
        if person_age < start_age:
            continue

        # 年金計算方法の選択
        pension_type = person.get('pension_type', 'employee')  # 'employee' or 'national'

        if pension_type == 'employee':
            # 厚生年金 + 国民年金の計算

            # 厚生年金の計算
            avg_monthly_salary = person.get('avg_monthly_salary', 0)
            work_start_age = person.get('work_start_age', 23)

            # FIRE達成していれば、FIRE時点までの加入期間
            # 達成していなければ、現在年齢までの加入期間（最大65歳まで）
            if fire_achieved and fire_year_offset is not None:
                # FIRE達成時の年齢
                fire_age = _get_age_at_offset(birthdate_str, fire_year_offset)
                work_end_age = fire_age
            else:
                # まだFIRE未達成の場合は、シミュレーション年の年齢まで働く（最大65歳）
                work_end_age = min(person_age, 65)

            # 厚生年金加入期間（月数）
            work_years = max(0, work_end_age - work_start_age)
            work_months = int(work_years * 12)

            # 厚生年金額を計算
            employees_pension = _calculate_employees_pension_amount(avg_monthly_salary, work_months)

            # 国民年金の計算（20歳から60歳まで、最大40年）
            national_pension_years = min(40, 60 - 20)  # 満額想定
            national_pension = _calculate_national_pension_amount(national_pension_years)

            # 合計
            annual_pension = employees_pension + national_pension

        elif pension_type == 'national':
            # 国民年金のみ
            national_pension_years = min(40, 60 - 20)  # 満額想定
            annual_pension = _calculate_national_pension_amount(national_pension_years)

        else:
            # 従来の固定値フォールバック（後方互換性）
            annual_pension = person.get('annual_amount', 0)

        total_pension_income += annual_pension

    return total_pension_income


def calculate_child_allowance(year_offset: float, config: Dict[str, Any]) -> float:
    """
    指定年における児童手当を計算

    Args:
        year_offset: シミュレーション開始からの経過年数
        config: 設定辞書

    Returns:
        年間児童手当額（円）
    """
    # 児童手当が無効の場合は0を返す
    if not _is_enabled(config, 'child_allowance'):
        return 0

    children = config.get('education', {}).get('children', [])
    if not children:
        return 0

    allowance_config = config['child_allowance']
    # 2024年10月改定: 第2子以降0-3歳は2万円/月、支給対象を高校生（18歳未満）まで拡大
    first_child_under_3 = allowance_config.get('first_child_under_3', 15000)
    second_child_plus_under_3 = allowance_config.get('second_child_plus_under_3', 20000)
    age_3_to_high_school = allowance_config.get('age_3_to_high_school', 10000)

    total_annual_allowance = 0

    for i, child in enumerate(children):
        birthdate_str = child.get('birthdate')
        if not birthdate_str:
            continue

        child_age = _get_age_at_offset(birthdate_str, year_offset)

        # 年齢に応じた月額手当を計算（2024年10月改定後）
        if child_age < 3:
            # 第1子と第2子以降で金額が異なる
            monthly_allowance = first_child_under_3 if i == 0 else second_child_plus_under_3
        elif child_age < 18:
            # 3歳以上高校生以下（18歳未満）: 1万円/月
            monthly_allowance = age_3_to_high_school
        else:
            monthly_allowance = 0

        total_annual_allowance += monthly_allowance * 12

    return total_annual_allowance


def calculate_national_pension_premium(
    year_offset: float,
    config: Dict[str, Any],
    fire_achieved: bool = False
) -> float:
    """
    国民年金保険料を計算（FIRE後のみ計上）

    Args:
        year_offset: シミュレーション開始からの経過年数
        config: 設定辞書
        fire_achieved: FIRE達成済みか（True: FIRE後、False: FIRE前）

    Returns:
        年間国民年金保険料（円）
    """
    # 社会保険設定が無効の場合は0を返す
    if not _is_enabled(config, 'social_insurance'):
        return 0

    # FIRE前は会社の厚生年金なので計上不要
    if not fire_achieved:
        return 0

    social_insurance_config = config['social_insurance']
    monthly_premium = social_insurance_config.get('national_pension_monthly_premium', 16980)

    # 年金受給者情報を取得
    pension_people = config.get('pension', {}).get('people', [])
    if not pension_people:
        return 0

    total_annual_premium = 0

    for person in pension_people:
        birthdate_str = person.get('birthdate')
        if not birthdate_str:
            continue

        # シミュレーション中の年齢を計算
        person_age = _get_age_at_offset(birthdate_str, year_offset)

        # 20歳～60歳の間のみ国民年金保険料を支払う
        if 20 <= person_age < 60:
            total_annual_premium += monthly_premium * 12

    return total_annual_premium


def calculate_national_health_insurance_premium(
    year_offset: float,
    config: Dict[str, Any],
    fire_achieved: bool = False,
    prev_year_capital_gains: float = 0
) -> float:
    """
    国民健康保険料を動的計算（FIRE後のみ計上）

    国民健康保険料 = 所得割 + 均等割 + 平等割（上限あり）
    所得割は前年の所得（副業収入 + 株式譲渡益）に基づいて計算する。

    Args:
        year_offset: シミュレーション開始からの経過年数
        config: 設定辞書
        fire_achieved: FIRE達成済みか（True: FIRE後、False: FIRE前）
        prev_year_capital_gains: 前年の株式譲渡益（円）

    Returns:
        年間国民健康保険料（円）
    """
    # 社会保険設定が無効の場合は0を返す
    if not _is_enabled(config, 'social_insurance'):
        return 0

    # FIRE前は会社の健康保険なので計上不要
    if not fire_achieved:
        return 0

    si = config['social_insurance']

    # --- 所得の算出 ---
    # 副業収入（年額）
    post_fire_income = config['simulation'].get('post_fire_income', 0)
    annual_side_income = post_fire_income * 12

    # 前年の株式譲渡益（キャピタルゲイン）
    # 国民健康保険の所得割は分離課税の譲渡所得も含む
    capital_gains = prev_year_capital_gains

    # 合計所得
    total_income = annual_side_income + capital_gains

    # --- 所得割 ---
    basic_deduction = si.get('health_insurance_basic_deduction', 430000)
    taxable_income = max(0, total_income - basic_deduction)
    income_rate = si.get('health_insurance_income_rate', 0.11)
    income_based_premium = taxable_income * income_rate

    # --- 均等割 + 平等割 ---
    per_person = si.get('health_insurance_per_person', 50000)
    members = si.get('health_insurance_members', 2)
    per_household = si.get('health_insurance_per_household', 30000)
    fixed_premium = per_person * members + per_household

    # --- 合計（上限適用）---
    max_premium = si.get('health_insurance_max_premium', 1060000)
    total_premium = min(income_based_premium + fixed_premium, max_premium)

    return total_premium


def calculate_mortgage_payment(year_offset: float, config: Dict[str, Any]) -> float:
    """
    指定年における住宅ローンの月次支払額を計算

    Args:
        year_offset: シミュレーション開始からの経過年数
        config: 設定辞書

    Returns:
        月次住宅ローン支払額（円）
    """
    # 住宅ローンが無効の場合は0を返す
    if not _is_enabled(config, 'mortgage'):
        return 0

    mortgage_config = config['mortgage']
    monthly_payment = mortgage_config.get('monthly_payment', 0)
    end_date_str = mortgage_config.get('end_date')

    if not end_date_str:
        return 0

    current_date = datetime.now()

    # 終了日をパース
    end_date = datetime.strptime(end_date_str, '%Y/%m/%d')

    # シミュレーション中の日付を計算（year_offsetは浮動小数点なので月単位に変換）
    months_offset = int(year_offset * 12)
    simulation_date = current_date + relativedelta(months=months_offset)

    # 終了日を過ぎていれば0、そうでなければ月次支払額を返す
    if simulation_date > end_date:
        return 0
    else:
        return monthly_payment


def calculate_house_maintenance(year_offset: float, config: Dict[str, Any]) -> float:
    """
    指定年における住宅メンテナンス費用を計算

    Args:
        year_offset: シミュレーション開始からの経過年数
        config: 設定辞書

    Returns:
        年間メンテナンス費用（円）
    """
    # 住宅メンテナンスが無効の場合は0を返す
    if not _is_enabled(config, 'house_maintenance'):
        return 0

    maintenance_config = config['house_maintenance']
    items = maintenance_config.get('items', [])

    if not items:
        return 0

    current_date = datetime.now()
    current_year = current_date.year

    # シミュレーション中の年を計算（整数に丸める）
    simulation_year = int(current_year + year_offset)

    total_maintenance_cost = 0

    for item in items:
        first_year = item.get('first_year')
        frequency_years = item.get('frequency_years')
        cost = item.get('cost', 0)

        if not first_year or not frequency_years:
            continue

        # 初回実施年以降かチェック
        if simulation_year < first_year:
            continue

        # 周期に該当するかチェック
        years_since_first = simulation_year - first_year
        if years_since_first % frequency_years == 0:
            total_maintenance_cost += cost

    return total_maintenance_cost


def calculate_workation_cost(year_offset: float, config: Dict[str, Any]) -> float:
    """
    指定年におけるワーケーション費用を計算

    Args:
        year_offset: シミュレーション開始からの経過年数
        config: 設定辞書

    Returns:
        年間ワーケーション費用（円）
    """
    # ワーケーションが無効の場合は0を返す
    if not _is_enabled(config, 'workation'):
        return 0

    workation_config = config['workation']
    start_child_index = workation_config.get('start_child_index', 1)
    start_child_age = workation_config.get('start_child_age', 18)
    annual_cost = workation_config.get('annual_cost', 0)

    # 子供情報を取得
    children = config.get('education', {}).get('children', [])
    if start_child_index >= len(children):
        return 0  # 指定された子供が存在しない

    # 基準となる子供の情報
    child = children[start_child_index]
    birthdate_str = child.get('birthdate')
    if not birthdate_str:
        return 0

    # シミュレーション時点での子供の年齢を計算
    child_age = _get_age_at_offset(birthdate_str, year_offset)

    # 開始年齢以降ならワーケーション費用を返す
    if child_age >= start_child_age:
        return annual_cost
    else:
        return 0


def _sell_stocks_with_tax(
    shortage: float,
    stocks: float,
    nisa_balance: float,
    nisa_cost_basis: float,
    stocks_cost_basis: float,
    capital_gains_tax_rate: float,
    allocation_enabled: bool,
) -> _StockSaleResult:
    """
    NISA優先で株を売却し、shortage分を確保する。

    呼び出し側での使い分け:
      支出不足型: cash += result.cash_from_taxable         （NISA分はcashを経由せず支出に充当）
      最低現金型: cash += result.nisa_sold + result.cash_from_taxable（全額cashへ）

    Returns:
      stocks, nisa_balance, nisa_cost_basis, stocks_cost_basis: 更新後の値
      nisa_sold:         NISA売却額（非課税）
      cash_from_taxable: 課税口座売却後の現金（税引後）
      capital_gain:      実現益（呼び出し側でcapital_gains_this_yearに加算）
      total_sold:        総売却額
    """
    nisa_sold = 0.0
    cash_from_taxable = 0.0
    capital_gain = 0.0

    if not allocation_enabled:
        # 資産配分無効: 税なし単純売却（全額cash_from_taxableとして返す）
        sold = min(shortage, stocks)
        return _StockSaleResult(
            stocks=stocks - sold,
            nisa_balance=nisa_balance,
            nisa_cost_basis=nisa_cost_basis,
            stocks_cost_basis=max(0.0, stocks_cost_basis - sold),
            nisa_sold=0.0,
            cash_from_taxable=sold,
            capital_gain=0.0,
            total_sold=sold,
        )

    # NISA優先売却（非課税）
    if nisa_balance > 0 and shortage > 0:
        nisa_sold = min(shortage, nisa_balance)
        nisa_sold_cost = nisa_sold / stocks * stocks_cost_basis if stocks > 0 else 0.0
        nisa_balance -= nisa_sold
        nisa_cost_basis = max(0.0, nisa_cost_basis - nisa_sold_cost)
        stocks -= nisa_sold
        stocks_cost_basis = max(0.0, stocks_cost_basis - nisa_sold_cost)
        shortage -= nisa_sold

    # 課税口座売却（税引後でshorageを確保）
    taxable_sold = 0.0
    if shortage > 0 and stocks > 0:
        taxable_stocks = stocks - nisa_balance
        if taxable_stocks > 0:
            avg_cost_basis = (stocks_cost_basis - nisa_cost_basis) / taxable_stocks
            gain_ratio = max(0.0, 1.0 - avg_cost_basis)
            effective_tax_rate = capital_gains_tax_rate * gain_ratio
            required_sale = shortage / (1 - effective_tax_rate) if effective_tax_rate < 1 else shortage
            taxable_sold = min(required_sale, taxable_stocks)
            sale_cost = taxable_sold * avg_cost_basis
            capital_gain = max(0.0, taxable_sold - sale_cost)
            tax = capital_gain * capital_gains_tax_rate
            cash_from_taxable = taxable_sold - tax
            stocks -= taxable_sold
            stocks_cost_basis = max(0.0, stocks_cost_basis - sale_cost)

    return _StockSaleResult(
        stocks=stocks,
        nisa_balance=nisa_balance,
        nisa_cost_basis=nisa_cost_basis,
        stocks_cost_basis=stocks_cost_basis,
        nisa_sold=nisa_sold,
        cash_from_taxable=cash_from_taxable,
        capital_gain=capital_gain,
        total_sold=nisa_sold + taxable_sold,
    )


def _calculate_monthly_expenses(
    years: float,
    config: Dict[str, Any],
    monthly_expense: float,
    expense_growth_rate: float,
    fire_achieved: bool,
    prev_year_capital_gains: float,
) -> dict:
    """
    月次支出の全項目を計算する。

    Returns:
        base_expense, education_expense, mortgage_payment, maintenance_cost,
        workation_cost, pension_premium, health_insurance_premium, total（全て月額・円）
    """
    fallback_annual = monthly_expense * 12 * (1 + expense_growth_rate) ** years
    base_expense = calculate_base_expense(years, config, fallback_annual) / 12
    education_expense = calculate_education_expense(years, config) / 12
    mortgage_payment = calculate_mortgage_payment(years, config)
    maintenance_cost = calculate_house_maintenance(years, config) / 12
    workation_cost = calculate_workation_cost(years, config) / 12
    pension_premium = calculate_national_pension_premium(years, config, fire_achieved) / 12
    health_insurance_premium = calculate_national_health_insurance_premium(
        years, config, fire_achieved, prev_year_capital_gains
    ) / 12
    total = (base_expense + education_expense + mortgage_payment
             + maintenance_cost + workation_cost
             + pension_premium + health_insurance_premium)
    return {
        'base_expense': base_expense,
        'education_expense': education_expense,
        'mortgage_payment': mortgage_payment,
        'maintenance_cost': maintenance_cost,
        'workation_cost': workation_cost,
        'pension_premium': pension_premium,
        'health_insurance_premium': health_insurance_premium,
        'total': total,
    }


def _auto_invest_surplus(
    cash: float,
    stocks: float,
    stocks_cost_basis: float,
    nisa_balance: float,
    nisa_cost_basis: float,
    nisa_used_this_year: float,
    expense: float,
    cash_buffer_months: float,
    min_cash_balance: float,
    auto_invest_threshold: float,
    nisa_enabled: bool,
    nisa_annual_limit: float,
    invest_beyond_nisa: bool,
) -> dict:
    """
    余剰現金をNISA優先で自動投資する（FIRE前専用）。

    Returns:
        cash, stocks, stocks_cost_basis, nisa_balance,
        nisa_cost_basis, nisa_used_this_year, auto_invested
    """
    auto_invested = 0
    expense_based_buffer = expense * cash_buffer_months
    required_cash_balance = max(expense_based_buffer, min_cash_balance)
    cash_threshold = required_cash_balance * auto_invest_threshold

    if cash > cash_threshold:
        surplus = cash - required_cash_balance

        nisa_remaining = nisa_annual_limit - nisa_used_this_year if nisa_enabled else 0
        if nisa_remaining > 0 and surplus > 0:
            nisa_invest = min(surplus, nisa_remaining)
            cash -= nisa_invest
            stocks += nisa_invest
            stocks_cost_basis += nisa_invest
            nisa_balance += nisa_invest
            nisa_cost_basis += nisa_invest
            nisa_used_this_year += nisa_invest
            auto_invested += nisa_invest
            surplus -= nisa_invest

        if surplus > 0 and invest_beyond_nisa:
            taxable_invest = surplus
            cash -= taxable_invest
            stocks += taxable_invest
            stocks_cost_basis += taxable_invest
            auto_invested += taxable_invest

        if cash < min_cash_balance:
            adjustment = min_cash_balance - cash
            cash += adjustment
            stocks -= adjustment
            stocks_cost_basis -= adjustment
            auto_invested -= adjustment

    return {
        'cash': cash, 'stocks': stocks, 'stocks_cost_basis': stocks_cost_basis,
        'nisa_balance': nisa_balance, 'nisa_cost_basis': nisa_cost_basis,
        'nisa_used_this_year': nisa_used_this_year, 'auto_invested': auto_invested,
    }


def _build_monthly_result(
    date, month: int,
    cash: float, stocks: float, stocks_cost_basis: float, nisa_balance: float,
    total_income: float, monthly_pension_income: float, labor_income: float,
    shuhei_income_monthly: float, sakura_income_monthly: float,
    monthly_child_allowance: float,
    expense: float, base_expense: float, monthly_education_expense: float,
    monthly_mortgage_payment: float, monthly_maintenance_cost: float,
    monthly_workation_cost: float, monthly_pension_premium: float,
    monthly_health_insurance_premium: float,
    investment_return: float, auto_invested: float,
    capital_gains_tax: float, fire_achieved: bool, fire_month,
) -> dict:
    """月次シミュレーション結果の1行分を構築する。"""
    return {
        'date': date, 'month': month,
        'assets': max(0, cash + stocks),
        'cash': max(0, cash), 'stocks': max(0, stocks),
        'stocks_cost_basis': max(0, stocks_cost_basis),
        'nisa_balance': max(0, nisa_balance),
        'income': total_income,
        'pension_income': monthly_pension_income,
        'labor_income': labor_income,
        'shuhei_income': shuhei_income_monthly,
        'sakura_income': sakura_income_monthly,
        'child_allowance': monthly_child_allowance,
        'expense': expense, 'base_expense': base_expense,
        'education_expense': monthly_education_expense,
        'mortgage_payment': monthly_mortgage_payment,
        'maintenance_cost': monthly_maintenance_cost,
        'workation_cost': monthly_workation_cost,
        'pension_premium': monthly_pension_premium,
        'health_insurance_premium': monthly_health_insurance_premium,
        'net_cashflow': total_income - expense,
        'investment_return': investment_return,
        'auto_invested': auto_invested,
        'capital_gains_tax': capital_gains_tax,
        'fire_achieved': fire_achieved,
        'fire_month': fire_month,
    }


def _calculate_monthly_income(
    years: float,
    fire_achieved: bool,
    fire_month,
    shuhei_income_base: float,
    sakura_income_base: float,
    monthly_income: float,
    shuhei_ratio: float,
    income_growth_rate: float,
    config: dict,
) -> dict:
    """
    月次収入を計算する。FIRE前後で労働収入の扱いを切り替える。

    Returns:
      total_income:          月次合計収入
      labor_income:          労働収入（FIRE後は post_fire_income）
      pension_income:        月次年金収入
      child_allowance:       月次児童手当
      shuhei_income_monthly: 修平の月収（FIRE後は0）
      sakura_income_monthly: 桜の月収（FIRE後は0）
      post_fire_income:      FIRE後副収入設定値
    """

    # 年金収入
    fire_year_offset = (fire_month / 12) if fire_month is not None else None
    annual_pension_income = calculate_pension_income(
        years, config, fire_achieved=fire_achieved, fire_year_offset=fire_year_offset
    )
    monthly_pension_income = annual_pension_income / 12

    # 児童手当
    monthly_child_allowance = calculate_child_allowance(years, config) / 12

    post_fire_income = config['simulation'].get('post_fire_income', 0)

    if fire_achieved:
        return {
            'total_income': monthly_pension_income + monthly_child_allowance + post_fire_income,
            'labor_income': post_fire_income,
            'pension_income': monthly_pension_income,
            'child_allowance': monthly_child_allowance,
            'shuhei_income_monthly': 0.0,
            'sakura_income_monthly': 0.0,
            'post_fire_income': post_fire_income,
        }

    # FIRE前: 労働収入を成長率に応じて計算
    # 修平（会社員）: income_growth_rateを適用
    # 桜（個人事業主）: 固定（成長なし）
    if shuhei_income_base + sakura_income_base > 0:
        income = shuhei_income_base * (1 + income_growth_rate) ** years + sakura_income_base
        shuhei_income_monthly = shuhei_income_base * (1 + income_growth_rate) ** years
        sakura_income_monthly = sakura_income_base
    else:
        income = monthly_income * (1 + income_growth_rate) ** years
        shuhei_income_monthly = income * shuhei_ratio
        sakura_income_monthly = income * (1 - shuhei_ratio)

    return {
        'total_income': income + monthly_pension_income + monthly_child_allowance,
        'labor_income': income,
        'pension_income': monthly_pension_income,
        'child_allowance': monthly_child_allowance,
        'shuhei_income_monthly': shuhei_income_monthly,
        'sakura_income_monthly': sakura_income_monthly,
        'post_fire_income': post_fire_income,
    }


def simulate_post_fire_assets(
    current_cash: float,
    current_stocks: float,
    years_offset: float,
    config: Dict[str, Any],
    scenario: str = 'standard',
    nisa_balance: float = 0,
    nisa_cost_basis: float = 0,
    stocks_cost_basis: float = None
) -> float:
    """
    FIRE後の資産推移をシミュレーション（実際のロジックと同じ）

    Args:
        current_cash: 現在の現金残高
        current_stocks: 現在の株式残高
        years_offset: シミュレーション開始からの経過年数
        config: 設定辞書
        scenario: シナリオ名
        nisa_balance: NISA残高
        nisa_cost_basis: NISA簿価
        stocks_cost_basis: 株式全体の簿価（Noneの場合は時価と仮定）

    Returns:
        90歳時点での資産額
    """

    # シナリオ設定取得
    scenario_config = config['simulation'][scenario]
    annual_return_rate = scenario_config['annual_return_rate']

    # シミュレーション期間
    life_expectancy = config['simulation'].get('life_expectancy', 90)
    start_age = config['simulation'].get('start_age', 35)
    current_age = start_age + years_offset
    remaining_years = life_expectancy - current_age
    remaining_months = int(remaining_years * 12)

    # 月次リターン率
    monthly_return_rate = (1 + annual_return_rate) ** (1/12) - 1

    # 資産配分設定
    allocation_enabled = _is_enabled(config, 'asset_allocation')
    if allocation_enabled:
        capital_gains_tax_rate = config['asset_allocation'].get('capital_gains_tax_rate', 0.20315)
    else:
        capital_gains_tax_rate = 0.20315

    # 初期値
    cash = current_cash
    stocks = current_stocks
    if stocks_cost_basis is None:
        stocks_cost_basis = current_stocks  # 簿価は時価と仮定
    nisa_balance = nisa_balance
    nisa_cost_basis = nisa_cost_basis

    # FIRE後の副収入
    post_fire_income = config['simulation'].get('post_fire_income', 0)

    # 健康保険料の動的計算用（年間キャピタルゲイン追跡）
    current_date_post = datetime.now()
    current_year_post = (current_date_post + relativedelta(months=int(years_offset * 12))).year
    capital_gains_this_year_post = 0
    prev_year_capital_gains_post = 0

    # 月次シミュレーション（FIRE後）
    for month in range(remaining_months):
        years = years_offset + month / 12
        date_post = current_date_post + relativedelta(months=int(years * 12))
        _prev_gains = capital_gains_this_year_post
        current_year_post, capital_gains_this_year_post, _year_advanced = _advance_year(
            date_post.year, current_year_post, capital_gains_this_year_post
        )
        if _year_advanced:
            prev_year_capital_gains_post = _prev_gains

        # 基本生活費
        annual_base_expense = calculate_base_expense(years, config, 0)
        base_expense = annual_base_expense / 12

        # 教育費
        annual_education_expense = calculate_education_expense(years, config)
        monthly_education_expense = annual_education_expense / 12

        # 年金収入（FIRE後なので、FIRE時点までの加入期間で計算）
        annual_pension_income = calculate_pension_income(
            years,
            config,
            fire_achieved=True,
            fire_year_offset=years_offset  # FIRE達成時点
        )
        monthly_pension_income = annual_pension_income / 12

        # 児童手当
        annual_child_allowance = calculate_child_allowance(years, config)
        monthly_child_allowance = annual_child_allowance / 12

        # 住宅ローン
        monthly_mortgage_payment = calculate_mortgage_payment(years, config)

        # 住宅メンテナンス
        annual_maintenance_cost = calculate_house_maintenance(years, config)
        monthly_maintenance_cost = annual_maintenance_cost / 12

        # ワーケーション
        annual_workation_cost = calculate_workation_cost(years, config)
        monthly_workation_cost = annual_workation_cost / 12

        # 社会保険料（FIRE後）
        annual_pension_premium = calculate_national_pension_premium(years, config, fire_achieved=True)
        monthly_pension_premium = annual_pension_premium / 12

        annual_health_insurance_premium = calculate_national_health_insurance_premium(
            years, config, fire_achieved=True,
            prev_year_capital_gains=prev_year_capital_gains_post
        )
        monthly_health_insurance_premium = annual_health_insurance_premium / 12

        # 総支出
        expense = (base_expense + monthly_education_expense + monthly_mortgage_payment +
                  monthly_maintenance_cost + monthly_workation_cost +
                  monthly_pension_premium + monthly_health_insurance_premium)

        # 収入（FIRE後は副収入 + 年金 + 児童手当のみ）
        total_income = post_fire_income + monthly_pension_income + monthly_child_allowance

        # 収入を現金に加算
        cash += total_income

        # 支出を現金から引き出し
        if cash >= expense:
            cash -= expense
        else:
            # 現金が足りない場合は株から取り崩し
            shortage = expense - cash
            cash = 0

            # 支出不足型: NISAはshorageを直接削減、課税分のみcashへ
            result = _sell_stocks_with_tax(
                shortage, stocks, nisa_balance, nisa_cost_basis,
                stocks_cost_basis, capital_gains_tax_rate, allocation_enabled,
            )
            stocks = result.stocks
            nisa_balance = result.nisa_balance
            nisa_cost_basis = result.nisa_cost_basis
            stocks_cost_basis = result.stocks_cost_basis
            cash += result.cash_from_taxable
            capital_gains_this_year_post += result.capital_gain

        # 運用リターン（株のみ）
        investment_return = stocks * monthly_return_rate
        stocks += investment_return

        # 最低現金残高を確保（資産配分が有効な場合）
        if allocation_enabled:
            min_cash_balance = config['asset_allocation'].get('min_cash_balance', _BANKRUPTCY_THRESHOLD)
            if cash < min_cash_balance and stocks > 0:
                shortage = min_cash_balance - cash
                # 最低現金型: NISAも課税分も両方cashへ
                result = _sell_stocks_with_tax(
                    shortage, stocks, nisa_balance, nisa_cost_basis,
                    stocks_cost_basis, capital_gains_tax_rate, allocation_enabled,
                )
                stocks = result.stocks
                nisa_balance = result.nisa_balance
                nisa_cost_basis = result.nisa_cost_basis
                stocks_cost_basis = result.stocks_cost_basis
                cash += result.nisa_sold + result.cash_from_taxable
                capital_gains_this_year_post += result.capital_gain

        # 資産が破綻ライン以下になったら終了
        if cash + stocks <= _BANKRUPTCY_THRESHOLD:
            return 0

    return cash + stocks


def can_retire_now(
    current_assets: float,
    years_offset: float,
    current_annual_expense: float,
    config: Dict[str, Any],
    scenario: str,
    current_cash: float = None,
    current_stocks: float = None,
    nisa_balance: float = 0,
    nisa_cost_basis: float = 0,
    stocks_cost_basis: float = None
) -> bool:
    """
    現在のタイミングで退職して、寿命まで資産が持つかチェック

    実際のシミュレーションと同じロジックを使用

    Args:
        current_assets: 現在の資産（cash+stocksが未指定時のみ使用）
        years_offset: シミュレーション開始からの経過年数
        current_annual_expense: 現在の年間支出
        config: 設定辞書
        scenario: シナリオ名
        current_cash: 現在の現金残高（オプション）
        current_stocks: 現在の株式残高（オプション）
        nisa_balance: NISA残高（オプション）
        nisa_cost_basis: NISA簿価（オプション）
        stocks_cost_basis: 株式全体の簿価（オプション）

    Returns:
        True if 退職可能、False otherwise
    """
    life_expectancy = config['simulation'].get('life_expectancy', 90)
    start_age = config['simulation'].get('start_age', 35)

    # 現在の年齢
    current_age = start_age + years_offset

    # 残り年数
    remaining_years = life_expectancy - current_age

    if remaining_years <= 0:
        return True  # すでに寿命到達

    # 現金と株の分離（指定されていない場合は全額株と仮定）
    if current_cash is None or current_stocks is None:
        # 資産配分が有効な場合は、適切に分離
        allocation_enabled = _is_enabled(config, 'asset_allocation')
        if allocation_enabled:
            cash_buffer_months = config['asset_allocation'].get('cash_buffer_months', 6)
            monthly_expense = current_annual_expense / 12
            estimated_cash = monthly_expense * cash_buffer_months
            current_cash = min(estimated_cash, current_assets * 0.1)  # 最大10%を現金
            current_stocks = current_assets - current_cash
        else:
            current_cash = 0
            current_stocks = current_assets

    # 退職後のシミュレーション実行（実際のロジックと同じ）
    final_assets = simulate_post_fire_assets(
        current_cash=current_cash,
        current_stocks=current_stocks,
        years_offset=years_offset,
        config=config,
        scenario=scenario,
        nisa_balance=nisa_balance,
        nisa_cost_basis=nisa_cost_basis,
        stocks_cost_basis=stocks_cost_basis
    )

    # 破綻ライン: 500万円を下回らないことを確認
    return final_assets > _BANKRUPTCY_THRESHOLD


def calculate_base_expense(year_offset: float, config: Dict[str, Any], fallback_expense: float) -> float:
    """
    指定年における基本生活費を計算（ライフステージ別 + 家族人数調整）

    Args:
        year_offset: シミュレーション開始からの経過年数
        config: 設定辞書
        fallback_expense: フォールバック年間支出（ライフステージ設定がない場合）

    Returns:
        年間基本生活費（円）
    """
    # 手動設定の年間支出があればそれを使用
    manual_expense = config.get('fire', {}).get('manual_annual_expense')
    if manual_expense is not None:
        return manual_expense

    # ライフステージ別支出設定を取得
    base_expense_by_stage = config.get('fire', {}).get('base_expense_by_stage', {})

    # ライフステージ設定がない場合はフォールバックを使用
    if not base_expense_by_stage:
        return fallback_expense

    # 子供の情報を取得（最初の子供を基準にライフステージを決定）
    children = config.get('education', {}).get('children', [])
    if not children:
        # 子供がいない場合はempty_nestの支出を使用
        return base_expense_by_stage.get('empty_nest', fallback_expense)

    # 最初の子供の年齢を計算してライフステージを決定
    current_date = datetime.now()

    child = children[0]
    birthdate_str = child.get('birthdate')
    if not birthdate_str:
        return fallback_expense

    child_age = _get_age_at_offset(birthdate_str, year_offset)

    # 基本支出（第一子の年齢に基づく）
    stage = _get_life_stage(child_age)
    base_expense = base_expense_by_stage.get(stage, fallback_expense)

    # 第二子以降：各子供の年齢（ステージ）に応じた追加費用を加算
    additional_by_stage = config.get('fire', {}).get('additional_child_expense_by_stage', {})

    if additional_by_stage and len(children) > 1:
        simulation_date = current_date + pd.Timedelta(days=year_offset * 365.25)

        for additional_child in children[1:]:
            child_birthdate_str = additional_child.get('birthdate')
            if not child_birthdate_str:
                continue

            child_birthdate = datetime.strptime(child_birthdate_str, '%Y/%m/%d')

            # まだ生まれていない場合はスキップ
            if child_birthdate > simulation_date:
                continue

            # 各子供の年齢からステージを判定
            child_age = _get_age_at_offset(child_birthdate_str, year_offset)
            child_stage = _get_life_stage(child_age)

            base_expense += additional_by_stage.get(child_stage, 0)

    return base_expense


def simulate_future_assets(
    current_cash: float = None,
    current_stocks: float = None,
    current_assets: float = None,  # 後方互換性のため
    monthly_income: float = 0,
    monthly_expense: float = 0,
    config: Dict[str, Any] = None,
    scenario: str = 'standard'
) -> pd.DataFrame:
    """
    将来の資産推移をシミュレーション（現金と株を分離管理）

    毎月「今退職しても寿命まで資産が持つか?」をチェックし、
    初めて持つと判定された月がFIRE達成日となる

    Args:
        current_cash: 現在の現金残高（優先）
        current_stocks: 現在の株式残高（優先）
        current_assets: 現在の純資産（後方互換性のため、cash/stocksが未指定時のみ使用）
        monthly_income: 月次収入
        monthly_expense: 月次支出
        config: 設定辞書
        scenario: シナリオ名 ('standard', 'optimistic', 'pessimistic')

    Returns:
        シミュレーション結果のデータフレーム
    """
    print(f"Simulating future assets ({scenario} scenario)...")

    # 後方互換性: current_assetsが指定されている場合は全額株として扱う
    if current_cash is None and current_stocks is None:
        if current_assets is not None:
            current_cash = 0
            current_stocks = current_assets
        else:
            raise ValueError("Either (current_cash, current_stocks) or current_assets must be provided")

    # シナリオ設定取得
    scenario_config = config['simulation'][scenario]
    annual_return_rate = scenario_config['annual_return_rate']
    inflation_rate = scenario_config['inflation_rate']
    income_growth_rate = scenario_config['income_growth_rate']
    expense_growth_rate = scenario_config['expense_growth_rate']

    # シミュレーション期間（寿命まで）
    life_expectancy = config['simulation'].get('life_expectancy', 90)
    start_age = config['simulation'].get('start_age', 35)
    simulation_years = life_expectancy - start_age  # 寿命まで計算
    simulation_months = simulation_years * 12

    # 月次リターン率（複利計算）
    monthly_return_rate = (1 + annual_return_rate) ** (1/12) - 1

    # 資産配分設定
    allocation_enabled = _is_enabled(config, 'asset_allocation')
    if allocation_enabled:
        cash_buffer_months = config['asset_allocation'].get('cash_buffer_months', 6)
        auto_invest_threshold = config['asset_allocation'].get('auto_invest_threshold', 1.5)
        nisa_enabled = config['asset_allocation'].get('nisa_enabled', True)
        nisa_annual_limit = config['asset_allocation'].get('nisa_annual_limit', 3600000)
        invest_beyond_nisa = config['asset_allocation'].get('invest_beyond_nisa', True)
        min_cash_balance = config['asset_allocation'].get('min_cash_balance', 1000000)
        capital_gains_tax_rate = config['asset_allocation'].get('capital_gains_tax_rate', 0.20315)
    else:
        # 資産配分が無効の場合はデフォルト値
        cash_buffer_months = 0
        auto_invest_threshold = 999  # 自動投資しない
        nisa_enabled = False
        nisa_annual_limit = 0
        invest_beyond_nisa = False
        min_cash_balance = 0
        capital_gains_tax_rate = 0.20315

    # シミュレーション結果を格納
    results = []

    # 夫婦別収入の比率を計算（詳細表示用）
    shuhei_income_base = config['simulation'].get('shuhei_income', 0)
    sakura_income_base = config['simulation'].get('sakura_income', 0)
    if shuhei_income_base + sakura_income_base > 0:
        shuhei_ratio = shuhei_income_base / (shuhei_income_base + sakura_income_base)
    else:
        shuhei_ratio = 1.0  # 個別設定がない場合は全額を修平に割り当て

    # 初期値
    cash = current_cash
    stocks = current_stocks
    stocks_cost_basis = current_stocks  # 初期の株は簿価=時価と仮定
    nisa_balance = 0  # NISA枠内の投資額
    nisa_cost_basis = 0  # NISA枠内の簿価
    income = monthly_income
    expense = monthly_expense
    fire_achieved = False  # FIRE達成フラグ
    fire_month = None  # FIRE達成月を記録

    # 開始日
    current_date = datetime.now()
    current_year = current_date.year
    nisa_used_this_year = 0  # 今年のNISA投資額
    capital_gains_this_year = 0   # 今年の株式譲渡益（健康保険料計算用）
    prev_year_capital_gains = 0   # 前年の株式譲渡益（来年の健康保険料計算用）

    # 月次シミュレーション
    for month in range(simulation_months + 1):
        # 現在月の日付
        date = current_date + relativedelta(months=month)

        # 年数（成長率計算用）
        years = month / 12

        # 年が変わったらNISA枠と譲渡益集計をリセット
        _prev_gains = capital_gains_this_year
        current_year, capital_gains_this_year, _year_advanced = _advance_year(
            date.year, current_year, capital_gains_this_year
        )
        if _year_advanced:
            nisa_used_this_year = 0
            prev_year_capital_gains = _prev_gains

        # 収入計算（労働収入・年金・児童手当・FIRE前後の切替）
        _income = _calculate_monthly_income(
            years, fire_achieved, fire_month,
            shuhei_income_base, sakura_income_base, monthly_income,
            shuhei_ratio, income_growth_rate, config,
        )
        total_income = _income['total_income']
        labor_income = _income['labor_income']
        monthly_pension_income = _income['pension_income']
        monthly_child_allowance = _income['child_allowance']
        shuhei_income_monthly = _income['shuhei_income_monthly']
        sakura_income_monthly = _income['sakura_income_monthly']

        # 支出計算（全項目）
        _exp = _calculate_monthly_expenses(
            years, config, monthly_expense, expense_growth_rate,
            fire_achieved, prev_year_capital_gains
        )
        base_expense                     = _exp['base_expense']
        monthly_education_expense        = _exp['education_expense']
        monthly_mortgage_payment         = _exp['mortgage_payment']
        monthly_maintenance_cost         = _exp['maintenance_cost']
        monthly_workation_cost           = _exp['workation_cost']
        monthly_pension_premium          = _exp['pension_premium']
        monthly_health_insurance_premium = _exp['health_insurance_premium']
        expense                          = _exp['total']

        # 1. 収入を現金に加算
        cash += total_income

        # 2. 支出を現金から引き出し
        if cash >= expense:
            cash -= expense
            withdrawal_from_stocks = 0
            capital_gains_tax = 0
        else:
            # 現金が足りない場合は株から取り崩し
            shortage = expense - cash
            cash = 0

            # 支出不足型: NISAはshorageを直接削減、課税分のみcashへ
            result = _sell_stocks_with_tax(
                shortage, stocks, nisa_balance, nisa_cost_basis,
                stocks_cost_basis, capital_gains_tax_rate, allocation_enabled,
            )
            stocks = result.stocks
            nisa_balance = result.nisa_balance
            nisa_cost_basis = result.nisa_cost_basis
            stocks_cost_basis = result.stocks_cost_basis
            cash += result.cash_from_taxable
            capital_gains_this_year += result.capital_gain
            withdrawal_from_stocks = result.total_sold
            capital_gains_tax = result.capital_gain * capital_gains_tax_rate

        # 3. 運用リターン（株のみ）
        investment_return = stocks * monthly_return_rate
        stocks += investment_return
        # 簿価は増えない（リターンは含み益）

        # 3.5. FIRE後は最低現金残高を維持（資産配分が有効な場合）
        if allocation_enabled and fire_achieved:
            if cash < min_cash_balance and stocks > 0:
                shortage = min_cash_balance - cash
                # 最低現金型: NISAも課税分も両方cashへ
                result = _sell_stocks_with_tax(
                    shortage, stocks, nisa_balance, nisa_cost_basis,
                    stocks_cost_basis, capital_gains_tax_rate, allocation_enabled,
                )
                stocks = result.stocks
                nisa_balance = result.nisa_balance
                nisa_cost_basis = result.nisa_cost_basis
                stocks_cost_basis = result.stocks_cost_basis
                cash += result.nisa_sold + result.cash_from_taxable
                capital_gains_this_year += result.capital_gain

        # 4. 余剰現金がある場合は自動投資（FIRE前のみ、資産配分が有効な場合）
        auto_invested = 0
        if allocation_enabled and not fire_achieved:
            _inv = _auto_invest_surplus(
                cash, stocks, stocks_cost_basis, nisa_balance, nisa_cost_basis,
                nisa_used_this_year, expense, cash_buffer_months, min_cash_balance,
                auto_invest_threshold, nisa_enabled, nisa_annual_limit, invest_beyond_nisa,
            )
            cash                = _inv['cash']
            stocks              = _inv['stocks']
            stocks_cost_basis   = _inv['stocks_cost_basis']
            nisa_balance        = _inv['nisa_balance']
            nisa_cost_basis     = _inv['nisa_cost_basis']
            nisa_used_this_year = _inv['nisa_used_this_year']
            auto_invested       = _inv['auto_invested']

        # FIRE達成チェック: 今退職しても寿命まで資産が持つか?
        # 収入・支出・運用益を全て処理した後の資産で判定
        total_assets = cash + stocks
        if not fire_achieved and month > 0:  # 最初の月はスキップ
            # 現在の年間支出を計算（FIREチェック用）
            # FIRE後の社会保険料を含める必要があるため、fire_achieved=Trueで再計算
            annual_pension_premium_for_fire = calculate_national_pension_premium(years, config, fire_achieved=True)
            annual_health_insurance_premium_for_fire = calculate_national_health_insurance_premium(years, config, fire_achieved=True)
            current_annual_expense = (base_expense + monthly_education_expense + monthly_mortgage_payment + monthly_maintenance_cost + monthly_workation_cost) * 12 + annual_pension_premium_for_fire + annual_health_insurance_premium_for_fire

            # 余剰現金を計算（FIRE時は最低残高を確保）
            if allocation_enabled:
                fire_cash_buffer = max(expense * cash_buffer_months, min_cash_balance)
            else:
                fire_cash_buffer = cash
            potential_investment = max(0, cash - fire_cash_buffer)

            fire_check_result = can_retire_now(
                current_assets=total_assets,
                years_offset=years,
                current_annual_expense=current_annual_expense,
                config=config,
                scenario=scenario,
                current_cash=cash,
                current_stocks=stocks,
                nisa_balance=nisa_balance,
                nisa_cost_basis=nisa_cost_basis,
                stocks_cost_basis=stocks_cost_basis
            )

            if fire_check_result:
                fire_achieved = True
                fire_month = month
                print(f"  FIRE可能! at month {month} ({years:.1f} years), assets=JPY{total_assets:,.0f} (cash={cash:,.0f}, stocks={stocks:,.0f}, potential_investment={potential_investment:,.0f})")

        # 記録
        results.append(_build_monthly_result(
            date, month, cash, stocks, stocks_cost_basis, nisa_balance,
            total_income, monthly_pension_income, labor_income,
            shuhei_income_monthly, sakura_income_monthly, monthly_child_allowance,
            expense, base_expense, monthly_education_expense,
            monthly_mortgage_payment, monthly_maintenance_cost, monthly_workation_cost,
            monthly_pension_premium, monthly_health_insurance_premium,
            investment_return, auto_invested, capital_gains_tax, fire_achieved, fire_month,
        ))

        # 資産が破綻ライン（500万円）以下になったら終了
        if cash + stocks <= _BANKRUPTCY_THRESHOLD:
            break

    df = pd.DataFrame(results)

    return df


def simulate_with_withdrawal(
    initial_assets: float,
    annual_expense: float,
    years: int,
    return_rate: float,
    inflation_rate: float,
    config: Dict[str, Any] = None,
    start_year_offset: float = 0.0
) -> float:
    """
    定額引き出しシミュレーション（FIRE計算用）

    Args:
        initial_assets: 初期資産
        annual_expense: 年間支出（基本生活費）
        years: シミュレーション期間（年）
        return_rate: 年率リターン
        inflation_rate: インフレ率
        config: 設定辞書（教育費・年金収入計算用、オプション）
        start_year_offset: シミュレーション開始時点の経過年数（デフォルト0）

    Returns:
        最終資産額
    """
    assets = initial_assets
    monthly_base_expense = annual_expense / 12
    monthly_return_rate = (1 + return_rate) ** (1/12) - 1

    for month in range(int(years * 12)):
        # 年数（開始オフセットを加算）
        years_elapsed = start_year_offset + (month / 12)

        # ライフステージ別の基本生活費を計算
        fallback_annual_expense = annual_expense * (1 + inflation_rate) ** years_elapsed
        if config is not None:
            annual_base_expense = calculate_base_expense(years_elapsed, config, fallback_annual_expense)
        else:
            annual_base_expense = fallback_annual_expense
        adjusted_base_expense = annual_base_expense / 12

        # 教育費を追加（configが提供されている場合）
        monthly_education_expense = 0
        if config is not None:
            annual_education_expense = calculate_education_expense(years_elapsed, config)
            monthly_education_expense = annual_education_expense / 12

        # 年金収入を追加（configが提供されている場合）
        # この関数はFIRE後のシミュレーションなので、FIRE達成済みとして計算
        monthly_pension_income = 0
        if config is not None:
            annual_pension_income = calculate_pension_income(
                years_elapsed,
                config,
                fire_achieved=True,
                fire_year_offset=start_year_offset  # FIRE達成時点の年数
            )
            monthly_pension_income = annual_pension_income / 12

        # 児童手当を追加（configが提供されている場合）
        monthly_child_allowance = 0
        if config is not None:
            annual_child_allowance = calculate_child_allowance(years_elapsed, config)
            monthly_child_allowance = annual_child_allowance / 12

        # 住宅ローン支払額を追加（configが提供されている場合）
        monthly_mortgage_payment = 0
        if config is not None:
            monthly_mortgage_payment = calculate_mortgage_payment(years_elapsed, config)

        # 住宅メンテナンス費用を追加（configが提供されている場合）
        monthly_maintenance_cost = 0
        if config is not None:
            annual_maintenance_cost = calculate_house_maintenance(years_elapsed, config)
            monthly_maintenance_cost = annual_maintenance_cost / 12

        # ワーケーション費用を追加（configが提供されている場合）
        monthly_workation_cost = 0
        if config is not None:
            annual_workation_cost = calculate_workation_cost(years_elapsed, config)
            monthly_workation_cost = annual_workation_cost / 12

        # FIRE後の副収入を追加（configが提供されている場合）
        monthly_post_fire_income = 0
        if config is not None:
            monthly_post_fire_income = config['simulation'].get('post_fire_income', 0)

        # 社会保険料を追加（FIRE後のみ、configが提供されている場合）
        monthly_pension_premium = 0
        monthly_health_insurance_premium = 0
        if config is not None:
            annual_pension_premium = calculate_national_pension_premium(years_elapsed, config, fire_achieved=True)
            monthly_pension_premium = annual_pension_premium / 12
            # simulate_with_withdrawalはFIREチェック用の簡易計算なので、
            # 実際の譲渡益は不明のため0で近似（保守的な見積もり）
            annual_health_insurance_premium = calculate_national_health_insurance_premium(
                years_elapsed, config, fire_achieved=True, prev_year_capital_gains=0
            )
            monthly_health_insurance_premium = annual_health_insurance_premium / 12

        # 総支出 = 基本支出 + 教育費 + 住宅ローン + メンテナンス費用 + ワーケーション費用 + 社会保険料
        total_expense = adjusted_base_expense + monthly_education_expense + monthly_mortgage_payment + monthly_maintenance_cost + monthly_workation_cost + monthly_pension_premium + monthly_health_insurance_premium

        # 運用リターン
        investment_return = assets * monthly_return_rate

        # 資産更新（年金収入、児童手当、FIRE後副収入も考慮）
        assets = assets - total_expense + investment_return + monthly_pension_income + monthly_child_allowance + monthly_post_fire_income

        # 資産が破綻ライン（500万円）以下になったら終了
        if assets <= _BANKRUPTCY_THRESHOLD:
            return 0

    # 最終資産も破綻ライン以下なら0を返す
    if assets <= _BANKRUPTCY_THRESHOLD:
        return 0

    return assets


