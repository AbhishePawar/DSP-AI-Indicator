import type { LoginPayload } from "@/lib/api/types";
import type { Session } from "./types";

const STORAGE_KEY = "dsp.auth.session.v2";

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

export function sessionFromLoginPayload(
  payload: LoginPayload,
  rememberMe: boolean,
): Session {
  const issuedAt = new Date().toISOString();
  const username = payload.username ?? payload.subject;
  const accessToken = payload.access_token;
  return {
    accessToken,
    tokenType: payload.token_type,
    role: payload.role,
    subject: payload.subject,
    username,
    displayName: username,
    email: null,
    authMethod: payload.auth_method,
    issuedAt,
    expiresAt: resolveExpiry(accessToken, issuedAt, rememberMe),
    rememberMe,
  };
}

export function readStoredSession(): Session | null {
  if (typeof window === "undefined") return null;
  for (const store of [window.sessionStorage, window.localStorage]) {
    try {
      const raw = store.getItem(STORAGE_KEY);
      if (!raw) continue;
      const parsed = JSON.parse(raw) as Session;
      if (!parsed?.accessToken) continue;
      if (isSessionExpired(parsed)) {
        store.removeItem(STORAGE_KEY);
        continue;
      }
      return parsed;
    } catch {
      store.removeItem(STORAGE_KEY);
    }
  }
  return null;
}

export function persistSession(session: Session): void {
  const store = storageFor(session.rememberMe);
  const other = oppositeStorage(session.rememberMe);
  other?.removeItem(STORAGE_KEY);
  store?.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredSession(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(STORAGE_KEY);
  window.localStorage.removeItem(STORAGE_KEY);
}
