import { expect, type Page } from "@playwright/test";

/**
 * Current login UI contract (LoginForm + login.journey unit test):
 *   /login → chooser → "Username and password" → labelled fields → Sign in
 *
 * FormField appends a screen-reader " (required)" suffix, so accessible names
 * are "Username (required)" / "Password (required)". Match by role + substring
 * so required-indicator wording cannot break the gate.
 */
export async function openPasswordLogin(page: Page): Promise<void> {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  const chooser = page.getByRole("button", {
    name: /username and password/i,
  });
  await expect(
    chooser,
    "[P1-09 LOGIN] authentication-method chooser must be visible",
  ).toBeVisible({ timeout: 30_000 });
  await chooser.click();
}

export async function fillPasswordCredentials(
  page: Page,
  username: string,
  password: string,
): Promise<void> {
  const usernameField = page.getByRole("textbox", { name: /username/i });
  const passwordField = page.getByRole("textbox", { name: /password/i });
  await expect(
    usernameField,
    "[P1-09 LOGIN] username field must be reachable after chooser",
  ).toBeVisible({ timeout: 15_000 });
  await expect(
    passwordField,
    "[P1-09 LOGIN] password field must be reachable after chooser",
  ).toBeVisible();
  await usernameField.fill(username);
  await passwordField.fill(password);
}

export async function submitPasswordLogin(page: Page): Promise<void> {
  await page.getByRole("button", { name: /^sign in$/i }).click();
}

/**
 * Authenticated chrome: Topbar replaces "Sign in" with UserMenu
 * (`button[aria-haspopup="menu"]` + menuitem Logout).
 */
export async function assertAuthenticatedSession(page: Page): Promise<void> {
  await expect(
    page,
    "[P1-09 LOGIN] must leave /login after sign-in",
  ).not.toHaveURL(/\/login(\?|$)/, { timeout: 60_000 });

  const accountMenu = page.locator("button[aria-haspopup='menu']");
  await expect(
    accountMenu,
    "[P1-09 LOGIN] authenticated account menu must appear",
  ).toBeVisible({ timeout: 30_000 });

  await accountMenu.click();
  await expect(
    page.getByRole("menuitem", { name: /^logout$/i }),
    "[P1-09 LOGIN] Logout control must be available when authenticated",
  ).toBeVisible();
  await page.keyboard.press("Escape");
}

export async function loginWithUsernamePassword(
  page: Page,
  username: string,
  password: string,
): Promise<void> {
  await openPasswordLogin(page);
  await fillPasswordCredentials(page, username, password);
  await submitPasswordLogin(page);
  await assertAuthenticatedSession(page);
}
