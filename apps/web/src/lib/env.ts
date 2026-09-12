/** Environment configuration — no secrets in client beyond public API URL. */

function resolveApiBaseUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
  if (explicit) {
    return explicit;
  }
  // Vercel injects NEXT_PUBLIC_VERCEL_ENV for preview/production builds.
  // Same-origin `/api/v1` is rewritten to Cloud Run (see next.config.ts).
  if (process.env.NEXT_PUBLIC_VERCEL_ENV) {
    return "/api/v1";
  }
  return "http://127.0.0.1:8000/api/v1";
}

export const env = {
  apiBaseUrl: resolveApiBaseUrl(),
  appName: process.env.NEXT_PUBLIC_APP_NAME || "DSP AI Indicator",
  tagline: "Complex Analysis. Simple Decisions.",
  /** EPS-003 Version 2.0 Release Candidate — feature freeze. */
  frontendVersion: "2.0.0-rc.1",
  foundationVersion: "2.0.0-rc.1",
  environment: process.env.NODE_ENV ?? "development",
  marketCacheTtlMs: Number(process.env.NEXT_PUBLIC_MARKET_CACHE_TTL_MS ?? 60_000),
  marketRefreshMs: Number(process.env.NEXT_PUBLIC_MARKET_REFRESH_MS ?? 60_000),
  aiProviderId:
    (process.env.NEXT_PUBLIC_AI_PROVIDER as
      | "mock"
      | "deterministic"
      | "backend"
      | undefined) ?? "deterministic",
} as const;
