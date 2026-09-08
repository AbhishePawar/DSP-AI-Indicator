import { defineConfig, devices } from "@playwright/test";

/**
 * EPIC-019A — Visual regression + multi-browser smoke.
 * Baselines under e2e/visual/__screenshots__.
 *
 * SIMPLE-14I-A: tests run against the local/CI standalone server
 * (default http://127.0.0.1:3000). Do not point PLAYWRIGHT_BASE_URL
 * at an external preview host.
 */
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "playwright-report" }],
    ["json", { outputFile: "playwright-results.json" }],
  ],
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.02,
      animations: "disabled",
    },
  },
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
    ...(process.env.PLAYWRIGHT_INCLUDE_EDGE === "1"
      ? [
          {
            name: "msedge",
            use: { ...devices["Desktop Edge"], channel: "msedge" as const },
          },
        ]
      : []),
  ],
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        // Prefer production standalone server — avoids Next dev bundling test-only deps.
        // Copy static/public beside server.js (same as docker/frontend/Dockerfile).
        // CI already ran `npm run build`. A second webpack compile then resolves a
        // 29-file Next standalone stub at apps/web/node_modules/next instead of the
        // real package, and webServer exits before any smoke test runs.
        command: process.env.CI
          ? "node ./scripts/prepare-standalone-static.mjs && node .next/standalone/server.js"
          : "npm run build && node ./scripts/prepare-standalone-static.mjs && node .next/standalone/server.js",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 300_000,
        env: {
          ...process.env,
          PORT: "3000",
          HOSTNAME: "127.0.0.1",
        },
      },
});
