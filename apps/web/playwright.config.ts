import { defineConfig, devices } from "@playwright/test";

/**
 * EPIC-019A — Visual regression + multi-browser smoke.
 * Baselines under e2e/visual/__screenshots__.
 *
 * P1-09 starts API + Next itself and sets PLAYWRIGHT_SKIP_WEBSERVER=1.
 * That gate must not retry, must not spawn a second webServer/build, and
 * must retain traces on the first failure.
 */
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
const p109Standalone = process.env.PLAYWRIGHT_SKIP_WEBSERVER === "1";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: !p109Standalone,
  forbidOnly: !!process.env.CI,
  retries: p109Standalone ? 0 : process.env.CI ? 1 : 0,
  workers: p109Standalone ? 1 : process.env.CI ? 2 : undefined,
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
    trace: p109Standalone ? "retain-on-failure" : "on-first-retry",
    screenshot: "only-on-failure",
    video: p109Standalone ? "retain-on-failure" : "off",
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
        command: "npm run build && node .next/standalone/server.js",
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
