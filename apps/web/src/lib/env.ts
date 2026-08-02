/** Environment configuration — no secrets in client beyond public API URL. */

export const env = {
  apiBaseUrl:
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
    "http://127.0.0.1:8000/api/v1",
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
