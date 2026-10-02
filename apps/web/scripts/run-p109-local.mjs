#!/usr/bin/env node

/**
 * P1-09 Local Execution Runner.
 *
 * - Explicitly loads apps/web/.env.local.
 * - Detects and reuses existing services at 127.0.0.1:8000 and 127.0.0.1:3000.
 * - Inspects process ownership to avoid attaching to alien or stale working trees.
 * - Enforces bounded HTTP readiness checks rather than relying on raw TCP port listeners.
 * - Auto-launches missing services with configurable health polling and output capture.
 * - Cleans up only child processes it spawned on exit.
 * - Never prints or leaks credentials.
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

  const {
    ManagedProcessTracker,
    getHealthConfig,
    ensureBackendService,
    ensureFrontendService,
  } = await import("../e2e/browser/p109/runnerCore.ts");

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

  const tracker = new ManagedProcessTracker();
  const cleanup = () => tracker.cleanup();
  process.on("exit", cleanup);
  process.on("SIGINT", () => {
    cleanup();
    process.exit(130);
  });
  process.on("SIGTERM", () => {
    cleanup();
    process.exit(143);
  });

  const healthConfig = getHealthConfig();
  console.log(`[PREFLIGHT] Health check timeout: ${healthConfig.timeoutMs}ms, interval: ${healthConfig.intervalMs}ms`);

  // 1. Ensure backend service
  const backendResult = await ensureBackendService(config, tracker, healthConfig, {
    onProgress: (dot) => process.stdout.write(dot),
  });

  if (backendResult.alreadyRunning) {
    console.log(`[PREFLIGHT] Backend is already running (reused existing process).`);
  } else if (!backendResult.ok) {
    console.error(`\n[PREFLIGHT ERROR] BACKEND_UNAVAILABLE`);
    if (backendResult.errorDiagnostic) {
      console.error(backendResult.errorDiagnostic);
    }
    console.error("\nSafe Manual Startup Command (Backend):");
    console.error([
      "DSP_ENVIRONMENT=development \\",
      "DSP_INFRA_OFFLINE=0 \\",
      "DSP_MARKET_QUOTE_MEMORY=1 \\",
      "DSP_FINANCIAL_STATEMENT_MEMORY=1 \\",
      "DSP_P109_E2E_FIXTURE=1 \\",
      "DSP_SEED_ADMIN_PASSWORD='[configured in apps/web/.env.local]' \\",
      "python -m uvicorn api_platform.api.app:app --host 127.0.0.1 --port 8000",
    ].join("\n"));
    tracker.cleanup();
    process.exit(2);
  }

  // 2. Ensure frontend service
  const frontendResult = await ensureFrontendService(config, tracker, healthConfig, {
    webDir,
    onProgress: (dot) => process.stdout.write(dot),
  });

  if (frontendResult.alreadyRunning) {
    console.log(`[PREFLIGHT] Frontend is already running and verified responsive (reused existing process).`);
  } else if (!frontendResult.ok) {
    console.error(`\n[PREFLIGHT ERROR] FRONTEND_UNAVAILABLE`);
    if (frontendResult.errorDiagnostic) {
      console.error(frontendResult.errorDiagnostic);
    }
    console.error("\nP1-09: BLOCKED — frontend infrastructure unavailable");
    tracker.cleanup();
    process.exit(2);
  }

  // 3. Final preflight validation check
  try {
    await validateP109Preflight(config, { timeoutMs: 3000 });
    console.log("\n[PREFLIGHT] Backend & Frontend services are verified READY.");
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
    tracker.cleanup();
    process.exit(2);
  }

  console.log("\n[EXECUTION] Launching P1-09 Chromium journey (PLAYWRIGHT_SKIP_WEBSERVER=1)...");
  const child = spawn(
    "npx",
    ["playwright", "test", "e2e/browser/p109-critical-investment.journey.spec.ts", "--project=chromium"],
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
    tracker.cleanup();
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
