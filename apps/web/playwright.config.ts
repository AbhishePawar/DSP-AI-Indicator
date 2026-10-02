import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

import { loadP109LocalEnv } from "./e2e/browser/p109/env";

// Playwright does not automatically load apps/web/.env.local. Resolve the
// file from this config's directory rather than relying on process.cwd().
// Explicit shell/CI variables win over local-file values.
loadP109LocalEnv(path.resolve(__dirname, ".env.local"));

/**
 * EPIC-019A — Visual regression + multi-browser smoke.
 * Baselines under e2e/visual/__screenshots__.
 */
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? (process.env.PORT ? `http://127.0.0.1:${process.env.PORT}` : "http://127.0.0.1:3000");

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
        command:
          "npm run build && node ./scripts/prepare-standalone-static.mjs && node .next/standalone/server.js",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 300_000,
        env: {
          ...process.env,
          PORT: process.env.PORT || (baseURL ? String(new URL(baseURL).port || "3000") : "3000"),
          HOSTNAME: "127.0.0.1",
        },
      },
});
