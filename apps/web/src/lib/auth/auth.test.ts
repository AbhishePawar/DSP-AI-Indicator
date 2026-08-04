/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";

import {
  isProtectedRoute,
  isPublicRoute,
  loginRedirectUrl,
  normalizePath,
  requiresAuth,
  isAuthPublicPath,
  isMarketingPath,
} from "./routeGuards";
import {
  isSessionExpired,
  parseJwtExpiryMs,
  resolveExpiry,
  sessionFromLoginPayload,
  sessionFromRbacLogin,
  tokenStatus,
} from "./sessionStore";
import { sessionStatusLabel, userFromSession } from "./types";

describe("routeGuards", () => {
  it("marks public terminal routes", () => {
    expect(isPublicRoute("/dashboard")).toBe(true);
    expect(isPublicRoute("/companies")).toBe(true);
    expect(isPublicRoute("/research/AAPL")).toBe(true);
    expect(isPublicRoute("/analysis")).toBe(true);
  });

  it("marks protected routes", () => {
    expect(isProtectedRoute("/portfolio")).toBe(true);
    expect(isProtectedRoute("/copilot")).toBe(true);
    expect(isProtectedRoute("/diagnostics")).toBe(true);
    expect(isProtectedRoute("/profile")).toBe(true);
    expect(isProtectedRoute("/admin")).toBe(true);
    expect(requiresAuth("/portfolio")).toBe(true);
    expect(requiresAuth("/admin")).toBe(true);
  });

  it("exposes F002 / P9.2 auth public screens", () => {
    expect(isAuthPublicPath("/login")).toBe(true);
    expect(isAuthPublicPath("/signup")).toBe(true);
    expect(isAuthPublicPath("/register")).toBe(true);
    expect(isAuthPublicPath("/invite")).toBe(true);
    expect(isAuthPublicPath("/oauth/callback")).toBe(true);
    expect(isAuthPublicPath("/mobile-login")).toBe(true);
    expect(isAuthPublicPath("/email-login")).toBe(true);
    expect(isAuthPublicPath("/email-login/verify")).toBe(true);
    expect(isAuthPublicPath("/forgot-password")).toBe(true);
    expect(isAuthPublicPath("/reset-password")).toBe(true);
    expect(isAuthPublicPath("/verify-email")).toBe(true);
    expect(isAuthPublicPath("/verification-pending")).toBe(true);
    expect(isAuthPublicPath("/session-expired")).toBe(true);
    expect(isAuthPublicPath("/unauthorized")).toBe(true);
    expect(isAuthPublicPath("/forbidden")).toBe(true);
    expect(isAuthPublicPath("/logout")).toBe(true);
  });

  it("exposes P9.1 marketing public paths", () => {
    expect(isMarketingPath("/")).toBe(true);
    expect(isMarketingPath("/about")).toBe(true);
    expect(isMarketingPath("/contact")).toBe(true);
    expect(isMarketingPath("/pricing")).toBe(true);
    expect(isMarketingPath("/faq")).toBe(true);
    expect(isAuthPublicPath("/")).toBe(true);
    expect(isPublicRoute("/about")).toBe(true);
    expect(requiresAuth("/pricing")).toBe(false);
  });

  it("does not require auth for public routes", () => {
    expect(requiresAuth("/dashboard")).toBe(false);
    expect(requiresAuth("/screening")).toBe(false);
  });

  it("builds login redirect with next path", () => {
    expect(loginRedirectUrl("/portfolio")).toBe("/login?next=%2Fportfolio");
    expect(loginRedirectUrl("/portfolio", true)).toBe(
      "/login?expired=1&next=%2Fportfolio",
    );
  });

  it("normalizes safe in-app paths", () => {
    expect(normalizePath("/portfolio")).toBe("/portfolio");
    expect(normalizePath("/portfolio/")).toBe("/portfolio");
    expect(normalizePath("")).toBe("/dashboard");
    expect(normalizePath("/")).toBe("/dashboard");
  });

  it("rejects open-redirect payloads in ?next=, falling back to /dashboard", () => {
    expect(normalizePath("https://evil.com")).toBe("/dashboard");
    expect(normalizePath("http://evil.com/phish")).toBe("/dashboard");
    expect(normalizePath("//evil.com")).toBe("/dashboard");
    expect(normalizePath("///evil.com")).toBe("/dashboard");
    expect(normalizePath("/\\evil.com")).toBe("/dashboard");
    expect(normalizePath("/\\/evil.com")).toBe("/dashboard");
    expect(normalizePath("javascript:alert(1)")).toBe("/dashboard");
  });
});

describe("sessionStore", () => {
  it("creates session from login payload", () => {
    const session = sessionFromLoginPayload(
      {
        access_token: "token",
        token_type: "bearer",
        role: "admin",
        subject: "user-1",
        username: "admin",
        auth_method: "username",
      },
      true,
    );
    expect(session.username).toBe("admin");
    expect(session.rememberMe).toBe(true);
    expect(session.expiresAt).toBeTruthy();
    expect(session.roles).toEqual(["admin"]);
    expect(userFromSession(session).displayName).toBe("admin");
  });

  it("creates session from RBAC login", () => {
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
          access_token: "access",
          refresh_token: "refresh",
          token_type: "bearer",
          expires_in: 3600,
          session_id: "s-1",
        },
        session: {
          session_id: "s-1",
          user_id: "u-1",
          created_at: "2026-07-28T12:00:00+00:00",
          expires_at: "2026-07-29T12:00:00+00:00",
          revoked: false,
          refresh_token_id: "r-1",
        },
      },
      false,
      ["read_research"],
    );
    expect(session.sessionId).toBe("s-1");
    expect(session.refreshToken).toBe("refresh");
    expect(session.permissions).toEqual(["read_research"]);
    expect(tokenStatus(session).hasRefresh).toBe(true);
  });

  it("detects expired sessions", () => {
    const session = sessionFromLoginPayload(
      {
        access_token: "token",
        token_type: "bearer",
        role: "admin",
        subject: "user-1",
        username: "admin",
        auth_method: "username",
      },
      false,
    );
    const expired = {
      ...session,
      expiresAt: new Date(Date.now() - 1000).toISOString(),
    };
    expect(isSessionExpired(expired)).toBe(true);
    expect(tokenStatus(expired).valid).toBe(false);
  });

  it("parses jwt expiry when present", () => {
    const header = btoa(JSON.stringify({ alg: "none" }));
    const payload = btoa(JSON.stringify({ exp: 2_000_000_000 }));
    const token = `${header}.${payload}.sig`;
    expect(parseJwtExpiryMs(token)).toBe(2_000_000_000_000);
    expect(resolveExpiry(token, new Date().toISOString(), false)).toContain(
      "2033",
    );
  });
});

describe("sessionStatusLabel", () => {
  it("labels statuses", () => {
    expect(sessionStatusLabel("authenticated")).toBe("Authenticated");
    expect(sessionStatusLabel("expired")).toBe("Session expired");
  });
});
