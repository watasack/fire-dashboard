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
  await page.waitForSelector(".plotly-graph-div", { timeout: 10000 });
  await new Promise((r) => setTimeout(r, 2000));

  // Top portion: hero KPI + risk metrics cards
  console.log("Capturing: Hero KPI + Risk metrics cards...");
  await page.evaluate(() => window.scrollTo(0, 0));
  await new Promise((r) => setTimeout(r, 300));
  const clipHeight = await page.evaluate(() => {
    const el = document.querySelector(".secondary-kpi");
    return el ? el.getBoundingClientRect().bottom : 900;
  });
  await page.screenshot({
    path: path.join(outputDir, "top_section.png"),
    clip: { x: 0, y: 0, width: VIEWPORT_WIDTH, height: clipHeight },
  });

  await browser.close();
  console.log(`\nScreenshot saved to: ${outputDir}/top_section.png`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
