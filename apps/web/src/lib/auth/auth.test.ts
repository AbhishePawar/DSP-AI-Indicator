import { describe, expect, it } from "vitest";

import {
  isProtectedRoute,
  isPublicRoute,
  loginRedirectUrl,
  requiresAuth,
} from "./routeGuards";
import {
  isSessionExpired,
  parseJwtExpiryMs,
  resolveExpiry,
  sessionFromLoginPayload,
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
    expect(requiresAuth("/portfolio")).toBe(true);
  });

  it("does not require auth for public routes", () => {
    expect(requiresAuth("/dashboard")).toBe(false);
    expect(requiresAuth("/screening")).toBe(false);
  });

  it("builds login redirect with next path", () => {
    expect(loginRedirectUrl("/portfolio")).toBe("/login?next=%2Fportfolio");
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
    expect(userFromSession(session).displayName).toBe("admin");
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
  });

  it("parses jwt exp when present", () => {
    const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
    const payload = btoa(
      JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }),
    );
    const token = `${header}.${payload}.sig`;
    expect(parseJwtExpiryMs(token)).toBeGreaterThan(Date.now());
    expect(
      resolveExpiry(token, new Date().toISOString(), false),
    ).toBeTruthy();
  });
});

describe("sessionStatusLabel", () => {
  it("maps authentication statuses", () => {
    expect(sessionStatusLabel("authenticated")).toBe("Authenticated");
    expect(sessionStatusLabel("expired")).toBe("Session expired");
  });
});
