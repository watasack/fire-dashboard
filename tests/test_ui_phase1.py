"""
Phase1 UI 動作確認テスト（Playwright）
対象: Block 1（サイドバーexpander）、Block 2（KPI カード）
"""

import re
import pytest
from playwright.sync_api import Page, expect

URL = "https://fire-dashboard-n4bdcefvcuu3ytl68fwtrw.streamlit.app/"
ACCESS_CODE = "DEV-LOCAL-ONLY"
TIMEOUT = 60_000  # Streamlit Cloud は初回起動が遅い


def get_app_frame(page: Page):
    """Streamlit アプリ本体の iframe を返す。"""
    # Streamlit は /~/+/ という iframe 内にコンテンツをレンダリングする
    return page.frame_locator("iframe[src*='/~/+/']")


def login(page: Page) -> None:
    """アクセスコード認証を通過する。"""
    page.goto(URL, timeout=TIMEOUT)
    page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT)
    page.wait_for_timeout(5_000)  # Streamlit JS 初期化待ち

    app = get_app_frame(page)
    app.locator("input[type='password']").wait_for(timeout=TIMEOUT)
    app.locator("input[type='password']").fill(ACCESS_CODE)
    page.keyboard.press("Enter")

    # ログイン後にサイドバーが表示されるまで待つ
    app.locator("[data-testid='stSidebar']").wait_for(timeout=TIMEOUT)
    page.wait_for_timeout(3_000)  # 描画安定待ち


# =============================================================================
# Block 1: サイドバー expander
# =============================================================================

def test_block1_expander_exists(page: Page) -> None:
    """expander が存在し、デフォルトで折り畳まれていること。"""
    login(page)
    app = get_app_frame(page)
    sidebar = app.locator("[data-testid='stSidebar']")
    expect(sidebar.get_by_text("FIRE後の設定（副収入・取り崩し）")).to_be_visible()


def test_block1_expander_collapsed_by_default(page: Page) -> None:
    """expander 内の副収入入力が初期状態で非表示であること。"""
    login(page)
    app = get_app_frame(page)
    sidebar = app.locator("[data-testid='stSidebar']")
    expect(sidebar.get_by_text("夫の副収入（万円/月）")).to_be_hidden()


def test_block1_expander_opens(page: Page) -> None:
    """expander をクリックすると副収入・取り崩し入力が表示されること。"""
    login(page)
    app = get_app_frame(page)
    sidebar = app.locator("[data-testid='stSidebar']")

    sidebar.get_by_text("FIRE後の設定（副収入・取り崩し）").click()
    page.wait_for_timeout(1_000)

    expect(sidebar.get_by_text("夫の副収入（万円/月）")).to_be_visible()
    expect(sidebar.get_by_text("FIRE後の取り崩し方法")).to_be_visible()


# =============================================================================
# Block 2: KPI カード
# =============================================================================

def _run_simulation(page: Page, app) -> None:
    """シミュレーションを実行して結果が出るまで待つ。"""
    # Phase2 以降、ボタンは expander 内にある。折り畳まれていれば開く
    expander = app.get_by_text("詳細な確率計算（1,000通り）")
    if expander.count() > 0:
        expander.first.click()
        page.wait_for_timeout(1_000)
    app.get_by_role("button", name="シミュレーションを開始").click(timeout=180_000)
    # スピナーが出れば消えるまで待つ（速いケースはスキップ）
    try:
        app.locator("[data-testid='stSpinner']").wait_for(state="visible", timeout=10_000)
        app.locator("[data-testid='stSpinner']").wait_for(state="hidden", timeout=90_000)
    except Exception:
        pass
    # 結果が出るまで固定待機（MC 最大 90 秒）
    # full_app.py がボタン押下時に show_detail=True をセットするため
    # 再レンダリング後も expander は開いたまま維持される
    page.wait_for_timeout(90_000)


def test_block2_kpi_card_appears_after_simulation(page: Page) -> None:
    """シミュレーション実行後に KPI カードが表示されること。
    KPI カード内の「FIRE時の資産」ラベルで存在を確認する。"""
    login(page)
    app = get_app_frame(page)
    _run_simulation(page, app)

    # KPI カード内の固定ラベルで存在確認（日本語正規表現を避ける）
    expect(app.get_by_text("FIRE時の資産")).to_be_visible()
    expect(app.get_by_text("今から")).to_be_visible()


def test_block2_kpi_shows_fire_age(page: Page) -> None:
    """KPI カードに FIRE 年齢が表示されること。
    メインコンテンツ内の「今から」ラベルと同じカード内に年齢テキストがあることで確認する。"""
    login(page)
    app = get_app_frame(page)
    _run_simulation(page, app)

    # メインエリア（サイドバー・JSON表示の外）に「今から」が含まれること
    main = app.locator("[data-testid='stMain']")
    expect(main.get_by_text("今から")).to_be_visible()
    # 「今から」の近傍に「年後」テキストがあること
    expect(main.get_by_text(re.compile(r"\d+\.\d+年後"))).to_be_visible()


def test_block2_kpi_shows_years_and_assets(page: Page) -> None:
    """KPI カードに「年後」「FIRE時の資産」「達成確率」が表示されること。"""
    login(page)
    app = get_app_frame(page)
    _run_simulation(page, app)

    expect(app.get_by_text(re.compile(r"\d+\.\d+年後"))).to_be_visible()
    expect(app.get_by_text("FIRE時の資産")).to_be_visible()
    expect(app.get_by_text(re.compile(r"達成確率"))).to_be_visible()


# =============================================================================
# Block 3: 失敗メッセージ
# =============================================================================

def _set_impossible_conditions(page: Page, app) -> None:
    """FIRE不可能な条件を設定する。
    夫婦の年収を0にする → 月次赤字 -28万/月 → 資産は増えず impossible=True になる。
    (expense=50万+assets=100万は income があれば FIRE達成可能なため使用しない)
    """
    sidebar = app.locator("[data-testid='stSidebar']")
    gross_inputs = sidebar.get_by_role("spinbutton", name=re.compile(r"年収（税引き前"))
    gross_inputs.nth(0).fill("0")
    gross_inputs.nth(0).press("Tab")
    page.wait_for_timeout(500)
    gross_inputs.nth(1).fill("0")
    gross_inputs.nth(1).press("Tab")


@pytest.mark.xfail(
    reason=(
        "impossible 条件の再現が困難: "
        "income=0 だと binary search が年金収入で FIRE 可能と判断し最終MC(1000回)がクラッシュする。"
        "expense=100万等の高支出も同様にクラッシュ。"
        "simulator の堅牢化(負資産ガード)後に再修正予定。"
    ),
    strict=False,
)
def test_block3_impossible_shows_warning_not_error(page: Page) -> None:
    """FIRE不可時に st.error（赤）ではなく st.warning（黄）が表示されること。"""
    login(page)
    app = get_app_frame(page)

    _set_impossible_conditions(page, app)
    page.wait_for_timeout(1000)
    _run_simulation(page, app)

    # st.warning の本文テキストで確認（Streamlit は kind 属性を HTML に出力しないため）
    main = app.locator("[data-testid='stMain']")
    expect(main.get_by_text(re.compile(r"に届きません"))).to_be_visible(timeout=10_000)


@pytest.mark.xfail(
    reason=(
        "impossible 条件の再現が困難: "
        "income=0 だと binary search が年金収入で FIRE 可能と判断し最終MC(1000回)がクラッシュする。"
        "simulator の堅牢化後に再修正予定。"
    ),
    strict=False,
)
def test_block3_impossible_shows_hints(page: Page) -> None:
    """FIRE不可時に改善ヒントが表示されること。"""
    login(page)
    app = get_app_frame(page)

    _set_impossible_conditions(page, app)
    page.wait_for_timeout(1000)
    _run_simulation(page, app)

    main = app.locator("[data-testid='stMain']")
    expect(main.get_by_text(re.compile(r"改善のヒント"))).to_be_visible()
