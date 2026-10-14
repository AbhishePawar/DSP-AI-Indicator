import { expect, test } from "@playwright/test";

/**
 * Frontend-only smoke for the protected analysis route.
 *
 * This job intentionally has no API or authenticated session. It verifies the
 * route responds without a server error or uncaught browser exception.
 * Authenticated section navigation is covered by the P1-09 fixture-backed
 * Playwright hard gate.
 */

test("analysis route responds safely without an authenticated session", async ({
  page,
}) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  const response = await page.goto("/analysis", {
    waitUntil: "domcontentloaded",
  });
  expect(response, "analysis route response").toBeTruthy();
  expect(response!.status(), "analysis route status").toBeLessThan(500);
  await expect(page.locator("body")).toBeVisible();
  expect(pageErrors, `uncaught page errors: ${pageErrors.join("; ")}`).toEqual(
    [],
  );
});
