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

# Time to wait for MC 1000-run calculation (ms). Increase if chart is missing.
MC_WAIT_MS = 10000


def take_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # --- Full viewport (above fold) ---
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(URL, timeout=30000)
        page.wait_for_load_state("domcontentloaded", timeout=30000)
        page.wait_for_timeout(MC_WAIT_MS)

        out = OUT_DIR / "result_top.png"
        page.screenshot(path=str(out))
        print(f"[OK] {out}")

        # --- Full page (tall viewport, no scroll needed) ---
        page2 = browser.new_page(viewport={"width": 1440, "height": 4000})
        page2.goto(URL, timeout=30000)
        page2.wait_for_load_state("domcontentloaded", timeout=30000)
        page2.wait_for_timeout(MC_WAIT_MS)

        out = OUT_DIR / "full_page.png"
        page2.screenshot(path=str(out))
        print(f"[OK] {out}")

        # --- Chart area only ---
        chart_heading = page2.get_by_text("資産推移予測").first
        if chart_heading.is_visible():
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

        browser.close()

    print(f"\nDone: {OUT_DIR}/")


if __name__ == "__main__":
    take_screenshots()
