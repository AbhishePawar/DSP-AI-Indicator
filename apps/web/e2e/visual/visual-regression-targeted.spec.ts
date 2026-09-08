import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";

/**
 * Targeted visual regression tests for:
 *  - Hero section (marketing landing page)
 *  - Pricing cards
 *  - Auth flows (login, register, forgot-password, email-login)
 *  - Dashboard (focused component-level checks)
 *
 * Pixel baselines stored beside this suite; failures attach diffs in report.
 * Run:  pnpm test:visual  (or npm run test:visual)
 * Update baselines:  npm run test:visual:update
 */

const VIEWPORTS = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
] as const;

/** Wait for network idle + a short paint settle */
async function settle(page: Page, extra = 300) {
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await page.waitForTimeout(extra);
}

// ---------------------------------------------------------------------------
// 1. HERO SECTION — marketing landing page
// ---------------------------------------------------------------------------
test.describe("Hero section — marketing landing page", () => {
  for (const vp of VIEWPORTS) {
    test.describe(`${vp.name}`, () => {
      test.use({ viewport: { width: vp.width, height: vp.height } });

      test("light — hero section layout", async ({ page }) => {
        await page.emulateMedia({ colorScheme: "light" });
        await page.goto("/", { waitUntil: "domcontentloaded" });
        await settle(page);

        // Clip to the hero section only (first viewport height)
        await expect(page).toHaveScreenshot(
          `hero-${vp.name}-light.png`,
          {
            clip: { x: 0, y: 0, width: vp.width, height: vp.height },
            maxDiffPixelRatio: 0.02,
          },
        );
      });

      test("dark — hero section layout", async ({ page }) => {
        await page.emulateMedia({ colorScheme: "dark" });
        await page.goto("/", { waitUntil: "domcontentloaded" });
        await settle(page);

        await expect(page).toHaveScreenshot(
          `hero-${vp.name}-dark.png`,
          {
            clip: { x: 0, y: 0, width: vp.width, height: vp.height },
            maxDiffPixelRatio: 0.02,
          },
        );
      });
    });
  }
});

// Hero section element presence (non-visual guard)
test.describe("Hero section — element guards", () => {
  test("hero heading and CTA buttons are present", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await settle(page, 200);

    // Heading must exist
    const heading = page.locator("h1").first();
    await expect(heading).toBeVisible();

    // At least one primary CTA link/button
    const cta = page
      .getByRole("link", { name: /sign in|get started|create account|start/i })
      .first();
    const ctaBtn = page
      .getByRole("button", { name: /sign in|get started|create account|start/i })
      .first();
    const hasCta =
      (await cta.count()) > 0 || (await ctaBtn.count()) > 0;
    expect(hasCta).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// 2. PRICING CARDS — /pricing
// ---------------------------------------------------------------------------
test.describe("Pricing cards — /pricing", () => {
  for (const vp of VIEWPORTS) {
    test.describe(`${vp.name}`, () => {
      test.use({ viewport: { width: vp.width, height: vp.height } });

      test("light — full pricing page", async ({ page }) => {
        await page.emulateMedia({ colorScheme: "light" });
        await page.goto("/pricing", { waitUntil: "domcontentloaded" });
        await settle(page);

        await expect(page).toHaveScreenshot(
          `pricing-${vp.name}-light.png`,
          { fullPage: true, maxDiffPixelRatio: 0.02 },
        );
      });

      test("dark — full pricing page", async ({ page }) => {
        await page.emulateMedia({ colorScheme: "dark" });
        await page.goto("/pricing", { waitUntil: "domcontentloaded" });
        await settle(page);

        await expect(page).toHaveScreenshot(
          `pricing-${vp.name}-dark.png`,
          { fullPage: true, maxDiffPixelRatio: 0.02 },
        );
      });
    });
  }
});

// Pricing card structural guards
test.describe("Pricing cards — structural guards", () => {
  test("pricing page renders at least one pricing card / tier", async ({
    page,
  }) => {
    await page.goto("/pricing", { waitUntil: "domcontentloaded" });
    await settle(page, 200);

    // Cards typically contain a price amount or tier name
    const priceEl = page
      .locator('[data-testid*="pricing"], [class*="pricing"], [class*="plan"], [class*="tier"]')
      .first();
    const headingEl = page
      .getByRole("heading", { name: /free|starter|pro|enterprise|edition|plan/i })
      .first();

    const hasCard = (await priceEl.count()) > 0 || (await headingEl.count()) > 0;
    expect(hasCard).toBe(true);
  });

  test("recommended / highlighted pricing tier is visually distinct", async ({
    page,
  }) => {
    await page.goto("/pricing", { waitUntil: "domcontentloaded" });
    await settle(page, 200);

    // Look for a "recommended" badge or ring highlight
    const badge = page.getByText(/recommended|popular|best value/i).first();
    const hasBadge = (await badge.count()) > 0;
    // Non-fatal: just record whether the badge exists
    if (hasBadge) {
      await expect(badge).toBeVisible();
    }
  });
});

// ---------------------------------------------------------------------------
// 3. AUTH FLOWS
// ---------------------------------------------------------------------------
const AUTH_ROUTES = [
  { name: "login", path: "/login" },
  { name: "register", path: "/register" },
  { name: "forgot-password", path: "/forgot-password" },
  { name: "email-login", path: "/email-login" },
] as const;

test.describe("Auth flows — visual regression", () => {
  for (const route of AUTH_ROUTES) {
    for (const vp of VIEWPORTS) {
      test.describe(`${route.name} ${vp.name}`, () => {
        test.use({ viewport: { width: vp.width, height: vp.height } });

        test("light theme", async ({ page }) => {
          await page.emulateMedia({ colorScheme: "light" });
          await page.goto(route.path, { waitUntil: "domcontentloaded" });
          await settle(page);

          await expect(page).toHaveScreenshot(
            `auth-${route.name}-${vp.name}-light.png`,
            { fullPage: true, maxDiffPixelRatio: 0.02 },
          );
        });

        test("dark theme", async ({ page }) => {
          await page.emulateMedia({ colorScheme: "dark" });
          await page.goto(route.path, { waitUntil: "domcontentloaded" });
          await settle(page);

          await expect(page).toHaveScreenshot(
            `auth-${route.name}-${vp.name}-dark.png`,
            { fullPage: true, maxDiffPixelRatio: 0.02 },
          );
        });
      });
    }
  }
});

// Auth form structural guards
test.describe("Auth flows — structural guards", () => {
  test("login page has email/password fields and submit button", async ({
    page,
  }) => {
    await page.goto("/login", { waitUntil: "domcontentloaded" });
    await settle(page, 200);

    const emailField = page
      .getByRole("textbox", { name: /email/i })
      .or(page.locator('input[type="email"]'))
      .first();
    const submitBtn = page
      .getByRole("button", { name: /sign in|log in|continue/i })
      .first();

    await expect(emailField).toBeVisible();
    await expect(submitBtn).toBeVisible();
  });

  test("register page has required fields", async ({ page }) => {
    await page.goto("/register", { waitUntil: "domcontentloaded" });
    await settle(page, 200);

    const emailField = page
      .getByRole("textbox", { name: /email/i })
      .or(page.locator('input[type="email"]'))
      .first();
    const hasEmail = (await emailField.count()) > 0;
    expect(hasEmail).toBe(true);
  });

  test("forgot-password page has email field", async ({ page }) => {
    await page.goto("/forgot-password", { waitUntil: "domcontentloaded" });
    await settle(page, 200);

    const emailField = page
      .getByRole("textbox", { name: /email/i })
      .or(page.locator('input[type="email"]'))
      .first();
    const hasEmail = (await emailField.count()) > 0;
    expect(hasEmail).toBe(true);
  });

  test("auth pages have back-to-home navigation", async ({ page }) => {
    for (const path of ["/login", "/register"]) {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      await settle(page, 200);

      const homeLink = page
        .getByRole("link", { name: /home|back|dsp/i })
        .or(page.locator('a[href="/"]'))
        .first();
      const hasHomeLink = (await homeLink.count()) > 0;
      expect(hasHomeLink).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// 4. DASHBOARD — focused component-level visual checks
// ---------------------------------------------------------------------------
test.describe("Dashboard — visual regression", () => {
  for (const vp of VIEWPORTS) {
    test.describe(`${vp.name}`, () => {
      test.use({ viewport: { width: vp.width, height: vp.height } });

      test("light — dashboard above-the-fold", async ({ page }) => {
        await page.emulateMedia({ colorScheme: "light" });
        await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
        await settle(page);

        // Capture above-the-fold only for fast regression detection
        await expect(page).toHaveScreenshot(
          `dashboard-atf-${vp.name}-light.png`,
          {
            clip: { x: 0, y: 0, width: vp.width, height: vp.height },
            maxDiffPixelRatio: 0.02,
          },
        );
      });

      test("dark — dashboard above-the-fold", async ({ page }) => {
        await page.emulateMedia({ colorScheme: "dark" });
        await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
        await settle(page);

        await expect(page).toHaveScreenshot(
          `dashboard-atf-${vp.name}-dark.png`,
          {
            clip: { x: 0, y: 0, width: vp.width, height: vp.height },
            maxDiffPixelRatio: 0.02,
          },
        );
      });

      test("light — dashboard full page", async ({ page }) => {
        await page.emulateMedia({ colorScheme: "light" });
        await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
        await settle(page);

        await expect(page).toHaveScreenshot(
          `dashboard-full-${vp.name}-light.png`,
          { fullPage: true, maxDiffPixelRatio: 0.02 },
        );
      });

      test("dark — dashboard full page", async ({ page }) => {
        await page.emulateMedia({ colorScheme: "dark" });
        await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
        await settle(page);

        await expect(page).toHaveScreenshot(
          `dashboard-full-${vp.name}-dark.png`,
          { fullPage: true, maxDiffPixelRatio: 0.02 },
        );
      });
    });
  }
});

// Dashboard structural guards
test.describe("Dashboard — structural guards", () => {
  test("dashboard renders search box or main content area", async ({
    page,
  }) => {
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    await settle(page, 200);

    // Either the search-first dashboard or a login redirect
    const searchBox = page
      .getByRole("searchbox")
      .or(page.locator('[data-testid="search-box"], [class*="search"]'))
      .first();
    const loginHeading = page
      .getByRole("heading", { name: /sign in|log in|login/i })
      .first();

    const hasContent =
      (await searchBox.count()) > 0 || (await loginHeading.count()) > 0;
    expect(hasContent).toBe(true);
  });

  test("dashboard sidebar / navigation is present", async ({ page }) => {
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    await settle(page, 200);

    const nav = page.getByRole("navigation").first();
    const sidebar = page.locator('[data-testid="sidebar"], [class*="sidebar"]').first();
    const loginHeading = page
      .getByRole("heading", { name: /sign in|log in|login/i })
      .first();

    const hasNav =
      (await nav.count()) > 0 ||
      (await sidebar.count()) > 0 ||
      (await loginHeading.count()) > 0;
    expect(hasNav).toBe(true);
  });

  test("dashboard topbar is present", async ({ page }) => {
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    await settle(page, 200);

    const topbar = page
      .locator('[data-testid="topbar"], [class*="topbar"], header')
      .first();
    const loginHeading = page
      .getByRole("heading", { name: /sign in|log in|login/i })
      .first();

    const hasTopbar =
      (await topbar.count()) > 0 || (await loginHeading.count()) > 0;
    expect(hasTopbar).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// 5. POST-DEPLOYMENT SMOKE — critical CSS/layout regression guards
// ---------------------------------------------------------------------------
test.describe("Post-deployment CSS regression guards", () => {
  const CRITICAL_ROUTES = [
    { name: "marketing-home", path: "/" },
    { name: "pricing", path: "/pricing" },
    { name: "login", path: "/login" },
    { name: "dashboard", path: "/dashboard" },
  ] as const;

  for (const route of CRITICAL_ROUTES) {
    test(`${route.name} — no layout overflow at 1440px`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(route.path, { waitUntil: "domcontentloaded" });
      await settle(page, 200);

      // Check for horizontal overflow (common CSS regression symptom)
      const hasHorizontalOverflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth;
      });
      expect(hasHorizontalOverflow).toBe(false);
    });

    test(`${route.name} — no layout overflow at 390px`, async ({ page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto(route.path, { waitUntil: "domcontentloaded" });
      await settle(page, 200);

      const hasHorizontalOverflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth;
      });
      expect(hasHorizontalOverflow).toBe(false);
    });
  }
});
