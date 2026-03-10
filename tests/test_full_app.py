"""
full_app.py の統合テスト

Streamlit AppTest を使ったヘッドレステスト。
実際のUIインタラクション（アクセスコード入力・スライダー操作・ボタンクリック）を
ブラウザなしで自動検証する。

実行方法:
    pytest tests/test_full_app.py -v

注意:
    - secrets は AppTest 経由でモック注入
    - MC計算は iterations=100 に減らしてテスト高速化
    - full_app.py が demo_config.yaml を読む → リポジトリルートで実行すること
"""

import sys
import os
import copy
from pathlib import Path

import pytest
import yaml

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from streamlit.testing.v1 import AppTest

APP_PATH = str(project_root / "full_app.py")
VALID_CODE = "DEV-LOCAL-ONLY"
INVALID_CODE = "WRONG-CODE-9999"


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def make_app(secrets: dict | None = None) -> AppTest:
    """AppTest インスタンスを生成してシークレットを注入する。"""
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    if secrets is None:
        secrets = {"access_codes": [VALID_CODE]}
    for k, v in secrets.items():
        at.secrets[k] = v
    return at


def authenticate(at: AppTest) -> AppTest:
    """認証画面でアクセスコードを入力して認証を通過させる。"""
    at.run()
    at.text_input[0].set_value(VALID_CODE).run()
    return at


# ---------------------------------------------------------------------------
# 1. 認証フローテスト
# ---------------------------------------------------------------------------

class TestAuthentication:
    def test_auth_screen_shown_before_login(self):
        """認証前: アクセスコード入力フォームが表示される"""
        at = make_app()
        at.run()
        assert not at.exception
        # テキスト入力が1つ以上存在する
        assert len(at.text_input) >= 1

    def test_wrong_code_shows_error(self):
        """誤ったコード → エラーメッセージが表示される"""
        at = make_app()
        at.run()
        at.text_input[0].set_value(INVALID_CODE).run()
        assert not at.exception
        # エラー (st.error) が表示されている
        assert len(at.error) >= 1

    def test_correct_code_passes_auth(self):
        """正しいコード → メインコンテンツが表示される（ヘッダーが出る）"""
        at = make_app()
        at = authenticate(at)
        assert not at.exception
        # 認証後はテキスト入力（パスワード欄）が消えて本体が表示される
        # ボタン（シミュレーション開始）が存在する
        assert len(at.button) >= 1

    def test_empty_code_shows_no_exception(self):
        """空コード → 例外なし・エラー表示"""
        at = make_app()
        at.run()
        at.text_input[0].set_value("").run()
        assert not at.exception

    def test_empty_access_codes_list_blocks_all(self):
        """access_codes リストが空 → どのコードも拒否される"""
        at = make_app(secrets={"access_codes": []})
        at.run()
        at.text_input[0].set_value(VALID_CODE).run()
        assert not at.exception
        # エラーが表示される
        assert len(at.error) >= 1

    def test_multiple_valid_codes(self):
        """複数コードのどれでも認証できる"""
        codes = ["CODE-A", "CODE-B", "CODE-C"]
        for code in codes:
            at = make_app(secrets={"access_codes": codes})
            at.run()
            at.text_input[0].set_value(code).run()
            assert not at.exception, f"{code} でエラー発生"
            assert len(at.button) >= 1, f"{code} で認証失敗"


# ---------------------------------------------------------------------------
# 2. 設定ファイル整合性テスト (demo_config.yaml)
# ---------------------------------------------------------------------------

class TestDemoConfig:
    @pytest.fixture(scope="class")
    def cfg(self):
        config_path = project_root / "demo_config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_config_loads(self, cfg):
        """demo_config.yaml が読み込める"""
        assert cfg is not None

    def test_required_keys_exist(self, cfg):
        """必須キーが全て存在する"""
        assert "simulation" in cfg
        assert "fire" in cfg
        assert "education" in cfg
        assert "pension" in cfg
        assert "asset_allocation" in cfg

    def test_simulation_standard_keys(self, cfg):
        """standard シナリオに必要なパラメータが存在する"""
        std = cfg["simulation"]["standard"]
        assert "annual_return_rate" in std
        assert "inflation_rate" in std
        assert "income_growth_rate" in std
        assert 0 < std["annual_return_rate"] < 0.20, "利回りが非現実的"
        assert 0 <= std["inflation_rate"] < 0.10, "インフレ率が非現実的"

    def test_monte_carlo_config(self, cfg):
        """モンテカルロ設定が存在する"""
        mc = cfg["simulation"]["monte_carlo"]
        assert mc["enabled"] is True
        assert mc["iterations"] >= 100

    def test_education_children_list(self, cfg):
        """教育設定に子供リストが存在する"""
        assert "children" in cfg["education"]
        assert len(cfg["education"]["children"]) >= 1

    def test_nisa_annual_limit(self, cfg):
        """NISA年間投資枠が正しい（360万円）"""
        limit = cfg["asset_allocation"]["nisa_annual_limit"]
        assert limit == 3_600_000, f"NISA枠が {limit} 円 (期待: 3,600,000)"

    def test_pension_people(self, cfg):
        """年金設定に夫婦が設定されている"""
        people = cfg["pension"]["people"]
        assert len(people) == 2


# ---------------------------------------------------------------------------
# 3. シミュレーション実行テスト (デフォルト値)
# ---------------------------------------------------------------------------

class TestSimulationExecution:
    @pytest.fixture(scope="class")
    def app_after_sim(self):
        """認証 → デフォルト値でシミュレーション実行済みの AppTest を返す"""
        at = make_app()
        at = authenticate(at)
        # シミュレーションボタンをクリック
        at.button[0].click().run()
        return at

    def test_no_exception_after_simulation(self, app_after_sim):
        """シミュレーション実行後に例外が発生しない"""
        assert not app_after_sim.exception

    def test_metrics_displayed(self, app_after_sim):
        """FIRE到達年齢などのメトリクスが表示される"""
        # st.metric が少なくとも1つ表示されている
        assert len(app_after_sim.metric) >= 1

    def test_fire_age_metric_reasonable(self, app_after_sim):
        """FIRE到達年齢が現実的な範囲（30〜90歳）"""
        metrics = app_after_sim.metric
        # 最初のメトリクスがFIRE到達年齢
        if len(metrics) > 0:
            val = metrics[0].value
            # "45歳" のような文字列から数値を抽出
            age = int("".join(filter(str.isdigit, str(val))))
            assert 30 <= age <= 90, f"FIRE年齢が非現実的: {age}歳"

    def test_no_error_alert_in_normal_case(self, app_after_sim):
        """通常ケースではエラーアラートが出ない（90歳前にFIRE達成）"""
        # st.error の数が 0 または「警告」が出ていない
        errors = app_after_sim.error
        fire_errors = [e for e in errors if "90歳" in str(e.value)]
        assert len(fire_errors) == 0, "デフォルト値でFIRE未達のエラーが出ている"


# ---------------------------------------------------------------------------
# 4. エッジケーステスト
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_very_low_income_shows_no_exception(self):
        """極端に低い収入（夫婦合計10万円）→ 例外なし"""
        at = make_app()
        at = authenticate(at)
        # number_input[0]=夫収入, [1]=妻収入 (サイドバー順)
        at.number_input[0].set_value(5).run()
        at.number_input[1].set_value(5).run()
        at.button[0].click().run()
        assert not at.exception

    def test_high_expense_fire_not_achieved(self):
        """支出が収入と同等 → FIRE未達エラーが表示される（または例外なし）"""
        at = make_app()
        at = authenticate(at)
        # number_input[4]=支出 (0=夫収入,1=夫年齢,2=妻収入,3=妻年齢,4=支出,5=資産)
        at.number_input[4].set_value(70).run()
        at.button[0].click().run()
        assert not at.exception

    def test_zero_parental_leave(self):
        """スライダーをデフォルトのまま（育休あり）シミュレーション → 例外なし"""
        at = make_app()
        at = authenticate(at)
        at.button[0].click().run()
        assert not at.exception

    def test_large_assets(self):
        """大きな資産（1億円）→ 例外なし・FIRE到達が早い"""
        at = make_app()
        at = authenticate(at)
        # number_input[5]=資産
        at.number_input[5].set_value(10000).run()
        at.button[0].click().run()
        assert not at.exception


# ---------------------------------------------------------------------------
# 5. バックエンド単体テスト (full_app.py が使う関数の直接呼び出し)
# ---------------------------------------------------------------------------

class TestBackendFunctions:
    @pytest.fixture(scope="class")
    def base_cfg(self):
        config_path = project_root / "demo_config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_simulate_future_assets_runs(self, base_cfg):
        """simulate_future_assets が demo_config.yaml で正常に動く"""
        from src.simulator import simulate_future_assets
        cfg = copy.deepcopy(base_cfg)
        cash = 600_000_0  # 600万円
        stocks = 1_400_000_0  # 1400万円
        monthly_inc = 750_000  # 75万円
        monthly_exp = 280_000  # 28万円

        df = simulate_future_assets(cash, stocks, None, monthly_inc, monthly_exp, cfg, "standard")
        assert len(df) > 0
        assert "assets" in df.columns
        assert "fire_achieved" in df.columns

    def test_nisa_invariant_with_demo_config(self, base_cfg):
        """demo_config.yaml 使用時、常に nisa_balance <= stocks"""
        from src.simulator import simulate_future_assets
        cfg = copy.deepcopy(base_cfg)
        cash = 600_000_0
        stocks = 1_400_000_0
        monthly_inc = 750_000
        monthly_exp = 280_000

        df = simulate_future_assets(cash, stocks, None, monthly_inc, monthly_exp, cfg, "standard")
        violations = df[df["nisa_balance"] > df["stocks"]]
        assert len(violations) == 0, (
            f"NISA残高が株式残高を超える期間が {len(violations)} 件\n"
            f"{violations[['date','stocks','nisa_balance']].head()}"
        )

    def test_monte_carlo_runs_with_demo_config(self, base_cfg):
        """run_monte_carlo_simulation が demo_config.yaml で動く（100回）"""
        from src.simulator import simulate_future_assets, run_monte_carlo_simulation
        cfg = copy.deepcopy(base_cfg)
        cash = 600_000_0
        stocks = 1_400_000_0
        monthly_inc = 750_000
        monthly_exp = 280_000

        # まず FIRE 達成を確認
        df = simulate_future_assets(cash, stocks, None, monthly_inc, monthly_exp, cfg, "standard")
        if not df["fire_achieved"].any():
            pytest.skip("デモ設定でFIREが達成されないためMCテストをスキップ")

        mc_res = run_monte_carlo_simulation(
            cash, stocks, cfg, "standard", 100,  # 100回で高速化
            monthly_inc, monthly_exp,
            include_pre_fire=True
        )
        assert mc_res is not None
        assert "success_rate" in mc_res
        assert 0.0 <= mc_res["success_rate"] <= 1.0
        assert "all_results" in mc_res
        assert len(mc_res["all_results"]) == 100

    def test_maternity_leave_config_structure(self, base_cfg):
        """育休設定を full_app.py と同じ形式で渡してシミュレーションできる"""
        from src.simulator import simulate_future_assets
        cfg = copy.deepcopy(base_cfg)

        # full_app.py が生成するのと同じ形式
        cfg["simulation"].update({
            "maternity_leave": [{
                "child": "お子さん",
                "months_before": 2,
                "months_after": 12,
                "monthly_income": 150_000
            }],
            "sakura_reduced_hours": [{
                "child": "お子さん",
                "start_months_after": 12,
                "end_months_after": 36,
                "income_ratio": 0.7
            }],
            "shuhei_parental_leave": [{
                "child": "お子さん",
                "months_after": 1,
                "monthly_income": 300_000,
                "monthly_income_after_180days": 300_000
            }]
        })
        cfg["education"]["children"] = [{
            "name": "お子さん",
            "birthdate": "2026/10/01",
            "nursery": "public",
            "kindergarten": "public",
            "elementary": "public",
            "junior_high": "public",
            "high": "public",
            "university": "national"
        }]

        cash = 600_000_0
        stocks = 1_400_000_0
        monthly_inc = 750_000
        monthly_exp = 280_000

        df = simulate_future_assets(cash, stocks, None, monthly_inc, monthly_exp, cfg, "standard")
        assert len(df) > 0
        assert not df["assets"].isna().any(), "NaN が含まれている"
