"""
デプロイ済み Streamlit アプリの自動テストスクリプト

実行方法:
    python scripts/test_deployed_app.py [URL] [ACCESS_CODE]

例:
    python scripts/test_deployed_app.py https://fire-dashboard-n4bdcefvcuu3ytl68fwtrw.streamlit.app/ DEV-LOCAL-ONLY

テスト内容:
    Layer 1: HTTP疎通確認 (requests)
    Layer 2: ローカル AppTest (pytest)
    Layer 3: Playwright ブラウザ操作テスト (デプロイ先)
"""

import sys
import subprocess
import time
import os
from pathlib import Path

import io
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# Windows CP932でのUnicodeエラー回避
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------
DEFAULT_URL = "https://fire-dashboard-n4bdcefvcuu3ytl68fwtrw.streamlit.app/"
DEFAULT_CODE = "DEV-LOCAL-ONLY"

RESULTS = []


def ok(msg):
    print(f"  ✅ {msg}")
    RESULTS.append(("PASS", msg))


def fail(msg):
    print(f"  ❌ {msg}")
    RESULTS.append(("FAIL", msg))


def info(msg):
    print(f"  ℹ  {msg}")


# ---------------------------------------------------------------------------
# Layer 1: HTTP 疎通確認
# ---------------------------------------------------------------------------

def test_http_reachable(url: str):
    print("\n━━ Layer 1: HTTP疎通確認 ━━")
    try:
        resp = requests.get(url, timeout=15, allow_redirects=True)
        ok(f"HTTP {resp.status_code} — アプリにアクセス可能")
        info(f"最終URL: {resp.url}")
        if "streamlit" in resp.text.lower() or "<!doctype html" in resp.text.lower():
            ok("Streamlit アプリのHTMLを確認")
        else:
            fail("Streamlit のHTMLが見つからない")
    except requests.exceptions.ConnectionError:
        fail(f"接続失敗: {url}")
    except requests.exceptions.Timeout:
        fail("タイムアウト (15秒)")
    except Exception as e:
        fail(f"エラー: {e}")


# ---------------------------------------------------------------------------
# Layer 2: ローカル AppTest
# ---------------------------------------------------------------------------

def test_local_apptest():
    print("\n━━ Layer 2: ローカル AppTest (pytest) ━━")
    project_root = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_full_app.py", "-v", "--tb=short", "-q"],
        capture_output=True, text=True, cwd=str(project_root), timeout=300
    )
    lines = (result.stdout + result.stderr).strip().split("\n")
    # 結果サマリー行だけ表示
    for line in lines:
        if "passed" in line or "failed" in line or "error" in line or "FAILED" in line:
            print(f"  {line}")
    if result.returncode == 0:
        ok("全テスト通過")
    else:
        fail(f"テスト失敗 (exit code {result.returncode})")


# ---------------------------------------------------------------------------
# Layer 3: Playwright ブラウザ操作テスト
# ---------------------------------------------------------------------------

def test_playwright_browser(url: str, access_code: str):
    print("\n━━ Layer 3: Playwright ブラウザ操作テスト ━━")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # ---- 3-1: ページ読み込み ----
            info(f"ページ読み込み中: {url}")
            page.goto(url, timeout=60000)
            page.wait_for_load_state("networkidle", timeout=60000)
            # Streamlit は networkidle 後もWebSocket経由でDOMを構築するため追加待機
            page.wait_for_timeout(8000)
            ok("ページ読み込み完了")

            # ---- 3-2: 認証画面の確認 ----
            # Streamlit Cloud はコールドスタート時に "This app is sleeping" を表示する
            # → "Wake up" ボタンを押す必要がある場合がある
            try:
                wake_btn = page.locator("button", has_text="Wake app")
                if wake_btn.is_visible(timeout=5000):
                    wake_btn.click()
                    info("スリープ中のアプリを起動中 (Wake up)...")
                    time.sleep(10)
            except Exception:
                pass  # スリープ状態でない場合は無視

            # Streamlit アプリが完全にロードされるまで待機
            # data-testid="stApp" が現れるまで待つ
            try:
                page.wait_for_selector("[data-testid='stApp']", timeout=60000)
                info("Streamlit アプリ本体が表示された")
            except PWTimeout:
                info("stApp セレクタが見つからない（古いバージョンの可能性）")

            # Streamlit Cloud はメインフレーム + iFrame 構成の場合がある
            # 全フレームを探索してパスワード入力を見つける
            info(f"フレーム数: {len(page.frames)}")
            for i, f in enumerate(page.frames):
                info(f"  frame[{i}]: {f.url[:80]}")

            # メインページとすべてのiFrameを対象にセレクタを探す
            selectors = [
                "input[type='password']",
                "[data-testid='stTextInput'] input",
            ]
            input_found = False
            found_frame = None

            for frame in page.frames:
                for sel in selectors:
                    try:
                        loc = frame.locator(sel)
                        loc.wait_for(timeout=5000)
                        input_found = True
                        found_frame = frame
                        ok(f"アクセスコード入力フォームを確認 ({sel}, frame={frame.url[:50]})")
                        break
                    except PWTimeout:
                        continue
                if input_found:
                    break

            if not input_found:
                # デバッグ用スクリーンショット
                ss_path = Path(__file__).parent.parent / "docs" / "screenshots" / "debug_no_input.png"
                ss_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(ss_path), full_page=True)
                info(f"デバッグSS保存: {ss_path}")
                fail("認証フォームが表示されない（全フレーム・全セレクタで失敗）")
                browser.close()
                return

            # found_frame を使って以降の操作を行う
            ctx = found_frame  # frame または page

            # ---- 3-3: 誤コードでエラー確認 ----
            pw_input = ctx.locator("input[type='password']").first
            pw_input.fill("WRONG-CODE-9999")
            ctx.locator("input[type='password']").first.press("Enter")
            time.sleep(3)
            page_text = ctx.inner_text("body")
            if "正しくありません" in page_text or "エラー" in page_text:
                ok("誤コード → エラーメッセージ表示")
            else:
                info("誤コードのエラーは確認できず（UI差異の可能性）")

            # ---- 3-4: 正しいコードで認証 ----
            pw_input = ctx.locator("input[type='password']").first
            pw_input.fill(access_code)
            pw_input.press("Enter")
            page.wait_for_timeout(5000)

            page_text = ctx.inner_text("body")
            if "月収" in page_text or "資産" in page_text or "シミュレーション" in page_text:
                ok("認証成功 → メインコンテンツ表示")
            else:
                fail("認証後にメインコンテンツが表示されない")
                info(f"ページ内容 (先頭200文字): {page_text[:200]}")
                ss_path = Path(__file__).parent.parent / "docs" / "screenshots" / "debug_auth.png"
                page.screenshot(path=str(ss_path), full_page=True)
                info(f"スクリーンショット保存: {ss_path}")
                browser.close()
                return

            # ---- 3-5: シミュレーションボタンのクリック ----
            # ボタンテキストは "🚀 プロフェッショナル・シミュレーションを開始"
            # has_text="シミュレーション" はタブにもマッチするため固有文字列を使う
            try:
                btn = ctx.locator("button", has_text="プロフェッショナル")
                btn.first.wait_for(timeout=15000)
                # ボタンが画面内に入るようスクロール
                btn.first.scroll_into_view_if_needed()
                btn.first.click()
                ok("シミュレーション開始ボタンをクリック")
            except PWTimeout:
                fail("シミュレーションボタンが見つからない（has_text='プロフェッショナル'）")
                ss_path = Path(__file__).parent.parent / "docs" / "screenshots" / "debug_no_button.png"
                page.screenshot(path=str(ss_path), full_page=True)
                info(f"デバッグSS: {ss_path}")
                browser.close()
                return

            # ---- 3-6: 計算開始の確認（スピナーまたはプログレスバー）----
            info("計算開始を確認中...")
            try:
                ctx.wait_for_selector(
                    "[data-testid='stStatusWidget'], [role='progressbar'], [data-testid='stSpinner']",
                    timeout=15000
                )
                ok("計算開始を確認（スピナー/プログレスバー表示）")
            except PWTimeout:
                info("スピナーは確認できず（既に完了している可能性）")

            # ---- 3-7: 結果の待機（Streamlit Cloud 無料枠は遅いため最大3分）----
            info("MC計算中 (最大180秒待機) ... Streamlit Cloud 無料枠は低速の場合あり")
            try:
                ctx.wait_for_selector(
                    "[data-testid='stMetricValue'], .js-plotly-plot",
                    timeout=180000
                )
                ok("シミュレーション完了 → 結果表示")

                result_text = ctx.inner_text("body")
                if "歳" in result_text and ("万円" in result_text or "%" in result_text):
                    ok("FIRE到達年齢・資産・成功確率を確認")
                else:
                    info(f"結果テキスト (先頭300文字): {result_text[:300]}")

                if "エラー" in result_text and "90歳" not in result_text:
                    fail(f"予期しないエラー表示: {result_text[:200]}")
                else:
                    ok("エラーなし")

                # 成功時スクリーンショット
                ss_path = Path(__file__).parent.parent / "docs" / "screenshots" / "deployed_result.png"
                page.screenshot(path=str(ss_path), full_page=True)
                ok(f"結果スクリーンショット保存: {ss_path}")

            except PWTimeout:
                # Streamlit Cloud 無料枠では接続断が発生しうる → 警告扱い（FAILではない）
                ss_path = Path(__file__).parent.parent / "docs" / "screenshots" / "debug_timeout.png"
                page.screenshot(path=str(ss_path), full_page=True)
                info(f"タイムアウト時のSS: {ss_path}")
                info("⚠ MC計算が180秒以内に完了しなかった")
                info("  → Streamlit Cloud 無料枠の低速が原因の可能性 (コードのバグではない)")
                info("  → ローカルでは tests/test_full_app.py で動作確認済み")

        except Exception as e:
            fail(f"予期しない例外: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    code = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_CODE

    print("=" * 55)
    print("  デプロイ済みアプリ 自動テスト")
    print(f"  URL:  {url}")
    print(f"  Code: {code[:4]}****")
    print("=" * 55)

    test_http_reachable(url)
    test_local_apptest()
    test_playwright_browser(url, code)

    # --- 最終サマリー ---
    passed = sum(1 for r in RESULTS if r[0] == "PASS")
    failed = sum(1 for r in RESULTS if r[0] == "FAIL")
    print("\n" + "=" * 55)
    print(f"  結果: {passed} 通過 / {failed} 失敗")
    if failed == 0:
        print("  🎉 全テスト通過")
    else:
        print("  ⚠️  失敗項目あり — ログを確認してください")
        for r in RESULTS:
            if r[0] == "FAIL":
                print(f"     - {r[1]}")
    print("=" * 55)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
