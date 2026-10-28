/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  persistCsrfToken,
  clearCsrfToken,
  probeCookieSession,
} from "@/lib/auth/cookieSession";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import { rbacAuthApi } from "@/lib/api/rbacAuth";
import { adminApi } from "@/lib/api/adminClient";
import { betaApi } from "@/lib/beta/betaApi";
import { clearStoredSession } from "@/lib/auth/sessionStore";
import { buildApiUrl } from "@/lib/env";

describe("direct fetch authentication and URL normalization", () => {
  const originalFetch = global.fetch;
  const originalEnvCookieAuth = process.env.NEXT_PUBLIC_COOKIE_AUTH;

  beforeEach(() => {
    clearStoredSession();
    clearCsrfToken();
    process.env.NEXT_PUBLIC_COOKIE_AUTH = "true";
  });

  afterEach(() => {
    global.fetch = originalFetch;
    process.env.NEXT_PUBLIC_COOKIE_AUTH = originalEnvCookieAuth;
    vi.restoreAllMocks();
  });

  it("probeCookieSession uses normalized buildApiUrl and credentials include", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ok: true,
        payload: {
          authenticated: true,
          cookie_auth: true,
          csrf_token: "csrf-probe-token",
          session_id: "s-probe",
        },
      }),
    });
    global.fetch = fetchMock;

    const res = await probeCookieSession();
    expect(res).not.toBeNull();
    expect(res?.authenticated).toBe(true);
    expect(res?.csrf_token).toBe("csrf-probe-token");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(buildApiUrl("/auth/session"));
    expect(url).toMatch(/\/api\/v1\/auth\/session$/);
    expect(url).not.toContain("/api/v1/api/v1");
    expect(init.credentials).toBe("include");
  });

  it("enterpriseAuthApi endpoints use normalized buildApiUrl", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () =>
        JSON.stringify({
          ok: true,
          providers: [],
        }),
    });
    global.fetch = fetchMock;

    await enterpriseAuthApi.providers();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe(buildApiUrl("/auth/enterprise/providers"));
    expect(url).toMatch(/\/api\/v1\/auth\/enterprise\/providers$/);
    expect(url).not.toContain("/api/v1/api/v1");
  });

  it("rbacAuthApi endpoints use normalized buildApiUrl", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () =>
        JSON.stringify({
          ok: true,
          data: {
            user_id: "u-rbac",
            username: "rbac_user",
            roles: ["analyst"],
            permissions: [],
          },
        }),
    });
    global.fetch = fetchMock;

    await rbacAuthApi.me("tok-2");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe(buildApiUrl("/auth/rbac/me"));
    expect(url).toMatch(/\/api\/v1\/auth\/rbac\/me$/);
    expect(url).not.toContain("/api/v1/api/v1");
  });

  it("adminApi uses normalized buildApiUrl and sends cookie credentials and CSRF header", async () => {
    persistCsrfToken("csrf-admin-token", false);

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      text: async () =>
        JSON.stringify({
          ok: true,
          result: [],
        }),
    });
    global.fetch = fetchMock;

    await adminApi.listUsers({ token: "__cookie__" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(buildApiUrl("/admin/users"));
    expect(url).toMatch(/\/api\/v1\/admin\/users$/);
    expect(url).not.toContain("/api/v1/api/v1");
    expect(init.credentials).toBe("include");
    const headers = init.headers as Headers;
    expect(headers.get("X-CSRF-Token")).toBe("csrf-admin-token");
    expect(headers.get("Authorization")).toBeNull();
  });

  it("betaApi uses normalized buildApiUrl and sends cookie credentials and CSRF header", async () => {
    persistCsrfToken("csrf-beta-token", false);

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ok: true,
        result: {
          metrics: { active_users: 10 },
          pipeline_status: {},
          issue_counts_by_status: {},
          system_health_summary: {},
          programme: {},
          success_criteria: {},
        },
      }),
    });
    global.fetch = fetchMock;

    await betaApi.status("user-1");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(buildApiUrl("/beta/status?identity=user-1"));
    expect(url).toMatch(/\/api\/v1\/beta\/status\?identity=user-1$/);
    expect(url).not.toContain("/api/v1/api/v1");
    expect(init.credentials).toBe("include");
    const headers = init.headers as Headers;
    expect(headers.get("X-CSRF-Token")).toBe("csrf-beta-token");
    expect(headers.get("Authorization")).toBeNull();
  });
});
