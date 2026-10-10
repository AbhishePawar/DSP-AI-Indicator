/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api } from "./client";
import { persistCsrfToken, clearCsrfToken } from "@/lib/auth/cookieSession";
import { persistSession, readStoredSession, clearStoredSession, COOKIE_TOKEN_PLACEHOLDER } from "@/lib/auth/sessionStore";
import { pushRecentAnalysis, loadRecentAnalyses, clearRecentAnalyses } from "@/lib/analysis/recentAnalyses";

describe("api.logout", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    clearStoredSession();
    clearCsrfToken();
    clearRecentAnalyses();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("calls /auth/logout via POST and clears client-side state", async () => {
    persistCsrfToken("csrf-logout-token", false);
    persistSession({
      accessToken: COOKIE_TOKEN_PLACEHOLDER,
      refreshToken: null,
      tokenType: "bearer",
      role: "admin",
      roles: ["admin"],
      permissions: [],
      subject: "u-logout",
      username: "admin",
      displayName: "Admin",
      email: null,
      authMethod: "cookie",
      sessionId: "s-logout",
      issuedAt: new Date().toISOString(),
      expiresAt: null,
      rememberMe: false,
    });
    pushRecentAnalysis({
      ticker: "TCS",
      company: "Tata Consultancy Services",
      exchange: "NSE",
      recommendation: "Analysed",
      analysedAt: new Date().toISOString(),
    });

    expect(readStoredSession()).not.toBeNull();
    expect(loadRecentAnalyses().length).toBe(1);

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      text: async () => JSON.stringify({ ok: true }),
      json: async () => ({ ok: true }),
    });
    global.fetch = fetchMock;

    const result = await api.logout();

    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/auth/logout");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    const headers = init.headers as Headers;
    expect(headers.get("X-CSRF-Token")).toBe("csrf-logout-token");

    // Client session & caches must be cleared
    expect(readStoredSession()).toBeNull();
    expect(loadRecentAnalyses().length).toBe(0);
  });

  it("clears client-side state even when server logout returns 500 or network fails", async () => {
    persistSession({
      accessToken: COOKIE_TOKEN_PLACEHOLDER,
      refreshToken: null,
      tokenType: "bearer",
      role: "admin",
      roles: ["admin"],
      permissions: [],
      subject: "u-logout",
      username: "admin",
      displayName: "Admin",
      email: null,
      authMethod: "cookie",
      sessionId: "s-logout",
      issuedAt: new Date().toISOString(),
      expiresAt: null,
      rememberMe: false,
    });

    const fetchMock = vi.fn().mockRejectedValue(new Error("Network connection lost"));
    global.fetch = fetchMock;

    const result = await api.logout();

    expect(result.ok).toBe(false);
    expect(readStoredSession()).toBeNull();
  });
});
