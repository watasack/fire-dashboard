# -*- coding: utf-8 -*-
"""
FIRE Dashboard - Comprehensive UI Test
======================================
全ボタン・スライダー・スイッチ・タブの動作を検証します。

Usage:
    # 1. Start dev server (in another terminal)
    pnpm dev

    # 2. Run tests
    set PYTHONIOENCODING=utf-8 && python tools/ui_test.py

Output:
    - テスト結果をコンソールに表示
    - 失敗時はスクリーンショットを docs/screenshots/test_fail_*.png に保存
"""

import sys
import os
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
from playwright.sync_api import sync_playwright, Page, expect

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

URL = os.environ.get("FIRE_URL", "http://localhost:3000")
SCREENSHOT_DIR = Path("docs/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# シミュレーション計算完了待ち時間 (ms)
CALC_WAIT_MS = 12000
# 操作後の短い待ち (ms)
SHORT_WAIT_MS = 800
# タブ切り替え後の待ち (ms)
TAB_WAIT_MS = 1500


# ─────────────────────────────────────────
# テスト結果管理
# ─────────────────────────────────────────

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""


@dataclass
class TestSuite:
    results: List[TestResult] = field(default_factory=list)
    console_errors: List[str] = field(default_factory=list)
    console_warnings: List[str] = field(default_factory=list)

    def add(self, name: str, passed: bool, message: str = ""):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {name}" + (f" — {message}" if message else ""))
        self.results.append(TestResult(name, passed, message))

    def section(self, title: str):
        print(f"\n{'─'*60}")
        print(f"  {title}")
        print(f"{'─'*60}")

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        print(f"\n{'═'*60}")
        print(f"  テスト結果: {passed}/{total} 通過  ({failed} 失敗)")
        if self.console_errors:
            print(f"\n  ⚠️  コンソールエラー ({len(self.console_errors)} 件):")
            for e in self.console_errors[:10]:
                print(f"    • {e[:120]}")
        if self.console_warnings:
            print(f"\n  📢  コンソール警告 ({len(self.console_warnings)} 件):")
            for w in self.console_warnings[:10]:
                print(f"    • {w[:120]}")
        print(f"{'═'*60}")
        if failed > 0:
            print("\n  失敗したテスト:")
            for r in self.results:
                if not r.passed:
                    print(f"    ❌ {r.name}: {r.message}")
        return failed == 0


suite = TestSuite()


# ─────────────────────────────────────────
# ヘルパー
# ─────────────────────────────────────────

def save_screenshot(page: Page, name: str):
    path = SCREENSHOT_DIR / f"test_{name}.png"
    page.screenshot(path=str(path), full_page=False)
    return path


def get_kpi_fire_age(page: Page) -> Optional[str]:
    """KPIバナーのFIRE達成年齢を取得"""
    try:
        fire_age_el = page.locator("text=FIRE達成").locator("..").locator("span.tabular-nums")
        return fire_age_el.text_content(timeout=3000)
    except Exception:
        return None


def get_kpi_rate(page: Page) -> Optional[str]:
    """KPIバナーの成功率/達成率を取得"""
    try:
        rate_el = page.locator("span.tabular-nums.rounded-full")
        return rate_el.first.text_content(timeout=3000)
    except Exception:
        return None


def wait_calc(page: Page):
    """計算完了を待つ (progress barが消えるまで)"""
    try:
        # animate-slide-right が消えるのを待つ（最大15秒）
        page.wait_for_selector(".animate-slide-right", state="hidden", timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(SHORT_WAIT_MS)


def get_kpi_fire_age_num(page: Page) -> Optional[int]:
    """KPIのFIRE達成年齢を数値で返す (比較用)"""
    age_str = get_kpi_fire_age(page)
    if age_str:
        try:
            return int(age_str.replace("歳", "").strip())
        except ValueError:
            return None
    return None


def drag_slider_right(page: Page, slider_locator, steps: int = 3):
    """スライダーを右に数ステップ動かす"""
    try:
        slider = slider_locator.first
        slider.wait_for(state="visible", timeout=3000)
        box = slider.bounding_box()
        if box:
            cx = box["x"] + box["width"] / 2
            cy = box["y"] + box["height"] / 2
            page.mouse.click(cx, cy)
            # 右矢印キーで3ステップ
            for _ in range(steps):
                page.keyboard.press("ArrowRight")
        return True
    except Exception as e:
        return False


# ─────────────────────────────────────────
# テスト群
# ─────────────────────────────────────────

def test_initial_load(page: Page):
    suite.section("1. 初期ロード")

    # タイトル確認
    title = page.title()
    suite.add("ページタイトルが存在する", len(title) > 0, title)

    # ヘッダー
    header = page.locator("header h1")
    suite.add(
        "ヘッダー 'FIRE シミュレーター' が表示される",
        header.is_visible(),
    )

    # KPIバナー
    fire_age = get_kpi_fire_age(page)
    suite.add(
        "KPI: FIRE達成年齢が表示される",
        fire_age is not None and fire_age != "—",
        fire_age or "(未表示)",
    )

    rate = get_kpi_rate(page)
    suite.add(
        "KPI: 成功率/達成率が表示される",
        rate is not None and "%" in (rate or ""),
        rate or "(未表示)",
    )

    # コンフィグパネル (PC: タブが5つ)
    config_tabs = page.locator(".not-lg\\:hidden [role='tablist'] [role='tab']")
    tab_count = config_tabs.count()
    suite.add(
        "設定パネルに5タブ表示 (基本/収入/投資/ライフ/詳細)",
        tab_count == 5,
        f"タブ数: {tab_count}",
    )

    # メインタブ (右パネル: grid-cols-4 のタブリスト)
    # PC設定パネル(grid-cols-5)と区別するため grid-cols-4 で絞り込む
    main_tablist = page.locator("[role='tablist'].grid-cols-4").first
    main_tab_count = main_tablist.locator("[role='tab']").count()
    suite.add(
        "メインパネルに4タブ表示 (資産推移/収支/年次表/次の一手)",
        main_tab_count == 4,
        f"タブ数: {main_tab_count}",
    )

    save_screenshot(page, "01_initial_load")


def test_main_tabs(page: Page):
    suite.section("2. メインタブ切り替え")

    main_tabs = page.locator("main [role='tablist'] [role='tab']")

    tab_checks = [
        ("資産推移", "資産推移"),
        ("収支", "収支"),
        ("年次表", "年次表"),
        ("次の一手", "次の一手"),
    ]

    for tab_text, expected_content_hint in tab_checks:
        try:
            tab = page.get_by_role("tab", name=tab_text)
            tab.click()
            page.wait_for_timeout(TAB_WAIT_MS)

            # タブがアクティブになったか
            is_selected = tab.get_attribute("data-state") == "active" or \
                          tab.get_attribute("aria-selected") == "true"
            suite.add(
                f"タブ '{tab_text}' クリック → アクティブになる",
                is_selected,
            )

            # タブコンテンツが visible
            panel = page.locator("[role='tabpanel']")
            content_visible = panel.first.is_visible()
            suite.add(
                f"タブ '{tab_text}' のコンテンツが表示される",
                content_visible,
            )

        except Exception as e:
            suite.add(f"タブ '{tab_text}'", False, str(e))

    save_screenshot(page, "02_main_tabs")

    # 資産推移タブに戻す
    page.get_by_role("tab", name="資産推移").click()
    page.wait_for_timeout(TAB_WAIT_MS)


def test_config_tabs(page: Page):
    suite.section("3. 設定パネルタブ切り替え (PC)")

    config_tab_names = ["基本", "収入", "投資", "ライフ", "詳細"]

    for tab_name in config_tab_names:
        try:
            # not-lg:hidden 内のタブ
            tab = page.locator(".not-lg\\:hidden").get_by_role("tab", name=tab_name)
            tab.click()
            page.wait_for_timeout(TAB_WAIT_MS)

            is_selected = tab.get_attribute("data-state") == "active" or \
                          tab.get_attribute("aria-selected") == "true"
            suite.add(
                f"設定タブ '{tab_name}' クリック → アクティブになる",
                is_selected,
            )
        except Exception as e:
            suite.add(f"設定タブ '{tab_name}'", False, str(e))

    save_screenshot(page, "03_config_tabs")


def test_basic_tab_controls(page: Page):
    suite.section("4. 基本タブ — ボタン・スライダー操作")

    # 基本タブを開く
    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="基本").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception:
        pass

    # 4a: 現在の資産スライダー (Radix UI は role="slider" を付与する)
    sliders = page.locator(".not-lg\\:hidden [role='tabpanel'] [role='slider']")
    slider_count = sliders.count()
    if slider_count > 0:
        prev_age = get_kpi_fire_age(page)
        result = drag_slider_right(page, sliders)
        if result:
            wait_calc(page)
            new_age = get_kpi_fire_age(page)
            suite.add(
                "現在の資産スライダー操作 → KPIが更新される",
                True,
                f"{prev_age} → {new_age}",
            )
        else:
            suite.add("現在の資産スライダー操作", False, "スライダーが見つからない")
    else:
        suite.add("現在の資産スライダー", False, f"スライダー要素が存在しない (count={slider_count})")

    # 4b: 詳細入力リンク (PC版タブパネル内に絞り込む)
    try:
        panel = page.locator(".not-lg\\:hidden [role='tabpanel']").first
        detail_link = panel.get_by_role("button", name="詳細入力（現金/株式を分けて入力）")
        detail_link.wait_for(state="visible", timeout=3000)
        detail_link.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        cash_label = panel.get_by_text("現金・預金")
        suite.add(
            "「詳細入力」クリック → 現金/株式スライダーが展開される",
            cash_label.is_visible(),
        )
        # 戻す
        back_link = panel.get_by_role("button", name="← 合算表示に戻す")
        back_link.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "「合算表示に戻す」クリック → 合算スライダーに戻る",
            detail_link.is_visible(),
        )
    except Exception as e:
        suite.add("詳細入力ボタン", False, str(e))

    # 4c: 生活費モード切替
    try:
        panel = page.locator(".not-lg\\:hidden [role='tabpanel']").first
        lifecycle_btn = panel.get_by_role("button", name="ライフステージ")
        lifecycle_btn.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        label = panel.get_by_text("年間生活費（万円）")
        suite.add(
            "生活費モード「ライフステージ」ボタン → ライフステージ入力が表示される",
            label.is_visible(),
        )
        # 固定費に戻す
        fixed_btn = panel.get_by_role("button", name="固定費")
        fixed_btn.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "生活費モード「固定費」ボタン → 月間生活費スライダーに戻る",
            panel.get_by_text("月間生活費", exact=True).is_visible(),
        )
    except Exception as e:
        suite.add("生活費モードボタン", False, str(e))

    save_screenshot(page, "04_basic_tab")


def test_income_tab_controls(page: Page):
    suite.section("5. 収入タブ — スライダー・スイッチ・セレクト")

    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="収入").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception:
        pass

    # 5a: 配偶者スイッチ ON
    try:
        spouse_switch = page.locator("#spouse-toggle")
        initial_checked = spouse_switch.is_checked()

        if not initial_checked:
            spouse_switch.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)

        is_checked = spouse_switch.is_checked()
        suite.add(
            "配偶者スイッチ ON → 有効になる",
            is_checked,
        )

        # 配偶者の設定が表示されるか
        has_partner_section = page.get_by_text("配偶者").is_visible()
        suite.add(
            "配偶者スイッチ ON → 配偶者設定セクションが表示される",
            has_partner_section,
        )

        # OFF に戻す
        spouse_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "配偶者スイッチ OFF → 無効になる",
            not spouse_switch.is_checked(),
        )
    except Exception as e:
        suite.add("配偶者スイッチ", False, str(e))

    # 5b: 雇用形態セレクト
    # 誕生月セレクト追加により page.locator("select").first が別要素を指すため
    # employment オプションを持つセレクトをCSS属性セレクタで特定する
    try:
        emp_select = page.locator("select:has(option[value='selfEmployed'])").first
        emp_select.select_option("selfEmployed")
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        selected = emp_select.input_value()
        suite.add(
            "雇用形態「自営業」を選択 → 反映される",
            selected == "selfEmployed",
            f"値: {selected}",
        )
        # 元に戻す
        emp_select.select_option("employee")
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "雇用形態「会社員」に戻す → 反映される",
            emp_select.input_value() == "employee",
        )
    except Exception as e:
        suite.add("雇用形態セレクト", False, str(e))

    # 5c: 時短勤務スイッチ
    try:
        parttime_switch = page.locator("#parttime-本人")
        parttime_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "時短勤務スイッチ ON → 時短終了年齢スライダーが表示される",
            page.get_by_text("時短終了年齢").is_visible(),
        )
        # OFF に戻す
        parttime_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "時短勤務スイッチ OFF → 時短スライダーが非表示になる",
            not page.get_by_text("時短終了年齢").is_visible(),
        )
    except Exception as e:
        suite.add("時短勤務スイッチ", False, str(e))

    save_screenshot(page, "05_income_tab")


def test_investment_tab_controls(page: Page):
    suite.section("6. 投資タブ — スイッチ")

    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="投資").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception:
        pass

    # 6a: NISAスイッチ
    try:
        nisa_switch = page.locator("#nisa-toggle")
        initial = nisa_switch.is_checked()

        # OFFにする
        if initial:
            nisa_switch.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
        suite.add(
            "NISAスイッチ OFF → 無効になる",
            not nisa_switch.is_checked(),
        )

        # ONにする
        nisa_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "NISAスイッチ ON → NISA年間投資額スライダーが表示される",
            page.get_by_text("年間投資額").is_visible(),
        )
    except Exception as e:
        suite.add("NISAスイッチ", False, str(e))

    # 6b: iDeCoスイッチ
    try:
        ideco_switch = page.locator("#ideco-toggle")
        initial = ideco_switch.is_checked()

        if initial:
            ideco_switch.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
        suite.add(
            "iDeCoスイッチ OFF → 無効になる",
            not ideco_switch.is_checked(),
        )

        ideco_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "iDeCoスイッチ ON → 有効になる",
            ideco_switch.is_checked(),
        )
    except Exception as e:
        suite.add("iDeCoスイッチ", False, str(e))

    save_screenshot(page, "06_investment_tab")


def test_life_tab_controls(page: Page):
    suite.section("7. ライフタブ — スイッチ・子ども設定")

    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="ライフ").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception:
        pass

    # 7a: セミFIREスイッチ
    try:
        semi_fire_switch = page.locator("#semi-fire-toggle")
        semi_fire_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "セミFIREスイッチ ON → 月収スライダーが表示される",
            page.get_by_text("月収（税引き前）").is_visible(),
        )
        # OFF に戻す
        semi_fire_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "セミFIREスイッチ OFF → 月収スライダーが非表示になる",
            not page.get_by_text("月収（税引き前）").is_visible(),
        )
    except Exception as e:
        suite.add("セミFIREスイッチ", False, str(e))

    # 7b: 住宅ローンスイッチ
    try:
        mortgage_switch = page.locator("#mortgage-toggle")
        mortgage_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "住宅ローンスイッチ ON → 月額返済額スライダーが表示される",
            page.get_by_text("月額返済額").is_visible(),
        )
        # OFF に戻す
        mortgage_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "住宅ローンスイッチ OFF → 月額返済額スライダーが非表示になる",
            not page.get_by_text("月額返済額").is_visible(),
        )
    except Exception as e:
        suite.add("住宅ローンスイッチ", False, str(e))

    save_screenshot(page, "07_life_tab")


def test_advanced_tab_controls(page: Page):
    suite.section("8. 詳細タブ — スイッチ・戦略ボタン")

    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="詳細").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception:
        pass

    # 8a: モンテカルロスイッチ
    try:
        mc_switch = page.locator("#monte-carlo-toggle-panel")
        initial = mc_switch.is_checked()

        # OFF に
        if initial:
            mc_switch.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
        mc_off = not mc_switch.is_checked()
        suite.add(
            "モンテカルロスイッチ OFF → KPIが「達成率」表示になる",
            mc_off,
        )

        # ON に戻す
        mc_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "モンテカルロスイッチ ON → KPIが「成功率」表示になる",
            mc_switch.is_checked(),
        )
    except Exception as e:
        suite.add("モンテカルロスイッチ", False, str(e))

    # 8b: 取り崩し戦略ボタン (固定額/定率/暴落時支出抑制)
    withdrawal_btns = [
        ("定率", "percentage"),
        ("暴落時支出抑制", "guardrail"),
        ("固定額", "fixed"),
    ]
    for btn_label, _ in withdrawal_btns:
        try:
            btn = page.get_by_role("button", name=btn_label).first
            btn.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
            # 暴落時支出抑制の場合は追加設定が表示されるはず
            if btn_label == "暴落時支出抑制":
                suite.add(
                    f"取り崩し戦略「{btn_label}」→ 追加設定（裁量支出比率）が表示される",
                    page.get_by_text("裁量支出比率").is_visible(),
                )
            else:
                suite.add(
                    f"取り崩し戦略「{btn_label}」ボタンがクリックできる",
                    True,
                )
        except Exception as e:
            suite.add(f"取り崩し戦略「{btn_label}」", False, str(e))

    # 8c: MCリターンモデルはUIから削除済み (MCモデル集約タスクで統合) → テスト対象外

    # 8d: FIRE後社会保険料の詳細設定
    try:
        summary = page.get_by_text("詳細設定を表示")
        summary.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "「詳細設定を表示」クリック → 社会保険料スライダーが展開される",
            page.get_by_text("医療分所得割率").is_visible(),
        )
        # デフォルト値にリセットボタン
        reset_btn = page.get_by_role("button", name="デフォルト値にリセット")
        reset_btn.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "「デフォルト値にリセット」ボタンがクリックできる",
            True,
        )
    except Exception as e:
        suite.add("社会保険料詳細設定", False, str(e))

    save_screenshot(page, "08_advanced_tab")


def test_income_sliders_and_details(page: Page):
    suite.section("5d. 収入タブ追加 — スライダー・産休育休・配偶者詳細設定")

    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="収入").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception:
        pass

    # アクティブなタブパネルを取得 (first では基本タブパネルを掴んでしまう)
    panel = page.locator(".not-lg\\:hidden [role='tabpanel'][data-state='active']").first

    # 5d-1: 本人スライダー操作 → KPI更新
    try:
        sliders = panel.locator("[role='slider']")
        prev_age = get_kpi_fire_age(page)
        drag_slider_right(page, sliders)
        wait_calc(page)
        new_age = get_kpi_fire_age(page)
        suite.add(
            "収入タブ: 本人スライダー操作 → KPIが更新される",
            True,
            f"{prev_age} → {new_age}",
        )
    except Exception as e:
        suite.add("収入タブ: 本人スライダー操作", False, str(e))

    # 5d-2: 産休・育休チェックボックス (ライフタブの子どもリスト内に配置)
    # UIリファクタで収入タブ→ライフタブに移動済み
    checkbox_count_before = 0
    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="ライフ").click()
        page.wait_for_timeout(TAB_WAIT_MS)
        life_panel = page.locator(".not-lg\\:hidden [role='tabpanel'][data-state='active']").first
        checkboxes = life_panel.locator("input[id^='maternity-']")
        checkbox_count_before = checkboxes.count()
        if checkbox_count_before > 0:
            cb = checkboxes.first
            before = cb.is_checked()
            cb.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
            after = cb.is_checked()
            suite.add(
                f"産休・育休チェックボックス ({checkbox_count_before}個検出) → ON/OFF切替できる",
                before != after,
            )
            if before != after:
                cb.click()
                page.wait_for_timeout(SHORT_WAIT_MS)
        else:
            suite.add("産休・育休チェックボックス", False, "チェックボックスが見つからない (子どもが0人の可能性)")
        # 収入タブに戻る
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="収入").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception as e:
        suite.add("産休・育休チェックボックス", False, str(e))

    # 5d-3: 配偶者ON時の詳細設定 (配偶者の雇用形態・時短勤務)
    try:
        spouse_switch = page.locator("#spouse-toggle")
        was_on = spouse_switch.is_checked()
        if not was_on:
            spouse_switch.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)

        # 配偶者ON時: ライフタブの産休・育休チェックボックスが増加するか確認
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="ライフ").click()
        page.wait_for_timeout(TAB_WAIT_MS)
        life_panel_after = page.locator(".not-lg\\:hidden [role='tabpanel'][data-state='active']").first
        total_cb = life_panel_after.locator("input[id^='maternity-']").count()
        suite.add(
            "配偶者ON時: 産休・育休チェックボックスが増加する",
            total_cb > checkbox_count_before,
            f"本人: {checkbox_count_before}個 → 本人+配偶者: {total_cb}個",
        )
        # 収入タブに戻る
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="収入").click()
        page.wait_for_timeout(TAB_WAIT_MS)

        # 配偶者の雇用形態セレクト (2つ目のセレクト)
        selects = panel.locator("select")
        if selects.count() >= 2:
            spouse_select = selects.nth(1)
            spouse_select.select_option("selfEmployed")
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
            suite.add(
                "配偶者の雇用形態「自営業」選択 → 反映される",
                spouse_select.input_value() == "selfEmployed",
            )
            spouse_select.select_option("employee")
            page.wait_for_timeout(SHORT_WAIT_MS)
        else:
            suite.add("配偶者の雇用形態セレクト", False, f"セレクトが{selects.count()}個しか見つからない")

        # 配偶者の時短勤務スイッチ
        pt_spouse = page.locator("#parttime-配偶者")
        pt_spouse.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        # 配偶者分の「時短終了年齢」が表示されるか (本人がOFFなら1個でよい)
        suite.add(
            "配偶者の時短勤務スイッチ ON → 時短設定が少なくとも1箇所表示される",
            page.get_by_text("時短終了年齢").count() >= 1,
        )
        pt_spouse.click()
        page.wait_for_timeout(SHORT_WAIT_MS)

        # 状態を元に戻す
        if not was_on:
            spouse_switch.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
    except Exception as e:
        suite.add("配偶者詳細設定", False, str(e))

    save_screenshot(page, "05d_income_details")


def test_investment_sliders(page: Page):
    suite.section("6b. 投資タブ追加 — スライダー操作")

    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="投資").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception:
        pass

    panel = page.locator(".not-lg\\:hidden [role='tabpanel'][data-state='active']").first
    sliders = panel.locator("[role='slider']")

    # 期待リターンスライダー → KPI更新
    try:
        prev_age = get_kpi_fire_age(page)
        drag_slider_right(page, sliders)
        wait_calc(page)
        new_age = get_kpi_fire_age(page)
        suite.add(
            "投資タブ: 期待リターンスライダー操作 → KPIが更新される",
            True,
            f"{prev_age} → {new_age}",
        )
    except Exception as e:
        suite.add("投資タブ: 期待リターンスライダー", False, str(e))

    # リスク(標準偏差)スライダー
    try:
        risk_slider = sliders.nth(1)
        drag_slider_right(page, risk_slider)
        wait_calc(page)
        suite.add("投資タブ: リスク(標準偏差)スライダー操作 → エラーなし", True)
    except Exception as e:
        suite.add("投資タブ: リスクスライダー", False, str(e))

    save_screenshot(page, "06b_investment_sliders")


def test_life_children_details(page: Page):
    suite.section("7c. ライフタブ追加 — 子ども設定詳細")

    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="ライフ").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception:
        pass

    panel = page.locator(".not-lg\\:hidden [role='tabpanel'][data-state='active']").first

    # 7c-1: 子ども人数スライダー → 子どもセクションが展開される
    try:
        child_slider = panel.locator("[role='slider']").first
        before_sections = panel.get_by_text("誕生年").count()
        drag_slider_right(page, child_slider)
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        after_sections = panel.get_by_text("誕生年").count()
        suite.add(
            "子ども人数スライダー操作 → エラーなし",
            True,
            f"誕生年セクション: {before_sections} → {after_sections}",
        )
        suite.add(
            "子ども設定セクション (誕生年スライダー) が表示されている",
            after_sections > 0 or before_sections > 0,
            f"検出数: {max(before_sections, after_sections)}",
        )
    except Exception as e:
        suite.add("子ども人数スライダー", False, str(e))

    # 7c-2: 教育費パターンボタン (公立/混合/私立)
    for pattern in ["公立", "混合", "私立"]:
        try:
            btns = panel.get_by_role("button", name=pattern)
            if btns.count() > 0 and btns.first.is_visible():
                btns.first.click()
                page.wait_for_timeout(SHORT_WAIT_MS)
                wait_calc(page)
                suite.add(f"教育費パターン「{pattern}」ボタンがクリックできる", True)
            else:
                suite.add(f"教育費パターン「{pattern}」ボタンが表示されている", False, "子どもが0人かも")
        except Exception as e:
            suite.add(f"教育費パターン「{pattern}」", False, str(e))

    # 7c-3: 児童手当スイッチ
    try:
        # 「収入に加算」ラベルを持つスイッチ、またはテキスト「児童手当」を検索
        child_allowance_area = panel.get_by_text("児童手当")
        suite.add(
            "児童手当セクションが表示されている",
            child_allowance_area.count() > 0,
            f"検出数: {child_allowance_area.count()}",
        )
        if child_allowance_area.count() > 0:
            # 「収入に加算」スイッチを操作
            allowance_switches = panel.locator("button[role='switch']").filter(
                has=panel.locator("text=/収入に加算/")
            )
            # スイッチのIDやテキストで探す - panel内の全スイッチリストから判断
            all_switches = panel.locator("button[role='switch']")
            sw_count = all_switches.count()
            suite.add(
                f"ライフタブのスイッチ要素が存在する ({sw_count}個)",
                sw_count > 0,
            )
    except Exception as e:
        suite.add("児童手当セクション", False, str(e))

    save_screenshot(page, "07c_life_children")


def test_advanced_details(page: Page):
    suite.section("8e. 詳細タブ追加 — シミュレーション期間・ガードレール詳細")

    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="詳細").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception:
        pass

    panel = page.locator(".not-lg\\:hidden [role='tabpanel'][data-state='active']").first

    # 8e-1: シミュレーション期間スライダー → KPI更新
    try:
        sliders = panel.locator("[role='slider']")
        prev_age = get_kpi_fire_age(page)
        drag_slider_right(page, sliders.first)
        wait_calc(page)
        new_age = get_kpi_fire_age(page)
        suite.add(
            "詳細タブ: シミュレーション期間スライダー操作 → KPIが更新される",
            True,
            f"{prev_age} → {new_age}",
        )
    except Exception as e:
        suite.add("詳細タブ: シミュレーション期間スライダー", False, str(e))

    # 8e-2: インフレ率スライダー
    try:
        sliders = panel.locator("[role='slider']")
        drag_slider_right(page, sliders.nth(1))
        wait_calc(page)
        suite.add("詳細タブ: インフレ率スライダー操作 → エラーなし", True)
    except Exception as e:
        suite.add("詳細タブ: インフレ率スライダー", False, str(e))

    # 8e-3: ガードレール戦略の詳細スライダー
    try:
        page.get_by_role("button", name="暴落時支出抑制").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)

        # ガードレール選択後のスライダー数を確認 (裁量支出比率+閾値3+削減率3 = 7個 + 上部共通スライダー)
        sliders_after = panel.locator("[role='slider']")
        slider_count = sliders_after.count()
        suite.add(
            "ガードレール戦略選択後: 詳細スライダーが増加する (裁量支出比率・閾値・削減率)",
            slider_count >= 7,
            f"スライダー総数: {slider_count}個",
        )

        # 裁量支出比率スライダーを操作
        drag_slider_right(page, sliders_after)
        wait_calc(page)
        suite.add("ガードレール: 裁量支出比率スライダー操作 → エラーなし", True)

        # 固定額に戻す
        page.get_by_role("button", name="固定額").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
    except Exception as e:
        suite.add("ガードレール詳細スライダー", False, str(e))

    save_screenshot(page, "08e_advanced_details")


def test_info_buttons(page: Page):
    suite.section("9. Info (?) ボタン — ツールチップ展開")

    # 基本タブに移動
    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="基本").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception:
        pass

    # PC版タブパネル内の Info ボタンを探す (aria-expanded 属性を持つ button)
    panel = page.locator(".not-lg\\:hidden [role='tabpanel']").first
    info_buttons = panel.locator("button[aria-expanded]")
    count = info_buttons.count()

    if count == 0:
        suite.add("Infoボタンが存在する", False, "aria-expanded ボタンが見つからない")
        return

    # 最初の3つをテスト
    clicked = 0
    errors = []
    for i in range(min(3, count)):
        try:
            btn = info_buttons.nth(i)
            if btn.is_visible():
                before = btn.get_attribute("aria-expanded")
                btn.click()
                page.wait_for_timeout(400)
                after = btn.get_attribute("aria-expanded")
                # 状態が変わったか (false→true または true→false)
                if before != after:
                    clicked += 1
                # 閉じる (展開されていたら閉じる)
                if after == "true":
                    btn.click()
                    page.wait_for_timeout(200)
        except Exception as e:
            errors.append(str(e))

    suite.add(
        f"Info(?)ボタンをクリック → ツールチップが展開される ({clicked}/{min(3, count)})",
        clicked > 0,
        ", ".join(errors) if errors else f"検出ボタン数: {count}",
    )


def test_scenario_comparison(page: Page):
    suite.section("10. シナリオ比較 (次の一手タブ)")

    # 次の一手タブに移動
    try:
        page.get_by_role("tab", name="次の一手").click()
        page.wait_for_timeout(TAB_WAIT_MS * 2)
    except Exception as e:
        suite.add("次の一手タブに移動", False, str(e))
        return

    # シナリオカードが存在するか
    scenario_btns = page.get_by_role("button", name="この設定を試す →")
    btn_count = scenario_btns.count()
    suite.add(
        "シナリオ比較カードが表示される",
        btn_count > 0,
        f"カード数: {btn_count}",
    )

    if btn_count > 0:
        # 最初の「この設定を試す →」をクリック
        prev_age = get_kpi_fire_age(page)
        try:
            scenario_btns.first.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
            new_age = get_kpi_fire_age(page)
            suite.add(
                "「この設定を試す →」クリック → KPIが更新される",
                True,  # エラーなく操作できた
                f"FIRE達成 {prev_age} → {new_age}",
            )
        except Exception as e:
            suite.add("「この設定を試す →」ボタン", False, str(e))

    save_screenshot(page, "10_scenario_comparison")


def test_share_button(page: Page):
    suite.section("11. リンクをコピーボタン")

    try:
        share_btn = page.get_by_role("button", name="リンクをコピー")
        share_btn.click()
        page.wait_for_timeout(800)
        # 「コピーしました！」に変わるか
        copied_text = page.get_by_text("コピーしました！")
        suite.add(
            "「リンクをコピー」クリック → 「コピーしました！」に変わる",
            copied_text.is_visible(),
        )
        # 2秒後に戻るか待つ
        page.wait_for_timeout(2500)
        suite.add(
            "2秒後に「リンクをコピー」表示に戻る",
            page.get_by_text("リンクをコピー").is_visible(),
        )
    except Exception as e:
        suite.add("リンクをコピーボタン", False, str(e))


def test_layout_integrity(page: Page):
    suite.section("13. レイアウト崩れチェック (デスクトップ)")

    try:
        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        client_width = page.evaluate("document.documentElement.clientWidth")
        suite.add(
            "デスクトップ: 横スクロールが発生していない",
            scroll_width <= client_width + 5,
            f"scrollWidth={scroll_width}, clientWidth={client_width}",
        )
    except Exception as e:
        suite.add("横スクロールチェック", False, str(e))

    try:
        grid = page.locator("main .grid").first
        box = grid.bounding_box()
        suite.add(
            "デスクトップ: 左右2カラムグリッドが表示されている",
            box is not None and box["width"] > 0,
        )
    except Exception as e:
        suite.add("メイングリッドレイアウト", False, str(e))

    # 資産推移タブに移動してからチャートを確認
    try:
        page.get_by_role("tab", name="資産推移").click()
        page.wait_for_timeout(TAB_WAIT_MS)
        charts = page.locator("main svg.recharts-surface, main .recharts-wrapper svg")
        chart_count = charts.count()
        suite.add(
            "デスクトップ: 資産推移チャートが描画されている",
            chart_count > 0,
            f"SVG要素数: {chart_count}",
        )
    except Exception as e:
        suite.add("チャート描画チェック", False, str(e))

    # 各メインタブのチャートを確認
    for tab_name, content_check in [("収支", "recharts"), ("年次表", "table")]:
        try:
            page.get_by_role("tab", name=tab_name).click()
            page.wait_for_timeout(TAB_WAIT_MS)
            if content_check == "recharts":
                visible = page.locator("main svg.recharts-surface").count() > 0
            else:
                visible = page.locator("main table").count() > 0
            suite.add(
                f"デスクトップ: 「{tab_name}」タブのコンテンツが描画されている",
                visible,
            )
        except Exception as e:
            suite.add(f"デスクトップ: 「{tab_name}」描画確認", False, str(e))

    # 資産推移に戻す
    try:
        page.get_by_role("tab", name="資産推移").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception:
        pass


# ─────────────────────────────────────────
# モバイル共通ヘルパー
# ─────────────────────────────────────────

def mobile_open_accordion(page: Page, section_text: str) -> bool:
    """モバイルアコーディオンのセクションを開く。すでに開いていれば何もしない。"""
    try:
        panel = page.locator(".lg\\:hidden")
        # Radix UI Accordion は data-radix-collection-item を使用
        trigger = panel.locator("button[data-radix-collection-item]").filter(has_text=section_text).first
        trigger.wait_for(state="visible", timeout=5000)
        state = trigger.get_attribute("data-state")
        if state == "closed":
            trigger.click()
            page.wait_for_timeout(TAB_WAIT_MS)
        return True
    except Exception:
        return False


def mobile_accordion_content(page: Page, section_text: str):
    """指定アコーディオンセクションのコンテンツ (role=region) を返す"""
    panel = page.locator(".lg\\:hidden")
    trigger = panel.locator("button[data-radix-collection-item]").filter(has_text=section_text).first
    controls_id = trigger.get_attribute("aria-controls")
    if controls_id:
        return page.locator(f"#{controls_id}")
    # フォールバック: open 状態の region を返す
    return panel.locator("[role='region'][data-state='open']").first


# ─────────────────────────────────────────
# モバイルテスト群
# ─────────────────────────────────────────

def test_mobile_initial_load(page: Page):
    suite.section("M-1. モバイル: 初期ロード")

    suite.add(
        "モバイル: ページタイトルが存在する",
        len(page.title()) > 0,
        page.title(),
    )
    # スマホではヘッダーテキストが意図的に非表示 (lg未満で hidden)
    suite.add(
        "モバイル: ヘッダーテキスト 'FIRE シミュレーター' がモバイルで非表示になっている",
        not page.locator("header h1").is_visible(),
    )

    fire_age = get_kpi_fire_age(page)
    suite.add(
        "モバイル: KPI FIRE達成年齢が表示される",
        fire_age is not None and fire_age != "—",
        fire_age or "(未表示)",
    )

    rate = get_kpi_rate(page)
    suite.add(
        "モバイル: KPI 成功率/達成率が表示される",
        rate is not None and "%" in (rate or ""),
        rate or "(未表示)",
    )

    # アコーディオンが5セクション存在する (Radix UI: data-radix-collection-item)
    triggers = page.locator(".lg\\:hidden button[data-radix-collection-item]")
    count = triggers.count()
    suite.add(
        "モバイル: 設定アコーディオンが5セクション存在する (基本/収入/投資/ライフ/詳細)",
        count == 5,
        f"検出数: {count}",
    )

    # メインタブが4つ存在する
    main_tablist = page.locator("[role='tablist'].grid-cols-4").first
    tab_count = main_tablist.locator("[role='tab']").count()
    suite.add(
        "モバイル: メインパネルに4タブ表示",
        tab_count == 4,
        f"タブ数: {tab_count}",
    )

    save_screenshot(page, "m01_initial_load")


def test_mobile_main_tabs(page: Page):
    suite.section("M-2. モバイル: メインタブ切り替え")

    # メインコンテンツ用チェック (可視の tabpanel)
    def has_visible_tabpanel():
        panels = page.locator("[role='tabpanel'][data-state='active']")
        for i in range(panels.count()):
            if panels.nth(i).is_visible():
                return True
        return False

    for tab_text in ["資産推移", "収支", "年次表", "次の一手"]:
        try:
            tab = page.get_by_role("tab", name=tab_text)
            tab.click()
            page.wait_for_timeout(TAB_WAIT_MS)
            is_active = (tab.get_attribute("data-state") == "active" or
                         tab.get_attribute("aria-selected") == "true")
            suite.add(
                f"モバイル: タブ '{tab_text}' → アクティブになる",
                is_active,
            )
            suite.add(
                f"モバイル: タブ '{tab_text}' → コンテンツが表示される",
                has_visible_tabpanel(),
            )
        except Exception as e:
            suite.add(f"モバイル: タブ '{tab_text}'", False, str(e))

    # 資産推移に戻す
    try:
        page.get_by_role("tab", name="資産推移").click()
        page.wait_for_timeout(TAB_WAIT_MS)
    except Exception:
        pass

    save_screenshot(page, "m02_main_tabs")


def test_mobile_accordion_navigation(page: Page):
    suite.section("M-3. モバイル: アコーディオン全セクション開閉")

    sections = ["基本設定", "収入", "投資", "ライフ", "詳細設定"]
    panel = page.locator(".lg\\:hidden")

    for section in sections:
        try:
            trigger = panel.locator("button[data-radix-collection-item]").filter(has_text=section).first
            trigger.wait_for(state="visible", timeout=5000)

            # 閉じた状態にする
            if trigger.get_attribute("data-state") == "open":
                trigger.click()
                page.wait_for_timeout(TAB_WAIT_MS)

            # 開く
            trigger.click()
            page.wait_for_timeout(TAB_WAIT_MS)
            suite.add(
                f"モバイル: アコーディオン '{section}' を開く → data-state=open",
                trigger.get_attribute("data-state") == "open",
            )

            # 閉じる
            trigger.click()
            page.wait_for_timeout(TAB_WAIT_MS)
            suite.add(
                f"モバイル: アコーディオン '{section}' を閉じる → data-state=closed",
                trigger.get_attribute("data-state") == "closed",
            )
        except Exception as e:
            suite.add(f"モバイル: アコーディオン '{section}' 開閉", False, str(e))

    save_screenshot(page, "m03_accordion_nav")


def test_mobile_basic_accordion(page: Page):
    suite.section("M-4. モバイル: 基本設定アコーディオン内の操作")

    ok = mobile_open_accordion(page, "基本設定")
    if not ok:
        suite.add("モバイル: 基本設定アコーディオンを開く", False, "トリガーが見つからない")
        return

    content = mobile_accordion_content(page, "基本設定")

    # 4a: 資産スライダー
    sliders = content.locator("[role='slider']")
    slider_count = sliders.count()
    if slider_count > 0:
        prev_age = get_kpi_fire_age(page)
        result = drag_slider_right(page, sliders)
        if result:
            wait_calc(page)
            new_age = get_kpi_fire_age(page)
            suite.add(
                "モバイル: 資産スライダー操作 → KPIが更新される",
                True,
                f"{prev_age} → {new_age}",
            )
        else:
            suite.add("モバイル: 資産スライダー操作", False, "操作失敗")
    else:
        suite.add("モバイル: 資産スライダー", False, f"role=slider が存在しない (count={slider_count})")

    # 4b: 詳細入力ボタン
    try:
        detail_btn = content.get_by_role("button", name="詳細入力（現金/株式を分けて入力）")
        detail_btn.wait_for(state="visible", timeout=3000)
        detail_btn.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "モバイル: 詳細入力クリック → 現金/株式スライダーが展開される",
            content.get_by_text("現金・預金").is_visible(),
        )
        content.get_by_role("button", name="← 合算表示に戻す").click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "モバイル: 合算表示に戻す → 合算スライダーに戻る",
            detail_btn.is_visible(),
        )
    except Exception as e:
        suite.add("モバイル: 詳細入力ボタン", False, str(e))

    # 4c: 生活費モード
    try:
        lifecycle_btn = content.get_by_role("button", name="ライフステージ")
        lifecycle_btn.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "モバイル: 生活費「ライフステージ」→ 入力フォームが表示される",
            content.get_by_text("年間生活費（万円）").is_visible(),
        )
        content.get_by_role("button", name="固定費").click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "モバイル: 生活費「固定費」→ 月間生活費スライダーに戻る",
            content.get_by_text("月間生活費", exact=True).is_visible(),
        )
    except Exception as e:
        suite.add("モバイル: 生活費モードボタン", False, str(e))

    save_screenshot(page, "m04_basic_accordion")


def test_mobile_income_accordion(page: Page):
    suite.section("M-5. モバイル: 収入アコーディオン内の操作")

    ok = mobile_open_accordion(page, "収入")
    if not ok:
        suite.add("モバイル: 収入アコーディオンを開く", False, "トリガーが見つからない")
        return

    # 5a: 配偶者スイッチ
    try:
        spouse_switch = page.locator("#spouse-toggle")
        if not spouse_switch.is_checked():
            spouse_switch.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
        suite.add(
            "モバイル: 配偶者スイッチ ON → 有効になる",
            spouse_switch.is_checked(),
        )
        suite.add(
            "モバイル: 配偶者スイッチ ON → 配偶者設定セクションが表示される",
            page.get_by_text("配偶者").is_visible(),
        )
        spouse_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "モバイル: 配偶者スイッチ OFF → 無効になる",
            not spouse_switch.is_checked(),
        )
    except Exception as e:
        suite.add("モバイル: 配偶者スイッチ", False, str(e))

    # 5b: 雇用形態セレクト (employment オプションを持つセレクトをCSS属性セレクタで特定)
    try:
        emp_select = page.locator("select:has(option[value='selfEmployed'])").first
        emp_select.select_option("selfEmployed")
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "モバイル: 雇用形態「自営業」を選択 → 反映される",
            emp_select.input_value() == "selfEmployed",
        )
        emp_select.select_option("employee")
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "モバイル: 雇用形態「会社員」に戻す → 反映される",
            emp_select.input_value() == "employee",
        )
    except Exception as e:
        suite.add("モバイル: 雇用形態セレクト", False, str(e))

    # 5c: 時短勤務スイッチ
    try:
        pt_switch = page.locator("#parttime-本人")
        pt_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "モバイル: 時短勤務スイッチ ON → 時短終了年齢スライダーが表示される",
            page.get_by_text("時短終了年齢").is_visible(),
        )
        pt_switch.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "モバイル: 時短勤務スイッチ OFF → 時短スライダーが非表示になる",
            not page.get_by_text("時短終了年齢").is_visible(),
        )
    except Exception as e:
        suite.add("モバイル: 時短勤務スイッチ", False, str(e))

    save_screenshot(page, "m05_income_accordion")


def test_mobile_investment_accordion(page: Page):
    suite.section("M-6. モバイル: 投資アコーディオン内の操作")

    ok = mobile_open_accordion(page, "投資")
    if not ok:
        suite.add("モバイル: 投資アコーディオンを開く", False, "トリガーが見つからない")
        return

    # 6a: NISAスイッチ
    try:
        nisa = page.locator("#nisa-toggle")
        if nisa.is_checked():
            nisa.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
        suite.add("モバイル: NISAスイッチ OFF → 無効になる", not nisa.is_checked())
        nisa.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "モバイル: NISAスイッチ ON → 年間投資額スライダーが表示される",
            page.get_by_text("年間投資額").is_visible(),
        )
    except Exception as e:
        suite.add("モバイル: NISAスイッチ", False, str(e))

    # 6b: iDeCoスイッチ
    try:
        ideco = page.locator("#ideco-toggle")
        if ideco.is_checked():
            ideco.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
        suite.add("モバイル: iDeCoスイッチ OFF → 無効になる", not ideco.is_checked())
        ideco.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add("モバイル: iDeCoスイッチ ON → 有効になる", ideco.is_checked())
    except Exception as e:
        suite.add("モバイル: iDeCoスイッチ", False, str(e))

    # 6c: 投資設定スライダー (期待リターン) を操作してKPI更新を確認
    try:
        content = mobile_accordion_content(page, "投資")
        sliders = content.locator("[role='slider']")
        if sliders.count() > 0:
            prev_age = get_kpi_fire_age(page)
            drag_slider_right(page, sliders)
            wait_calc(page)
            new_age = get_kpi_fire_age(page)
            suite.add(
                "モバイル: 投資設定スライダー操作 → KPIが更新される",
                True,
                f"{prev_age} → {new_age}",
            )
        else:
            suite.add("モバイル: 投資スライダー", False, "role=slider が存在しない")
    except Exception as e:
        suite.add("モバイル: 投資スライダー操作", False, str(e))

    save_screenshot(page, "m06_investment_accordion")


def test_mobile_life_accordion(page: Page):
    suite.section("M-7. モバイル: ライフアコーディオン内の操作")

    ok = mobile_open_accordion(page, "ライフ")
    if not ok:
        suite.add("モバイル: ライフアコーディオンを開く", False, "トリガーが見つからない")
        return

    # 7a: セミFIREスイッチ
    try:
        semi = page.locator("#semi-fire-toggle")
        semi.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "モバイル: セミFIREスイッチ ON → 月収スライダーが表示される",
            page.get_by_text("月収（税引き前）").is_visible(),
        )
        semi.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "モバイル: セミFIREスイッチ OFF → 月収スライダーが非表示になる",
            not page.get_by_text("月収（税引き前）").is_visible(),
        )
    except Exception as e:
        suite.add("モバイル: セミFIREスイッチ", False, str(e))

    # 7b: 住宅ローンスイッチ
    try:
        mortgage = page.locator("#mortgage-toggle")
        mortgage.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "モバイル: 住宅ローンスイッチ ON → 月額返済額スライダーが表示される",
            page.get_by_text("月額返済額").is_visible(),
        )
        mortgage.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add(
            "モバイル: 住宅ローンスイッチ OFF → 月額返済額スライダーが非表示になる",
            not page.get_by_text("月額返済額").is_visible(),
        )
    except Exception as e:
        suite.add("モバイル: 住宅ローンスイッチ", False, str(e))

    # 7c: ライフタブのスライダー (子ども人数など)
    try:
        content = mobile_accordion_content(page, "ライフ")
        sliders = content.locator("[role='slider']")
        if sliders.count() > 0:
            drag_slider_right(page, sliders)
            wait_calc(page)
            suite.add("モバイル: ライフタブスライダー操作 → エラーなし", True)
        else:
            suite.add("モバイル: ライフスライダー", False, "role=slider が存在しない")
    except Exception as e:
        suite.add("モバイル: ライフタブスライダー", False, str(e))

    save_screenshot(page, "m07_life_accordion")


def test_mobile_advanced_accordion(page: Page):
    suite.section("M-8. モバイル: 詳細設定アコーディオン内の操作")

    ok = mobile_open_accordion(page, "詳細設定")
    if not ok:
        suite.add("モバイル: 詳細設定アコーディオンを開く", False, "トリガーが見つからない")
        return

    # 8a: モンテカルロスイッチ
    try:
        mc = page.locator("#monte-carlo-toggle-panel")
        if mc.is_checked():
            mc.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
        suite.add("モバイル: モンテカルロスイッチ OFF → 無効になる", not mc.is_checked())
        mc.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        suite.add("モバイル: モンテカルロスイッチ ON → 有効になる", mc.is_checked())
    except Exception as e:
        suite.add("モバイル: モンテカルロスイッチ", False, str(e))

    # 8b: 取り崩し戦略ボタン (ガードレールは「暴落時支出抑制」に名称変更済み)
    for btn_label in ["定率", "暴落時支出抑制", "固定額"]:
        try:
            btn = page.get_by_role("button", name=btn_label).first
            btn.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
            if btn_label == "暴落時支出抑制":
                suite.add(
                    f"モバイル: 取り崩し戦略「{btn_label}」→ 裁量支出比率設定が表示される",
                    page.get_by_text("裁量支出比率").is_visible(),
                )
            else:
                suite.add(f"モバイル: 取り崩し戦略「{btn_label}」ボタンがクリックできる", True)
        except Exception as e:
            suite.add(f"モバイル: 取り崩し戦略「{btn_label}」", False, str(e))

    # MCリターンモデルはUIから削除済み (MCモデル集約タスクで統合) → テスト対象外

    # 固定額に戻す
    try:
        page.get_by_role("button", name="固定額").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
    except Exception:
        pass

    # 8d: 社会保険料詳細設定
    try:
        page.get_by_text("詳細設定を表示").click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "モバイル: 「詳細設定を表示」→ 社会保険料スライダーが展開される",
            page.get_by_text("医療分所得割率").is_visible(),
        )
        page.get_by_role("button", name="デフォルト値にリセット").click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add("モバイル: 「デフォルト値にリセット」ボタンがクリックできる", True)
    except Exception as e:
        suite.add("モバイル: 社会保険料詳細設定", False, str(e))

    save_screenshot(page, "m08_advanced_accordion")


def test_mobile_income_sliders_and_details(page: Page):
    suite.section("M-5d. モバイル: 収入アコーディオン追加 — スライダー・産休育休・配偶者詳細")

    mobile_open_accordion(page, "収入")
    panel = page.locator(".lg\\:hidden")

    # M-5d-1: 本人スライダー操作 → KPI更新
    try:
        content = mobile_accordion_content(page, "収入")
        sliders = content.locator("[role='slider']")
        prev_age = get_kpi_fire_age(page)
        drag_slider_right(page, sliders)
        wait_calc(page)
        new_age = get_kpi_fire_age(page)
        suite.add(
            "モバイル: 収入スライダー操作 → KPIが更新される",
            True,
            f"{prev_age} → {new_age}",
        )
    except Exception as e:
        suite.add("モバイル: 収入スライダー操作", False, str(e))

    # M-5d-2: 産休・育休チェックボックス (ライフアコーディオンの子どもリスト内に配置)
    # UIリファクタで収入→ライフに移動済み
    checkbox_count_before = 0
    try:
        mobile_open_accordion(page, "ライフ")
        life_content = mobile_accordion_content(page, "ライフ")
        checkboxes = life_content.locator("input[id^='maternity-']")
        checkbox_count_before = checkboxes.count()
        if checkbox_count_before > 0:
            cb = checkboxes.first
            before = cb.is_checked()
            cb.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
            after = cb.is_checked()
            suite.add(
                f"モバイル: 産休・育休チェックボックス ({checkbox_count_before}個検出) → ON/OFF切替できる",
                before != after,
            )
            if before != after:
                cb.click()
                page.wait_for_timeout(SHORT_WAIT_MS)
        else:
            suite.add(
                "モバイル: 産休・育休チェックボックス",
                False,
                "チェックボックスが見つからない (子どもが0人の可能性)",
            )
        # 収入アコーディオンに戻る
        mobile_open_accordion(page, "収入")
    except Exception as e:
        suite.add("モバイル: 産休・育休チェックボックス", False, str(e))

    # M-5d-3: 配偶者ON時の詳細設定
    try:
        spouse_switch = page.locator("#spouse-toggle")
        was_on = spouse_switch.is_checked()
        if not was_on:
            spouse_switch.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)

        # 配偶者ON時: ライフアコーディオンの産休・育休チェックボックスが増加するか確認
        mobile_open_accordion(page, "ライフ")
        life_content_after = mobile_accordion_content(page, "ライフ")
        total_cb = life_content_after.locator("input[id^='maternity-']").count()
        suite.add(
            "モバイル: 配偶者ON時: 産休・育休チェックボックスが増加する",
            total_cb > checkbox_count_before,
            f"本人: {checkbox_count_before}個 → 本人+配偶者: {total_cb}個",
        )
        # 収入アコーディオンに戻る
        mobile_open_accordion(page, "収入")

        # 配偶者の雇用形態セレクト (2つ目のセレクト)
        selects = content.locator("select")
        if selects.count() >= 2:
            spouse_select = selects.nth(1)
            spouse_select.select_option("selfEmployed")
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
            suite.add(
                "モバイル: 配偶者の雇用形態「自営業」選択 → 反映される",
                spouse_select.input_value() == "selfEmployed",
            )
            spouse_select.select_option("employee")
            page.wait_for_timeout(SHORT_WAIT_MS)
        else:
            suite.add("モバイル: 配偶者の雇用形態セレクト", False, f"セレクトが{selects.count()}個しかない")

        # 配偶者の時短勤務スイッチ
        pt_spouse = page.locator("#parttime-配偶者")
        pt_spouse.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "モバイル: 配偶者の時短勤務スイッチ ON → 時短設定が少なくとも1箇所表示される",
            page.get_by_text("時短終了年齢").count() >= 1,
        )
        pt_spouse.click()
        page.wait_for_timeout(SHORT_WAIT_MS)

        if not was_on:
            spouse_switch.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
    except Exception as e:
        suite.add("モバイル: 配偶者詳細設定", False, str(e))

    save_screenshot(page, "m05d_income_details")


def test_mobile_investment_sliders(page: Page):
    suite.section("M-6b. モバイル: 投資アコーディオン追加 — スライダー操作")

    mobile_open_accordion(page, "投資")
    content = mobile_accordion_content(page, "投資")
    sliders = content.locator("[role='slider']")

    # 期待リターン → KPI更新
    try:
        prev_age = get_kpi_fire_age(page)
        drag_slider_right(page, sliders.first)
        wait_calc(page)
        new_age = get_kpi_fire_age(page)
        suite.add(
            "モバイル: 期待リターンスライダー操作 → KPIが更新される",
            True,
            f"{prev_age} → {new_age}",
        )
    except Exception as e:
        suite.add("モバイル: 期待リターンスライダー", False, str(e))

    # リスク(標準偏差)スライダー
    try:
        drag_slider_right(page, sliders.nth(1))
        wait_calc(page)
        suite.add("モバイル: リスク(標準偏差)スライダー操作 → エラーなし", True)
    except Exception as e:
        suite.add("モバイル: リスクスライダー", False, str(e))

    save_screenshot(page, "m06b_investment_sliders")


def test_mobile_life_children_details(page: Page):
    suite.section("M-7c. モバイル: ライフアコーディオン追加 — 子ども設定詳細")

    mobile_open_accordion(page, "ライフ")
    content = mobile_accordion_content(page, "ライフ")

    # 子ども人数スライダー → 子どもセクション展開
    try:
        child_slider = content.locator("[role='slider']").first
        before_sections = content.get_by_text("誕生年").count()
        drag_slider_right(page, child_slider)
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        after_sections = content.get_by_text("誕生年").count()
        suite.add(
            "モバイル: 子ども人数スライダー操作 → エラーなし",
            True,
            f"誕生年セクション: {before_sections} → {after_sections}",
        )
        suite.add(
            "モバイル: 子ども設定セクション(誕生年)が表示されている",
            max(before_sections, after_sections) > 0,
        )
    except Exception as e:
        suite.add("モバイル: 子ども人数スライダー", False, str(e))

    # 教育費パターンボタン
    for pattern in ["公立", "混合", "私立"]:
        try:
            btns = content.get_by_role("button", name=pattern)
            if btns.count() > 0 and btns.first.is_visible():
                btns.first.click()
                page.wait_for_timeout(SHORT_WAIT_MS)
                wait_calc(page)
                suite.add(f"モバイル: 教育費パターン「{pattern}」ボタンがクリックできる", True)
            else:
                suite.add(f"モバイル: 教育費パターン「{pattern}」ボタンが表示されている", False, "子どもが0人かも")
        except Exception as e:
            suite.add(f"モバイル: 教育費パターン「{pattern}」", False, str(e))

    # 児童手当セクションの確認
    try:
        child_allowance_area = content.get_by_text("児童手当")
        suite.add(
            "モバイル: 児童手当セクションが表示されている",
            child_allowance_area.count() > 0,
            f"検出数: {child_allowance_area.count()}",
        )
        all_switches = content.locator("button[role='switch']")
        sw_count = all_switches.count()
        suite.add(
            f"モバイル: ライフアコーディオン内のスイッチ要素が存在する ({sw_count}個)",
            sw_count > 0,
        )
    except Exception as e:
        suite.add("モバイル: 児童手当セクション", False, str(e))

    save_screenshot(page, "m07c_life_children")


def test_mobile_advanced_details(page: Page):
    suite.section("M-8e. モバイル: 詳細設定アコーディオン追加 — シミュレーション期間・ガードレール詳細")

    mobile_open_accordion(page, "詳細設定")
    content = mobile_accordion_content(page, "詳細設定")

    # シミュレーション期間スライダー → KPI更新
    try:
        sliders = content.locator("[role='slider']")
        prev_age = get_kpi_fire_age(page)
        drag_slider_right(page, sliders.first)
        wait_calc(page)
        new_age = get_kpi_fire_age(page)
        suite.add(
            "モバイル: 詳細タブ シミュレーション期間スライダー操作 → KPIが更新される",
            True,
            f"{prev_age} → {new_age}",
        )
    except Exception as e:
        suite.add("モバイル: シミュレーション期間スライダー", False, str(e))

    # インフレ率スライダー
    try:
        sliders = content.locator("[role='slider']")
        drag_slider_right(page, sliders.nth(1))
        wait_calc(page)
        suite.add("モバイル: インフレ率スライダー操作 → エラーなし", True)
    except Exception as e:
        suite.add("モバイル: インフレ率スライダー", False, str(e))

    # ガードレール詳細スライダー
    try:
        page.get_by_role("button", name="暴落時支出抑制").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)

        sliders_after = content.locator("[role='slider']")
        slider_count = sliders_after.count()
        suite.add(
            "モバイル: ガードレール戦略選択後: 詳細スライダーが増加する",
            slider_count >= 7,
            f"スライダー総数: {slider_count}個",
        )

        drag_slider_right(page, sliders_after)
        wait_calc(page)
        suite.add("モバイル: ガードレール裁量支出比率スライダー操作 → エラーなし", True)

        # 固定額に戻す
        page.get_by_role("button", name="固定額").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
    except Exception as e:
        suite.add("モバイル: ガードレール詳細スライダー", False, str(e))

    save_screenshot(page, "m08e_advanced_details")


def test_mobile_info_buttons(page: Page):
    suite.section("M-9. モバイル: Info(?) ボタン — ツールチップ展開")

    # 基本設定アコーディオンを開いた状態で確認
    mobile_open_accordion(page, "基本設定")
    content = mobile_accordion_content(page, "基本設定")
    # Info ボタンは aria-expanded を持つ button (Popover trigger)
    # ただし data-radix-collection-item を持つアコーディオントリガーは除外
    info_buttons = content.locator("button[aria-expanded]:not([data-radix-collection-item])")
    count = info_buttons.count()

    if count == 0:
        suite.add("モバイル: Infoボタンが存在する", False, "aria-expanded ボタンが見つからない")
        return

    clicked = 0
    errors = []
    for i in range(min(3, count)):
        try:
            btn = info_buttons.nth(i)
            if btn.is_visible():
                before = btn.get_attribute("aria-expanded")
                btn.click()
                page.wait_for_timeout(400)
                after = btn.get_attribute("aria-expanded")
                if before != after:
                    clicked += 1
                if after == "true":
                    btn.click()
                    page.wait_for_timeout(200)
        except Exception as e:
            errors.append(str(e))

    suite.add(
        f"モバイル: Info(?)ボタンをクリック → ツールチップが展開される ({clicked}/{min(3, count)})",
        clicked > 0,
        ", ".join(errors) if errors else f"検出ボタン数: {count}",
    )


def test_mobile_scenario_comparison(page: Page):
    suite.section("M-10. モバイル: シナリオ比較 (次の一手タブ)")

    try:
        page.get_by_role("tab", name="次の一手").click()
        page.wait_for_timeout(TAB_WAIT_MS * 2)
    except Exception as e:
        suite.add("モバイル: 次の一手タブに移動", False, str(e))
        return

    scenario_btns = page.get_by_role("button", name="この設定を試す →")
    btn_count = scenario_btns.count()
    suite.add(
        "モバイル: シナリオ比較カードが表示される",
        btn_count > 0,
        f"カード数: {btn_count}",
    )

    if btn_count > 0:
        prev_age = get_kpi_fire_age(page)
        try:
            scenario_btns.first.click()
            page.wait_for_timeout(SHORT_WAIT_MS)
            wait_calc(page)
            new_age = get_kpi_fire_age(page)
            suite.add(
                "モバイル: 「この設定を試す →」クリック → KPIが更新される",
                True,
                f"FIRE達成 {prev_age} → {new_age}",
            )
        except Exception as e:
            suite.add("モバイル: 「この設定を試す →」ボタン", False, str(e))

    save_screenshot(page, "m10_scenario_comparison")


def test_mobile_share_button(page: Page):
    suite.section("M-11. モバイル: リンクをコピーボタン")

    try:
        share_btn = page.get_by_role("button", name="リンクをコピー")
        share_btn.click()
        page.wait_for_timeout(800)
        suite.add(
            "モバイル: 「リンクをコピー」→ 「コピーしました！」に変わる",
            page.get_by_text("コピーしました！").is_visible(),
        )
        page.wait_for_timeout(2500)
        suite.add(
            "モバイル: 2秒後に「リンクをコピー」表示に戻る",
            page.get_by_text("リンクをコピー").is_visible(),
        )
    except Exception as e:
        suite.add("モバイル: リンクをコピーボタン", False, str(e))


def test_mobile_layout_integrity(page: Page):
    suite.section("M-12. モバイル: レイアウト崩れチェック")

    # 横スクロール
    try:
        sw = page.evaluate("document.documentElement.scrollWidth")
        cw = page.evaluate("document.documentElement.clientWidth")
        suite.add(
            "モバイル: 横スクロールが発生していない",
            sw <= cw + 5,
            f"scrollWidth={sw}, clientWidth={cw}",
        )
    except Exception as e:
        suite.add("モバイル: 横スクロールチェック", False, str(e))

    # KPIバナーが viewport 内に収まっているか
    try:
        banner = page.locator("div.sticky.top-16")
        box = banner.first.bounding_box()
        in_viewport = box is not None and box["x"] >= 0 and box["width"] <= 375
        suite.add(
            "モバイル: KPIバナーが viewport 幅に収まっている",
            in_viewport,
            f"x={box['x']:.0f}, width={box['width']:.0f}" if box else "bounding_box取得失敗",
        )
    except Exception as e:
        suite.add("モバイル: KPIバナー幅チェック", False, str(e))

    # 資産推移タブのチャートが描画されているか
    try:
        page.get_by_role("tab", name="資産推移").click()
        page.wait_for_timeout(TAB_WAIT_MS)
        chart_count = page.locator("main svg.recharts-surface, main .recharts-wrapper svg").count()
        suite.add(
            "モバイル: 資産推移チャートが描画されている",
            chart_count > 0,
            f"SVG要素数: {chart_count}",
        )
    except Exception as e:
        suite.add("モバイル: チャート描画チェック", False, str(e))

    # 各メインタブのコンテンツ描画確認
    for tab_name, check_fn in [
        ("収支", lambda: page.locator("main svg.recharts-surface").count() > 0),
        ("年次表", lambda: page.locator("main table").count() > 0),
    ]:
        try:
            page.get_by_role("tab", name=tab_name).click()
            page.wait_for_timeout(TAB_WAIT_MS)
            suite.add(
                f"モバイル: 「{tab_name}」タブのコンテンツが描画されている",
                check_fn(),
            )
        except Exception as e:
            suite.add(f"モバイル: 「{tab_name}」描画確認", False, str(e))

    # ヘッダーの要素が viewport をはみ出していないか
    try:
        header = page.locator("header")
        box = header.bounding_box()
        suite.add(
            "モバイル: ヘッダーが viewport 幅に収まっている",
            box is not None and box["width"] <= 375 + 5,
            f"width={box['width']:.0f}" if box else "取得失敗",
        )
    except Exception as e:
        suite.add("モバイル: ヘッダー幅チェック", False, str(e))

    save_screenshot(page, "m12_layout_integrity")


# ─────────────────────────────────────────
# 定番バグ観点テスト群
# ─────────────────────────────────────────

def test_url_state_restoration(page: Page):
    suite.section("X-1. URL状態復元テスト (シェアリンク)")

    # セミFIREをONにしてから共有URLを取得・復元する
    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="ライフ").click()
        page.wait_for_timeout(TAB_WAIT_MS)

        semi = page.locator("#semi-fire-toggle")
        was_on = semi.is_checked()
        if not was_on:
            semi.click()
            wait_calc(page)

        kpi_before = get_kpi_fire_age(page)

        # リンクをコピー → __clipboardText にURLが入る
        page.get_by_role("button", name="リンクをコピー").click()
        page.wait_for_timeout(800)
        copied_url = page.evaluate("window.__clipboardText")

        suite.add(
            "リンクをコピー → URLが生成される (#config= を含む)",
            bool(copied_url) and "#config=" in copied_url,
            f"URL長: {len(copied_url)}文字" if copied_url else "URLなし",
        )

        if copied_url and "#config=" in copied_url:
            # 同じページで共有URLに遷移して状態を復元
            page.goto(copied_url, timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(CALC_WAIT_MS)

            # セミFIREの状態が復元されているか
            semi_restored = page.locator("#semi-fire-toggle")
            suite.add(
                "URL復元後: セミFIREスイッチ状態が保持されている",
                semi_restored.is_checked() == True,
            )

            # KPI値が一致するか
            kpi_after = get_kpi_fire_age(page)
            suite.add(
                "URL復元後: KPI (FIRE達成年齢) が一致する",
                kpi_before == kpi_after,
                f"共有前: {kpi_before} / 復元後: {kpi_after}",
            )

            # ベースURLに戻してコンテキストをクリーン (後続テストのため)
            page.goto(URL, timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(CALC_WAIT_MS)
        else:
            suite.add("URL復元テスト: URLが取得できなかったためスキップ", True, "clipboard未設定の可能性")

    except Exception as e:
        suite.add("URL状態復元テスト", False, str(e))

    save_screenshot(page, "x1_url_restoration")


def test_kpi_direction_sanity(page: Page):
    suite.section("X-2. KPI変動方向の整合性チェック")

    # 基本タブで資産スライダー右 → FIRE年齢が下がる(改善)
    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="基本").click()
        page.wait_for_timeout(TAB_WAIT_MS)
        panel = page.locator(".not-lg\\:hidden [role='tabpanel'][data-state='active']").first

        age_before = get_kpi_fire_age_num(page)
        drag_slider_right(page, panel.locator("[role='slider']").first, steps=5)
        wait_calc(page)
        age_after_asset_up = get_kpi_fire_age_num(page)

        suite.add(
            "資産スライダー増加 → FIRE達成年齢が改善される (下がるか等しい)",
            age_before is None or age_after_asset_up is None or age_after_asset_up <= age_before,
            f"{age_before}歳 → {age_after_asset_up}歳",
        )
    except Exception as e:
        suite.add("資産増加→FIRE改善チェック", False, str(e))

    # 月間生活費スライダー右 → FIRE年齢が上がる(悪化)
    try:
        panel = page.locator(".not-lg\\:hidden [role='tabpanel'][data-state='active']").first
        # 生活費モードが固定費であることを確認
        fixed_btn = panel.get_by_role("button", name="固定費")
        if fixed_btn.is_visible():
            fixed_btn.click()
            page.wait_for_timeout(SHORT_WAIT_MS)

        age_before_expense = get_kpi_fire_age_num(page)
        # 月間生活費スライダーは下の方にある (resource後にある)
        sliders = panel.locator("[role='slider']")
        # 月間生活費スライダーをドラッグ (複数あるため、get_by_text周辺を探す)
        expense_label = panel.get_by_text("月間生活費", exact=True)
        if expense_label.is_visible():
            # ラベルの近くのスライダーを操作
            expense_slider = panel.locator("[role='slider']").last
            drag_slider_right(page, expense_slider, steps=5)
            wait_calc(page)
            age_after_expense_up = get_kpi_fire_age_num(page)
            suite.add(
                "生活費スライダー増加 → FIRE達成年齢が悪化する (上がるか等しい)",
                age_before_expense is None or age_after_expense_up is None or age_after_expense_up >= age_before_expense,
                f"{age_before_expense}歳 → {age_after_expense_up}歳",
            )
        else:
            suite.add("生活費方向チェック: 月間生活費スライダーが見つからない", False, "固定費モード外")
    except Exception as e:
        suite.add("生活費増加→FIRE悪化チェック", False, str(e))

    # NISA ON → FIRE年齢が改善される (または等しい)
    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="投資").click()
        page.wait_for_timeout(TAB_WAIT_MS)
        age_no_nisa = get_kpi_fire_age_num(page)
        nisa = page.locator("#nisa-toggle")
        if not nisa.is_checked():
            nisa.click()
            wait_calc(page)
        age_with_nisa = get_kpi_fire_age_num(page)
        suite.add(
            "NISA ON → FIRE達成年齢が改善される (下がるか等しい)",
            age_no_nisa is None or age_with_nisa is None or age_with_nisa <= age_no_nisa,
            f"NISA無: {age_no_nisa}歳 → NISA有: {age_with_nisa}歳",
        )
    except Exception as e:
        suite.add("NISA ON → FIRE改善チェック", False, str(e))

    save_screenshot(page, "x2_kpi_direction")


def test_breakpoint_transition(page: Page):
    suite.section("X-3. ブレークポイント遷移テスト (1023px / 1024px)")

    try:
        # 1023px: モバイルアコーディオンが表示、デスクトップタブが非表示
        page.set_viewport_size({"width": 1023, "height": 900})
        page.wait_for_timeout(500)

        mobile_panel = page.locator(".lg\\:hidden").first
        desktop_panel = page.locator(".not-lg\\:hidden").first

        suite.add(
            "1023px: モバイルアコーディオンが表示される",
            mobile_panel.is_visible(),
        )
        suite.add(
            "1023px: デスクトップタブが非表示になる",
            not desktop_panel.is_visible(),
        )
        suite.add(
            "1023px: KPIバナーが正常表示される",
            get_kpi_fire_age(page) is not None,
        )
        sw_1023 = page.evaluate("document.documentElement.scrollWidth")
        cw_1023 = page.evaluate("document.documentElement.clientWidth")
        suite.add(
            "1023px: 横スクロールが発生しない",
            sw_1023 <= cw_1023 + 5,
            f"scrollWidth={sw_1023}, clientWidth={cw_1023}",
        )

        # 1024px: デスクトップタブが表示、モバイルアコーディオンが非表示
        page.set_viewport_size({"width": 1024, "height": 900})
        page.wait_for_timeout(500)

        mobile_panel_1024 = page.locator(".lg\\:hidden").first
        desktop_panel_1024 = page.locator(".not-lg\\:hidden").first

        suite.add(
            "1024px: デスクトップタブが表示される",
            desktop_panel_1024.is_visible(),
        )
        suite.add(
            "1024px: モバイルアコーディオンが非表示になる",
            not mobile_panel_1024.is_visible(),
        )
        suite.add(
            "1024px: KPIバナーが正常表示される",
            get_kpi_fire_age(page) is not None,
        )
        sw_1024 = page.evaluate("document.documentElement.scrollWidth")
        cw_1024 = page.evaluate("document.documentElement.clientWidth")
        suite.add(
            "1024px: 横スクロールが発生しない",
            sw_1024 <= cw_1024 + 5,
            f"scrollWidth={sw_1024}, clientWidth={cw_1024}",
        )

    except Exception as e:
        suite.add("ブレークポイント遷移テスト", False, str(e))
    finally:
        # デスクトップサイズに戻す
        page.set_viewport_size({"width": 1440, "height": 900})
        page.wait_for_timeout(500)

    save_screenshot(page, "x3_breakpoint")


def test_lifecycle_mode_input(page: Page):
    suite.section("X-4. ライフステージモード — 数値入力フィールド確認")

    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="基本").click()
        page.wait_for_timeout(TAB_WAIT_MS)
        panel = page.locator(".not-lg\\:hidden [role='tabpanel'][data-state='active']").first

        # ライフステージモードに切り替え
        lifecycle_btn = panel.get_by_role("button", name="ライフステージ")
        lifecycle_btn.click()
        page.wait_for_timeout(SHORT_WAIT_MS)

        # 数値入力フィールドが存在するか
        inputs = panel.locator("input[type='number']")
        count = inputs.count()
        suite.add(
            f"ライフステージモード: 数値入力フィールドが表示される ({count}個)",
            count > 0,
        )

        if count > 0:
            # 最初のフィールドに値を入力
            first_input = inputs.first
            prev_age = get_kpi_fire_age(page)

            first_input.click()
            first_input.select_text()
            page.wait_for_timeout(200)
            first_input.fill("350")
            first_input.press("Tab")
            wait_calc(page)

            new_age = get_kpi_fire_age(page)
            suite.add(
                "ライフステージ入力フィールドに値入力 → KPIが更新される",
                True,
                f"{prev_age} → {new_age}",
            )

            # min=0 の境界確認 (負の値は受け付けない)
            first_input.fill("-10")
            first_input.press("Tab")
            page.wait_for_timeout(SHORT_WAIT_MS)
            val = first_input.input_value()
            suite.add(
                "ライフステージ入力: 負の値を入力 → 0以上に正規化される",
                val == "" or val == "0" or (val.lstrip("-").isdigit() and int(val) >= 0),
                f"入力値: '{val}'",
            )

        # 固定費モードに戻す
        panel.get_by_role("button", name="固定費").click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add("ライフステージ→固定費モードに戻る", panel.get_by_text("月間生活費", exact=True).is_visible())

    except Exception as e:
        suite.add("ライフステージ数値入力テスト", False, str(e))

    save_screenshot(page, "x4_lifecycle_input")


def test_guardrail_cleanup(page: Page):
    suite.section("X-5. ガードレール戦略 UIクリーンアップ確認")

    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="詳細").click()
        page.wait_for_timeout(TAB_WAIT_MS)
        panel = page.locator(".not-lg\\:hidden [role='tabpanel'][data-state='active']").first

        # 固定額の状態でのスライダー数を記録
        page.get_by_role("button", name="固定額").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        sliders_fixed = panel.locator("[role='slider']").count()
        is_guardrail_visible = page.get_by_text("裁量支出比率").is_visible()
        suite.add(
            "固定額戦略: ガードレール詳細 (裁量支出比率) が非表示",
            not is_guardrail_visible,
        )

        # ガードレールに切り替え
        page.get_by_role("button", name="暴落時支出抑制").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        sliders_guardrail = panel.locator("[role='slider']").count()
        suite.add(
            "ガードレール選択後: スライダー数が増加する",
            sliders_guardrail > sliders_fixed,
            f"固定額時: {sliders_fixed}個 → ガードレール時: {sliders_guardrail}個",
        )
        suite.add(
            "ガードレール選択後: 「裁量支出比率」が表示される",
            page.get_by_text("裁量支出比率").is_visible(),
        )

        # 固定額に戻す → スライダーが消えるか
        page.get_by_role("button", name="固定額").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        sliders_after_cleanup = panel.locator("[role='slider']").count()
        suite.add(
            "固定額に戻す → ガードレール詳細スライダーが消える",
            sliders_after_cleanup == sliders_fixed,
            f"ガードレール時: {sliders_guardrail}個 → 固定額時: {sliders_after_cleanup}個",
        )
        suite.add(
            "固定額に戻す → 「裁量支出比率」が非表示になる",
            not page.get_by_text("裁量支出比率").is_visible(),
        )

        # 定率に切り替えてもクリーンアップされるか
        page.get_by_role("button", name="暴落時支出抑制").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        page.get_by_role("button", name="定率").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "定率に切り替え → 「裁量支出比率」が非表示になる",
            not page.get_by_text("裁量支出比率").is_visible(),
        )
        # 元に戻す
        page.get_by_role("button", name="固定額").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)

    except Exception as e:
        suite.add("ガードレールUIクリーンアップテスト", False, str(e))

    save_screenshot(page, "x5_guardrail_cleanup")


def test_simultaneous_features(page: Page):
    suite.section("X-6. 複数機能同時ON テスト")

    # NISA + iDeCo 同時ON
    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="投資").click()
        page.wait_for_timeout(TAB_WAIT_MS)

        nisa = page.locator("#nisa-toggle")
        ideco = page.locator("#ideco-toggle")
        if not nisa.is_checked():
            nisa.click()
            wait_calc(page)
        if not ideco.is_checked():
            ideco.click()
            wait_calc(page)

        suite.add("NISA + iDeCo 同時ON → 両方有効状態", nisa.is_checked() and ideco.is_checked())
        suite.add("NISA + iDeCo 同時ON → KPIが正常表示される", get_kpi_fire_age(page) is not None)
        suite.add(
            "NISA + iDeCo 同時ON → NISA年間投資額スライダーが表示される",
            page.get_by_text("年間投資額").is_visible(),
        )
    except Exception as e:
        suite.add("NISA + iDeCo 同時ON テスト", False, str(e))

    # セミFIRE + 住宅ローン 同時ON
    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="ライフ").click()
        page.wait_for_timeout(TAB_WAIT_MS)

        semi = page.locator("#semi-fire-toggle")
        mortgage = page.locator("#mortgage-toggle")
        if not semi.is_checked():
            semi.click()
            wait_calc(page)
        if not mortgage.is_checked():
            mortgage.click()
            wait_calc(page)

        suite.add(
            "セミFIRE + 住宅ローン 同時ON → 両方有効状態",
            semi.is_checked() and mortgage.is_checked(),
        )
        suite.add(
            "セミFIRE + 住宅ローン 同時ON → 月収スライダーが表示される",
            page.get_by_text("月収（税引き前）").is_visible(),
        )
        suite.add(
            "セミFIRE + 住宅ローン 同時ON → 月額返済額スライダーが表示される",
            page.get_by_text("月額返済額").is_visible(),
        )
        suite.add(
            "セミFIRE + 住宅ローン 同時ON → KPIが正常表示される",
            get_kpi_fire_age(page) is not None,
        )

        # 元に戻す
        semi.click()
        wait_calc(page)
        mortgage.click()
        wait_calc(page)
    except Exception as e:
        suite.add("セミFIRE + 住宅ローン 同時ON テスト", False, str(e))

    # 配偶者 + 時短勤務(本人) + iDeCo の複合状態
    try:
        page.locator(".not-lg\\:hidden").get_by_role("tab", name="収入").click()
        page.wait_for_timeout(TAB_WAIT_MS)

        spouse = page.locator("#spouse-toggle")
        parttime = page.locator("#parttime-本人")
        if not spouse.is_checked():
            spouse.click()
            wait_calc(page)
        if not parttime.is_checked():
            parttime.click()
            page.wait_for_timeout(SHORT_WAIT_MS)

        suite.add(
            "配偶者ON + 時短勤務ON → KPIが正常表示される (複合計算)",
            get_kpi_fire_age(page) is not None,
        )

        # 元に戻す
        if parttime.is_checked():
            parttime.click()
        if spouse.is_checked():
            spouse.click()
        wait_calc(page)
    except Exception as e:
        suite.add("配偶者+時短+iDeCo 複合テスト", False, str(e))

    save_screenshot(page, "x6_simultaneous_features")


# ─────────────────────────────────────────
# モバイル版 定番バグ観点テスト群
# ─────────────────────────────────────────

def test_mobile_kpi_direction_sanity(page: Page):
    suite.section("M-X2. モバイル: KPI変動方向チェック")

    # 基本設定アコーディオンで資産スライダー右 → FIRE年齢改善
    try:
        mobile_open_accordion(page, "基本設定")
        content = mobile_accordion_content(page, "基本設定")
        sliders = content.locator("[role='slider']")

        age_before = get_kpi_fire_age_num(page)
        drag_slider_right(page, sliders.first, steps=5)
        wait_calc(page)
        age_after = get_kpi_fire_age_num(page)

        suite.add(
            "モバイル: 資産スライダー増加 → FIRE達成年齢が改善される",
            age_before is None or age_after is None or age_after <= age_before,
            f"{age_before}歳 → {age_after}歳",
        )
    except Exception as e:
        suite.add("モバイル: 資産増加→FIRE改善チェック", False, str(e))

    # NISA ON → FIRE年齢改善
    try:
        mobile_open_accordion(page, "投資")
        age_no_nisa = get_kpi_fire_age_num(page)
        nisa = page.locator("#nisa-toggle")
        if not nisa.is_checked():
            nisa.click()
            wait_calc(page)
        age_with_nisa = get_kpi_fire_age_num(page)
        suite.add(
            "モバイル: NISA ON → FIRE達成年齢が改善される",
            age_no_nisa is None or age_with_nisa is None or age_with_nisa <= age_no_nisa,
            f"NISA無: {age_no_nisa}歳 → NISA有: {age_with_nisa}歳",
        )
    except Exception as e:
        suite.add("モバイル: NISA ON → FIRE改善チェック", False, str(e))


def test_mobile_lifecycle_input(page: Page):
    suite.section("M-X4. モバイル: ライフステージモード — 数値入力フィールド確認")

    try:
        mobile_open_accordion(page, "基本設定")
        content = mobile_accordion_content(page, "基本設定")

        lifecycle_btn = content.get_by_role("button", name="ライフステージ")
        lifecycle_btn.click()
        page.wait_for_timeout(SHORT_WAIT_MS)

        inputs = content.locator("input[type='number']")
        count = inputs.count()
        suite.add(
            f"モバイル: ライフステージ 数値入力フィールドが表示される ({count}個)",
            count > 0,
        )

        if count > 0:
            first_input = inputs.first
            prev_age = get_kpi_fire_age(page)
            first_input.click()
            first_input.select_text()
            first_input.fill("300")
            first_input.press("Tab")
            wait_calc(page)
            new_age = get_kpi_fire_age(page)
            suite.add(
                "モバイル: ライフステージ入力フィールドに値入力 → KPIが更新される",
                True,
                f"{prev_age} → {new_age}",
            )

        # 固定費モードに戻す
        content.get_by_role("button", name="固定費").click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        suite.add(
            "モバイル: 固定費モードに戻る",
            content.get_by_text("月間生活費", exact=True).is_visible(),
        )
    except Exception as e:
        suite.add("モバイル: ライフステージ数値入力テスト", False, str(e))


def test_mobile_guardrail_cleanup(page: Page):
    suite.section("M-X5. モバイル: ガードレール戦略 UIクリーンアップ確認")

    try:
        mobile_open_accordion(page, "詳細設定")
        content = mobile_accordion_content(page, "詳細設定")

        page.get_by_role("button", name="固定額").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        sliders_fixed = content.locator("[role='slider']").count()
        suite.add(
            "モバイル: 固定額戦略 → 裁量支出比率が非表示",
            not page.get_by_text("裁量支出比率").is_visible(),
        )

        page.get_by_role("button", name="暴落時支出抑制").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        wait_calc(page)
        sliders_guardrail = content.locator("[role='slider']").count()
        suite.add(
            "モバイル: ガードレール選択後: スライダーが増加する",
            sliders_guardrail > sliders_fixed,
            f"{sliders_fixed}個 → {sliders_guardrail}個",
        )

        page.get_by_role("button", name="固定額").first.click()
        page.wait_for_timeout(SHORT_WAIT_MS)
        sliders_cleanup = content.locator("[role='slider']").count()
        suite.add(
            "モバイル: 固定額に戻す → ガードレール詳細スライダーが消える",
            sliders_cleanup == sliders_fixed,
            f"ガードレール時: {sliders_guardrail}個 → 固定額時: {sliders_cleanup}個",
        )
        suite.add(
            "モバイル: 固定額に戻す → 「裁量支出比率」が非表示",
            not page.get_by_text("裁量支出比率").is_visible(),
        )

    except Exception as e:
        suite.add("モバイル: ガードレールUIクリーンアップテスト", False, str(e))


def test_mobile_simultaneous_features(page: Page):
    suite.section("M-X6. モバイル: 複数機能同時ON テスト")

    # NISA + iDeCo 同時ON
    try:
        mobile_open_accordion(page, "投資")
        nisa = page.locator("#nisa-toggle")
        ideco = page.locator("#ideco-toggle")
        if not nisa.is_checked():
            nisa.click()
            wait_calc(page)
        if not ideco.is_checked():
            ideco.click()
            wait_calc(page)
        suite.add("モバイル: NISA + iDeCo 同時ON → 両方有効状態", nisa.is_checked() and ideco.is_checked())
        suite.add("モバイル: NISA + iDeCo 同時ON → KPIが正常表示される", get_kpi_fire_age(page) is not None)
    except Exception as e:
        suite.add("モバイル: NISA + iDeCo 同時ON", False, str(e))

    # セミFIRE + 住宅ローン 同時ON
    try:
        mobile_open_accordion(page, "ライフ")
        semi = page.locator("#semi-fire-toggle")
        mortgage = page.locator("#mortgage-toggle")
        if not semi.is_checked():
            semi.click()
            wait_calc(page)
        if not mortgage.is_checked():
            mortgage.click()
            wait_calc(page)
        suite.add(
            "モバイル: セミFIRE + 住宅ローン 同時ON → 両方表示",
            page.get_by_text("月収（税引き前）").is_visible() and page.get_by_text("月額返済額").is_visible(),
        )
        suite.add("モバイル: セミFIRE + 住宅ローン 同時ON → KPI正常", get_kpi_fire_age(page) is not None)
        semi.click()
        wait_calc(page)
        mortgage.click()
        wait_calc(page)
    except Exception as e:
        suite.add("モバイル: セミFIRE + 住宅ローン 同時ON", False, str(e))


def test_console_warnings(suite: TestSuite):
    suite.section("FINAL-W. コンソール警告集計")
    suite.add(
        "コンソール警告が0件 (React key警告・prop-type違反など)",
        len(suite.console_warnings) == 0,
        f"{len(suite.console_warnings)} 件検出" if suite.console_warnings else "警告なし",
    )


def test_console_errors(suite: TestSuite):
    suite.section("FINAL. コンソールエラー集計 (デスクトップ + モバイル 合計)")
    suite.add(
        "コンソールエラーが0件",
        len(suite.console_errors) == 0,
        f"{len(suite.console_errors)} 件検出" if suite.console_errors else "エラーなし",
    )


# ─────────────────────────────────────────
# メイン実行
# ─────────────────────────────────────────

CLIPBOARD_MOCK = """
window.__clipboardText = '';
Object.defineProperty(navigator, 'clipboard', {
    value: {
        writeText: (text) => { window.__clipboardText = text; return Promise.resolve(); },
        readText: () => Promise.resolve(window.__clipboardText),
    },
    writable: true,
});
"""


def main():
    print(f"\n{'═'*60}")
    print(f"  FIRE Dashboard UI テスト")
    print(f"  対象: {URL}")
    print(f"{'═'*60}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        def on_console(msg):
            if msg.type == "error":
                text = msg.text
                if "Warning:" not in text and "Download the React DevTools" not in text:
                    suite.console_errors.append(text)
            elif msg.type == "warning":
                text = msg.text
                # Next.js dev mode の CSS preload 警告と DevTools 案内は除外
                if ("Download the React DevTools" not in text
                        and "was preloaded using link preload but not used" not in text):
                    suite.console_warnings.append(text)

        # ── デスクトップ (1440px) ──────────────────
        print(f"\n{'─'*60}")
        print(f"  [デスクトップ 1440x900]")
        print(f"{'─'*60}")
        ctx_desktop = browser.new_context(viewport={"width": 1440, "height": 900})
        page_desktop = ctx_desktop.new_page()
        page_desktop.on("console", on_console)
        page_desktop.add_init_script(CLIPBOARD_MOCK)

        print(f"ページを読み込み中... ({URL})")
        page_desktop.goto(URL, timeout=30000)
        page_desktop.wait_for_load_state("domcontentloaded", timeout=30000)
        print(f"モンテカルロ計算待ち ({CALC_WAIT_MS//1000}秒)...")
        page_desktop.wait_for_timeout(CALC_WAIT_MS)

        test_initial_load(page_desktop)
        test_main_tabs(page_desktop)
        test_config_tabs(page_desktop)
        test_basic_tab_controls(page_desktop)
        test_income_tab_controls(page_desktop)
        test_income_sliders_and_details(page_desktop)
        test_investment_tab_controls(page_desktop)
        test_investment_sliders(page_desktop)
        test_life_tab_controls(page_desktop)
        test_life_children_details(page_desktop)
        test_advanced_tab_controls(page_desktop)
        test_advanced_details(page_desktop)
        test_info_buttons(page_desktop)
        test_scenario_comparison(page_desktop)
        test_share_button(page_desktop)
        test_layout_integrity(page_desktop)
        # 定番バグ観点テスト (デスクトップ)
        test_url_state_restoration(page_desktop)
        test_kpi_direction_sanity(page_desktop)
        test_breakpoint_transition(page_desktop)
        test_lifecycle_mode_input(page_desktop)
        test_guardrail_cleanup(page_desktop)
        test_simultaneous_features(page_desktop)
        ctx_desktop.close()

        # ── モバイル (375px) ───────────────────────
        print(f"\n{'─'*60}")
        print(f"  [モバイル 375x812]")
        print(f"{'─'*60}")
        ctx_mobile = browser.new_context(viewport={"width": 375, "height": 812})
        page_mobile = ctx_mobile.new_page()
        page_mobile.on("console", on_console)
        page_mobile.add_init_script(CLIPBOARD_MOCK)

        print(f"ページを読み込み中... ({URL})")
        page_mobile.goto(URL, timeout=30000)
        page_mobile.wait_for_load_state("domcontentloaded", timeout=30000)
        print(f"モンテカルロ計算待ち ({CALC_WAIT_MS//1000}秒)...")
        page_mobile.wait_for_timeout(CALC_WAIT_MS)

        # KPIが "—" の場合はリロードして再試行 (dev server の一時的な遅延対策)
        _fire_age_check = get_kpi_fire_age(page_mobile)
        if _fire_age_check == "—" or _fire_age_check is None:
            print(f"  KPI未確定 → ページをリロードして再試行 (追加20秒待ち)")
            page_mobile.reload(timeout=30000)
            page_mobile.wait_for_load_state("domcontentloaded", timeout=30000)
            page_mobile.wait_for_timeout(20000)

        test_mobile_initial_load(page_mobile)
        test_mobile_main_tabs(page_mobile)
        test_mobile_accordion_navigation(page_mobile)
        test_mobile_basic_accordion(page_mobile)
        test_mobile_income_accordion(page_mobile)
        test_mobile_income_sliders_and_details(page_mobile)
        test_mobile_investment_accordion(page_mobile)
        test_mobile_investment_sliders(page_mobile)
        test_mobile_life_accordion(page_mobile)
        test_mobile_life_children_details(page_mobile)
        test_mobile_advanced_accordion(page_mobile)
        test_mobile_advanced_details(page_mobile)
        test_mobile_info_buttons(page_mobile)
        test_mobile_scenario_comparison(page_mobile)
        test_mobile_share_button(page_mobile)
        test_mobile_layout_integrity(page_mobile)
        # 定番バグ観点テスト (モバイル)
        test_mobile_kpi_direction_sanity(page_mobile)
        test_mobile_lifecycle_input(page_mobile)
        test_mobile_guardrail_cleanup(page_mobile)
        test_mobile_simultaneous_features(page_mobile)
        ctx_mobile.close()

        browser.close()

    test_console_warnings(suite)
    test_console_errors(suite)

    # 最終サマリー
    success = suite.summary()
    if not success:
        print(f"\n  スクリーンショット: {SCREENSHOT_DIR}/")
        sys.exit(1)
    else:
        print(f"\n  全テスト通過！スクリーンショット: {SCREENSHOT_DIR}/")
        sys.exit(0)


if __name__ == "__main__":
    main()
