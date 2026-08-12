/**
 * HttpOnly cookie session helpers (EPIC-016).
 *
 * Production path: tokens live in HttpOnly cookies; the SPA keeps only
 * non-secret session metadata + CSRF token. Bearer/localStorage remains a
 * compatibility fallback when cookie auth is disabled.
 */

import { env } from "@/lib/env";

const CSRF_STORAGE_KEY = "dsp.auth.csrf.v1";
const META_STORAGE_KEY = "dsp.auth.meta.v1";

export type CookieAuthMeta = {
  subject: string;
  username: string;
  displayName: string;
  email: string | null;
  role: string;
  roles: string[];
  permissions: string[];
  authMethod: string;
  sessionId: string | null;
  issuedAt: string;
  expiresAt: string | null;
  rememberMe: boolean;
  cookieAuth: true;
};

export function cookieAuthPreferred(): boolean {
  const flag = process.env.NEXT_PUBLIC_COOKIE_AUTH;
  if (flag === "false" || flag === "0") return false;
  return true;
}

export function readCsrfToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return (
      window.sessionStorage.getItem(CSRF_STORAGE_KEY) ||
      window.localStorage.getItem(CSRF_STORAGE_KEY)
    );
  } catch {
    return null;
  }
}

export function persistCsrfToken(token: string, rememberMe = false): void {
  if (typeof window === "undefined") return;
  const primary = rememberMe ? window.localStorage : window.sessionStorage;
  const other = rememberMe ? window.sessionStorage : window.localStorage;
  other.removeItem(CSRF_STORAGE_KEY);
  primary.setItem(CSRF_STORAGE_KEY, token);
}

export function clearCsrfToken(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(CSRF_STORAGE_KEY);
  window.localStorage.removeItem(CSRF_STORAGE_KEY);
}

export function persistCookieMeta(meta: CookieAuthMeta): void {
  if (typeof window === "undefined") return;
  const store = meta.rememberMe ? window.localStorage : window.sessionStorage;
  const other = meta.rememberMe ? window.sessionStorage : window.localStorage;
  other.removeItem(META_STORAGE_KEY);
  store.setItem(META_STORAGE_KEY, JSON.stringify(meta));
}

export function readCookieMeta(): CookieAuthMeta | null {
  if (typeof window === "undefined") return null;
  for (const store of [window.sessionStorage, window.localStorage]) {
    try {
      const raw = store.getItem(META_STORAGE_KEY);
      if (!raw) continue;
      const parsed = JSON.parse(raw) as CookieAuthMeta;
      if (parsed?.cookieAuth && parsed.subject) return parsed;
    } catch {
      store.removeItem(META_STORAGE_KEY);
    }
  }
  return null;
}

export function clearCookieMeta(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(META_STORAGE_KEY);
  window.localStorage.removeItem(META_STORAGE_KEY);
}

export function csrfHeaders(): Record<string, string> {
  const token = readCsrfToken();
  return token ? { "X-CSRF-Token": token } : {};
}

/** Shared fetch defaults for cookie-authenticated API calls. */
export function cookieFetchInit(init: RequestInit = {}): RequestInit {
  const headers = new Headers(init.headers);
  for (const [k, v] of Object.entries(csrfHeaders())) {
    if (!headers.has(k)) headers.set(k, v);
  }
  return {
    ...init,
    headers,
    credentials: "include",
  };
}

export async function probeCookieSession(): Promise<{
  authenticated: boolean;
  csrf_token: string | null;
  session_id: string | null;
  cookie_auth: boolean;
} | null> {
  try {
    const response = await fetch(`${env.apiBaseUrl}/auth/session`, {
      method: "GET",
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) return null;
    const data = (await response.json()) as {
      payload?: {
        authenticated?: boolean;
        csrf_token?: string | null;
        session_id?: string | null;
        cookie_auth?: boolean;
      };
    };
    return {
      authenticated: Boolean(data.payload?.authenticated),
      csrf_token: data.payload?.csrf_token ?? null,
      session_id: data.payload?.session_id ?? null,
      cookie_auth: Boolean(data.payload?.cookie_auth),
    };
  } catch {
    return null;
  }
}
