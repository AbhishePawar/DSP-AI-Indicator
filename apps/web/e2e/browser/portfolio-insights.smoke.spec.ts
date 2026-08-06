import { expect, test } from "@playwright/test";

/**
 * Portfolio Intelligence Engine (RC1 Milestone 4) — structural smoke test.
 *
 * `/portfolio` is behind `ProtectedRoute`/`AuthGuard` (unlike `/analysis`,
 * which allows unauthenticated Research Mode access) — this environment's
 * Playwright run has no live backend/seeded session, so this test cannot
 * drive a real login. It verifies the page (including the client bundle
 * that now contains the 8 new lazy-loaded Portfolio Intelligence Engine
 * sections registered in `PortfolioIntelligenceWorkspace`) loads and
 * gracefully redirects to sign-in without a 5xx response or an uncaught
 * page error — a regression guard that the new imports/wiring did not break
 * the route's bundle. Deep interaction coverage (rendering every new
 * section with populated/empty Portfolio Intelligence Engine data) is
 * covered by the Vitest suite: `mapPortfolioInsights.test.ts`,
 * `PortfolioInsightsSections.test.tsx`, and the full workspace integration
 * tests in `portfolio-intelligence.test.tsx`.
 */

test("loads /portfolio and redirects to sign-in without crashing", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (err) => pageErrors.push(err.message));

  const response = await page.goto("/portfolio", { waitUntil: "domcontentloaded" });
  expect(response).toBeTruthy();
  expect(response!.status()).toBeLessThan(500);

  await expect(page.locator("body")).toBeVisible();
  // Unauthenticated in this environment — AuthGuard redirects to sign-in.
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible({
    timeout: 10_000,
  });

  expect(pageErrors, `uncaught page errors: ${pageErrors.join("; ")}`).toEqual([]);
});
