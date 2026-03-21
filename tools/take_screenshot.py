# -*- coding: utf-8 -*-
"""
Next.js FIRE Dashboard - Playwright screenshot script

Usage:
    # 1. Start dev server
    pnpm dev

    # 2. Run in another terminal (set encoding on Windows)
    set PYTHONIOENCODING=utf-8 && python take_screenshot.py

Output: docs/screenshots/
"""

import sys
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

# Windows terminal encoding fix
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

URL = os.environ.get("FIRE_URL", "http://localhost:3000")
OUT_DIR = Path("docs/screenshots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# note用の確定画像ディレクトリ（git管理）
NOTE_DIR = Path("docs/images/note")

# Time to wait for MC 1000-run calculation (ms). Increase if chart is missing.
MC_WAIT_MS = 10000


def take_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # --- Desktop: KPI + chart visible (1440x900, clip to content) ---
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(URL, timeout=30000)
        page.wait_for_load_state("domcontentloaded", timeout=30000)
        page.wait_for_timeout(MC_WAIT_MS)

        out = OUT_DIR / "result_top.png"
        # clip to top 860px: header + KPI banner + chart area
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": 1440, "height": 860})
        print(f"[OK] {out}")

        # --- Desktop: full page (viewport 1440x900 to avoid min-height:100vh inflation) ---
        page2 = browser.new_page(viewport={"width": 1440, "height": 900})
        page2.goto(URL, timeout=30000)
        page2.wait_for_load_state("domcontentloaded", timeout=30000)
        page2.wait_for_timeout(MC_WAIT_MS)

        out = OUT_DIR / "full_page.png"
        page2.screenshot(path=str(out), full_page=True)
        content_height = page2.evaluate("document.documentElement.scrollHeight")
        print(f"[OK] {out} (height={content_height}px)")

        # --- Chart area only ---
        chart_heading = page2.get_by_text("資産推移予測").first
        if chart_heading.count() > 0:
            chart_heading.scroll_into_view_if_needed()
            page2.wait_for_timeout(300)
            box = chart_heading.bounding_box()
            if box:
                out = OUT_DIR / "assets_chart.png"
                page2.screenshot(
                    path=str(out),
                    clip={
                        "x": max(0, box["x"] - 20),
                        "y": max(0, box["y"] - 10),
                        "width": 900,
                        "height": 450,
                    },
                )
                print(f"[OK] {out}")
        else:
            print("[SKIP] assets_chart - heading not found")

        # --- Mobile: above fold (KPI banner visible) ---
        page3 = browser.new_page(viewport={"width": 375, "height": 812})
        page3.goto(URL, timeout=30000)
        page3.wait_for_load_state("domcontentloaded", timeout=30000)
        page3.wait_for_timeout(MC_WAIT_MS)

        out = OUT_DIR / "mobile_top.png"
        page3.screenshot(path=str(out))
        print(f"[OK] {out}")

        # --- Mobile: chart tab (shows MC simulation graph on mobile) ---
        page4 = browser.new_page(viewport={"width": 375, "height": 812})
        page4.goto(URL, timeout=30000)
        page4.wait_for_load_state("domcontentloaded", timeout=30000)
        page4.wait_for_timeout(MC_WAIT_MS)

        # switch to chart tab (資産推移)
        chart_tab = page4.get_by_role("tab", name="資産推移").first
        if chart_tab.is_visible():
            chart_tab.click()
            page4.wait_for_timeout(1000)

        out = OUT_DIR / "mobile_chart.png"
        page4.screenshot(path=str(out))
        print(f"[OK] {out}")

        browser.close()

    print(f"\nDone: {OUT_DIR}/")


def confirm_to_note():
    """確定したスクリーンショットを docs/images/note/ にコピーする。"""
    import shutil

    NOTE_DIR.mkdir(parents=True, exist_ok=True)
    files = [
        "result_top.png",
        "full_page.png",
        "assets_chart.png",
        "mobile_top.png",
        "mobile_chart.png",
    ]
    for f in files:
        src = OUT_DIR / f
        dst = NOTE_DIR / f
        if src.exists():
            shutil.copy2(src, dst)
            print(f"[確定] {src} → {dst}")
        else:
            print(f"[SKIP] {src} が存在しません（先に take_screenshots() を実行してください）")
    print(f"\nnote用画像を {NOTE_DIR}/ に保存しました（git 管理対象）")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="スクリーンショットをnote用ディレクトリ (docs/images/note/) にコピーする",
    )
    args = parser.parse_args()

    take_screenshots()
    if args.confirm:
        confirm_to_note()
