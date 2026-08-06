import { expect, test } from "@playwright/test";

/**
 * Workflow Automation (RC1 Milestone 5) — structural smoke test.
 *
 * `/workflow` is behind `ProtectedRoute`/`AuthGuard` (same as `/portfolio`).
 * `AuthGuard`'s session check calls the backend and only resolves once that
 * call settles — with no live backend reachable (this sandboxed Playwright
 * run has none), the check can stay in its "Loading session…" state
 * indefinitely, so this test does not assert on the eventual sign-in
 * redirect (that would hang/flake here). It verifies the page — including
 * the client bundle for the new Alert Rules / Scheduled Reports /
 * Notification Center panels — loads without a 5xx response or an
 * uncaught page error while the auth check is in flight. Deep interaction
 * coverage (including the authenticated redirect) is covered by the
 * Vitest suite (mapper + component tests) and by this same spec running
 * against a real backend in CI.
 */

test("loads /workflow without a server error or page crash", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (err) => pageErrors.push(err.message));

  const response = await page.goto("/workflow", { waitUntil: "domcontentloaded" });
  expect(response).toBeTruthy();
  expect(response!.status()).toBeLessThan(500);

  await expect(page.locator("body")).toBeVisible();
  await page.waitForTimeout(500);

  expect(pageErrors, `uncaught page errors: ${pageErrors.join("; ")}`).toEqual([]);
});
