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

/** Load apps/web/.env.local without overwriting explicitly supplied process env. */
export function loadP109LocalEnv(
  envFile = path.resolve(process.cwd(), ".env.local"),
): boolean {
  if (!fs.existsSync(envFile)) return false;

  const contents = fs.readFileSync(envFile, "utf8");
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
 * The backend seed uses DSP_SEED_ADMIN_PASSWORD as its canonical source.
 * DSP_P109_PASSWORD exists only as a backwards-compatible test fallback.
 */
export function resolveP109AdminPassword(
  env: NodeJS.ProcessEnv = process.env,
): string | undefined {
  const canonical = env.DSP_SEED_ADMIN_PASSWORD;
  if (canonical !== undefined && canonical !== "") return canonical;

  const legacy = env.DSP_P109_PASSWORD;
  if (legacy !== undefined && legacy !== "") return legacy;

  return undefined;
}

export function resolveP109Config(
  env: NodeJS.ProcessEnv = process.env,
): P109Config {
  const adminPassword = resolveP109AdminPassword(env);
  if (!adminPassword) {
    throw new P109ConfigError(
      "MISSING_PASSWORD",
      "P1-09 configuration is incomplete: set DSP_SEED_ADMIN_PASSWORD in apps/web/.env.local (DSP_P109_PASSWORD is supported only as a legacy fallback).",
    );
  }

  const adminLogin = env.DSP_P109_LOGIN ?? "admin";
  const ticker = env.DSP_P109_TICKER ?? "DSPFIX";
  const apiBaseUrl =
    env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
  const baseUrl = env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";

  if (!adminLogin) {
    throw new P109ConfigError(
      "MISSING_LOGIN",
      "P1-09 configuration is missing DSP_P109_LOGIN.",
    );
  }
  if (!ticker) {
    throw new P109ConfigError(
      "MISSING_TICKER",
      "P1-09 configuration is missing DSP_P109_TICKER.",
    );
  }
  if (!apiBaseUrl) {
    throw new P109ConfigError(
      "MISSING_API_BASE_URL",
      "P1-09 configuration is missing PLAYWRIGHT_API_BASE_URL.",
    );
  }
  if (!baseUrl) {
    throw new P109ConfigError(
      "MISSING_BASE_URL",
      "P1-09 configuration is missing PLAYWRIGHT_BASE_URL.",
    );
  }

  return { adminLogin, adminPassword, ticker, apiBaseUrl, baseUrl };
}

/**
 * Fail during test-module initialization, before any browser fixture is
 * requested. This prevents a missing credential from becoming a confusing
 * browser/login failure.
 */
export function assertP109Config(env: NodeJS.ProcessEnv = process.env): P109Config {
  return resolveP109Config(env);
}
