import { expect, test } from "@playwright/test";

/**
 * EPIC-019A — Cross-browser smoke (Chromium / Firefox / WebKit / Edge projects).
 */

const PATHS = [
  "/",
  "/login",
  "/dashboard",
  "/dashboards",
  "/dashboards/research",
  "/dashboards/portfolio-manager",
  "/dashboards/wealth-advisor",
  "/dashboards/family-office",
  "/dashboards/executive",
  "/portfolio",
  "/research",
  "/research/workspace",
  "/saas",
  "/ops",
  "/control-center",
  "/copilot",
] as const;

for (const path of PATHS) {
  test(`smoke ${path}`, async ({ page, browserName }) => {
    const response = await page.goto(path, { waitUntil: "domcontentloaded" });
    expect(response, `${browserName} ${path} response`).toBeTruthy();
    expect(response!.status(), `${browserName} ${path} status`).toBeLessThan(500);
    await expect(page.locator("body")).toBeVisible();
  });
}
