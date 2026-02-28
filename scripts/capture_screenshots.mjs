#!/usr/bin/env node
/**
 * Capture dashboard screenshots using Playwright (Node.js).
 * Run: npx playwright run scripts/capture_screenshots.mjs
 * Or: node scripts/capture_screenshots.mjs (after npm i playwright)
 */

import { firefox } from "playwright";
import { fileURLToPath } from "url";
import path from "path";
import fs from "fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const dashboardPath = path.join(__dirname, "..", "dashboard", "index.html");
const outputDir = path.join(__dirname, "..", "dashboard_screenshots");
const fileUrl = `file://${path.resolve(dashboardPath)}`;

fs.mkdirSync(outputDir, { recursive: true });

const VIEWPORT_WIDTH = 1440;
async function main() {
  const browser = await firefox.launch();
  const context = await browser.newContext({
    viewport: { width: VIEWPORT_WIDTH, height: 900 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  console.log("Loading dashboard...");
  await page.goto(fileUrl, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForSelector(".secondary-kpi", { timeout: 10000 });
  await new Promise((r) => setTimeout(r, 1000));

  // v7_risk_cards.png - Risk metrics cards (4 cards below hero KPI)
  console.log("Capturing: Risk metrics cards...");
  await page.evaluate(() => window.scrollTo(0, 0));
  await new Promise((r) => setTimeout(r, 300));
  const riskCards = page.locator(".secondary-kpi").first();
  await riskCards.scrollIntoViewIfNeeded();
  await new Promise((r) => setTimeout(r, 300));
  await riskCards.screenshot({ path: path.join(outputDir, "v7_risk_cards.png") });

  await browser.close();
  console.log(`\nScreenshot saved to: ${outputDir}/v7_risk_cards.png`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
