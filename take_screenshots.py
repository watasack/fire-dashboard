"""
Streamlit デモアプリのスクリーンショット撮影スクリプト
"""
import asyncio
import os
from playwright.async_api import async_playwright


async def set_number_input(page, index, value):
    """Set a number input by index using Playwright fill (properly triggers React state)"""
    locator = page.locator('input[type=number]').nth(index)
    await locator.click(click_count=3)
    await locator.fill(str(value))
    await locator.press("Tab")
    await asyncio.sleep(0.8)


async def take_screenshot(case_name, values, output_path):
    """
    values: [夫収入, 妻収入, 夫年齢, 妻年齢, 支出, 資産（万円）]
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1200, "height": 900})

        print(f"[{case_name}] ページ読み込み中...")
        await page.goto("http://localhost:8502", wait_until="networkidle")
        await asyncio.sleep(3)

        # Wait for inputs to be available
        await page.wait_for_selector('input[type=number]', timeout=15000)

        n_inputs = await page.evaluate('document.querySelectorAll("input[type=number]").length')
        print(f"[{case_name}] 入力フィールド数: {n_inputs}")

        # Streamlit DOM order: col1 items first, then col2 items
        # col1: 夫月収(0), 夫年齢(1)
        # col2: 妻月収(2), 妻年齢(3)
        # col3: 支出(4), col4: 資産(5)
        # values = [夫収入, 妻収入, 夫年齢, 妻年齢, 支出, 資産]
        field_map = {
            0: ("夫月収", values[0]),
            1: ("夫年齢", values[2]),
            2: ("妻月収", values[1]),
            3: ("妻年齢", values[3]),
            4: ("支出", values[4]),
            5: ("資産", values[5]),
        }

        for idx, (label, val) in field_map.items():
            print(f"  [{label}] = {val}")
            await set_number_input(page, idx, val)

        # Wait for Streamlit to re-render
        await asyncio.sleep(2)

        # Verify total income
        caption_text = await page.evaluate('''
            () => {
                const all = document.querySelectorAll("*");
                for (let el of all) {
                    if (el.children.length === 0 && el.innerText && el.innerText.includes("世帯月手取り")) {
                        return el.innerText;
                    }
                }
                return "not found";
            }
        ''')
        print(f"[{case_name}] 世帯収入表示: {caption_text}")

        # Find and click FIRE button
        buttons = await page.query_selector_all('button')
        fire_btn = None
        for btn in buttons:
            text = await btn.inner_text()
            if 'FIRE' in text and '計算' in text:
                fire_btn = btn
                print(f"[{case_name}] ボタン発見: {text.strip()}")
                break

        if not fire_btn:
            print(f"[{case_name}] ERROR: FIREボタンが見つかりません")
            await page.screenshot(path=output_path.replace('.png', '_debug.png'), full_page=True)
            await browser.close()
            return

        await fire_btn.click()
        print(f"[{case_name}] ボタンクリック完了")

        # Wait for spinner to appear and disappear
        try:
            await page.wait_for_selector('[data-testid="stSpinner"]', timeout=5000)
            print(f"[{case_name}] スピナー検出")
            await page.wait_for_selector('[data-testid="stSpinner"]', state='hidden', timeout=60000)
            print(f"[{case_name}] スピナー消滅")
        except Exception:
            print(f"[{case_name}] スピナー検出なし、8秒待機...")
            await asyncio.sleep(8)

        # Extra wait for rendering
        await asyncio.sleep(3)

        # Check if results are shown
        page_text = await page.inner_text('body')
        if 'シミュレーション完了' in page_text or '推計FIRE到達年齢' in page_text:
            print(f"[{case_name}] OK: 結果表示確認")
        elif 'FIRE到達できませんでした' in page_text:
            print(f"[{case_name}] WARN: FIRE到達なし（warning表示）")
        else:
            print(f"[{case_name}] UNKNOWN: 結果不明")

        # Scroll to show results (below the fold)
        await page.evaluate('window.scrollTo(0, 0)')
        await asyncio.sleep(0.5)

        await page.screenshot(path=output_path, full_page=True)
        print(f"[{case_name}] DONE: {output_path}")

        await browser.close()


async def main():
    os.makedirs("docs/screenshots", exist_ok=True)

    # Case1: 育休なし（妻: 30万）
    await take_screenshot(
        "case1_no_ikukyu",
        values=[45, 30, 35, 33, 28, 2000],
        output_path="docs/screenshots/case1_no_ikukyu.png"
    )

    print()

    # Case2: 育休あり近似（妻: 15万 ≒ 育休給付金）
    await take_screenshot(
        "case2_with_ikukyu",
        values=[45, 15, 35, 33, 28, 2000],
        output_path="docs/screenshots/case2_with_ikukyu.png"
    )


if __name__ == "__main__":
    asyncio.run(main())
