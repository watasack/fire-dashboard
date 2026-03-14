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
