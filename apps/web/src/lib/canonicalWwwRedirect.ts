/**
 * Production www canonicalization. Destination origin is hardcoded.
 * Host headers are only used to detect the exact www hostname.
 */

export const WWW_PRODUCTION_HOST = "www.dspaiindicator.com";
export const CANONICAL_PRODUCTION_HOST = "dspaiindicator.com";
export const CANONICAL_PRODUCTION_ORIGIN = "https://dspaiindicator.com";
export const CANONICAL_WWW_REDIRECT_STATUS = 301 as const;

const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);

export type HeaderReader = {
  get(name: string): string | null;
};

export function normalizeHostname(raw: string | null | undefined): string {
  const first = String(raw || "").split(",")[0].trim().toLowerCase();
  if (!first) return "";
  if (first.startsWith("[")) {
    const end = first.indexOf("]");
    return end >= 0 ? first.slice(0, end + 1) : first;
  }
  return first.replace(/:\d+$/, "");
}

export function isSafeHostname(hostname: string): boolean {
  if (!hostname || hostname.length > 253) return false;
  return /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$/.test(
    hostname,
  );
}

export function isLoopbackHostname(hostname: string): boolean {
  return LOOPBACK_HOSTS.has(hostname);
}

/**
 * Resolve the public hostname for www detection only.
 * Loopback Host wins so a spoofed X-Forwarded-Host cannot bounce local traffic.
 * Destination URLs are never taken from these headers.
 */
export function resolveRequestHostname(
  headers: HeaderReader,
  fallbackHostname = "",
): string {
  const host = normalizeHostname(headers.get("host") || fallbackHostname);
  if (isLoopbackHostname(host)) {
    return host;
  }
  if (host === WWW_PRODUCTION_HOST) {
    return host;
  }
  const forwarded = normalizeHostname(headers.get("x-forwarded-host"));
  if (forwarded === WWW_PRODUCTION_HOST && isSafeHostname(forwarded)) {
    return forwarded;
  }
  return host;
}

export function canonicalWwwRedirectLocation(
  hostname: string,
  pathname: string,
  search = "",
): string | null {
  if (hostname !== WWW_PRODUCTION_HOST) {
    return null;
  }
  const path = pathname.startsWith("/") ? pathname : `/${pathname || ""}`;
  const query =
    search && !search.startsWith("?") ? `?${search}` : search;
  return `${CANONICAL_PRODUCTION_ORIGIN}${path}${query}`;
}

export function productionWwwRedirect(
  headers: HeaderReader,
  pathname: string,
  search = "",
  fallbackHostname = "",
): { status: 301; location: string } | null {
  const hostname = resolveRequestHostname(headers, fallbackHostname);
  const location = canonicalWwwRedirectLocation(hostname, pathname, search);
  if (!location) return null;
  return { status: CANONICAL_WWW_REDIRECT_STATUS, location };
}
