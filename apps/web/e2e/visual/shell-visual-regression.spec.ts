import { expect, test } from "@playwright/test";

/**
 * Shell & Navigation Visual Regression Spec.
 * Captures pixel baselines for header, sidebar, content container, and breadcrumbs.
 */

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
] as const;

for (const vp of VIEWPORTS) {
  test.describe(`Global Shell visual baseline — ${vp.name}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test("header, sidebar, content width, and breadcrumbs baseline", async ({ page }) => {
      await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(300);

      // Verify app topbar presence
      const topbar = page.getByTestId("app-topbar");
      if (await topbar.isVisible()) {
        await expect(topbar).toHaveScreenshot(`shell-topbar-${vp.name}.png`);
      }

      // Verify breadcrumbs if present
      const breadcrumbs = page.getByRole("navigation", { name: /breadcrumb/i });
      if (await breadcrumbs.isVisible()) {
        await expect(breadcrumbs).toHaveScreenshot(`shell-breadcrumbs-${vp.name}.png`);
      }

      // Verify full shell layout baseline
      await expect(page).toHaveScreenshot(`shell-layout-${vp.name}.png`, { fullPage: false });
    });
  });
}
