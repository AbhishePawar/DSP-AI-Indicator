/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { enterpriseRequest } from "./enterpriseClient";
import { persistCsrfToken, clearCsrfToken } from "@/lib/auth/cookieSession";
import { clearStoredSession } from "@/lib/auth/sessionStore";

describe("enterpriseRequest", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    clearStoredSession();
    clearCsrfToken();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("normalizes path with buildApiUrl and includes credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ ok: true, data: "test" }),
    });
    global.fetch = fetchMock;

    await enterpriseRequest("/audit/events", { method: "GET" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/audit/events");
    expect(url).not.toContain("/api/v1/api/v1");
    expect(init.credentials).toBe("include");
  });

  it("attaches X-CSRF-Token on mutating requests (POST) in cookie mode", async () => {
    persistCsrfToken("csrf-test-secret-123", false);

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ ok: true }),
    });
    global.fetch = fetchMock;

    await enterpriseRequest("/users/create", {
      method: "POST",
      body: JSON.stringify({ name: "Alice" }),
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0];
    const headers = init.headers as Headers;
    expect(headers.get("X-CSRF-Token")).toBe("csrf-test-secret-123");
  });

  it("does not attach CSRF token on GET requests", async () => {
    persistCsrfToken("csrf-test-secret-123", false);

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ ok: true }),
    });
    global.fetch = fetchMock;

    await enterpriseRequest("/users", { method: "GET" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0];
    const headers = init.headers as Headers;
    expect(headers.get("X-CSRF-Token")).toBeNull();
  });
});
