#!/usr/bin/env node

/**
 * P1-09 Local Execution Runner.
 *
 * 1. Explicitly loads apps/web/.env.local without overwriting existing environment.
 * 2. Resolves canonical DSP_SEED_ADMIN_PASSWORD (or legacy DSP_P109_PASSWORD fallback).
 * 3. Never prints, logs, or writes credential values.
 * 4. Runs preflight health checks against backend and frontend.
 * 5. Executes Playwright Chromium journey using PLAYWRIGHT_SKIP_WEBSERVER=1.
 */

import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const filename = fileURLToPath(import.meta.url);
const dirname = path.dirname(filename);
const webDir = path.resolve(dirname, "..");

async function main() {
  console.log("==================================================");
  console.log("   P1-09 Local Execution & Preflight Runner");
  console.log("==================================================");

  const {
    loadP109LocalEnv,
    resolveP109Config,
    validateP109Preflight,
    P109PreflightError,
  } = await import("../e2e/browser/p109/env.ts");

  loadP109LocalEnv();

  let config;
  try {
    config = resolveP109Config();
    console.log(`[PREFLIGHT] Credential status: CONFIGURED (canonical or fallback present)`);
    console.log(`[PREFLIGHT] Target API: ${config.apiBaseUrl}`);
    console.log(`[PREFLIGHT] Target Frontend: ${config.baseUrl}`);
  } catch (err) {
    if (err instanceof P109PreflightError) {
      console.error(`\n[PREFLIGHT ERROR] ${err.category}`);
      console.error(err.message);
      if (err.safeRemediation) {
        console.error(`\n${err.safeRemediation}`);
      }
    } else {
      console.error(`\n[CONFIG ERROR] ${err.message}`);
    }
    console.error("\nP1-09: BLOCKED — infrastructure unavailable");
    process.exit(1);
  }

  console.log("[PREFLIGHT] Verifying local services...");
  try {
    await validateP109Preflight(config, { timeoutMs: 3000 });
    console.log("[PREFLIGHT] Backend & Frontend services are READY.");
  } catch (err) {
    if (err instanceof P109PreflightError) {
      console.error(`\n[PREFLIGHT ERROR] ${err.category}`);
      console.error(err.message);
      if (err.safeRemediation) {
        console.error(`\n${err.safeRemediation}`);
      }
    } else {
      console.error(`\n[PREFLIGHT ERROR] ${err.message}`);
    }
    console.error("\nP1-09: BLOCKED — infrastructure unavailable");
    process.exit(2);
  }

  console.log("\n[EXECUTION] Launching P1-09 Chromium journey (PLAYWRIGHT_SKIP_WEBSERVER=1)...");
  const child = spawn(
    "npx",
    [
      "playwright",
      "test",
      "e2e/browser/p109-critical-investment.journey.spec.ts",
      "--project=chromium",
    ],
    {
      cwd: webDir,
      env: {
        ...process.env,
        PLAYWRIGHT_SKIP_WEBSERVER: "1",
      },
      stdio: "inherit",
    }
  );

  child.on("close", (code) => {
    if (code === 0) {
      console.log("\n==================================================");
      console.log("P1-09: PASS — actual Chromium journey executed");
      console.log("==================================================");
      process.exit(0);
    } else {
      console.error("\n==================================================");
      console.error("P1-09: FAIL — actual Chromium journey executed");
      console.error("==================================================");
      process.exit(code || 1);
    }
  });
}

main().catch((err) => {
  console.error(`Unexpected runner failure: ${err.message}`);
  process.exit(1);
});
