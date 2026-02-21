"""
シミュレーターモジュール
将来の資産推移を予測
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, NamedTuple, Optional, Tuple
from dataclasses import dataclass, field
from dateutil.relativedelta import relativedelta
from functools import lru_cache

# 年金・資産計算用定数
_NATIONAL_PENSION_FULL_AMOUNT = 816_000       # 国民年金満額（2024年度, 円/年）
_EMPLOYEE_PENSION_MULTIPLIER = 0.005481        # 厚生年金乗率（給付乗率）
_PENSION_MAX_CONTRIBUTION_YEARS = 40           # 国民年金最大加入年数
_BANKRUPTCY_THRESHOLD = 5_000_000              # 破綻ライン（円）

# 国民健康保険料計算用定数（config未設定時のフォールバック）
_HEALTH_INS_BASIC_DEDUCTION = 430_000  # 基礎控除（2024年度・円）
_HEALTH_INS_DEFAULT_INCOME_RATE = 0.11  # 所得割率デフォルト（40歳以上・全国平均）


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


@dataclass
class SimulationState:
    """
    シミュレーションの状態を保持するクラス

    月次シミュレーション処理の共通化のため、各シミュレーション関数が
    共有する状態変数を一つのクラスにまとめる。
    """
    # 時間
    month_index: int
    current_date: datetime
    year_offset: float

    # 資産
    cash: float
    stocks: float
    nisa_balance: float
    stocks_cost_basis: float
    nisa_cost_basis: float

    # 年度管理
    current_year: int
    nisa_annual_invested: float = 0.0

    # 譲渡益
    capital_gains_this_year: float = 0.0
    prev_year_capital_gains: float = 0.0

    # FIRE関連
    fire_achieved: bool = False
    fire_achievement_month: Optional[int] = None

    # 設定
    config: Dict[str, Any] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)  # シナリオパラメータ


class SimulationCallbacks:
    """
    シミュレーション固有の処理を定義するコールバッククラス

    各シミュレーション関数は、このクラスを継承して固有の処理を実装する。
    """

    def on_month_start(self, state: SimulationState) -> None:
        """
        月初処理（オプション）

        Args:
            state: シミュレーション状態（破壊的に更新可能）
        """
        pass

    def on_month_end(self, state: SimulationState) -> Optional[Dict[str, Any]]:
        """
        月末処理（オプション）

        Args:
            state: シミュレーション状態（破壊的に更新可能）

        Returns:
            結果レコードに追加するデータ（オプション）
        """
        return None

    def should_terminate(self, state: SimulationState) -> bool:
        """
        シミュレーション終了判定

        Args:
            state: シミュレーション状態

        Returns:
            True ならシミュレーション終了
        """
        return False


def _get_monthly_return_rate(annual_return_rate: float) -> float:
    """
    年率リターンから月次リターン率を計算（複利）。

    Args:
        annual_return_rate: 年率リターン（例: 0.05 = 5%）

    Returns:
        月次リターン率
    """
    return (1 + annual_return_rate) ** (1/12) - 1


def generate_random_returns(
    annual_return_mean: float,
    annual_return_std: float,
    total_months: int,
    random_seed: Optional[int] = None
) -> np.ndarray:
    """
    月次リターンをランダム生成（対数正規分布）

    モンテカルロシミュレーション用に、市場変動を考慮した
    ランダムな月次リターン率を生成する。

    対数正規分布モデルを採用することで：
    - 資産価格が負にならない（理論的に正確）
    - 幾何平均が自然に保存される
    - 手動のVolatility Drag補正が不要

    Args:
        annual_return_mean: 年率リターン平均（例: 0.05 = 5%）
        annual_return_std: 年率リターン標準偏差（例: 0.10 = 10%）
        total_months: シミュレーション月数
        random_seed: 乱数シード（再現性のため、オプション）

    Returns:
        月次リターン率の配列（長さ: total_months）

    Example:
        >>> returns = generate_random_returns(0.05, 0.10, 12, random_seed=42)
        >>> len(returns)
        12
        >>> returns[0] > -1  # リターンは-100%未満にならない
        True
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    # 対数リターンのパラメータ計算
    # 年率リターンを対数空間に変換
    log_annual_mean = np.log(1 + annual_return_mean)
    log_monthly_mean = log_annual_mean / 12

    # 標準偏差は√12で月次に変換
    log_monthly_std = annual_return_std / np.sqrt(12)

    # 対数リターンを正規分布からサンプリング
    log_returns = np.random.normal(
        loc=log_monthly_mean,
        scale=log_monthly_std,
        size=total_months
    )

    # 算術リターンに変換
    # r = exp(log_r) - 1
    returns = np.exp(log_returns) - 1

    return returns


@lru_cache(maxsize=32)
def _parse_birthdate(birthdate_str: str) -> datetime:
    """生年月日文字列をパース（キャッシュ付き）"""
    return datetime.strptime(birthdate_str, '%Y/%m/%d')

def _get_age_at_offset(birthdate_str: str, year_offset: float) -> float:
    """
    生年月日文字列とシミュレーション経過年数から、その時点での年齢を返す。

    Args:
        birthdate_str: 生年月日（'YYYY/MM/DD'形式）
        year_offset: シミュレーション開始からの経過年数

    Returns:
        シミュレーション時点での年齢（歳）
    """
    birthdate = _parse_birthdate(birthdate_str)  # キャッシュされたパース結果を使用
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


def _calculate_person_pension(
    person: dict,
    year_offset: float,
    start_age: float,
    fire_achieved: bool,
    fire_year_offset: float,
) -> float:
    """
    1人分の年金年間受給額を計算する。

    Args:
        person: config['pension']['people'] の1エントリ
        year_offset: シミュレーション開始からの経過年数
        start_age: 年金受給開始年齢
        fire_achieved: FIRE達成フラグ
        fire_year_offset: FIRE達成時点の経過年数（年）

    Returns:
        年間年金受給額（円）。受給開始前は 0。
    """
    birthdate_str = person.get('birthdate')
    if not birthdate_str:
        return 0

    person_age = _get_age_at_offset(birthdate_str, year_offset)
    if person_age < start_age:
        return 0

    pension_type = person.get('pension_type', 'employee')

    if pension_type == 'employee':
        avg_monthly_salary = person.get('avg_monthly_salary', 0)
        work_start_age = person.get('work_start_age', 23)
        if fire_achieved and fire_year_offset is not None:
            work_end_age = _get_age_at_offset(birthdate_str, fire_year_offset)
        else:
            work_end_age = min(person_age, 65)
        work_months = int(max(0, work_end_age - work_start_age) * 12)
        employees_pension = _calculate_employees_pension_amount(avg_monthly_salary, work_months)
        national_pension = _calculate_national_pension_amount(_PENSION_MAX_CONTRIBUTION_YEARS)
        return employees_pension + national_pension

    elif pension_type == 'national':
        return _calculate_national_pension_amount(_PENSION_MAX_CONTRIBUTION_YEARS)

    else:
        # 従来の固定値フォールバック（後方互換性）
        return person.get('annual_amount', 0)


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

    start_age = config['pension'].get('start_age', 65)
    return sum(
        _calculate_person_pension(person, year_offset, start_age, fire_achieved, fire_year_offset)
        for person in config['pension'].get('people', [])
    )


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
    # 副業収入（修平 + 桜の年額合計）
    annual_side_income = (
        config['simulation'].get('shuhei_post_fire_income', 0)
        + config['simulation'].get('sakura_post_fire_income', 0)
    ) * 12

    # 前年の株式譲渡益（キャピタルゲイン）
    # 国民健康保険の所得割は分離課税の譲渡所得も含む
    capital_gains = prev_year_capital_gains

    # 合計所得
    total_income = annual_side_income + capital_gains

    # --- 所得割 ---
    basic_deduction = si.get('health_insurance_basic_deduction', _HEALTH_INS_BASIC_DEDUCTION)
    taxable_income = max(0, total_income - basic_deduction)
    income_rate = si.get('health_insurance_income_rate', _HEALTH_INS_DEFAULT_INCOME_RATE)
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

    # 終了日をパース（キャッシュされる）
    end_date = _parse_birthdate(end_date_str)

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


def _sakura_income_for_month(date: datetime, sakura_income_base: float, config: dict) -> float:
    """
    指定月の桜の月収を返す。産休・育休期間中は config の monthly_income を使用する。

    Args:
        date: 判定する月の日付
        sakura_income_base: 通常時の桜の月収
        config: 設定辞書

    Returns:
        その月の桜の月収（円）
    """
    leave_list = config.get('simulation', {}).get('maternity_leave', [])
    children = config.get('education', {}).get('children', [])

    for leave in leave_list:
        child_name = leave.get('child')
        months_before = leave.get('months_before', 2)
        months_after = leave.get('months_after', 12)
        income_during_leave = leave.get('monthly_income', 0)

        # 対象の子供の生年月日を検索
        birthdate_str = next(
            (c.get('birthdate') for c in children if c.get('name') == child_name),
            None,
        )
        if birthdate_str is None:
            continue

        birthdate = datetime.strptime(birthdate_str, '%Y/%m/%d')
        leave_start = birthdate - relativedelta(months=months_before)
        leave_end = birthdate + relativedelta(months=months_after)

        if leave_start <= date <= leave_end:
            return income_during_leave

    return sakura_income_base


def _calculate_monthly_income(
    years: float,
    date: datetime,
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
      labor_income:               労働収入（FIRE後は shuhei + sakura の post_fire 合計）
      pension_income:             月次年金収入
      child_allowance:            月次児童手当
      shuhei_income_monthly:      修平の月収（FIRE後は shuhei_post_fire_income）
      sakura_income_monthly:      桜の月収（FIRE後は sakura_post_fire_income）
      post_fire_income:           修平の FIRE後副収入設定値
    """

    # 年金収入
    fire_year_offset = (fire_month / 12) if fire_month is not None else None
    annual_pension_income = calculate_pension_income(
        years, config, fire_achieved=fire_achieved, fire_year_offset=fire_year_offset
    )
    monthly_pension_income = annual_pension_income / 12

    # 児童手当
    monthly_child_allowance = calculate_child_allowance(years, config) / 12

    shuhei_post_fire_income = config['simulation'].get('shuhei_post_fire_income', 0)
    sakura_post_fire_income = config['simulation'].get('sakura_post_fire_income', 0)

    if fire_achieved:
        # 年金受給開始後は完全リタイア（労働収入なし）
        if monthly_pension_income > 0:
            shuhei_post_fire_income = 0
            sakura_post_fire_income = 0
        labor_income = shuhei_post_fire_income + sakura_post_fire_income
        return {
            'total_income': monthly_pension_income + monthly_child_allowance + labor_income,
            'labor_income': labor_income,
            'pension_income': monthly_pension_income,
            'child_allowance': monthly_child_allowance,
            'shuhei_income_monthly': shuhei_post_fire_income,
            'sakura_income_monthly': sakura_post_fire_income,
            'post_fire_income': shuhei_post_fire_income,
        }

    # FIRE前: 労働収入を成長率に応じて計算
    # 修平（会社員）: income_growth_rateを適用
    # 桜（個人事業主）: 固定（成長なし）。産休・育休期間中は月収を変動させる
    sakura_income_current = _sakura_income_for_month(date, sakura_income_base, config)
    if shuhei_income_base + sakura_income_base > 0:
        shuhei_income_monthly = shuhei_income_base * (1 + income_growth_rate) ** years
        sakura_income_monthly = sakura_income_current
        income = shuhei_income_monthly + sakura_income_monthly
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
        'post_fire_income': shuhei_post_fire_income,
    }


def _initialize_post_fire_simulation(
    current_cash: float,
    current_stocks: float,
    years_offset: float,
    config: Dict[str, Any],
    scenario: str,
    nisa_balance: float,
    nisa_cost_basis: float,
    stocks_cost_basis: Optional[float]
) -> Dict[str, Any]:
    """
    FIRE後シミュレーションの初期状態を設定

    Returns:
        初期化済みの設定と状態変数を含む辞書
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
    monthly_return_rate = _get_monthly_return_rate(annual_return_rate)

    # 資産配分設定
    allocation_enabled = _is_enabled(config, 'asset_allocation')
    if allocation_enabled:
        capital_gains_tax_rate = config['asset_allocation'].get('capital_gains_tax_rate', 0.20315)
        min_cash_balance = config['asset_allocation'].get('min_cash_balance', 1000000)
    else:
        capital_gains_tax_rate = 0.20315
        min_cash_balance = 0

    # FIRE後の収入
    post_fire_income = (
        config['simulation'].get('shuhei_post_fire_income', 0)
        + config['simulation'].get('sakura_post_fire_income', 0)
    )

    return {
        'cash': current_cash,
        'stocks': current_stocks,
        'stocks_cost_basis': stocks_cost_basis if stocks_cost_basis is not None else current_stocks,
        'nisa_balance': nisa_balance,
        'nisa_cost_basis': nisa_cost_basis,
        'remaining_months': remaining_months,
        'monthly_return_rate': monthly_return_rate,
        'allocation_enabled': allocation_enabled,
        'capital_gains_tax_rate': capital_gains_tax_rate,
        'min_cash_balance': min_cash_balance,
        'post_fire_income': post_fire_income,
    }


def _process_post_fire_monthly_cycle(
    month: int,
    cash: float,
    stocks: float,
    stocks_cost_basis: float,
    nisa_balance: float,
    nisa_cost_basis: float,
    current_year_post: int,
    capital_gains_this_year_post: float,
    prev_year_capital_gains_post: float,
    years_offset: float,
    config: Dict[str, Any],
    current_date_post: datetime,
    monthly_return_rate: float,
    allocation_enabled: bool,
    capital_gains_tax_rate: float,
    min_cash_balance: float,
    post_fire_income: float,
) -> Dict[str, Any]:
    """
    FIRE後の1ヶ月分のシミュレーション処理

    Returns:
        更新後の状態と破綻フラグを含む辞書
    """
    years = years_offset + month / 12
    date_post = current_date_post + relativedelta(months=int(years * 12))

    # 年度管理
    _prev_gains = capital_gains_this_year_post
    current_year_post, capital_gains_this_year_post, _year_advanced = _advance_year(
        date_post.year, current_year_post, capital_gains_this_year_post
    )
    if _year_advanced:
        prev_year_capital_gains_post = _prev_gains

    # 支出計算
    annual_base_expense = calculate_base_expense(years, config, 0)
    base_expense = annual_base_expense / 12

    annual_education_expense = calculate_education_expense(years, config)
    monthly_education_expense = annual_education_expense / 12

    monthly_mortgage_payment = calculate_mortgage_payment(years, config)

    annual_maintenance_cost = calculate_house_maintenance(years, config)
    monthly_maintenance_cost = annual_maintenance_cost / 12

    annual_workation_cost = calculate_workation_cost(years, config)
    monthly_workation_cost = annual_workation_cost / 12

    annual_pension_premium = calculate_national_pension_premium(years, config, fire_achieved=True)
    monthly_pension_premium = annual_pension_premium / 12

    annual_health_insurance_premium = calculate_national_health_insurance_premium(
        years, config, fire_achieved=True,
        prev_year_capital_gains=prev_year_capital_gains_post
    )
    monthly_health_insurance_premium = annual_health_insurance_premium / 12

    expense = (base_expense + monthly_education_expense + monthly_mortgage_payment +
              monthly_maintenance_cost + monthly_workation_cost +
              monthly_pension_premium + monthly_health_insurance_premium)

    # 収入計算
    annual_pension_income = calculate_pension_income(
        years, config, fire_achieved=True, fire_year_offset=years_offset
    )
    monthly_pension_income = annual_pension_income / 12

    # 年金受給開始後は完全リタイア
    effective_post_fire_income = 0 if monthly_pension_income > 0 else post_fire_income

    annual_child_allowance = calculate_child_allowance(years, config)
    monthly_child_allowance = annual_child_allowance / 12

    total_income = effective_post_fire_income + monthly_pension_income + monthly_child_allowance

    # 収入を現金に加算
    cash += total_income

    # 支出を現金から引き出し
    if cash >= expense:
        cash -= expense
    else:
        shortage = expense - cash
        cash = 0
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

    # 運用リターン
    investment_return = stocks * monthly_return_rate
    stocks += investment_return

    # 最低現金残高維持
    if allocation_enabled:
        if cash < min_cash_balance and stocks > 0:
            shortage = min_cash_balance - cash
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

    # 破綻判定
    should_break = (cash + stocks <= _BANKRUPTCY_THRESHOLD)

    return {
        'cash': cash,
        'stocks': stocks,
        'stocks_cost_basis': stocks_cost_basis,
        'nisa_balance': nisa_balance,
        'nisa_cost_basis': nisa_cost_basis,
        'current_year_post': current_year_post,
        'capital_gains_this_year_post': capital_gains_this_year_post,
        'prev_year_capital_gains_post': prev_year_capital_gains_post,
        'should_break': should_break,
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

    # 初期化
    init = _initialize_post_fire_simulation(
        current_cash, current_stocks, years_offset, config, scenario,
        nisa_balance, nisa_cost_basis, stocks_cost_basis
    )

    cash = init['cash']
    stocks = init['stocks']
    stocks_cost_basis = init['stocks_cost_basis']
    nisa_balance = init['nisa_balance']
    nisa_cost_basis = init['nisa_cost_basis']
    remaining_months = init['remaining_months']
    monthly_return_rate = init['monthly_return_rate']
    allocation_enabled = init['allocation_enabled']
    capital_gains_tax_rate = init['capital_gains_tax_rate']
    min_cash_balance = init['min_cash_balance']
    post_fire_income = init['post_fire_income']

    # 健康保険料の動的計算用
    current_date_post = datetime.now()
    current_year_post = (current_date_post + relativedelta(months=int(years_offset * 12))).year
    capital_gains_this_year_post = 0
    prev_year_capital_gains_post = 0

    # 月次シミュレーション
    for month in range(remaining_months):
        cycle_result = _process_post_fire_monthly_cycle(
            month, cash, stocks, stocks_cost_basis, nisa_balance, nisa_cost_basis,
            current_year_post, capital_gains_this_year_post, prev_year_capital_gains_post,
            years_offset, config, current_date_post,
            monthly_return_rate, allocation_enabled,
            capital_gains_tax_rate, min_cash_balance, post_fire_income,
        )

        # 状態を更新
        cash = cycle_result['cash']
        stocks = cycle_result['stocks']
        stocks_cost_basis = cycle_result['stocks_cost_basis']
        nisa_balance = cycle_result['nisa_balance']
        nisa_cost_basis = cycle_result['nisa_cost_basis']
        current_year_post = cycle_result['current_year_post']
        capital_gains_this_year_post = cycle_result['capital_gains_this_year_post']
        prev_year_capital_gains_post = cycle_result['prev_year_capital_gains_post']

        # 破綻判定
        if cycle_result['should_break']:
            return 0

    return cash + stocks

def _simulate_post_fire_with_random_returns(
    current_cash: float,
    current_stocks: float,
    years_offset: float,
    config: Dict[str, Any],
    scenario: str,
    random_returns: np.ndarray,
    nisa_balance: float = 0,
    nisa_cost_basis: float = 0,
    stocks_cost_basis: float = None,
    return_timeseries: bool = False
):
    """
    FIRE後の資産推移をランダムリターンでシミュレーション（モンテカルロ用）

    Args:
        current_cash: FIRE達成時の現金残高
        current_stocks: FIRE達成時の株式残高
        years_offset: FIRE達成時のシミュレーション開始からの経過年数
        config: 設定辞書
        scenario: シナリオ名
        random_returns: 月次リターン率の配列
        nisa_balance: NISA残高
        nisa_cost_basis: NISA簿価
        stocks_cost_basis: 株式全体の簿価
        return_timeseries: Trueの場合、月ごとの資産リストを返す

    Returns:
        return_timeseries=False: 90歳時点での資産額（破綻時は0）
        return_timeseries=True: 月ごとの資産額のリスト
    """
    # 初期化
    init = _initialize_post_fire_simulation(
        current_cash, current_stocks, years_offset, config, scenario,
        nisa_balance, nisa_cost_basis, stocks_cost_basis
    )

    cash = init['cash']
    stocks = init['stocks']
    stocks_cost_basis = init['stocks_cost_basis']
    nisa_balance = init['nisa_balance']
    nisa_cost_basis = init['nisa_cost_basis']
    remaining_months = init['remaining_months']
    allocation_enabled = init['allocation_enabled']
    capital_gains_tax_rate = init['capital_gains_tax_rate']
    min_cash_balance = init['min_cash_balance']
    post_fire_income = init['post_fire_income']

    # 健康保険料の動的計算用
    current_date_post = datetime.now()
    current_year_post = (current_date_post + relativedelta(months=int(years_offset * 12))).year
    capital_gains_this_year_post = 0
    prev_year_capital_gains_post = 0

    # ランダムリターンの長さチェック
    if len(random_returns) < remaining_months:
        raise ValueError(f"random_returns length ({len(random_returns)}) < remaining_months ({remaining_months})")

    # 月ごとの資産を記録（return_timeseries=Trueの場合）
    timeseries = [] if return_timeseries else None

    # 月次シミュレーション
    for month in range(remaining_months):
        years = years_offset + month / 12
        date_post = current_date_post + relativedelta(months=int(years * 12))

        # 年度管理
        _prev_gains = capital_gains_this_year_post
        current_year_post, capital_gains_this_year_post, _year_advanced = _advance_year(
            date_post.year, current_year_post, capital_gains_this_year_post
        )
        if _year_advanced:
            prev_year_capital_gains_post = _prev_gains

        # 支出計算
        annual_base_expense = calculate_base_expense(years, config, 0)
        base_expense = annual_base_expense / 12

        annual_education_expense = calculate_education_expense(years, config)
        monthly_education_expense = annual_education_expense / 12

        monthly_mortgage_payment = calculate_mortgage_payment(years, config)

        annual_maintenance_cost = calculate_house_maintenance(years, config)
        monthly_maintenance_cost = annual_maintenance_cost / 12

        annual_workation_cost = calculate_workation_cost(years, config)
        monthly_workation_cost = annual_workation_cost / 12

        annual_pension_premium = calculate_national_pension_premium(years, config, fire_achieved=True)
        monthly_pension_premium = annual_pension_premium / 12

        annual_health_insurance_premium = calculate_national_health_insurance_premium(
            years, config, fire_achieved=True,
            prev_year_capital_gains=prev_year_capital_gains_post
        )
        monthly_health_insurance_premium = annual_health_insurance_premium / 12

        expense = (base_expense + monthly_education_expense + monthly_mortgage_payment +
                  monthly_maintenance_cost + monthly_workation_cost +
                  monthly_pension_premium + monthly_health_insurance_premium)

        # 収入計算
        annual_pension_income = calculate_pension_income(
            years, config, fire_achieved=True, fire_year_offset=years_offset
        )
        monthly_pension_income = annual_pension_income / 12

        # 年金受給開始後は完全リタイア
        effective_post_fire_income = 0 if monthly_pension_income > 0 else post_fire_income

        annual_child_allowance = calculate_child_allowance(years, config)
        monthly_child_allowance = annual_child_allowance / 12

        total_income = effective_post_fire_income + monthly_pension_income + monthly_child_allowance

        # 収入を現金に加算
        cash += total_income

        # 支出を現金から引き出し
        if cash >= expense:
            cash -= expense
        else:
            shortage = expense - cash
            cash = 0
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

        # ランダムリターン適用（NISA含む）
        monthly_return = random_returns[month]
        stocks *= (1 + monthly_return)
        nisa_balance *= (1 + monthly_return)

        # 最低現金残高維持
        if allocation_enabled:
            if cash < min_cash_balance and stocks > 0:
                shortage = min_cash_balance - cash
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

        # 月ごとの資産を記録
        if return_timeseries:
            timeseries.append(cash + stocks)

        # 破綻判定（早期終了なし - ユーザー要求により全期間シミュレート）
        # ただし、資産がマイナスの場合
        if cash + stocks < 0:
            if return_timeseries:
                # 残りの月も0で埋める
                timeseries.extend([0] * (remaining_months - month - 1))
                return timeseries
            else:
                return 0

    if return_timeseries:
        return timeseries
    else:
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


def _initialize_future_simulation(
    current_cash: Optional[float],
    current_stocks: Optional[float],
    current_assets: Optional[float],
    monthly_income: float,
    monthly_expense: float,
    config: Dict[str, Any],
    scenario: str
) -> Dict[str, Any]:
    """
    将来シミュレーションの初期状態を設定

    Returns:
        初期化済みの設定と状態変数を含む辞書
    """
    # 後方互換性: current_assetsが指定されている場合は全額株として扱う
    if current_cash is None and current_stocks is None:
        if current_assets is not None:
            cash = 0.0
            stocks = current_assets
        else:
            raise ValueError("Either (current_cash, current_stocks) or current_assets must be provided")
    else:
        cash = current_cash if current_cash is not None else 0.0
        stocks = current_stocks if current_stocks is not None else 0.0

    # シナリオ設定取得
    scenario_config = config['simulation'][scenario]
    annual_return_rate = scenario_config['annual_return_rate']
    inflation_rate = scenario_config['inflation_rate']
    income_growth_rate = scenario_config['income_growth_rate']
    expense_growth_rate = scenario_config['expense_growth_rate']

    # シミュレーション期間（寿命まで）
    life_expectancy = config['simulation'].get('life_expectancy', 90)
    start_age = config['simulation'].get('start_age', 35)
    simulation_years = life_expectancy - start_age
    simulation_months = simulation_years * 12

    # 月次リターン率（複利計算）
    monthly_return_rate = _get_monthly_return_rate(annual_return_rate)

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
        cash_buffer_months = 0
        auto_invest_threshold = 999
        nisa_enabled = False
        nisa_annual_limit = 0
        invest_beyond_nisa = False
        min_cash_balance = 0
        capital_gains_tax_rate = 0.20315

    # 夫婦別収入の比率を計算
    shuhei_income_base = config['simulation'].get('shuhei_income', 0)
    sakura_income_base = config['simulation'].get('sakura_income', 0)
    if shuhei_income_base + sakura_income_base > 0:
        shuhei_ratio = shuhei_income_base / (shuhei_income_base + sakura_income_base)
    else:
        shuhei_ratio = 1.0

    return {
        # 資産
        'cash': cash,
        'stocks': stocks,
        'stocks_cost_basis': stocks,  # 初期の株は簿価=時価と仮定
        'nisa_balance': 0.0,
        'nisa_cost_basis': 0.0,

        # 設定
        'simulation_months': simulation_months,
        'monthly_return_rate': monthly_return_rate,
        'allocation_enabled': allocation_enabled,
        'cash_buffer_months': cash_buffer_months,
        'auto_invest_threshold': auto_invest_threshold,
        'nisa_enabled': nisa_enabled,
        'nisa_annual_limit': nisa_annual_limit,
        'invest_beyond_nisa': invest_beyond_nisa,
        'min_cash_balance': min_cash_balance,
        'capital_gains_tax_rate': capital_gains_tax_rate,

        # シナリオパラメータ
        'annual_return_rate': annual_return_rate,
        'inflation_rate': inflation_rate,
        'income_growth_rate': income_growth_rate,
        'expense_growth_rate': expense_growth_rate,

        # その他
        'shuhei_ratio': shuhei_ratio,
        'shuhei_income_base': shuhei_income_base,
        'sakura_income_base': sakura_income_base,
        'income': monthly_income,
        'expense': monthly_expense,
    }


def _process_future_monthly_cycle(
    month: int,
    cash: float,
    stocks: float,
    stocks_cost_basis: float,
    nisa_balance: float,
    nisa_cost_basis: float,
    fire_achieved: bool,
    fire_month: Optional[int],
    current_date: datetime,
    current_year: int,
    nisa_used_this_year: float,
    capital_gains_this_year: float,
    prev_year_capital_gains: float,
    config: Dict[str, Any],
    scenario: str,
    shuhei_income_base: float,
    sakura_income_base: float,
    shuhei_ratio: float,
    income: float,
    expense: float,
    monthly_return_rate: float,
    income_growth_rate: float,
    expense_growth_rate: float,
    allocation_enabled: bool,
    cash_buffer_months: float,
    min_cash_balance: float,
    auto_invest_threshold: float,
    nisa_enabled: bool,
    nisa_annual_limit: float,
    invest_beyond_nisa: bool,
    capital_gains_tax_rate: float,
) -> Dict[str, Any]:
    """
    1ヶ月分のシミュレーション処理

    Returns:
        {
            'cash': 更新後の現金,
            'stocks': 更新後の株式,
            'stocks_cost_basis': 更新後の株式簿価,
            'nisa_balance': 更新後のNISA残高,
            'nisa_cost_basis': 更新後のNISA簿価,
            'fire_achieved': FIRE達成フラグ,
            'fire_month': FIRE達成月,
            'current_year': 現在年度,
            'nisa_used_this_year': 今年のNISA投資額,
            'capital_gains_this_year': 今年の譲渡益,
            'prev_year_capital_gains': 前年の譲渡益,
            'monthly_result': 月次結果（DataFrame用）,
            'should_break': ループを終了すべきか
        }
    """
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

    # 収入計算
    _income = _calculate_monthly_income(
        years, date, fire_achieved, fire_month,
        shuhei_income_base, sakura_income_base, income,
        shuhei_ratio, income_growth_rate, config,
    )
    total_income = _income['total_income']
    labor_income = _income['labor_income']
    monthly_pension_income = _income['pension_income']
    monthly_child_allowance = _income['child_allowance']
    shuhei_income_monthly = _income['shuhei_income_monthly']
    sakura_income_monthly = _income['sakura_income_monthly']

    # 支出計算
    _exp = _calculate_monthly_expenses(
        years, config, expense, expense_growth_rate,
        fire_achieved, prev_year_capital_gains
    )
    base_expense = _exp['base_expense']
    monthly_education_expense = _exp['education_expense']
    monthly_mortgage_payment = _exp['mortgage_payment']
    monthly_maintenance_cost = _exp['maintenance_cost']
    monthly_workation_cost = _exp['workation_cost']
    monthly_pension_premium = _exp['pension_premium']
    monthly_health_insurance_premium = _exp['health_insurance_premium']
    expense = _exp['total']

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

    # 3.5. FIRE後は最低現金残高を維持
    if allocation_enabled and fire_achieved:
        if cash < min_cash_balance and stocks > 0:
            shortage = min_cash_balance - cash
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

    # 4. 余剰現金がある場合は自動投資（FIRE前のみ）
    auto_invested = 0
    if allocation_enabled and not fire_achieved:
        _inv = _auto_invest_surplus(
            cash, stocks, stocks_cost_basis, nisa_balance, nisa_cost_basis,
            nisa_used_this_year, expense, cash_buffer_months, min_cash_balance,
            auto_invest_threshold, nisa_enabled, nisa_annual_limit, invest_beyond_nisa,
        )
        cash = _inv['cash']
        stocks = _inv['stocks']
        stocks_cost_basis = _inv['stocks_cost_basis']
        nisa_balance = _inv['nisa_balance']
        nisa_cost_basis = _inv['nisa_cost_basis']
        nisa_used_this_year = _inv['nisa_used_this_year']
        auto_invested = _inv['auto_invested']

    # FIRE達成チェック
    total_assets = cash + stocks
    if not fire_achieved and month > 0:
        annual_pension_premium_for_fire = calculate_national_pension_premium(years, config, fire_achieved=True)
        annual_health_insurance_premium_for_fire = calculate_national_health_insurance_premium(years, config, fire_achieved=True)
        current_annual_expense = (base_expense + monthly_education_expense + monthly_mortgage_payment + monthly_maintenance_cost + monthly_workation_cost) * 12 + annual_pension_premium_for_fire + annual_health_insurance_premium_for_fire

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
    monthly_result = _build_monthly_result(
        date, month, cash, stocks, stocks_cost_basis, nisa_balance,
        total_income, monthly_pension_income, labor_income,
        shuhei_income_monthly, sakura_income_monthly, monthly_child_allowance,
        expense, base_expense, monthly_education_expense,
        monthly_mortgage_payment, monthly_maintenance_cost, monthly_workation_cost,
        monthly_pension_premium, monthly_health_insurance_premium,
        investment_return, auto_invested, capital_gains_tax, fire_achieved, fire_month,
    )

    # 破綻判定
    should_break = (cash + stocks <= _BANKRUPTCY_THRESHOLD)

    return {
        'cash': cash,
        'stocks': stocks,
        'stocks_cost_basis': stocks_cost_basis,
        'nisa_balance': nisa_balance,
        'nisa_cost_basis': nisa_cost_basis,
        'fire_achieved': fire_achieved,
        'fire_month': fire_month,
        'current_year': current_year,
        'nisa_used_this_year': nisa_used_this_year,
        'capital_gains_this_year': capital_gains_this_year,
        'prev_year_capital_gains': prev_year_capital_gains,
        'monthly_result': monthly_result,
        'should_break': should_break,
    }


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

    # 初期化処理
    init = _initialize_future_simulation(
        current_cash, current_stocks, current_assets,
        monthly_income, monthly_expense, config, scenario
    )

    # 初期化結果から変数を取得
    cash = init['cash']
    stocks = init['stocks']
    stocks_cost_basis = init['stocks_cost_basis']
    nisa_balance = init['nisa_balance']
    nisa_cost_basis = init['nisa_cost_basis']

    simulation_months = init['simulation_months']
    monthly_return_rate = init['monthly_return_rate']
    allocation_enabled = init['allocation_enabled']
    cash_buffer_months = init['cash_buffer_months']
    auto_invest_threshold = init['auto_invest_threshold']
    nisa_enabled = init['nisa_enabled']
    nisa_annual_limit = init['nisa_annual_limit']
    invest_beyond_nisa = init['invest_beyond_nisa']
    min_cash_balance = init['min_cash_balance']
    capital_gains_tax_rate = init['capital_gains_tax_rate']

    annual_return_rate = init['annual_return_rate']
    income_growth_rate = init['income_growth_rate']
    expense_growth_rate = init['expense_growth_rate']

    shuhei_ratio = init['shuhei_ratio']
    shuhei_income_base = init['shuhei_income_base']
    sakura_income_base = init['sakura_income_base']
    income = init['income']
    expense = init['expense']

    # シミュレーション結果を格納
    results = []

    # FIRE達成状態
    fire_achieved = False
    fire_month = None

    # 開始日
    current_date = datetime.now()
    current_year = current_date.year
    nisa_used_this_year = 0
    capital_gains_this_year = 0
    prev_year_capital_gains = 0

    # 月次シミュレーション
    for month in range(simulation_months + 1):
        cycle_result = _process_future_monthly_cycle(
            month,
            cash, stocks, stocks_cost_basis, nisa_balance, nisa_cost_basis,
            fire_achieved, fire_month,
            current_date, current_year, nisa_used_this_year,
            capital_gains_this_year, prev_year_capital_gains,
            config, scenario,
            shuhei_income_base, sakura_income_base, shuhei_ratio,
            income, expense,
            monthly_return_rate, income_growth_rate, expense_growth_rate,
            allocation_enabled, cash_buffer_months, min_cash_balance,
            auto_invest_threshold, nisa_enabled, nisa_annual_limit,
            invest_beyond_nisa, capital_gains_tax_rate,
        )

        # 状態を更新
        cash = cycle_result['cash']
        stocks = cycle_result['stocks']
        stocks_cost_basis = cycle_result['stocks_cost_basis']
        nisa_balance = cycle_result['nisa_balance']
        nisa_cost_basis = cycle_result['nisa_cost_basis']
        fire_achieved = cycle_result['fire_achieved']
        fire_month = cycle_result['fire_month']
        current_year = cycle_result['current_year']
        nisa_used_this_year = cycle_result['nisa_used_this_year']
        capital_gains_this_year = cycle_result['capital_gains_this_year']
        prev_year_capital_gains = cycle_result['prev_year_capital_gains']

        # 結果を記録
        results.append(cycle_result['monthly_result'])

        # 破綻判定で終了
        if cycle_result['should_break']:
            break

    df = pd.DataFrame(results)

    return df


def _initialize_withdrawal_simulation(
    initial_assets: float,
    annual_expense: float,
    years: int,
    return_rate: float,
) -> Dict[str, Any]:
    """
    引き出しシミュレーションの初期状態を設定

    Returns:
        初期化済みの設定と状態変数を含む辞書
    """
    return {
        'assets': initial_assets,
        'monthly_base_expense': annual_expense / 12,
        'monthly_return_rate': (1 + return_rate) ** (1/12) - 1,
        'total_months': int(years * 12),
    }


def _process_withdrawal_monthly_cycle(
    month: int,
    assets: float,
    start_year_offset: float,
    annual_expense: float,
    inflation_rate: float,
    monthly_return_rate: float,
    config: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    1ヶ月分の引き出しシミュレーション処理

    Returns:
        {
            'assets': 更新後の資産,
            'should_break': ループを終了すべきか（破綻判定）
        }
    """
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

    # FIRE後の収入（年金受給前のみ: 修平の副収入 + 桜の継続収入）
    monthly_post_fire_income = 0
    if config is not None and monthly_pension_income == 0:
        monthly_post_fire_income = (
            config['simulation'].get('shuhei_post_fire_income', 0)
            + config['simulation'].get('sakura_post_fire_income', 0)
        )

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
    total_expense = (adjusted_base_expense + monthly_education_expense + monthly_mortgage_payment +
                    monthly_maintenance_cost + monthly_workation_cost +
                    monthly_pension_premium + monthly_health_insurance_premium)

    # 運用リターン
    investment_return = assets * monthly_return_rate

    # 資産更新（年金収入、児童手当、FIRE後副収入も考慮）
    assets = assets - total_expense + investment_return + monthly_pension_income + monthly_child_allowance + monthly_post_fire_income

    # 資産が破綻ライン（500万円）以下になったら終了
    should_break = assets <= _BANKRUPTCY_THRESHOLD

    return {
        'assets': assets,
        'should_break': should_break,
    }


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
    # 初期化
    init = _initialize_withdrawal_simulation(initial_assets, annual_expense, years, return_rate)
    assets = init['assets']
    monthly_return_rate = init['monthly_return_rate']
    total_months = init['total_months']

    # 月次シミュレーション
    for month in range(total_months):
        cycle_result = _process_withdrawal_monthly_cycle(
            month, assets, start_year_offset, annual_expense,
            inflation_rate, monthly_return_rate, config,
        )

        # 状態を更新
        assets = cycle_result['assets']

        # 破綻判定
        if cycle_result['should_break']:
            return 0

    # 最終資産も破綻ライン以下なら0を返す
    if assets <= _BANKRUPTCY_THRESHOLD:
        return 0

    return assets


def simulate_with_random_returns(
    current_cash: float,
    current_stocks: float,
    config: Dict[str, Any],
    random_returns: np.ndarray,
    scenario: str = 'standard',
    monthly_income: float = 0,
    monthly_expense: float = 0
) -> pd.DataFrame:
    """
    ランダムリターンを使った全期間資産推移シミュレーション（モンテカルロ用）

    現在から90歳までの全期間をシミュレート：
    - FIRE前: 労働収入あり、自動投資あり、FIREチェックあり
    - FIRE後: 労働収入なし（副収入のみ）、年金収入あり

    シミュレーションは早期終了せず、資産がマイナスになっても90歳まで計算継続。

    Args:
        current_cash: 現在の現金
        current_stocks: 現在の株式
        config: 設定辞書
        random_returns: 月次リターン率の配列（generate_random_returns()で生成）
        scenario: シナリオ名
        monthly_income: 月次労働収入
        monthly_expense: 月次支出

    Returns:
        資産推移のDataFrame（全期間分）
    """
    # 初期化（simulate_future_assets と同様）
    init = _initialize_future_simulation(
        current_cash=current_cash,
        current_stocks=current_stocks,
        current_assets=None,
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        config=config,
        scenario=scenario
    )

    # 状態変数
    cash = init['cash']
    stocks = init['stocks']
    stocks_cost_basis = init['stocks_cost_basis']
    nisa_balance = init['nisa_balance']
    nisa_cost_basis = init['nisa_cost_basis']

    fire_achieved = False
    fire_month = None
    current_date = datetime.now()
    current_year = current_date.year
    nisa_used_this_year = 0
    capital_gains_this_year = 0
    prev_year_capital_gains = 0

    # パラメータ
    shuhei_ratio = init['shuhei_ratio']
    shuhei_income_base = init['shuhei_income_base']
    sakura_income_base = init['sakura_income_base']
    income_growth_rate = init['income_growth_rate']
    expense_growth_rate = init['expense_growth_rate']

    allocation_enabled = init['allocation_enabled']
    cash_buffer_months = init.get('cash_buffer_months', 6)
    min_cash_balance = init.get('min_cash_balance', 1000000)
    auto_invest_threshold = init.get('auto_invest_threshold', 1.5)
    nisa_enabled = init.get('nisa_enabled', True)
    nisa_annual_limit = init.get('nisa_annual_limit', 3600000)
    invest_beyond_nisa = init.get('invest_beyond_nisa', True)
    capital_gains_tax_rate = init.get('capital_gains_tax_rate', 0.20315)

    total_months = len(random_returns)
    results = []

    for month_index in range(total_months):
        # 日付・年数更新
        years = month_index / 12
        date = current_date + relativedelta(months=month_index)

        # 年度管理
        _prev_gains = capital_gains_this_year
        current_year, capital_gains_this_year, year_advanced = _advance_year(
            date.year, current_year, capital_gains_this_year
        )
        if year_advanced:
            prev_year_capital_gains = _prev_gains
            nisa_used_this_year = 0

        # 収入計算
        income_result = _calculate_monthly_income(
            years, date, fire_achieved, fire_month,
            shuhei_income_base, sakura_income_base,
            monthly_income, shuhei_ratio, income_growth_rate, config
        )
        total_income = income_result['total_income']

        # 支出計算
        expense_result = _calculate_monthly_expenses(
            years, config, monthly_expense, expense_growth_rate,
            fire_achieved, prev_year_capital_gains
        )
        total_expense = expense_result['total']

        # 現金に収入加算
        cash += total_income

        # 支出処理
        if cash >= total_expense:
            cash -= total_expense
        else:
            shortage = total_expense - cash
            cash = 0
            # 株売却（税金計算あり）
            sell_result = _sell_stocks_with_tax(
                shortage, stocks, nisa_balance, nisa_cost_basis,
                stocks_cost_basis, capital_gains_tax_rate, allocation_enabled
            )
            stocks = sell_result.stocks
            nisa_balance = sell_result.nisa_balance
            nisa_cost_basis = sell_result.nisa_cost_basis
            stocks_cost_basis = sell_result.stocks_cost_basis
            cash += sell_result.cash_from_taxable
            capital_gains_this_year += sell_result.capital_gain

        # ランダムリターン適用
        monthly_return = random_returns[month_index]
        stocks *= (1 + monthly_return)
        nisa_balance *= (1 + monthly_return)

        # 最低現金残高確保
        if allocation_enabled and cash < min_cash_balance and stocks > 0:
            shortage = min_cash_balance - cash
            sell_result = _sell_stocks_with_tax(
                shortage, stocks, nisa_balance, nisa_cost_basis,
                stocks_cost_basis, capital_gains_tax_rate, allocation_enabled
            )
            stocks = sell_result.stocks
            nisa_balance = sell_result.nisa_balance
            nisa_cost_basis = sell_result.nisa_cost_basis
            stocks_cost_basis = sell_result.stocks_cost_basis
            cash += sell_result.nisa_sold + sell_result.cash_from_taxable
            capital_gains_this_year += sell_result.capital_gain

        # FIRE前の自動投資
        if not fire_achieved and allocation_enabled:
            invest_result = _auto_invest_surplus(
                cash, stocks, stocks_cost_basis, nisa_balance, nisa_cost_basis,
                nisa_used_this_year, total_expense, cash_buffer_months, min_cash_balance,
                auto_invest_threshold, nisa_enabled, nisa_annual_limit, invest_beyond_nisa
            )
            cash = invest_result['cash']
            stocks = invest_result['stocks']
            nisa_balance = invest_result['nisa_balance']
            stocks_cost_basis = invest_result['stocks_cost_basis']
            nisa_cost_basis = invest_result['nisa_cost_basis']
            nisa_used_this_year = invest_result['nisa_used_this_year']

        # 結果記録
        total_assets = cash + stocks
        results.append({
            'month': month_index,
            'year_offset': years,
            'date': date,
            'assets': total_assets,
            'cash': cash,
            'stocks': stocks,
            'nisa_balance': nisa_balance,
            'fire_achieved': fire_achieved,
            'monthly_return': monthly_return
        })

        # FIRE判定（まだ達成していない場合のみ）
        if not fire_achieved and month_index > 0:
            # FIRE判定（4%ルール + 安全マージン500万円）
            fire_target = total_expense * 12 * 25 + _BANKRUPTCY_THRESHOLD
            if total_assets >= fire_target:
                fire_achieved = True
                fire_month = month_index

    return pd.DataFrame(results)


def run_monte_carlo_simulation(
    current_cash: float,
    current_stocks: float,
    config: Dict[str, Any],
    scenario: str = 'standard',
    iterations: int = 1000,
    monthly_income: float = 0,
    monthly_expense: float = 0
) -> Dict[str, Any]:
    """
    モンテカルロシミュレーションを実行し、FIRE成功確率を計算

    Option 1実装: FIRE達成まで固定リターン、FIRE後のみランダムリターン
    - ベースシミュレーションでFIRE達成時点の状態を取得
    - その時点からFIRE後の期間のみランダムリターンでシミュレート
    - 「計画通りFIRE達成後の成功確率」を評価

    Args:
        current_cash: 現在の現金
        current_stocks: 現在の株式
        config: 設定辞書
        scenario: シナリオ名
        iterations: シミュレーション回数
        monthly_income: 月次労働収入
        monthly_expense: 月次支出

    Returns:
        {
            'success_rate': 成功確率（0-1）,
            'median_final_assets': 最終資産の中央値,
            'percentile_10': 下位10%の最終資産,
            'percentile_90': 上位10%の最終資産,
            'mean_final_assets': 最終資産の平均値,
            'all_results': 全イテレーションの結果リスト
        }
    """
    print(f"Running Monte Carlo simulation ({iterations} iterations)...")

    # ステップ1: ベースシミュレーション（固定リターン）でFIRE達成時点を取得
    print("  Step 1: Running base simulation to find FIRE achievement point...")
    base_df = simulate_future_assets(
        current_cash=current_cash,
        current_stocks=current_stocks,
        config=config,
        scenario=scenario,
        monthly_income=monthly_income,
        monthly_expense=monthly_expense
    )

    # FIRE達成時点の状態を取得
    fire_rows = base_df[base_df['fire_achieved'] == True]
    if len(fire_rows) == 0:
        raise ValueError("FIRE not achieved in base simulation. Cannot run Monte Carlo.")

    fire_row = fire_rows.iloc[0]
    fire_month = int(fire_row['fire_month'])
    fire_cash = fire_row['cash']
    fire_stocks = fire_row['stocks']
    fire_nisa = fire_row['nisa_balance']
    fire_nisa_cost = fire_row.get('nisa_cost_basis', fire_nisa)  # デフォルトは簿価=時価
    fire_stocks_cost = fire_row['stocks_cost_basis']
    years_offset = fire_month / 12

    print(f"  FIRE achieved at month {fire_month} (age {config['simulation'].get('start_age', 35) + years_offset:.1f})")
    print(f"  Assets at FIRE: JPY{fire_cash + fire_stocks:,.0f}")

    # ステップ2: FIRE後の期間を計算
    life_expectancy = config['simulation'].get('life_expectancy', 90)
    start_age = config['simulation'].get('start_age', 35)
    fire_age = start_age + years_offset
    remaining_years = life_expectancy - fire_age
    remaining_months = int(remaining_years * 12)

    print(f"  Simulating {remaining_months} months post-FIRE with random returns...")

    # ステップ3: モンテカルロシミュレーション（FIRE後のみ）
    results = []
    all_timeseries = []  # 各イテレーションの月ごとデータ
    params = config['simulation'][scenario]
    mc_config = config['simulation'].get('monte_carlo', {})
    return_std_dev = mc_config.get('return_std_dev', 0.15)

    for i in range(iterations):
        # 進捗表示
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i + 1}/{iterations} iterations completed")

        # FIRE後の期間分のランダムリターンを生成
        random_returns = generate_random_returns(
            params['annual_return_rate'],
            return_std_dev,
            remaining_months,
            random_seed=i
        )

        # FIRE後シミュレーション実行（月ごとデータを取得）
        timeseries = _simulate_post_fire_with_random_returns(
            current_cash=fire_cash,
            current_stocks=fire_stocks,
            years_offset=years_offset,
            config=config,
            scenario=scenario,
            random_returns=random_returns,
            nisa_balance=fire_nisa,
            nisa_cost_basis=fire_nisa_cost,
            stocks_cost_basis=fire_stocks_cost,
            return_timeseries=True
        )

        final_assets = timeseries[-1] if len(timeseries) > 0 else 0
        all_timeseries.append(timeseries)

        # 成功判定: 資産がゼロ以上なら成功
        success = final_assets > 0

        results.append({
            'final_assets': final_assets,
            'success': success
        })

    # 統計情報を計算
    success_count = sum(1 for r in results if r['success'])
    success_rate = success_count / iterations
    final_assets_list = [r['final_assets'] for r in results]

    # 月ごとの統計を計算（パーセンタイルを使用）
    # 対数正規分布は非対称なので、median±σ ではなくパーセンタイルを使う
    all_timeseries_array = np.array(all_timeseries)  # shape: (iterations, months)
    monthly_p50 = np.percentile(all_timeseries_array, 50, axis=0)   # 中央値
    monthly_p025 = np.percentile(all_timeseries_array, 2.5, axis=0) # 2σ下限（約95%信頼区間）
    monthly_p16 = np.percentile(all_timeseries_array, 16, axis=0)   # 1σ下限（約68%信頼区間）
    monthly_p84 = np.percentile(all_timeseries_array, 84, axis=0)   # 1σ上限
    monthly_p975 = np.percentile(all_timeseries_array, 97.5, axis=0) # 2σ上限

    print(f"[OK] Monte Carlo simulation complete!")
    print(f"  Success rate: {success_rate*100:.1f}%")
    print(f"  Median final assets: JPY{np.median(final_assets_list):,.0f}")

    return {
        'success_rate': success_rate,
        'median_final_assets': np.median(final_assets_list),
        'mean_final_assets': np.mean(final_assets_list),
        'percentile_10': np.percentile(final_assets_list, 10),
        'percentile_90': np.percentile(final_assets_list, 90),
        'all_results': results,
        'fire_month': fire_month,  # FIRE達成時の月数
        'monthly_p50': monthly_p50,     # 月ごとの中央値
        'monthly_p025': monthly_p025,   # 月ごとの2.5パーセンタイル（2σ下限相当）
        'monthly_p16': monthly_p16,     # 月ごとの16パーセンタイル（1σ下限相当）
        'monthly_p84': monthly_p84,     # 月ごとの84パーセンタイル（1σ上限相当）
        'monthly_p975': monthly_p975    # 月ごとの97.5パーセンタイル（2σ上限相当）
    }


