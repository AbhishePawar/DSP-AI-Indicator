#!/usr/bin/env node

/**
 * P1-09 Local Execution Runner.
 *
 * 1. Explicitly loads apps/web/.env.local.
 * 2. Checks if backend (127.0.0.1:8000) and frontend (127.0.0.1:3000) are running.
 * 3. Auto-starts missing services when supported by local tools (python/uvicorn, npm/next).
 * 4. Polls health endpoints until ready or times out with clear manual startup instructions.
 * 5. Runs the P1-09 Chromium journey with PLAYWRIGHT_SKIP_WEBSERVER=1.
 * 6. Always cleans up any background processes it started on exit.
 * 7. Never echoes or leaks the credential value.
 */

import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const filename = fileURLToPath(import.meta.url);
const dirname = path.dirname(filename);
const webDir = path.resolve(dirname, "..");
const repoRoot = path.resolve(webDir, "../..");

const spawnedProcesses = [];

function registerProcessForCleanup(child) {
  spawnedProcesses.push(child);
}

function cleanupSpawnedProcesses() {
  for (const child of spawnedProcesses) {
    if (child && !child.killed) {
      try {
        child.kill("SIGTERM");
      } catch {
        /* ignore */
      }
    }
  }
}

process.on("exit", cleanupSpawnedProcesses);
process.on("SIGINT", () => {
  cleanupSpawnedProcesses();
  process.exit(130);
});
process.on("SIGTERM", () => {
  cleanupSpawnedProcesses();
  process.exit(143);
});

async function checkUrl(url, timeoutMs = 2000) {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const res = await fetch(url, { signal: controller.signal }).catch(() => null);
    clearTimeout(timer);
    return res !== null && res.ok;
  } catch {
    return false;
  }
}

async function pollHealth(checkFn, description, maxRetries = 20, delayMs = 1000) {
  process.stdout.write(`[PREFLIGHT] Waiting for ${description} to become ready...`);
  for (let i = 0; i < maxRetries; i++) {
    const ok = await checkFn();
    if (ok) {
      process.stdout.write(" READY\n");
      return true;
    }
    process.stdout.write(".");
    await new Promise((r) => setTimeout(r, delayMs));
  }
  process.stdout.write(" TIMED OUT\n");
  return false;
}

async function tryStartBackend(config) {
  const apiRoot = config.apiBaseUrl.replace(/\/api\/v1\/?$/, "");
  const isLive = await checkUrl(`${apiRoot}/health/live`, 1000);
  const isReady = await checkUrl(`${apiRoot}/health/ready`, 1000);

  if (isLive && isReady) {
    console.log(`[PREFLIGHT] Backend is already running at ${apiRoot}.`);
    return true;
  }

  console.log(`[PREFLIGHT] Backend is not running at ${apiRoot}. Attempting local startup in fixture mode...`);

  let child;
  try {
    child = spawn(
      "python",
      [
        "-m",
        "uvicorn",
        "api_platform.api.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
      ],
      {
        cwd: repoRoot,
        env: {
          ...process.env,
          DSP_ENVIRONMENT: "development",
          DSP_INFRA_OFFLINE: "0",
          DSP_MARKET_QUOTE_MEMORY: "1",
          DSP_FINANCIAL_STATEMENT_MEMORY: "1",
          DSP_P109_E2E_FIXTURE: "1",
          DSP_SEED_ADMIN_PASSWORD: config.adminPassword,
          DSP_COOKIE_AUTH: "true",
          DSP_ENABLE_SECURITY: "false",
          PYTHONUNBUFFERED: "1",
          NEXT_PUBLIC_API_BASE_URL: config.apiBaseUrl,
        },
        stdio: "ignore",
      }
    );
    child.on("error", () => {});
    registerProcessForCleanup(child);
  } catch (err) {
    console.warn(`[PREFLIGHT] Could not launch Python uvicorn: ${err.message}`);
    return false;
  }

  const ready = await pollHealth(
    async () => {
      const l = await checkUrl(`${apiRoot}/health/live`, 1000);
      const r = await checkUrl(`${apiRoot}/health/ready`, 1000);
      return l && r;
    },
    "Backend (http://127.0.0.1:8000)",
    25,
    1000
  );

  return ready;
}

async function tryStartFrontend(config) {
  const isUp = await checkUrl(config.baseUrl, 1000);
  if (isUp) {
    console.log(`[PREFLIGHT] Frontend is already running at ${config.baseUrl}.`);
    return true;
  }

  console.log(`[PREFLIGHT] Frontend is not running at ${config.baseUrl}. Attempting local startup...`);

  let child;
  try {
    child = spawn("npm", ["run", "dev", "--", "-p", "3000"], {
      cwd: webDir,
      env: {
        ...process.env,
        PORT: "3000",
        HOSTNAME: "127.0.0.1",
        NEXT_PUBLIC_API_BASE_URL: config.apiBaseUrl,
      },
      stdio: "ignore",
    });
    child.on("error", () => {});
    registerProcessForCleanup(child);
  } catch (err) {
    console.warn(`[PREFLIGHT] Could not launch npm run dev: ${err.message}`);
    return false;
  }

  const ready = await pollHealth(
    async () => checkUrl(config.baseUrl, 1000),
    `Frontend (${config.baseUrl})`,
    25,
    1000
  );

  return ready;
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

  // 1. Attempt to start backend if missing
  const backendReady = await tryStartBackend(config);
  if (!backendReady) {
    console.error("\n[PREFLIGHT] Automatic backend startup did not succeed. Manual startup required:");
    console.error([
      "DSP_ENVIRONMENT=development \\",
      "DSP_INFRA_OFFLINE=0 \\",
      "DSP_MARKET_QUOTE_MEMORY=1 \\",
      "DSP_FINANCIAL_STATEMENT_MEMORY=1 \\",
      "DSP_P109_E2E_FIXTURE=1 \\",
      "DSP_SEED_ADMIN_PASSWORD='[configured in apps/web/.env.local]' \\",
      "python -m uvicorn api_platform.api.app:app --host 127.0.0.1 --port 8000",
    ].join("\n"));
  }

  // 2. Attempt to start frontend if missing
  const frontendReady = await tryStartFrontend(config);
  if (!frontendReady) {
    console.error("\n[PREFLIGHT] Automatic frontend startup did not succeed. Manual startup required:");
    console.error([
      "cd apps/web && npm run dev",
    ].join("\n"));
  }

  // 3. Re-run preflight verification
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
    cleanupSpawnedProcesses();
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
    cleanupSpawnedProcesses();
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
  cleanupSpawnedProcesses();
  console.error(`Unexpected runner failure: ${err.message}`);
  process.exit(1);
});
