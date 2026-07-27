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
import { ApiClientError } from "@/lib/api/types";
import { logger } from "@/lib/observability/logger";
import {
  clearStoredSession,
  isSessionExpired,
  persistSession,
  readStoredSession,
  sessionFromLoginPayload,
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
  logout: () => void;
  refreshSession: () => Promise<void>;
  markExpired: () => void;
  handleUnauthorized: () => void;
  /** @deprecated Use `session` on AuthState — alias for compatibility. */
  setSession: (session: Session | null) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const EXPIRY_CHECK_MS = 60_000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthenticationStatus>("loading");
  const [session, setSessionState] = useState<Session | null>(null);

  const applySession = useCallback((next: Session | null) => {
    setSessionState(next);
    if (!next) {
      clearStoredSession();
      setStatus("unauthenticated");
      return;
    }
    if (isSessionExpired(next)) {
      clearStoredSession();
      setSessionState(null);
      setStatus("expired");
      return;
    }
    persistSession(next);
    setStatus("authenticated");
  }, []);

  useEffect(() => {
    const stored = readStoredSession();
    if (!stored) {
      setStatus("unauthenticated");
      return;
    }
    if (isSessionExpired(stored)) {
      clearStoredSession();
      setStatus("expired");
      return;
    }
    setSessionState(stored);
    setStatus("authenticated");
  }, []);

  useEffect(() => {
    if (!session?.expiresAt || status !== "authenticated") return;
    const check = () => {
      if (session && isSessionExpired(session)) {
        logger.warn("Session expired", { subject: session.subject });
        applySession(null);
        setStatus("expired");
      }
    };
    check();
    const id = window.setInterval(check, EXPIRY_CHECK_MS);
    return () => window.clearInterval(id);
  }, [session, status, applySession]);

  const login = useCallback(async (credentials: LoginCredentials) => {
    setStatus("loading");
    try {
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
      if (error instanceof ApiClientError && error.status === 401) {
        throw new Error("Invalid credentials");
      }
      throw error;
    }
  }, [applySession, session]);

  const logout = useCallback(() => {
    const subject = session?.subject;
    applySession(null);
    if (subject) clearMemoryUserData(subject);
    logger.info("User signed out", { subject });
  }, [applySession, session?.subject]);

  const refreshSession = useCallback(async () => {
    if (!session) return;
    setStatus("refreshing");
    // Placeholder — no refresh token endpoint in current API contract.
    await new Promise((resolve) => window.setTimeout(resolve, 200));
    if (isSessionExpired(session)) {
      applySession(null);
      setStatus("expired");
      return;
    }
    setStatus("authenticated");
  }, [session, applySession]);

  const markExpired = useCallback(() => {
    applySession(null);
    setStatus("expired");
  }, [applySession]);

  const handleUnauthorized = useCallback(() => {
    logger.warn("Unauthorized API response — expiring session");
    markExpired();
  }, [markExpired]);

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
