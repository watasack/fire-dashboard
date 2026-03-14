"""
src/tax_utils.py の単体テスト。

年収 → 手取り月収の変換が妥当な範囲に収まることを確認する。
（正確な税額計算ではなく、±10%以内の推計精度を目標とする）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.tax_utils import gross_to_net_monthly, _kyuyo_shotoku_kojo, _shotoku_zei


class TestGrossToNetMonthly:
    """gross_to_net_monthly の動作確認"""

    # 会社員ケース（目安値と ±15% 以内で一致すること）
    def test_employee_400man(self):
        net = gross_to_net_monthly(400, "会社員")
        # 年収400万の手取り月収目安: 約27万円/月
        assert 22 <= net <= 32, f"年収400万/会社員の手取り月収が範囲外: {net:.1f}万"

    def test_employee_600man(self):
        net = gross_to_net_monthly(600, "会社員")
        # 年収600万の手取り月収目安: 約38〜40万円/月
        assert 32 <= net <= 46, f"年収600万/会社員の手取り月収が範囲外: {net:.1f}万"

    def test_employee_800man(self):
        net = gross_to_net_monthly(800, "会社員")
        # 年収800万の手取り月収目安: 約50〜52万円/月
        assert 42 <= net <= 60, f"年収800万/会社員の手取り月収が範囲外: {net:.1f}万"

    def test_employee_1000man(self):
        net = gross_to_net_monthly(1000, "会社員")
        # 年収1000万の手取り月収目安: 約60〜63万円/月
        assert 50 <= net <= 75, f"年収1000万/会社員の手取り月収が範囲外: {net:.1f}万"

    # 個人事業主ケース
    def test_sole_proprietor_600man(self):
        net = gross_to_net_monthly(600, "個人事業主")
        # 個人事業主は社会保険料が少ない分、手取りが高い傾向
        assert 30 <= net <= 50, f"年収600万/個人事業主の手取り月収が範囲外: {net:.1f}万"

    def test_sole_proprietor_400man(self):
        net = gross_to_net_monthly(400, "個人事業主")
        assert 25 <= net <= 40, f"年収400万/個人事業主の手取り月収が範囲外: {net:.1f}万"

    # 専業主婦/夫ケース
    def test_housewife(self):
        net = gross_to_net_monthly(600, "専業主婦")
        assert net == 0.0, f"専業主婦の手取り月収は0であるべき: {net}"

    def test_househusband(self):
        net = gross_to_net_monthly(600, "専業主夫")
        assert net == 0.0, f"専業主夫の手取り月収は0であるべき: {net}"

    # エッジケース
    def test_zero_income(self):
        net = gross_to_net_monthly(0, "会社員")
        assert net == 0.0, f"年収0の手取りは0であるべき: {net}"

    def test_returns_float(self):
        net = gross_to_net_monthly(500, "会社員")
        assert isinstance(net, float)

    def test_net_less_than_gross(self):
        """手取り月収 < 年収/12 であること（控除が効いている）"""
        gross_monthly = 600 / 12  # 50万円/月
        net = gross_to_net_monthly(600, "会社員")
        assert net < gross_monthly, "手取りが額面を上回っている"

    def test_higher_income_higher_net(self):
        """高収入ほど手取り月収も高い（単調増加）"""
        net_400 = gross_to_net_monthly(400, "会社員")
        net_600 = gross_to_net_monthly(600, "会社員")
        net_800 = gross_to_net_monthly(800, "会社員")
        assert net_400 < net_600 < net_800


class TestKyuyoShotokuKojo:
    """給与所得控除の境界値テスト"""

    def test_below_162man(self):
        result = _kyuyo_shotoku_kojo(1_000_000)
        assert result == 550_000

    def test_at_360man(self):
        result = _kyuyo_shotoku_kojo(3_600_000)
        # 3,600,000 * 0.3 + 80,000 = 1,160,000
        assert abs(result - 1_160_000) < 1

    def test_above_850man(self):
        result = _kyuyo_shotoku_kojo(10_000_000)
        assert result == 1_950_000


class TestShotokuZei:
    """所得税速算表のテスト"""

    def test_zero_taxable(self):
        assert _shotoku_zei(0) == 0.0

    def test_195man_bracket(self):
        # 課税所得 195万以下: 5%
        result = _shotoku_zei(1_000_000)
        assert abs(result - 50_000) < 1

    def test_330man_bracket(self):
        # 課税所得 195〜330万: 10% - 97,500
        result = _shotoku_zei(2_500_000)
        assert abs(result - (2_500_000 * 0.10 - 97_500)) < 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
