"""
シミュレーターモジュール
将来の資産推移を予測
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from dateutil.relativedelta import relativedelta


def calculate_education_expense(year_offset: float, config: Dict[str, Any]) -> float:
    """
    指定年における教育費を計算

    Args:
        year_offset: シミュレーション開始からの経過年数
        config: 設定辞書

    Returns:
        年間教育費（円）
    """
    if not config.get('education', {}).get('enabled', False):
        return 0

    children = config['education'].get('children', [])
    costs = config['education']['costs']

    total_education_expense = 0

    from datetime import datetime
    current_date = datetime.now()

    for child in children:
        # 生年月日から現在の年齢を計算
        birthdate_str = child.get('birthdate')
        if not birthdate_str:
            continue

        birthdate = datetime.strptime(birthdate_str, '%Y/%m/%d')

        # 現在の年齢を計算
        current_age = (current_date - birthdate).days / 365.25

        # シミュレーション中の年齢 = 現在年齢 + 経過年数
        child_age = current_age + year_offset

        # 年齢に応じた教育段階と費用を計算
        if 3 <= child_age < 6:
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


def calculate_pension_income(year_offset: float, config: Dict[str, Any]) -> float:
    """
    指定年における年金収入を計算（複数人対応）

    Args:
        year_offset: シミュレーション開始からの経過年数
        config: 設定辞書

    Returns:
        年間年金収入（円）
    """
    if not config.get('pension', {}).get('enabled', False):
        return 0

    people = config['pension'].get('people', [])
    start_age = config['pension'].get('start_age', 65)

    total_pension_income = 0

    from datetime import datetime
    current_date = datetime.now()

    for person in people:
        # 生年月日から現在の年齢を計算
        birthdate_str = person.get('birthdate')
        if not birthdate_str:
            continue

        birthdate = datetime.strptime(birthdate_str, '%Y/%m/%d')

        # 現在の年齢を計算
        current_age = (current_date - birthdate).days / 365.25

        # シミュレーション中の年齢 = 現在年齢 + 経過年数
        person_age = current_age + year_offset

        # 年金受給開始年齢に達していれば年金収入を加算
        if person_age >= start_age:
            annual_amount = person.get('annual_amount', 0)
            total_pension_income += annual_amount

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
    if not config.get('child_allowance', {}).get('enabled', False):
        return 0

    children = config.get('education', {}).get('children', [])
    if not children:
        return 0

    allowance_config = config['child_allowance']
    under_3_monthly = allowance_config.get('under_3', 15000)
    age_3_to_15_monthly = allowance_config.get('age_3_to_15', 10000)

    total_annual_allowance = 0

    from datetime import datetime
    current_date = datetime.now()

    for child in children:
        birthdate_str = child.get('birthdate')
        if not birthdate_str:
            continue

        birthdate = datetime.strptime(birthdate_str, '%Y/%m/%d')
        current_age = (current_date - birthdate).days / 365.25
        child_age = current_age + year_offset

        # 年齢に応じた月額手当を計算
        if child_age < 3:
            monthly_allowance = under_3_monthly
        elif child_age <= 15:
            monthly_allowance = age_3_to_15_monthly
        else:
            monthly_allowance = 0

        total_annual_allowance += monthly_allowance * 12

    return total_annual_allowance


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
    if not config.get('mortgage', {}).get('enabled', False):
        return 0

    mortgage_config = config['mortgage']
    monthly_payment = mortgage_config.get('monthly_payment', 0)
    end_date_str = mortgage_config.get('end_date')

    if not end_date_str:
        return 0

    from datetime import datetime
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
    if not config.get('house_maintenance', {}).get('enabled', False):
        return 0

    maintenance_config = config['house_maintenance']
    items = maintenance_config.get('items', [])

    if not items:
        return 0

    from datetime import datetime
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
    if not config.get('workation', {}).get('enabled', False):
        return 0

    workation_config = config['workation']
    start_child_index = workation_config.get('start_child_index', 1)
    start_child_age = workation_config.get('start_child_age', 18)
    annual_cost = workation_config.get('annual_cost', 0)

    # 子供情報を取得
    children = config.get('education', {}).get('children', [])
    if start_child_index >= len(children):
        return 0  # 指定された子供が存在しない

    from datetime import datetime
    current_date = datetime.now()

    # 基準となる子供の情報
    child = children[start_child_index]
    birthdate_str = child.get('birthdate')
    if not birthdate_str:
        return 0

    birthdate = datetime.strptime(birthdate_str, '%Y/%m/%d')

    # シミュレーション時点での子供の年齢を計算
    current_age = (current_date - birthdate).days / 365.25
    child_age = current_age + year_offset

    # 開始年齢以降ならワーケーション費用を返す
    if child_age >= start_child_age:
        return annual_cost
    else:
        return 0


def can_retire_now(
    current_assets: float,
    years_offset: float,
    current_annual_expense: float,
    config: Dict[str, Any],
    scenario: str
) -> bool:
    """
    現在のタイミングで退職して、寿命まで資産が持つかチェック

    標準シナリオの前提で退職可能性を判定

    Args:
        current_assets: 現在の資産
        years_offset: シミュレーション開始からの経過年数
        current_annual_expense: 現在の年間支出
        config: 設定辞書
        scenario: シナリオ名（未使用 - 常に標準シナリオで判定）

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

    # 標準シナリオの前提で退職可能性を判定
    scenario_config = config['simulation']['standard']
    return_rate = scenario_config['annual_return_rate']
    inflation_rate = scenario_config['inflation_rate']

    # 退職後のシミュレーション実行
    final_assets = simulate_with_withdrawal(
        initial_assets=current_assets,
        annual_expense=current_annual_expense,
        years=remaining_years,
        return_rate=return_rate,
        inflation_rate=inflation_rate,
        config=config,
        start_year_offset=years_offset  # 現在の経過年数を渡す
    )

    # 破綻ライン: 500万円を下回らないことを確認
    return final_assets > 5_000_000


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
    from datetime import datetime
    current_date = datetime.now()

    child = children[0]
    birthdate_str = child.get('birthdate')
    if not birthdate_str:
        return fallback_expense

    birthdate = datetime.strptime(birthdate_str, '%Y/%m/%d')
    current_age = (current_date - birthdate).days / 365.25
    child_age = current_age + year_offset

    # 年齢に応じたライフステージを判定
    if child_age < 6:
        stage = 'young_child'
    elif child_age < 12:
        stage = 'elementary'
    elif child_age < 15:
        stage = 'junior_high'
    elif child_age < 18:
        stage = 'high_school'
    elif child_age < 22:
        stage = 'university'
    else:
        stage = 'empty_nest'

    # 基本支出（第一子の年齢に基づく）
    base_expense = base_expense_by_stage.get(stage, fallback_expense)

    # 追加の子供による生活費増加を計算
    additional_child_expense = config.get('fire', {}).get('additional_child_expense', 0)

    if additional_child_expense > 0 and len(children) > 1:
        # シミュレーション時点で出生済みの追加子供数をカウント
        simulation_date = current_date + pd.Timedelta(days=year_offset * 365.25)
        born_children_count = 0

        for child in children:
            child_birthdate_str = child.get('birthdate')
            if child_birthdate_str:
                child_birthdate = datetime.strptime(child_birthdate_str, '%Y/%m/%d')
                if child_birthdate <= simulation_date:
                    born_children_count += 1

        # 第一子を除く追加子供の人数
        additional_children = max(0, born_children_count - 1)

        # 追加子供分の生活費を加算
        base_expense += additional_child_expense * additional_children

    return base_expense


def simulate_future_assets(
    current_assets: float,
    monthly_income: float,
    monthly_expense: float,
    config: Dict[str, Any],
    scenario: str = 'standard'
) -> pd.DataFrame:
    """
    将来の資産推移をシミュレーション

    毎月「今退職しても寿命まで資産が持つか?」をチェックし、
    初めて持つと判定された月がFIRE達成日となる

    Args:
        current_assets: 現在の純資産
        monthly_income: 月次収入
        monthly_expense: 月次支出
        config: 設定辞書
        scenario: シナリオ名 ('standard', 'optimistic', 'pessimistic')

    Returns:
        シミュレーション結果のデータフレーム
    """
    print(f"Simulating future assets ({scenario} scenario)...")

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

    print(f"  Simulation period: {simulation_years} years (age {start_age} to {life_expectancy})")

    # 月次リターン率（複利計算）
    monthly_return_rate = (1 + annual_return_rate) ** (1/12) - 1

    # シミュレーション結果を格納
    results = []

    # 初期値
    assets = current_assets
    income = monthly_income
    expense = monthly_expense
    fire_achieved = False  # FIRE達成フラグ
    fire_month = None  # FIRE達成月を記録

    # 開始日
    from datetime import datetime
    current_date = datetime.now()

    # 月次シミュレーション
    for month in range(simulation_months + 1):
        # 現在月の日付
        date = current_date + relativedelta(months=month)

        # 年数（成長率計算用）
        years = month / 12

        # 収入の成長（複利）
        income = monthly_income * (1 + income_growth_rate) ** years

        # ライフステージ別の基本生活費を計算（月額に変換前）
        fallback_annual_expense = monthly_expense * 12 * (1 + expense_growth_rate) ** years
        annual_base_expense = calculate_base_expense(years, config, fallback_annual_expense)
        base_expense = annual_base_expense / 12

        # 教育費を追加（年間費用を月額に換算）
        annual_education_expense = calculate_education_expense(years, config)
        monthly_education_expense = annual_education_expense / 12

        # 年金収入を追加（年間収入を月額に換算）
        annual_pension_income = calculate_pension_income(years, config)
        monthly_pension_income = annual_pension_income / 12

        # 児童手当を追加（年間手当を月額に換算）
        annual_child_allowance = calculate_child_allowance(years, config)
        monthly_child_allowance = annual_child_allowance / 12

        # 住宅ローン支払額を追加
        monthly_mortgage_payment = calculate_mortgage_payment(years, config)

        # 住宅メンテナンス費用を追加（年間費用を月額に換算）
        annual_maintenance_cost = calculate_house_maintenance(years, config)
        monthly_maintenance_cost = annual_maintenance_cost / 12

        # ワーケーション費用を追加（年間費用を月額に換算）
        annual_workation_cost = calculate_workation_cost(years, config)
        monthly_workation_cost = annual_workation_cost / 12

        # 総支出 = 基本支出 + 教育費 + 住宅ローン + メンテナンス費用 + ワーケーション費用
        expense = base_expense + monthly_education_expense + monthly_mortgage_payment + monthly_maintenance_cost + monthly_workation_cost

        # 現在の年間支出を計算（FIREチェック用）
        current_annual_expense = (base_expense + monthly_education_expense + monthly_mortgage_payment) * 12 + annual_maintenance_cost + annual_workation_cost

        # FIRE達成チェック: 今退職しても寿命まで資産が持つか?
        if not fire_achieved and month > 0:  # 最初の月はスキップ
            if can_retire_now(
                current_assets=assets,
                years_offset=years,
                current_annual_expense=current_annual_expense,
                config=config,
                scenario=scenario
            ):
                fire_achieved = True
                fire_month = month
                print(f"  FIRE可能! at month {month} ({years:.1f} years), assets=JPY{assets:,.0f}")

        # FIRE達成後は労働収入を0にする（仕事を辞める想定）
        # ただし、年金収入、児童手当、副収入は継続
        post_fire_income = config['simulation'].get('post_fire_income', 0)

        if fire_achieved:
            total_income = monthly_pension_income + monthly_child_allowance + post_fire_income
            labor_income = post_fire_income  # FIRE後は副収入のみ
        else:
            total_income = income + monthly_pension_income + monthly_child_allowance
            labor_income = income  # FIRE前は労働収入

        # 運用リターン
        investment_return = assets * monthly_return_rate

        # 資産更新（収入 - 支出 + 運用リターン）
        assets = assets + total_income - expense + investment_return

        # 記録
        results.append({
            'date': date,
            'month': month,
            'assets': max(0, assets),  # 負債は0で下限
            'income': total_income,
            'pension_income': monthly_pension_income,
            'labor_income': labor_income,
            'expense': expense,
            'base_expense': base_expense,
            'education_expense': monthly_education_expense,
            'mortgage_payment': monthly_mortgage_payment,
            'maintenance_cost': monthly_maintenance_cost,
            'workation_cost': monthly_workation_cost,
            'net_cashflow': total_income - expense,
            'investment_return': investment_return,
            'fire_achieved': fire_achieved,
            'fire_month': fire_month,
        })

        # 資産が破綻ライン（500万円）以下になったら終了
        if assets <= 5_000_000:
            print(f"  Assets depleted at month {month} ({years:.1f} years)")
            break

    df = pd.DataFrame(results)

    print(f"  Simulated {len(df)} months ({len(df)/12:.1f} years)")
    print(f"  Final assets: JPY{df.iloc[-1]['assets']:,.0f}")

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
        monthly_pension_income = 0
        if config is not None:
            annual_pension_income = calculate_pension_income(years_elapsed, config)
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

        # 総支出 = 基本支出 + 教育費 + 住宅ローン + メンテナンス費用 + ワーケーション費用
        total_expense = adjusted_base_expense + monthly_education_expense + monthly_mortgage_payment + monthly_maintenance_cost + monthly_workation_cost

        # 運用リターン
        investment_return = assets * monthly_return_rate

        # 資産更新（年金収入、児童手当、FIRE後副収入も考慮）
        assets = assets - total_expense + investment_return + monthly_pension_income + monthly_child_allowance + monthly_post_fire_income

        # 資産が破綻ライン（500万円）以下になったら終了
        if assets <= 5_000_000:
            return 0

    # 最終資産も破綻ライン以下なら0を返す
    if assets <= 5_000_000:
        return 0

    return assets


