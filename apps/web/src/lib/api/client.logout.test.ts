/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api } from "./client";
import { persistCsrfToken, clearCsrfToken, readCsrfToken, persistCookieMeta, readCookieMeta } from "@/lib/auth/cookieSession";
import { persistSession, readStoredSession, clearStoredSession, COOKIE_TOKEN_PLACEHOLDER } from "@/lib/auth/sessionStore";
import { pushRecentAnalysis, loadRecentAnalyses, clearRecentAnalyses } from "@/lib/analysis/recentAnalyses";
import { useAuthStore } from "@/lib/auth/authStore";
import { archiveResearchSession, listArchivedSessions, clearResearchArchive } from "@/lib/copilot/sessionArchive";

describe("api.logout", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    clearStoredSession();
    clearCsrfToken();
    clearRecentAnalyses();
    clearResearchArchive();
    useAuthStore.getState().reset();
    window.sessionStorage.clear();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("calls /auth/logout via POST and clears client-side state, auth store, research archive, and oauth state", async () => {
    persistCsrfToken("csrf-logout-token", false);
    persistCookieMeta({
      subject: "u-logout",
      username: "admin",
      displayName: "Admin",
      email: null,
      role: "admin",
      roles: ["admin"],
      permissions: [],
      authMethod: "cookie",
      sessionId: "s-logout",
      issuedAt: new Date().toISOString(),
      expiresAt: null,
      rememberMe: false,
      cookieAuth: true,
    });
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
    archiveResearchSession({
      ticker: "TCS",
      exchange: "NSE",
      company: "Tata Consultancy Services",
      analysedAt: new Date().toISOString(),
      request: { ticker: "TCS" } as unknown as import("@/lib/api/compositionTypes").AnalyseRequest,
      response: { ok: true } as unknown as import("@/lib/api/compositionTypes").AnalyseResponse,
    });
    window.sessionStorage.setItem("dsp.oauth.pending", JSON.stringify({ state: "xyz" }));
    useAuthStore.getState().setAuth({
      user: {
        subject: "u-logout",
        username: "admin",
        displayName: "Admin",
        email: "admin@example.com",
        role: "admin",
        roles: ["admin"],
        permissions: [],
      },
    });

    expect(readStoredSession()).not.toBeNull();
    expect(readCsrfToken()).toBe("csrf-logout-token");
    expect(readCookieMeta()).not.toBeNull();
    expect(loadRecentAnalyses().length).toBe(1);
    expect(listArchivedSessions().length).toBe(1);
    expect(window.sessionStorage.getItem("dsp.oauth.pending")).not.toBeNull();
    expect(useAuthStore.getState().user).not.toBeNull();

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

    // Client session, CSRF, cookie meta & caches must be cleared
    expect(readStoredSession()).toBeNull();
    expect(readCsrfToken()).toBeNull();
    expect(readCookieMeta()).toBeNull();
    expect(loadRecentAnalyses().length).toBe(0);
    expect(listArchivedSessions().length).toBe(0);
    expect(window.sessionStorage.getItem("dsp.oauth.pending")).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
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
