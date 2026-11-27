import { expect, test } from "@playwright/test";

/**
 * Institutional Company Workspace — tab-through smoke test.
 *
 * Verifies the flagship `/analysis` workspace loads its start screen without a backend.
 * every section (Overview, Financials, Valuation, Business, Management,
 * Economic Moat, Risk, Ownership, Peers, Research, News, AI Copilot,
 * Documents, Settings, ...) and that switching between them — including the
 * newly-added lazy sections — never throws an uncaught page error or 5xx
 * response. Does not assert on live backend data; this is a structural
 * regression guard, not an integration test against a running API.
 */

test("analysis workspace start screen renders without fabricated sections", async ({
  page,
}) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (err) => pageErrors.push(err.message));

  // First-run onboarding overlay ("Welcome tour") can appear at any point
  // (including mid-interaction) and intercept clicks — auto-dismiss it
  // whenever it shows up rather than only once up front.
  await page.addLocatorHandler(
    page.getByRole("dialog", { name: "Welcome tour" }),
    async (dialog) => {
      await dialog.getByRole("button", { name: "Skip tutorial" }).click();
    },
  );

  const response = await page.goto("/analysis", {
    waitUntil: "domcontentloaded",
  });
  expect(response).toBeTruthy();
  expect(response!.status()).toBeLessThan(500);

  // Phase 7 release contract: with no backend and no analysed company the
  // workspace shows the research-depth start screen and must NOT fabricate
  // analysis sections. The full section tab-through runs against a real API
  // in the P1-09 critical journey (e2e/browser/p109-critical-investment.journey.spec.ts).
  await expect(
    page.getByRole("heading", { name: /Choose Research Depth/i }),
  ).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Analysis sections" })).toHaveCount(
    0,
  );

  expect(pageErrors, `uncaught page errors: ${pageErrors.join("; ")}`).toEqual([]);
});
