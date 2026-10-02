#!/usr/bin/env node

/**
 * P1-09 Local Execution Runner.
 *
 * - Explicitly loads apps/web/.env.local.
 * - Detects and reuses existing services at 127.0.0.1:8000 and 127.0.0.1:3000.
 * - Inspects process ownership to avoid attaching to alien or stale working trees.
 * - Enforces bounded HTTP readiness checks rather than relying on raw TCP port listeners.
 * - Auto-isolates to fallback port (3001) if port 3000 is occupied by a foreign worktree.
 * - Auto-launches missing services with configurable health polling and output capture.
 * - Cleans up only child processes it spawned on exit.
 * - Emits a final validation summary with selected port, verified frontend worktree, and test counts.
 * - Never prints or leaks credentials.
 */

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const filename = fileURLToPath(import.meta.url);
const dirname = path.dirname(filename);
const webDir = path.resolve(dirname, "..");

function parsePlaywrightResults(resultsPath) {
  try {
    if (!fs.existsSync(resultsPath)) return null;
    const raw = fs.readFileSync(resultsPath, "utf8");
    const json = JSON.parse(raw);
    let passed = 0;
    let failed = 0;
    let skipped = 0;

    function countSuites(suites) {
      if (!Array.isArray(suites)) return;
      for (const suite of suites) {
        if (Array.isArray(suite.specs)) {
          for (const spec of suite.specs) {
            if (Array.isArray(spec.tests)) {
              for (const test of spec.tests) {
                const status = test.status || (test.results && test.results[0]?.status);
                if (status === "expected" || status === "passed") passed++;
                else if (status === "skipped") skipped++;
                else if (status === "unexpected" || status === "failed") failed++;
              }
            }
          }
        }
        if (Array.isArray(suite.suites)) {
          countSuites(suite.suites);
        }
      }
    }

    countSuites(json.suites);
    return { passed, failed, skipped };
  } catch {
    return null;
  }
}

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
    parsePortFromUrl,
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

  // 2. Ensure frontend service (with autoFallbackPort support)
  const autoFallbackPort = process.env.DSP_P109_NO_FALLBACK === "1" ? false : 3001;
  const frontendResult = await ensureFrontendService(config, tracker, healthConfig, {
    webDir,
    autoFallbackPort,
    onProgress: (msg) => process.stdout.write(msg),
  });

  if (frontendResult.effectiveBaseUrl && frontendResult.effectiveBaseUrl !== config.baseUrl) {
    console.log(`\n[PREFLIGHT] Isolated P1-09 frontend to: ${frontendResult.effectiveBaseUrl}`);
    config.baseUrl = frontendResult.effectiveBaseUrl;
    process.env.PLAYWRIGHT_BASE_URL = frontendResult.effectiveBaseUrl;
  }

  const selectedPort = parsePortFromUrl(config.baseUrl);

  if (frontendResult.alreadyRunning) {
    console.log(`[PREFLIGHT] Frontend is already running and verified responsive (reused existing process at ${config.baseUrl}).`);
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

  console.log(`\n[EXECUTION] Launching P1-09 Chromium journey against ${config.baseUrl} (PLAYWRIGHT_SKIP_WEBSERVER=1)...`);
  const resultsJsonPath = path.resolve(webDir, "playwright-results.json");
  if (fs.existsSync(resultsJsonPath)) {
    try { fs.unlinkSync(resultsJsonPath); } catch {}
  }

  const child = spawn(
    "npx",
    ["playwright", "test", "e2e/browser/p109-critical-investment.journey.spec.ts", "--project=chromium"],
    {
      cwd: webDir,
      env: {
        ...process.env,
        PLAYWRIGHT_SKIP_WEBSERVER: "1",
        PLAYWRIGHT_BASE_URL: config.baseUrl,
      },
      stdio: "inherit",
    }
  );

  child.on("close", (code) => {
    tracker.cleanup();

    const counts = parsePlaywrightResults(resultsJsonPath) || {
      passed: code === 0 ? 1 : 0,
      failed: code !== 0 ? 1 : 0,
      skipped: 0,
    };

    const statusText = code === 0 ? "PASS" : "FAIL";

    console.log("\n==================================================");
    console.log(`P1-09 FINAL VALIDATION SUMMARY`);
    console.log("==================================================");
    console.log(`Selected Port:            ${selectedPort}`);
    console.log(`Verified Frontend Dir:    ${webDir}`);
    console.log(`Playwright Test Results:`);
    console.log(`  - Passed:               ${counts.passed}`);
    console.log(`  - Failed:               ${counts.failed}`);
    console.log(`  - Skipped:              ${counts.skipped}`);
    console.log(`Status:                   ${statusText}`);
    console.log("==================================================");

    process.exit(code || 0);
  });
}

main().catch((err) => {
  console.error(`Unexpected runner failure: ${err.message}`);
  process.exit(1);
});
