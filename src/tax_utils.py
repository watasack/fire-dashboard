"""
税金・社会保険料の簡易計算ユーティリティ。

主な用途: 年収（税引き前）→ 手取り月収 の変換。
"""


def gross_to_net_monthly(gross_annual_man: float, employment_type: str) -> float:
    """税引き前年収（万円）→ 手取り月収（万円）の簡易変換。

    社会保険料・所得税・住民税を概算で差し引く。
    正確な税額計算ではなく、シミュレーション入力用の目安値として使用する。

    Args:
        gross_annual_man: 税引き前年収（万円）
        employment_type:  "会社員" | "個人事業主" | "専業主夫" | "専業主婦"

    Returns:
        手取り月収（万円）
    """
    if employment_type in ("専業主夫", "専業主婦") or gross_annual_man <= 0:
        return 0.0

    gross_annual = gross_annual_man * 10000  # 円換算

    if employment_type == "会社員":
        # 社会保険料（健康保険 + 厚生年金 + 雇用保険の合計）
        social = gross_annual * 0.148
        # 給与所得控除
        deduction = _kyuyo_shotoku_kojo(gross_annual)
        # 課税所得 = 年収 - 社会保険料 - 給与所得控除 - 基礎控除（48万円）
        taxable = max(0.0, gross_annual - social - deduction - 480_000)
        income_tax = _shotoku_zei(taxable)
        residence_tax = taxable * 0.10
        net_annual = gross_annual - social - income_tax - residence_tax

    elif employment_type == "個人事業主":
        # 国民健康保険 + 国民年金（概算）
        social = min(gross_annual * 0.15, 1_000_000)
        # 事業所得控除（青色申告特別控除 65万円相当を簡易計上）
        deduction = gross_annual * 0.20 + 650_000
        taxable = max(0.0, gross_annual - social - deduction - 480_000)
        income_tax = _shotoku_zei(taxable)
        residence_tax = taxable * 0.10
        net_annual = gross_annual - social - income_tax - residence_tax

    else:
        net_annual = 0.0

    return max(0.0, (net_annual / 12) / 10000)  # 手取り月収（万円）


def _kyuyo_shotoku_kojo(gross: float) -> float:
    """給与所得控除を返す（2020年以降の税制）。

    Args:
        gross: 税引き前年収（円）

    Returns:
        給与所得控除額（円）
    """
    if gross <= 1_625_000:
        return 550_000
    if gross <= 1_800_000:
        return gross * 0.4 - 100_000
    if gross <= 3_600_000:
        return gross * 0.3 + 80_000
    if gross <= 6_600_000:
        return gross * 0.2 + 440_000
    if gross <= 8_500_000:
        return gross * 0.1 + 1_100_000
    return 1_950_000


def _shotoku_zei(taxable: float) -> float:
    """所得税を速算表で計算する。

    Args:
        taxable: 課税所得（円）

    Returns:
        所得税額（円）
    """
    brackets = [
        (1_950_000,      0.05,       0),
        (3_300_000,      0.10,  97_500),
        (6_950_000,      0.20, 427_500),
        (9_000_000,      0.23, 636_000),
        (18_000_000,     0.33, 1_536_000),
        (40_000_000,     0.40, 2_796_000),
        (float("inf"),   0.45, 4_796_000),
    ]
    for limit, rate, deduction in brackets:
        if taxable <= limit:
            return max(0.0, taxable * rate - deduction)
    return taxable * 0.45 - 4_796_000


def _calc_kokuho_annual(income: float) -> float:
    """国民健康保険料の簡易計算（単身世帯・全国平均ベース）。

    医療分 + 後期高齢者支援分 + 介護分（40〜65歳）を計上。
    上限: 医療106万 + 後期支援24万 + 介護17万。
    自治体によって異なるが、全国平均水準で推計。

    Args:
        income: 所得（円）

    Returns:
        年間国民健康保険料（円）
    """
    income_deducted = max(0, income - 430_000)
    iryou = income_deducted * 0.074 + 43_000   # 医療分（所得割 + 均等割）
    kouki = income_deducted * 0.025 + 15_000   # 後期高齢者支援分
    kaigo = income_deducted * 0.017 + 10_000   # 介護分（40〜64歳）
    total = min(iryou, 1_060_000) + min(kouki, 240_000) + min(kaigo, 170_000)
    return total


def nisa_tax_benefit_per_month(nisa_balance: float, monthly_return_rate: float) -> float:
    """NISA 非課税メリットの月次等価額。

    課税口座なら運用益に 20.315% の税がかかるが、NISA はかからない。
    その差分を月次の節税額として返す。

    Args:
        nisa_balance: NISA残高（円）
        monthly_return_rate: 月次リターン率（例: 0.004 for 年率約5%）

    Returns:
        月次節税額相当（円）
    """
    return nisa_balance * monthly_return_rate * 0.20315


def calc_post_fire_monthly_costs(
    pre_fire_annual_income: float,
    living_expenses: float,
    year_since_fire: int,
    age_h: float,
) -> dict:
    """FIRE後の追加税負担（月額）を返す。

    フェーズA (year_since_fire == 1): 前年給与収入をベースに国保算定（スパイク）。
    フェーズB (year_since_fire >= 2): 資産売却額（≒生活費の60%）をベースに算定。

    Args:
        pre_fire_annual_income: 退職前の世帯年収（円）
        living_expenses: 年間生活費（円）
        year_since_fire: FIRE後何年目か（1始まり）
        age_h: 夫の年齢

    Returns:
        {"kokuho": float, "nenkin": float, "total": float}  # 月額（円）
    """
    if year_since_fire <= 1:
        # 国保スパイク: 前年給与収入を基準に算定
        kokuho_annual = _calc_kokuho_annual(pre_fire_annual_income)
    else:
        # 2年目以降: 資産売却額（≒生活費）を収入として算定
        # 生活費の60%を特定口座から引き出しと仮定
        estimated_income = living_expenses * 0.6
        kokuho_annual = _calc_kokuho_annual(estimated_income)

    # 国民年金保険料（60歳未満の場合のみ）
    # 2026年度の第1号被保険者保険料
    nenkin_monthly = 16_980 if age_h < 60 else 0

    return {
        "kokuho": kokuho_annual / 12,
        "nenkin": nenkin_monthly,
        "total": kokuho_annual / 12 + nenkin_monthly,
    }
