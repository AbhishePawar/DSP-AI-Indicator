import type { LoginPayload } from "@/lib/api/types";
import type { RbacLoginResult, RbacUser } from "@/lib/api/rbacTypes";
import {
  clearCookieMeta,
  clearCsrfToken,
  cookieAuthPreferred,
  persistCookieMeta,
  persistCsrfToken,
  readCookieMeta,
  type CookieAuthMeta,
} from "./cookieSession";
import type { Session } from "./types";

const STORAGE_KEY = "dsp.auth.session.v3";
const LEGACY_STORAGE_KEY = "dsp.auth.session.v2";
/** Sentinel — real JWTs stay HttpOnly; SPA must not persist secrets. */
export const COOKIE_TOKEN_PLACEHOLDER = "__cookie__";

const SESSION_TTL_MS = 8 * 60 * 60 * 1000;
const REMEMBER_TTL_MS = 30 * 24 * 60 * 60 * 1000;

function storageFor(rememberMe: boolean): Storage | null {
  if (typeof window === "undefined") return null;
  return rememberMe ? window.localStorage : window.sessionStorage;
}

function oppositeStorage(rememberMe: boolean): Storage | null {
  if (typeof window === "undefined") return null;
  return rememberMe ? window.sessionStorage : window.localStorage;
}

export function parseJwtExpiryMs(token: string): number | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(
      atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")),
    ) as { exp?: number };
    return typeof payload.exp === "number" ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

export function resolveExpiry(
  accessToken: string,
  issuedAt: string,
  rememberMe: boolean,
): string | null {
  const jwtExp = parseJwtExpiryMs(accessToken);
  if (jwtExp) return new Date(jwtExp).toISOString();
  const ttl = rememberMe ? REMEMBER_TTL_MS : SESSION_TTL_MS;
  return new Date(new Date(issuedAt).getTime() + ttl).toISOString();
}

export function isSessionExpired(session: Session, now = Date.now()): boolean {
  if (!session.expiresAt) return false;
  return new Date(session.expiresAt).getTime() <= now;
}

function normalizeLegacy(raw: Record<string, unknown>): Session | null {
  if (typeof raw.accessToken !== "string") return null;
  return {
    accessToken: raw.accessToken,
    refreshToken:
      typeof raw.refreshToken === "string" ? raw.refreshToken : null,
    tokenType: String(raw.tokenType || "bearer"),
    role: String(raw.role || "read_only"),
    roles: Array.isArray(raw.roles)
      ? (raw.roles as string[])
      : [String(raw.role || "read_only")],
    permissions: Array.isArray(raw.permissions)
      ? (raw.permissions as string[])
      : [],
    subject: String(raw.subject || ""),
    username: String(raw.username || raw.subject || ""),
    displayName: String(raw.displayName || raw.username || ""),
    email: typeof raw.email === "string" ? raw.email : null,
    authMethod: String(raw.authMethod || "jwt"),
    sessionId: typeof raw.sessionId === "string" ? raw.sessionId : null,
    issuedAt: String(raw.issuedAt || new Date().toISOString()),
    expiresAt: typeof raw.expiresAt === "string" ? raw.expiresAt : null,
    rememberMe: Boolean(raw.rememberMe),
  };
}

export function sessionFromLoginPayload(
  payload: LoginPayload & { refresh_token?: string; session_id?: string },
  rememberMe: boolean,
): Session {
  const issuedAt = new Date().toISOString();
  const username = payload.username ?? payload.subject;
  const accessToken = payload.access_token;
  return {
    accessToken,
    refreshToken: payload.refresh_token ?? null,
    tokenType: payload.token_type,
    role: payload.role,
    roles: [payload.role],
    permissions: [],
    subject: payload.subject,
    username,
    displayName: username,
    email: null,
    authMethod: payload.auth_method,
    sessionId: payload.session_id ?? null,
    issuedAt,
    expiresAt: resolveExpiry(accessToken, issuedAt, rememberMe),
    rememberMe,
  };
}

export function sessionFromRbacLogin(
  result: RbacLoginResult & { csrf_token?: string; cookie_auth?: boolean },
  rememberMe: boolean,
  permissions: string[] = [],
): Session {
  const issuedAt = new Date().toISOString();
  const { user, tokens, session } = result;
  const roles = user.roles?.length ? user.roles : ["read_only"];
  const useCookies =
    cookieAuthPreferred() &&
    (Boolean(result.cookie_auth) || Boolean(result.csrf_token));
  if (result.csrf_token) {
    persistCsrfToken(result.csrf_token, rememberMe);
  }
  const accessToken = useCookies
    ? COOKIE_TOKEN_PLACEHOLDER
    : tokens.access_token;
  const refreshToken = useCookies ? null : tokens.refresh_token;
  const next: Session = {
    accessToken,
    refreshToken,
    tokenType: tokens.token_type || "bearer",
    role: roles[0] || "read_only",
    roles,
    permissions,
    subject: user.user_id,
    username: user.username,
    displayName: user.display_name || user.username,
    email: user.email || null,
    authMethod: useCookies ? "cookie_rbac" : "rbac_jwt",
    sessionId: tokens.session_id || session.session_id,
    issuedAt,
    expiresAt: resolveExpiry(tokens.access_token, issuedAt, rememberMe),
    rememberMe,
  };
  return next;
}

export function mergeUserProfile(session: Session, user: RbacUser): Session {
  const roles = user.roles?.length ? user.roles : session.roles;
  return {
    ...session,
    subject: user.user_id || session.subject,
    username: user.username || session.username,
    displayName: user.display_name || session.displayName,
    email: user.email || session.email,
    roles,
    role: roles[0] || session.role,
  };
}

function metaToSession(meta: CookieAuthMeta): Session {
  return {
    accessToken: COOKIE_TOKEN_PLACEHOLDER,
    refreshToken: null,
    tokenType: "bearer",
    role: meta.role,
    roles: meta.roles,
    permissions: meta.permissions,
    subject: meta.subject,
    username: meta.username,
    displayName: meta.displayName,
    email: meta.email,
    authMethod: meta.authMethod || "cookie_rbac",
    sessionId: meta.sessionId,
    issuedAt: meta.issuedAt,
    expiresAt: meta.expiresAt,
    rememberMe: meta.rememberMe,
  };
}

export function readStoredSession(): Session | null {
  if (typeof window === "undefined") return null;
  if (cookieAuthPreferred()) {
    const meta = readCookieMeta();
    if (meta) {
      const session = metaToSession(meta);
      if (!isSessionExpired(session)) return session;
      clearCookieMeta();
    }
  }
  for (const store of [window.sessionStorage, window.localStorage]) {
    try {
      for (const key of [STORAGE_KEY, LEGACY_STORAGE_KEY]) {
        const raw = store.getItem(key);
        if (!raw) continue;
        const parsed = normalizeLegacy(JSON.parse(raw) as Record<string, unknown>);
        if (!parsed?.accessToken) continue;
        if (isSessionExpired(parsed)) {
          store.removeItem(key);
          continue;
        }
        // Migrate away from persisted secrets when cookie mode is preferred.
        if (
          cookieAuthPreferred() &&
          parsed.accessToken &&
          parsed.accessToken !== COOKIE_TOKEN_PLACEHOLDER
        ) {
          store.removeItem(key);
          continue;
        }
        return parsed;
      }
    } catch {
      store.removeItem(STORAGE_KEY);
      store.removeItem(LEGACY_STORAGE_KEY);
    }
  }
  return null;
}

export function persistSession(session: Session): void {
  const isCookie =
    cookieAuthPreferred() &&
    (session.authMethod === "cookie_rbac" ||
      session.accessToken === COOKIE_TOKEN_PLACEHOLDER);
  if (isCookie) {
    // Never write JWTs / refresh tokens to Web Storage.
    clearLegacyTokenStorage();
    persistCookieMeta({
      subject: session.subject,
      username: session.username,
      displayName: session.displayName,
      email: session.email,
      role: session.role,
      roles: session.roles,
      permissions: session.permissions,
      authMethod: "cookie_rbac",
      sessionId: session.sessionId,
      issuedAt: session.issuedAt,
      expiresAt: session.expiresAt,
      rememberMe: session.rememberMe,
      cookieAuth: true,
    });
    return;
  }
  const store = storageFor(session.rememberMe);
  const other = oppositeStorage(session.rememberMe);
  other?.removeItem(STORAGE_KEY);
  other?.removeItem(LEGACY_STORAGE_KEY);
  store?.removeItem(LEGACY_STORAGE_KEY);
  store?.setItem(STORAGE_KEY, JSON.stringify(session));
}

function clearLegacyTokenStorage(): void {
  if (typeof window === "undefined") return;
  for (const store of [window.sessionStorage, window.localStorage]) {
    store.removeItem(STORAGE_KEY);
    store.removeItem(LEGACY_STORAGE_KEY);
  }
}

export function clearStoredSession(): void {
  if (typeof window === "undefined") return;
  clearLegacyTokenStorage();
  clearCookieMeta();
  clearCsrfToken();
}

export function tokenStatus(session: Session | null, now = Date.now()): {
  label: string;
  valid: boolean;
  expiresAt: string | null;
  hasRefresh: boolean;
} {
  if (!session) {
    return { label: "No token", valid: false, expiresAt: null, hasRefresh: false };
  }
  const expired = isSessionExpired(session, now);
  return {
    label: expired ? "Expired" : "Valid",
    valid: !expired,
    expiresAt: session.expiresAt,
    hasRefresh: Boolean(session.refreshToken),
  };
}
