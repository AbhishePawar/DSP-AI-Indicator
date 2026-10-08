/**
 * @vitest-environment jsdom
 */
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "./AuthProvider";
import {
  clearCookieMeta,
  clearCsrfToken,
  readCsrfToken,
} from "./cookieSession";
import { clearStoredSession, persistSession } from "./sessionStore";

const probeCookieSession = vi.fn();

vi.mock("./cookieSession", async () => {
  const actual = await vi.importActual<typeof import("./cookieSession")>(
    "./cookieSession",
  );

  return {
    ...actual,
    probeCookieSession: (...args: Parameters<typeof actual.probeCookieSession>) =>
      probeCookieSession(...args),
  };
});

vi.mock("@/lib/api/client", () => ({
  api: {
    setAuthFailureHandler: vi.fn(),
  },
  setApiAuthFailureHandler: vi.fn(),
}));

vi.mock("@/lib/api/enterpriseAuth", () => ({
  enterpriseAuthApi: {},
}));

vi.mock("@/lib/api/rbacAuth", () => ({
  rbacAuthApi: {
    logout: vi.fn(),
  },
}));

vi.mock("@/lib/observability/logger", () => ({
  logger: {
    warn: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

vi.mock("./authStore", () => ({
  useAuthStore: (selector: (state: {
    setAuth: ReturnType<typeof vi.fn>;
    reset: ReturnType<typeof vi.fn>;
  }) => unknown) =>
    selector({
      setAuth: vi.fn(),
      reset: vi.fn(),
    }),
}));

vi.mock("@/lib/analysis/recentAnalyses", () => ({
  clearRecentAnalyses: vi.fn(),
}));

vi.mock("@/lib/market/cache", () => ({
  clearMarketCache: vi.fn(),
}));

vi.mock("@/lib/persistence/storage", () => ({
  clearMemoryUserData: vi.fn(),
}));

vi.mock("@/lib/research/sessionStore", () => ({
  clearResearchSession: vi.fn(),
}));

describe("AuthProvider cookie-session restoration", () => {
  beforeEach(() => {
    clearStoredSession();
    clearCsrfToken();
    clearCookieMeta();
    probeCookieSession.mockReset();
    probeCookieSession.mockResolvedValue({
      authenticated: true,
      csrf_token: "csrf-restored",
      session_id: "session-1",
      cookie_auth: true,
    });

    persistSession({
      accessToken: "__cookie__",
      refreshToken: null,
      tokenType: "bearer",
      role: "research_analyst",
      roles: ["research_analyst"],
    permissions: [],
      subject: "u-1",
      username: "analyst1",
      displayName: "Analyst One",
      email: "a@example.com",
      authMethod: "cookie_rbac",
      sessionId: "session-1",
      issuedAt: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 3600_000).toISOString(),
      rememberMe: false,
    });
  });

  afterEach(() => {
    cleanup();
    clearStoredSession();
    clearCsrfToken();
    clearCookieMeta();
  });

  it("restores the server CSRF token after cookie-session reload", async () => {
    expect(readCsrfToken()).toBeNull();

    render(
      <AuthProvider>
        <div>authenticated</div>
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(probeCookieSession).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(readCsrfToken()).toBe("csrf-restored");
    });
  });

  it("includes X-CSRF-Token header in cookie logout request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const { useAuth } = await import("./AuthProvider");
    let authContext: any;
    function Consumer() {
      authContext = useAuth();
      return <div>consumer</div>;
    }

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(readCsrfToken()).toBe("csrf-restored");
    });

    await authContext.logout();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/auth/logout"),
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
    const lastCall = fetchMock.mock.calls.find((call: any[]) =>
      String(call[0]).includes("/auth/logout")
    );
    expect(lastCall).toBeDefined();
    const headers = lastCall[1].headers;
    const csrfSent = headers instanceof Headers ? headers.get("X-CSRF-Token") : headers["X-CSRF-Token"];
    expect(csrfSent).toBe("csrf-restored");
    vi.unstubAllGlobals();
  });
});
