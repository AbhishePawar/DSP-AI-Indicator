/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "./client";
import { persistCsrfToken, clearCsrfToken } from "@/lib/auth/cookieSession";
import { clearStoredSession } from "@/lib/auth/sessionStore";
import { ApiClientError } from "@/lib/api/types";

function createSseStream(chunks: Array<Record<string, unknown>>) {
  const encoder = new TextEncoder();
  const sseText = chunks.map((c) => `data: ${JSON.stringify(c)}\n\n`).join("");
  return new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(sseText));
      controller.close();
    },
  });
}

describe("api.copilotStream", () => {
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

  it("sends credentials: include and X-CSRF-Token header in cookie mode", async () => {
    persistCsrfToken("csrf-stream-token", false);

    const streamResponse = {
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "text/event-stream" }),
      body: createSseStream([
        { delta: "Analysis ", done: false },
        { delta: "completed.", done: true },
      ]),
    };
    const fetchMock = vi.fn().mockResolvedValue(streamResponse);
    global.fetch = fetchMock;

    const chunks = await api.copilotStream(
      {
        question_id: "freeform",
        freeform: "Tell me about TCS",
        request: null,
        response: null,
      },
      { token: "__cookie__" },
    );

    expect(chunks).toHaveLength(2);
    expect(chunks[0].delta).toBe("Analysis ");
    expect(chunks[1].done).toBe(true);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/copilot/stream");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");

    const headers = init.headers as Headers;
    expect(headers.get("Accept")).toBe("text/event-stream");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-CSRF-Token")).toBe("csrf-stream-token");
    // Must never send raw Bearer __cookie__
    expect(headers.get("Authorization")).toBeNull();
  });

  it("sends Authorization Bearer when cookie auth is disabled and token provided", async () => {
    process.env.NEXT_PUBLIC_COOKIE_AUTH = "false";

    const streamResponse = {
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "text/event-stream" }),
      body: createSseStream([{ delta: "Bearer response", done: true }]),
    };
    const fetchMock = vi.fn().mockResolvedValue(streamResponse);
    global.fetch = fetchMock;

    const chunks = await api.copilotStream(
      { question_id: "freeform", freeform: "Summarize", request: null, response: null },
      { token: "bearer-token-123" },
    );

    expect(chunks).toHaveLength(1);
    expect(chunks[0].delta).toBe("Bearer response");

    const [, init] = fetchMock.mock.calls[0];
    const headers = init.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer bearer-token-123");
    expect(init.credentials).toBeUndefined();
  });

  it("throws ApiClientError when response is not ok", async () => {
    const errorResponse = {
      ok: false,
      status: 401,
      headers: new Headers({ "content-type": "application/json" }),
      body: null,
    };
    global.fetch = vi.fn().mockResolvedValue(errorResponse);

    await expect(
      api.copilotStream({
        question_id: "freeform",
        freeform: "Test fail",
        request: null,
        response: null,
      }),
    ).rejects.toThrow(ApiClientError);
  });
});
