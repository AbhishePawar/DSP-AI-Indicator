/** Environment configuration — no secrets in client beyond public API URL. */

/** Same-origin API path served by the edge proxy (Caddy `reverse_proxy api:8000`). */
export const SAME_ORIGIN_API_BASE_URL = "/api/v1";
/** Local dev default when no public API URL is configured and we're off the browser. */
export const LOCAL_API_BASE_URL = "http://127.0.0.1:8000/api/v1";

/**
 * Resolve the API base URL the frontend should call.
 *
 * When `NEXT_PUBLIC_API_BASE_URL` is set we always honor it. When it is empty
 * we must NOT fall back to localhost in a deployed browser — that request can
 * never succeed and surfaces as "Authentication service temporarily
 * unavailable". Instead, a browser falls back to the same-origin `/api/v1`
 * path, which the edge proxy forwards to the API. Only non-browser contexts
 * (SSR/local dev/tests) fall back to the localhost dev server.
 */
export function resolveApiBaseUrl(
  rawUrl: string | undefined,
  isBrowser: boolean,
): string {
  const configured = rawUrl?.trim().replace(/\/$/, "");
  if (configured) return configured;
  return isBrowser ? SAME_ORIGIN_API_BASE_URL : LOCAL_API_BASE_URL;
}

export const env = {
  apiBaseUrl: resolveApiBaseUrl(
    process.env.NEXT_PUBLIC_API_BASE_URL,
    typeof window !== "undefined",
  ),
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
