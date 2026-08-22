/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearCookieMeta,
  clearCsrfToken,
  cookieAuthPreferred,
  csrfHeaders,
  persistCookieMeta,
  persistCsrfToken,
  readCookieMeta,
  readCsrfToken,
} from "./cookieSession";
import { persistEnterpriseSession } from "./finishEnterpriseSession";
import {
  COOKIE_TOKEN_PLACEHOLDER,
  CookieSessionUnavailableError,
  clearStoredSession,
  persistSession,
  readStoredSession,
  sessionFromLoginPayload,
  sessionFromRbacLogin,
} from "./sessionStore";

const rbacTokens = {
  access_token: "secret-access",
  refresh_token: "secret-refresh",
  token_type: "bearer",
  expires_in: 3600,
  session_id: "s-1",
};

function rbacResult(extra: { csrf_token?: string; cookie_auth?: boolean } = {}) {
  return {
    user: {
      user_id: "u-1",
      username: "analyst1",
      email: "a@example.com",
      display_name: "Analyst One",
      status: "active",
      created_at: "2026-07-28T12:00:00+00:00",
      updated_at: "2026-07-28T12:00:00+00:00",
      last_login: null,
      roles: ["research_analyst"],
    },
    tokens: rbacTokens,
    session: {
      session_id: "s-1",
      user_id: "u-1",
      created_at: "2026-07-28T12:00:00+00:00",
      expires_at: "2026-07-28T13:00:00+00:00",
      revoked: false,
    },
    ...extra,
  } as never;
}

describe("cookieSession", () => {
  beforeEach(() => {
    clearStoredSession();
    clearCsrfToken();
    clearCookieMeta();
  });

  it("defaults cookie auth preferred", () => {
    expect(cookieAuthPreferred()).toBe(true);
  });

  it("persists CSRF and meta without JWTs", () => {
    persistCsrfToken("csrf-test-token", false);
    expect(readCsrfToken()).toBe("csrf-test-token");
    expect(csrfHeaders()["X-CSRF-Token"]).toBe("csrf-test-token");

    persistCookieMeta({
      subject: "u-1",
      username: "analyst",
      displayName: "Analyst",
      email: null,
      role: "research_analyst",
      roles: ["research_analyst"],
      permissions: [],
      authMethod: "cookie_rbac",
      sessionId: "s-1",
      issuedAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 3600_000).toISOString(),
      rememberMe: false,
      cookieAuth: true,
    });
    expect(readCookieMeta()?.subject).toBe("u-1");
  });

  it("sessionFromRbacLogin uses cookie placeholder when csrf present", () => {
    const session = sessionFromRbacLogin(
      {
        user: {
          user_id: "u-1",
          username: "analyst1",
          email: "a@example.com",
          display_name: "Analyst One",
          status: "active",
          created_at: "2026-07-28T12:00:00+00:00",
          updated_at: "2026-07-28T12:00:00+00:00",
          last_login: null,
          roles: ["research_analyst"],
        },
        tokens: {
          access_token: "secret-access",
          refresh_token: "secret-refresh",
          token_type: "bearer",
          expires_in: 3600,
          session_id: "s-1",
        },
        session: {
          session_id: "s-1",
          user_id: "u-1",
          created_at: "2026-07-28T12:00:00+00:00",
          expires_at: "2026-07-28T13:00:00+00:00",
          revoked: false,
        },
        csrf_token: "csrf-abc",
        cookie_auth: true,
      } as never,
      true,
    );
    expect(session.accessToken).toBe(COOKIE_TOKEN_PLACEHOLDER);
    expect(session.refreshToken).toBeNull();
    expect(session.authMethod).toBe("cookie_rbac");
    persistSession(session);
    const stored = readStoredSession();
    expect(stored?.accessToken).toBe(COOKIE_TOKEN_PLACEHOLDER);
    expect(window.localStorage.getItem("dsp.auth.session.v3")).toBeNull();
    expect(window.sessionStorage.getItem("dsp.auth.session.v3")).toBeNull();
  });

  it("uses cookie mode when only csrf_token is present", () => {
    const session = sessionFromRbacLogin(rbacResult({ csrf_token: "csrf-only" }), false);
    expect(session.accessToken).toBe(COOKIE_TOKEN_PLACEHOLDER);
    expect(session.refreshToken).toBeNull();
    persistSession(session);
    expect(window.sessionStorage.getItem("dsp.auth.session.v3")).toBeNull();
    expect(window.localStorage.getItem("dsp.auth.session.v3")).toBeNull();
  });
});

describe("cookie-preferred JWT Web Storage restriction", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    clearStoredSession();
  });

  it("Cookie-preferred browser authentication must never persist access or refresh JWTs when cookie authentication is unavailable", () => {
    expect(cookieAuthPreferred()).toBe(true);
    expect(() => sessionFromRbacLogin(rbacResult(), false)).toThrow(
      CookieSessionUnavailableError,
    );
    expect(() =>
      persistSession({
        accessToken: "secret-access",
        refreshToken: "secret-refresh",
        tokenType: "bearer",
        role: "research_analyst",
        roles: ["research_analyst"],
        permissions: [],
        subject: "u-1",
        username: "analyst1",
        displayName: "Analyst One",
        email: null,
        authMethod: "rbac_jwt",
        sessionId: "s-1",
        issuedAt: new Date().toISOString(),
        expiresAt: null,
        rememberMe: false,
      }),
    ).toThrow(CookieSessionUnavailableError);
    expect(window.localStorage.getItem("dsp.auth.session.v3")).toBeNull();
    expect(window.sessionStorage.getItem("dsp.auth.session.v3")).toBeNull();
  });

  it("fails login when cookie auth is preferred but unconfirmed", () => {
    expect(() => persistEnterpriseSession(rbacResult(), false)).toThrow(
      CookieSessionUnavailableError,
    );
    expect(window.sessionStorage.getItem("dsp.auth.session.v3")).toBeNull();
    expect(window.localStorage.getItem("dsp.auth.session.v3")).toBeNull();
  });

  it("Google OAuth cookie confirmation uses __cookie__ and skips JWT storage", () => {
    persistEnterpriseSession(
      rbacResult({ cookie_auth: true, csrf_token: "csrf-oauth" }),
      false,
    );
    const stored = readStoredSession();
    expect(stored?.accessToken).toBe(COOKIE_TOKEN_PLACEHOLDER);
    expect(stored?.refreshToken).toBeNull();
    expect(window.sessionStorage.getItem("dsp.auth.session.v3")).toBeNull();
    expect(window.localStorage.getItem("dsp.auth.session.v3")).toBeNull();
  });

  it("cookie-mode sessions do not require a stored refresh JWT", () => {
    const session = sessionFromRbacLogin(
      rbacResult({ cookie_auth: true, csrf_token: "csrf-abc" }),
      false,
    );
    persistSession(session);
    expect(readStoredSession()?.refreshToken ?? null).toBeNull();
    expect(window.sessionStorage.getItem("dsp.auth.session.v3")).toBeNull();
  });

  it("keeps explicit Bearer Web Storage when cookie auth is disabled", () => {
    vi.stubEnv("NEXT_PUBLIC_COOKIE_AUTH", "false");
    expect(cookieAuthPreferred()).toBe(false);
    const session = sessionFromRbacLogin(rbacResult(), true);
    expect(session.accessToken).toBe("secret-access");
    expect(session.refreshToken).toBe("secret-refresh");
    persistSession(session);
    expect(window.localStorage.getItem("dsp.auth.session.v3")).toContain(
      "secret-access",
    );
    const legacy = sessionFromLoginPayload(
      {
        access_token: "legacy-access",
        token_type: "bearer",
        role: "admin",
        subject: "user-1",
        username: "admin",
        auth_method: "username",
      },
      true,
    );
    expect(legacy.accessToken).toBe("legacy-access");
  });
});
