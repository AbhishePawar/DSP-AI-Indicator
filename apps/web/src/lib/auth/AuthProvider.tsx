"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api } from "@/lib/api/client";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import { rbacAuthApi } from "@/lib/api/rbacAuth";
import { ApiClientError } from "@/lib/api/types";
import { logger } from "@/lib/observability/logger";
import { useAuthStore } from "./authStore";
import {
  clearStoredSession,
  isSessionExpired,
  mergeUserProfile,
  persistSession,
  readStoredSession,
  sessionFromLoginPayload,
  sessionFromRbacLogin,
} from "./sessionStore";
import { clearMemoryUserData } from "@/lib/persistence/storage";
import type {
  AuthState,
  AuthenticationStatus,
  LoginCredentials,
  Session,
  User,
} from "./types";
import { userFromSession } from "./types";

export type AuthContextValue = AuthState & {
  /** @deprecated Prefer `status === "loading"` — kept for existing consumers. */
  ready: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  markExpired: () => void;
  handleUnauthorized: () => void;
  handleForbidden: () => void;
  loadProfile: () => Promise<void>;
  /** @deprecated Use `session` on AuthState — alias for compatibility. */
  setSession: (session: Session | null) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const EXPIRY_CHECK_MS = 60_000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthenticationStatus>("loading");
  const [session, setSessionState] = useState<Session | null>(null);
  const setAuthStore = useAuthStore((s) => s.setAuth);
  const resetAuthStore = useAuthStore((s) => s.reset);

  const syncStore = useCallback(
    (nextStatus: AuthenticationStatus, nextSession: Session | null) => {
      setAuthStore({
        status: nextStatus,
        session: nextSession,
        user: nextSession ? userFromSession(nextSession) : null,
      });
    },
    [setAuthStore],
  );

  const applySession = useCallback(
    (next: Session | null, nextStatus?: AuthenticationStatus) => {
      setSessionState(next);
      if (!next) {
        clearStoredSession();
        const st = nextStatus ?? "unauthenticated";
        setStatus(st);
        if (st === "unauthenticated") resetAuthStore();
        else syncStore(st, null);
        return;
      }
      if (isSessionExpired(next)) {
        clearStoredSession();
        setSessionState(null);
        setStatus("expired");
        syncStore("expired", null);
        return;
      }
      persistSession(next);
      const st = nextStatus ?? "authenticated";
      setStatus(st);
      syncStore(st, next);
    },
    [resetAuthStore, syncStore],
  );

  useEffect(() => {
    const stored = readStoredSession();
    if (!stored) {
      setStatus("unauthenticated");
      resetAuthStore();
      return;
    }
    if (isSessionExpired(stored)) {
      clearStoredSession();
      setStatus("expired");
      syncStore("expired", null);
      return;
    }
    setSessionState(stored);
    setStatus("authenticated");
    syncStore("authenticated", stored);
  }, [resetAuthStore, syncStore]);

  useEffect(() => {
    if (!session?.expiresAt || status !== "authenticated") return;
    const check = () => {
      if (session && isSessionExpired(session)) {
        logger.warn("Session expired", { subject: session.subject });
        applySession(null, "expired");
      }
    };
    check();
    const id = window.setInterval(check, EXPIRY_CHECK_MS);
    return () => window.clearInterval(id);
  }, [session, status, applySession]);

  const enrichPermissions = useCallback(async (next: Session) => {
    if (!next.roles.length) return next;
    try {
      const token =
        next.authMethod === "cookie_rbac" ? null : next.accessToken;
      const evalResult = await rbacAuthApi.evaluate(token ?? "", {
        user_id: next.subject,
        permission: "read_research",
      });
      const permissions = evalResult.result?.permissions ?? next.permissions;
      return { ...next, permissions };
    } catch {
      return next;
    }
  }, []);

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      setStatus("loading");
      syncStore("loading", null);
      const useRbac = credentials.useRbac !== false;
      const useEnterprise = credentials.useEnterprise !== false;
      try {
        if (useEnterprise && credentials.password) {
          try {
            const envelope = await enterpriseAuthApi.login({
              identifier: credentials.username.trim(),
              password: credentials.password,
              remember_me: Boolean(credentials.rememberMe),
            });
            if (envelope.ok && envelope.result?.tokens?.access_token) {
              let next = sessionFromRbacLogin(
                envelope.result as typeof envelope.result & {
                  csrf_token?: string;
                  cookie_auth?: boolean;
                },
                Boolean(credentials.rememberMe),
              );
              next = await enrichPermissions(next);
              applySession(next);
              // Note: an additive MFA step-up signal (mfa_required) may be
              // present on `envelope.result` here. This generic `login()`
              // entry point has no per-screen UI to present that challenge,
              // so callers that need step-up MFA (see LoginForm) call
              // `enterpriseAuthApi.login` directly and handle the challenge
              // via `lib/auth/finishEnterpriseSession.ts` instead of this
              // method. Session establishment above is unaffected either way
              // — see EnterpriseAuthPlatform's additive-fields contract.
              logger.info("User signed in (enterprise)", {
                subject: next.subject,
                role: next.role,
              });
              return;
            }
          } catch (enterpriseErr) {
            if (!useRbac) throw enterpriseErr;
            // Fall through to legacy RBAC username login.
          }
        }
        if (useRbac && credentials.password) {
          const envelope = await rbacAuthApi.login({
            username: credentials.username.trim(),
            password: credentials.password,
            remember_me: Boolean(credentials.rememberMe),
          });
          if (!envelope.ok || !envelope.result?.tokens?.access_token) {
            throw new Error(envelope.error || "Login failed");
          }
          let next = sessionFromRbacLogin(
            envelope.result as typeof envelope.result & {
              csrf_token?: string;
              cookie_auth?: boolean;
            },
            Boolean(credentials.rememberMe),
          );
          next = await enrichPermissions(next);
          applySession(next);
          logger.info("User signed in (rbac)", {
            subject: next.subject,
            role: next.role,
          });
          return;
        }

        const result = await api.login({
          username: credentials.username.trim(),
        });
        if (!result.ok || !result.payload?.access_token) {
          throw new Error(result.errors?.[0] || "Login failed");
        }
        const next = sessionFromLoginPayload(
          result.payload,
          Boolean(credentials.rememberMe),
        );
        applySession(next);
        logger.info("User signed in", { subject: next.subject, role: next.role });
      } catch (error) {
        setStatus(session ? "authenticated" : "unauthenticated");
        syncStore(session ? "authenticated" : "unauthenticated", session);
        if (error instanceof ApiClientError && error.status === 401) {
          throw new Error("Invalid credentials");
        }
        throw error;
      }
    },
    [applySession, enrichPermissions, session, syncStore],
  );

  const logout = useCallback(async () => {
    const current = session;
    const subject = current?.subject;
    if (
      current?.sessionId &&
      (current.authMethod === "rbac_jwt" || current.authMethod === "cookie_rbac")
    ) {
      try {
        await rbacAuthApi.logout({ session_id: current.sessionId });
      } catch (error) {
        logger.warn("RBAC logout failed — clearing local session", {
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }
    applySession(null);
    if (subject) clearMemoryUserData(subject);
    logger.info("User signed out", { subject });
  }, [applySession, session]);

  const refreshSession = useCallback(async () => {
    if (!session) return;
    setStatus("refreshing");
    syncStore("refreshing", session);

    const canRefresh =
      session.authMethod === "cookie_rbac" ||
      (session.refreshToken && session.authMethod === "rbac_jwt");
    if (canRefresh) {
      try {
        const envelope = await rbacAuthApi.refresh({
          refresh_token: session.refreshToken,
        });
        if (!envelope.ok || !envelope.result) {
          throw new Error(envelope.error || "Refresh failed");
        }
        let next = sessionFromRbacLogin(
          envelope.result as typeof envelope.result & {
            csrf_token?: string;
            cookie_auth?: boolean;
          },
          session.rememberMe,
        );
        next = {
          ...next,
          permissions: session.permissions,
        };
        next = await enrichPermissions(next);
        applySession(next);
        return;
      } catch (error) {
        logger.warn("Token refresh failed", {
          error: error instanceof Error ? error.message : String(error),
        });
        applySession(null, "expired");
        return;
      }
    }

    // Legacy sessions without refresh token — validate expiry only.
    await new Promise((resolve) => window.setTimeout(resolve, 50));
    if (isSessionExpired(session)) {
      applySession(null, "expired");
      return;
    }
    setStatus("authenticated");
    syncStore("authenticated", session);
  }, [session, applySession, enrichPermissions, syncStore]);

  const loadProfile = useCallback(async () => {
    if (
      !session ||
      (session.authMethod !== "rbac_jwt" && session.authMethod !== "cookie_rbac")
    ) {
      return;
    }
    try {
      const envelope = await rbacAuthApi.me(
        session.authMethod === "cookie_rbac" ? null : session.accessToken,
      );
      if (!envelope.ok || !envelope.result) return;
      let next = mergeUserProfile(session, envelope.result);
      next = await enrichPermissions(next);
      applySession(next);
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 401) {
        applySession(null, "expired");
      }
    }
  }, [session, applySession, enrichPermissions]);

  const markExpired = useCallback(() => {
    applySession(null, "expired");
  }, [applySession]);

  const handleUnauthorized = useCallback(() => {
    logger.warn("Unauthorized API response — expiring session");
    markExpired();
  }, [markExpired]);

  const handleForbidden = useCallback(() => {
    logger.warn("Forbidden API response");
    if (typeof window !== "undefined") {
      window.location.assign("/forbidden");
    }
  }, []);

  const setSession = useCallback(
    (next: Session | null) => {
      applySession(next);
    },
    [applySession],
  );

  const user: User | null = useMemo(
    () => (session ? userFromSession(session) : null),
    [session],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      session,
      user,
      ready: status !== "loading" && status !== "refreshing",
      login,
      logout,
      refreshSession,
      markExpired,
      handleUnauthorized,
      handleForbidden,
      loadProfile,
      setSession,
    }),
    [
      status,
      session,
      user,
      login,
      logout,
      refreshSession,
      markExpired,
      handleUnauthorized,
      handleForbidden,
      loadProfile,
      setSession,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

export type { Session, User, AuthenticationStatus, LoginCredentials };
export type { AuthSession } from "./types";
