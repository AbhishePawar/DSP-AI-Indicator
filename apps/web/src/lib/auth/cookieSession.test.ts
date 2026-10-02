/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it } from "vitest";

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
import {
  COOKIE_TOKEN_PLACEHOLDER,
  clearStoredSession,
  persistSession,
  readStoredSession,
  sessionFromRbacLogin,
} from "./sessionStore";

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

  it("sessionFromRbacLogin uses cookie placeholder when csrf present on the API origin", () => {
    const page = window.location;
    Object.defineProperty(window, "location", {
      configurable: true,
      value: new URL("http://127.0.0.1:8000/"),
    });
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
    Object.defineProperty(window, "location", { configurable: true, value: page });
  });

  it("keeps the bearer token when the page and API are different origins", () => {
    const session = sessionFromRbacLogin(
      {
        user: {
          user_id: "u-3",
          username: "admin",
          email: null,
          display_name: "Admin",
          status: "active",
          created_at: "2026-07-28T12:00:00+00:00",
          updated_at: "2026-07-28T12:00:00+00:00",
          last_login: null,
          roles: ["platform_admin"],
        },
        tokens: {
          access_token: "bearer-cross-origin",
          refresh_token: "refresh-cross-origin",
          token_type: "bearer",
          expires_in: 3600,
          session_id: "s-3",
        },
        session: {
          session_id: "s-3",
          user_id: "u-3",
          created_at: "2026-07-28T12:00:00+00:00",
          expires_at: "2026-07-28T13:00:00+00:00",
          revoked: false,
        },
        csrf_token: "csrf-cross",
        cookie_auth: true,
      } as never,
      false,
    );
    expect(session.accessToken).toBe("bearer-cross-origin");
    expect(session.authMethod).not.toBe("cookie_rbac");
    persistSession(session);
    expect(readStoredSession()?.accessToken).toBe("bearer-cross-origin");
  });

  it("keeps a bearer session when cookie mode is preferred but no cookie was issued", () => {
    const session = sessionFromRbacLogin(
      {
        user: {
          user_id: "u-2",
          username: "admin",
          email: null,
          display_name: "Admin",
          status: "active",
          created_at: "2026-07-28T12:00:00+00:00",
          updated_at: "2026-07-28T12:00:00+00:00",
          last_login: null,
          roles: ["platform_admin"],
        },
        tokens: {
          access_token: "bearer-access",
          refresh_token: "bearer-refresh",
          token_type: "bearer",
          expires_in: 3600,
          session_id: "s-2",
        },
        session: {
          session_id: "s-2",
          user_id: "u-2",
          created_at: "2026-07-28T12:00:00+00:00",
          expires_at: "2026-07-28T13:00:00+00:00",
          revoked: false,
        },
      } as never,
      false,
    );
    expect(session.authMethod).not.toBe("cookie_rbac");
    persistSession(session);
    const stored = readStoredSession();
    expect(stored?.accessToken).toBe("bearer-access");
    expect(stored?.username).toBe("admin");
  });
});
