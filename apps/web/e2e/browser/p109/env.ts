import fs from "node:fs";
import path from "node:path";

export type P109Config = {
  adminLogin: string;
  adminPassword: string;
  ticker: string;
  apiBaseUrl: string;
  baseUrl: string;
};

export type P109PreflightCategory =
  | "MISSING_CONFIGURATION"
  | "FIXTURE_INFRASTRUCTURE_UNAVAILABLE"
  | "BACKEND_UNAVAILABLE"
  | "FRONTEND_UNAVAILABLE"
  | "AUTHENTICATION_FAILED";

export class P109ConfigError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "P109ConfigError";
    this.code = code;
  }
}

export class P109PreflightError extends Error {
  readonly category: P109PreflightCategory;
  readonly safeRemediation: string;

  constructor(
    category: P109PreflightCategory,
    message: string,
    safeRemediation: string = ""
  ) {
    super(message);
    this.name = "P109PreflightError";
    this.category = category;
    this.safeRemediation = safeRemediation;
  }
}

function parseEnvLine(line: string): [string, string] | null {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) return null;

  const withoutExport = trimmed.startsWith("export ")
    ? trimmed.slice("export ".length).trim()
    : trimmed;
  const separator = withoutExport.indexOf("=");
  if (separator <= 0) return null;

  const key = withoutExport.slice(0, separator).trim();
  let value = withoutExport.slice(separator + 1).trim();
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  return [key, value];
}

/**
 * Locate apps/web/.env.local reliably regardless of whether tests
 * are executed from repo root, apps/web, or another directory.
 */
export function findP109LocalEnvFile(): string | null {
  const candidates = [
    process.env.DSP_P109_ENV_FILE,
    path.resolve(typeof __dirname !== "undefined" ? __dirname : process.cwd(), "../../../.env.local"),
    path.resolve(process.cwd(), "apps/web/.env.local"),
    path.resolve(process.cwd(), ".env.local"),
  ].filter((p): p is string => Boolean(p && fs.existsSync(p)));

  return candidates.length > 0 ? candidates[0] : null;
}

/** Load apps/web/.env.local without overwriting explicitly supplied process env. */
export function loadP109LocalEnv(envFile?: string): boolean {
  const target = envFile ?? findP109LocalEnvFile();
  if (!target || !fs.existsSync(target)) return false;

  const contents = fs.readFileSync(target, "utf8");
  for (const line of contents.split(/\r?\n/)) {
    const parsed = parseEnvLine(line);
    if (!parsed) continue;
    const [key, value] = parsed;
    if (process.env[key] === undefined) process.env[key] = value;
  }
  return true;
}

/**
 * Resolve the P1-09 fixture credential in one canonical order.
 *
 * 1. DSP_SEED_ADMIN_PASSWORD (canonical source shared with backend seed)
 * 2. DSP_P109_PASSWORD (legacy backwards-compatible test fallback)
 *
 * Empty or whitespace-only credentials are strictly rejected.
 */
export function resolveP109AdminPassword(
  env: NodeJS.ProcessEnv = process.env,
): string | undefined {
  const canonical = env.DSP_SEED_ADMIN_PASSWORD?.trim();
  if (canonical && canonical.length > 0) return canonical;

  const legacy = env.DSP_P109_PASSWORD?.trim();
  if (legacy && legacy.length > 0) return legacy;

  return undefined;
}

export function resolveP109Config(
  env: NodeJS.ProcessEnv = process.env,
): P109Config {
  if (env === process.env && !env.DSP_SEED_ADMIN_PASSWORD && !env.DSP_P109_PASSWORD) {
    loadP109LocalEnv();
  }

  const adminPassword = resolveP109AdminPassword(env);
  if (!adminPassword) {
    throw new P109PreflightError(
      "MISSING_CONFIGURATION",
      "P1-09 configuration is incomplete: required credential is not configured.",
      [
        "Safe Remediation:",
        "1. Create apps/web/.env.local",
        "2. Add the canonical credential:",
        "   DSP_SEED_ADMIN_PASSWORD=<local_fixture_secret>",
        "   (DSP_P109_PASSWORD is supported only as a legacy fallback)",
      ].join("\n")
    );
  }

  const adminLogin = env.DSP_P109_LOGIN?.trim() || "admin";
  const ticker = env.DSP_P109_TICKER?.trim() || "DSPFIX";
  const apiBaseUrl =
    env.PLAYWRIGHT_API_BASE_URL?.trim() || "http://127.0.0.1:8000/api/v1";
  const defaultPort = env.PORT?.trim() || "3000";
  const baseUrl = env.PLAYWRIGHT_BASE_URL?.trim() || `http://127.0.0.1:${defaultPort}`;

  return { adminLogin, adminPassword, ticker, apiBaseUrl, baseUrl };
}

export function assertP109Config(
  env: NodeJS.ProcessEnv = process.env,
): P109Config {
  return resolveP109Config(env);
}

/**
 * Validate backend, fixture infrastructure, and frontend before launching Chromium.
 */
export async function validateP109Preflight(
  config: P109Config = assertP109Config(),
  options: { timeoutMs?: number; fetchFn?: typeof fetch } = {}
): Promise<{ ok: boolean; backendReady: boolean; frontendReady: boolean; fixtureReady: boolean }> {
  const fetcher = options.fetchFn ?? fetch;
  const timeoutMs = options.timeoutMs ?? 5000;

  // 1. Verify backend reachability
  const apiRoot = config.apiBaseUrl.replace(/\/api\/v1\/?$/, "");
  const liveUrl = `${apiRoot}/health/live`;
  const readyUrl = `${apiRoot}/health/ready`;

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const [liveRes, readyRes] = await Promise.all([
      fetcher(liveUrl, { signal: controller.signal }).catch(() => null),
      fetcher(readyUrl, { signal: controller.signal }).catch(() => null),
    ]);
    clearTimeout(timer);

    if (!liveRes || !liveRes.ok || !readyRes || !readyRes.ok) {
      throw new P109PreflightError(
        "BACKEND_UNAVAILABLE",
        `Backend is unreachable at ${liveUrl} or ${readyUrl}.`,
        [
          "Safe Startup Command (Backend):",
          "DSP_ENVIRONMENT=development \\",
          "DSP_INFRA_OFFLINE=0 \\",
          "DSP_P109_E2E_FIXTURE=1 \\",
          "DSP_SEED_ADMIN_PASSWORD='[configured in apps/web/.env.local]' \\",
          "python -m uvicorn api_platform.api.app:app --host 127.0.0.1 --port 8000",
        ].join("\n")
      );
    }
  } catch (err) {
    if (err instanceof P109PreflightError) throw err;
    throw new P109PreflightError(
      "BACKEND_UNAVAILABLE",
      `Backend is unreachable at ${liveUrl}.`,
      [
        "Safe Startup Command (Backend):",
        "DSP_ENVIRONMENT=development \\",
        "DSP_INFRA_OFFLINE=0 \\",
        "DSP_P109_E2E_FIXTURE=1 \\",
        "DSP_SEED_ADMIN_PASSWORD='[configured in apps/web/.env.local]' \\",
        "python -m uvicorn api_platform.api.app:app --host 127.0.0.1 --port 8000",
      ].join("\n")
    );
  }

  // 2. Verify fixture infrastructure (quotes / statements endpoints)
  const quoteUrl = `${config.apiBaseUrl}/market/quote?symbol=${config.ticker}`;
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const quoteRes = await fetcher(quoteUrl, { signal: controller.signal }).catch(() => null);
    clearTimeout(timer);

    if (quoteRes && quoteRes.status === 503) {
      throw new P109PreflightError(
        "FIXTURE_INFRASTRUCTURE_UNAVAILABLE",
        `Backend is running but fixture infrastructure is unavailable for ${config.ticker}.`,
        [
          "Safe Remediation:",
          "Ensure backend is started with fixture memory flags:",
          "DSP_MARKET_QUOTE_MEMORY=1 DSP_FINANCIAL_STATEMENT_MEMORY=1 DSP_P109_E2E_FIXTURE=1",
        ].join("\n")
      );
    }
  } catch (err) {
    if (err instanceof P109PreflightError) throw err;
  }

  // 3. Verify frontend reachability
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const feRes = await fetcher(config.baseUrl, { signal: controller.signal }).catch(() => null);
    clearTimeout(timer);

    if (!feRes || !feRes.ok) {
      throw new P109PreflightError(
        "FRONTEND_UNAVAILABLE",
        `Frontend is unreachable at ${config.baseUrl}.`,
        [
          "Safe Startup Command (Frontend):",
          "cd apps/web && npm run dev",
        ].join("\n")
      );
    }
  } catch (err) {
    if (err instanceof P109PreflightError) throw err;
    throw new P109PreflightError(
      "FRONTEND_UNAVAILABLE",
      `Frontend is unreachable at ${config.baseUrl}.`,
      [
        "Safe Startup Command (Frontend):",
        "cd apps/web && npm run dev",
      ].join("\n")
    );
  }

  return { ok: true, backendReady: true, frontendReady: true, fixtureReady: true };
}
