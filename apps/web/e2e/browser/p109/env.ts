import fs from "node:fs";
import path from "node:path";

export type P109Config = {
  adminLogin: string;
  adminPassword: string;
  ticker: string;
  apiBaseUrl: string;
  baseUrl: string;
};

export type P109ConfigErrorCode =
  | "MISSING_PASSWORD"
  | "MISSING_LOGIN"
  | "MISSING_TICKER"
  | "MISSING_API_BASE_URL"
  | "MISSING_BASE_URL";

export class P109ConfigError extends Error {
  readonly code: P109ConfigErrorCode;

  constructor(code: P109ConfigErrorCode, message: string) {
    super(message);
    this.name = "P109ConfigError";
    this.code = code;
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
    path.resolve(__dirname, "../../../.env.local"),
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
    throw new P109ConfigError(
      "MISSING_PASSWORD",
      "P1-09 configuration is incomplete: set DSP_SEED_ADMIN_PASSWORD in apps/web/.env.local (DSP_P109_PASSWORD is supported only as a legacy fallback).",
    );
  }

  const adminLogin = env.DSP_P109_LOGIN?.trim() || "admin";
  const ticker = env.DSP_P109_TICKER?.trim() || "DSPFIX";
  const apiBaseUrl =
    env.PLAYWRIGHT_API_BASE_URL?.trim() || "http://127.0.0.1:8000/api/v1";
  const baseUrl = env.PLAYWRIGHT_BASE_URL?.trim() || "http://127.0.0.1:3000";

  return { adminLogin, adminPassword, ticker, apiBaseUrl, baseUrl };
}

/**
 * Fail during test-module initialization, before any browser fixture is
 * requested. This prevents a missing credential from becoming a confusing
 * browser/login failure.
 */
export function assertP109Config(
  env: NodeJS.ProcessEnv = process.env,
): P109Config {
  return resolveP109Config(env);
}

/** Diagnostic failure categories for P1-09 preflight checks. */
export type P109PreflightCategory =
  | "MISSING_CONFIGURATION"
  | "BACKEND_UNAVAILABLE"
  | "FRONTEND_UNAVAILABLE"
  | "AUTHENTICATION_FAILED";

export class P109PreflightError extends Error {
  readonly category: P109PreflightCategory;

  constructor(category: P109PreflightCategory, message: string) {
    super(message);
    this.name = "P109PreflightError";
    this.category = category;
  }
}


/**
 * Run asynchronous preflight checks against backend and frontend before launching the browser.
 * Throws P109PreflightError with distinct categories.
 */
export async function validateP109Preflight(
  config: P109Config = assertP109Config(),
  options: { timeoutMs?: number; fetchFn?: typeof fetch } = {}
): Promise<{ ok: boolean; backendReady: boolean; frontendReady: boolean }> {
  const fetcher = options.fetchFn ?? fetch;
  const timeoutMs = options.timeoutMs ?? 5000;

  // 1. Verify backend reachability
  const apiRoot = config.apiBaseUrl.replace(/\/api\/v1\/?$/, "");
  const liveUrl = `${apiRoot}/health/live`;
  const readyUrl = `${apiRoot}/health/ready`;

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const liveRes = await fetcher(liveUrl, { signal: controller.signal }).catch(() => null);
    const readyRes = await fetcher(readyUrl, { signal: controller.signal }).catch(() => null);
    clearTimeout(timer);

    if (!liveRes || !liveRes.ok || !readyRes || !readyRes.ok) {
      throw new P109PreflightError(
        "BACKEND_UNAVAILABLE",
        `Backend is unreachable at ${liveUrl}. Start local backend service before running P1-09.`
      );
    }
  } catch (err) {
    if (err instanceof P109PreflightError) throw err;
    throw new P109PreflightError(
      "BACKEND_UNAVAILABLE",
      `Backend is unreachable at ${liveUrl}. Start local backend service before running P1-09.`
    );
  }

  // 2. Verify frontend reachability
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const feRes = await fetcher(config.baseUrl, { signal: controller.signal }).catch(() => null);
    clearTimeout(timer);

    if (!feRes || !feRes.ok) {
      throw new P109PreflightError(
        "FRONTEND_UNAVAILABLE",
        `Frontend is unreachable at ${config.baseUrl}. Start local frontend dev or preview server before running P1-09.`
      );
    }
  } catch (err) {
    if (err instanceof P109PreflightError) throw err;
    throw new P109PreflightError(
      "FRONTEND_UNAVAILABLE",
      `Frontend is unreachable at ${config.baseUrl}. Start local frontend dev or preview server before running P1-09.`
    );
  }

  return { ok: true, backendReady: true, frontendReady: true };
}
