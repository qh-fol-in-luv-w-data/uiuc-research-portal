// Full-page screenshots for the README (final animation states via reduced motion).
import { chromium } from "@playwright/test";

const base = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const out = new URL("../../../docs/screenshots/", import.meta.url).pathname;
const browser = await chromium.launch({ channel: "chrome" });
for (const [name, viewport, scale] of [["desktop", { width: 1440, height: 900 }, 1], ["phone", { width: 390, height: 844 }, 2]]) {
  const page = await browser.newPage({ viewport, deviceScaleFactor: scale, reducedMotion: "reduce" });
  await page.goto(base);
  for (const id of ["focus", "output", "notable", "faculty", "collab", "assistant"]) {
    await page.locator(`#${id}-title`).scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
  }
  await page.waitForTimeout(2500); // map tiles
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: `${out}${name}.png`, fullPage: true });
  await page.close();
}
await browser.close();
console.log("saved to", out);
