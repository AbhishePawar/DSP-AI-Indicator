import { expect, test } from "@playwright/test";

/**
 * EPIC-019A — Cross-browser smoke (Chromium / Firefox / WebKit / Edge projects).
 */

const PATHS = ["/", "/login", "/dashboard", "/portfolio", "/research"] as const;

for (const path of PATHS) {
  test(`smoke ${path}`, async ({ page, browserName }) => {
    const response = await page.goto(path, { waitUntil: "domcontentloaded" });
    expect(response, `${browserName} ${path} response`).toBeTruthy();
    expect(response!.status(), `${browserName} ${path} status`).toBeLessThan(500);
    await expect(page.locator("body")).toBeVisible();
  });
}
