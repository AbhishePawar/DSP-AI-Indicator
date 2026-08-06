import { expect, test } from "@playwright/test";

/**
 * Portfolio Intelligence Engine (RC1 Milestone 4) — structural smoke test.
 *
 * `/portfolio` is behind `ProtectedRoute`/`AuthGuard` (unlike `/analysis`,
 * which allows unauthenticated Research Mode access). `AuthGuard`'s session
 * check calls the backend and only resolves once that call settles — with
 * no live backend reachable (this sandboxed Playwright run has none), the
 * check can stay in its "Loading session…" state indefinitely, so this test
 * does not assert on the eventual sign-in redirect (that would hang/flake
 * here). It verifies the page — including the client bundle that now
 * contains the 8 new lazy-loaded Portfolio Intelligence Engine sections
 * registered in `PortfolioIntelligenceWorkspace` — loads without a 5xx
 * response or an uncaught page error while the auth check is in flight —
 * a regression guard that the new imports/wiring did not break the route's
 * bundle. Deep interaction coverage (rendering every new section with
 * populated/empty Portfolio Intelligence Engine data, and the authenticated
 * redirect itself in CI against a real backend) is covered by the Vitest
 * suite: `mapPortfolioInsights.test.ts`, `PortfolioInsightsSections.test.tsx`,
 * and the full workspace integration tests in `portfolio-intelligence.test.tsx`.
 */

test("loads /portfolio without a server error or page crash", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (err) => pageErrors.push(err.message));

  const response = await page.goto("/portfolio", { waitUntil: "domcontentloaded" });
  expect(response).toBeTruthy();
  expect(response!.status()).toBeLessThan(500);

  await expect(page.locator("body")).toBeVisible();
  await page.waitForTimeout(500);

  expect(pageErrors, `uncaught page errors: ${pageErrors.join("; ")}`).toEqual([]);
});
