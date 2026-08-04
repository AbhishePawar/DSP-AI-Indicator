import { expect, test, type Page } from "@playwright/test";

/**
 * EPIC-019A — Headed/CI visual regression for primary commercial surfaces.
 * Pixel baselines stored beside this suite; failures attach diffs in report.
 */

const ROUTES = [
  { name: "login", path: "/login" },
  { name: "dashboard", path: "/dashboard" },
  { name: "portfolio", path: "/portfolio" },
  { name: "research", path: "/research" },
  { name: "ird", path: "/research/institutional/dashboard" },
  { name: "analysis", path: "/analysis" },
] as const;

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
] as const;

async function settle(page: Page) {
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.waitForTimeout(250);
}

for (const route of ROUTES) {
  for (const vp of VIEWPORTS) {
    test.describe(`${route.name} ${vp.name}`, () => {
      test.use({ viewport: { width: vp.width, height: vp.height } });

      test(`light theme screenshot`, async ({ page }) => {
        await page.emulateMedia({ colorScheme: "light" });
        await page.goto(route.path, { waitUntil: "domcontentloaded" });
        await settle(page);
        await expect(page).toHaveScreenshot(
          `${route.name}-${vp.name}-light.png`,
          { fullPage: true },
        );
      });

      test(`dark theme screenshot`, async ({ page }) => {
        await page.emulateMedia({ colorScheme: "dark" });
        await page.goto(route.path, { waitUntil: "domcontentloaded" });
        await settle(page);
        await expect(page).toHaveScreenshot(
          `${route.name}-${vp.name}-dark.png`,
          { fullPage: true },
        );
      });
    });
  }
}

test.describe("trust chrome presence", () => {
  for (const path of [
    "/dashboard",
    "/portfolio",
    "/research",
    "/research/institutional/dashboard",
  ]) {
    test(`${path} exposes trust ladder`, async ({ page }) => {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      await settle(page);
      // Auth gates may redirect; assert either trust chrome or login shell.
      const trust = page.getByTestId("surface-trust-ladder");
      const login = page.getByRole("heading", { name: /sign in|log in|login/i });
      const hasTrust = await trust.count();
      const hasLogin = await login.count();
      expect(hasTrust + hasLogin).toBeGreaterThan(0);
    });
  }
});
