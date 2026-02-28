#!/usr/bin/env python3
"""Capture screenshots of the FIRE dashboard for documentation."""

import asyncio
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Installing playwright...")
    import subprocess
    subprocess.check_call(["pip", "install", "playwright"])
    subprocess.check_call(["playwright", "install", "chromium"])
    from playwright.async_api import async_playwright


DASHBOARD_PATH = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "dashboard_screenshots"


# Section selectors (first captures header through hero-kpi via container)
SECTIONS = [
    ("01_header_hero_kpi", ".dashboard-header, .hero-kpi", "Header and Hero KPI"),
    ("02_risk_metrics", ".secondary-kpi", "Risk metrics cards"),
    ("03_asset_simulation", ".main-chart", "Main asset simulation chart"),  # first .main-chart
    ("04_income_expense", ".main-chart >> nth=1", "Income/expense stream chart"),
    ("05_life_events", ".life-events-section", "Life events table"),
    ("06_assumptions_optimization", ".info-panels", "Assumptions and optimization panels"),
]


async def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    file_url = f"file://{DASHBOARD_PATH}"

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            device_scale_factor=2,
        )
        page = await context.new_page()

        print(f"Loading {file_url}")
        await page.goto(file_url, wait_until="networkidle", timeout=60000)

        # Wait for Plotly charts to render
        await page.wait_for_selector(".plotly-graph-div", timeout=10000)
        await asyncio.sleep(2)  # Extra time for chart animations

        # 1. Full-page screenshot
        print("Taking full-page screenshot...")
        await page.screenshot(path=OUTPUT_DIR / "00_full_page.png", full_page=True)

        # 2. Screenshots of each section
        for slug, selector, name in SECTIONS:
            print(f"Capturing: {name}...")
            try:
                if slug == "01_header_hero_kpi":
                    # Header + Hero KPI: scroll to top and capture viewport
                    await page.evaluate("window.scrollTo(0, 0)")
                    await asyncio.sleep(0.3)
                    await page.screenshot(path=OUTPUT_DIR / f"{slug}.png")
                else:
                    locator = page.locator(selector).first
                    await locator.screenshot(path=OUTPUT_DIR / f"{slug}.png")
            except Exception as e:
                print(f"  Warning: {e}")

        # 3. Scroll-through viewport screenshots
        viewport_height = 900
        total_height = await page.evaluate("document.body.scrollHeight")
        scroll_positions = [0, viewport_height, viewport_height * 2, viewport_height * 3]
        scroll_positions = [p for p in scroll_positions if p < total_height]
        scroll_positions.append(total_height - viewport_height)  # Bottom

        for i, scroll_y in enumerate(scroll_positions):
            await page.evaluate(f"window.scrollTo(0, {scroll_y})")
            await asyncio.sleep(0.5)
            await page.screenshot(path=OUTPUT_DIR / f"scroll_{i:02d}_y{scroll_y}.png")

        await browser.close()

    print(f"\nScreenshots saved to: {OUTPUT_DIR}")
    for f in sorted(OUTPUT_DIR.glob("*.png")):
        print(f"  - {f.name}")


if __name__ == "__main__":
    asyncio.run(main())
