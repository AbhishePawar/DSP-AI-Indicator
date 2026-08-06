import { expect, test } from "@playwright/test";

/**
 * Institutional Company Workspace — tab-through smoke test.
 *
 * Verifies the flagship `/analysis` workspace's left navigation renders
 * every section (Overview, Financials, Valuation, Business, Management,
 * Economic Moat, Risk, Ownership, Peers, Research, News, AI Copilot,
 * Documents, Settings, ...) and that switching between them — including the
 * newly-added lazy sections — never throws an uncaught page error or 5xx
 * response. Does not assert on live backend data; this is a structural
 * regression guard, not an integration test against a running API.
 */

test("tabs through every Company Workspace section without crashing", async ({
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

  const nav = page.getByRole("navigation", { name: "Analysis sections" });
  await expect(nav).toBeVisible();

  const sectionButtons = nav.getByRole("button");
  const count = await sectionButtons.count();
  expect(count).toBeGreaterThanOrEqual(14);

  const main = page.getByRole("region", { name: "Main analysis area" });

  for (let i = 0; i < count; i += 1) {
    const button = sectionButtons.nth(i);
    const label = (await button.textContent())?.trim() ?? `section-${i}`;
    await button.click();
    await expect(main, `main content after selecting "${label}"`).toBeVisible();
    // Give lazy React Query hooks a beat to mount/settle before the next tab.
    await page.waitForTimeout(50);
  }

  expect(pageErrors, `uncaught page errors: ${pageErrors.join("; ")}`).toEqual(
    [],
  );
});
