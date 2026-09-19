import { describe, expect, it } from "vitest";

import {
  LOCAL_API_BASE_URL,
  resolveApiBaseUrl,
  SAME_ORIGIN_API_BASE_URL,
} from "./env";

describe("resolveApiBaseUrl", () => {
  it("honors a configured public API URL and strips a trailing slash", () => {
    expect(resolveApiBaseUrl("https://api.example.com/api/v1/", true)).toBe(
      "https://api.example.com/api/v1",
    );
    expect(resolveApiBaseUrl("https://api.example.com/api/v1", false)).toBe(
      "https://api.example.com/api/v1",
    );
  });

  it("falls back to the same-origin path in a deployed browser when unset", () => {
    // Regression: an empty NEXT_PUBLIC_API_BASE_URL must NOT become a localhost
    // URL in the browser, which surfaces as "Authentication service
    // temporarily unavailable" on /login.
    expect(resolveApiBaseUrl(undefined, true)).toBe(SAME_ORIGIN_API_BASE_URL);
    expect(resolveApiBaseUrl("", true)).toBe(SAME_ORIGIN_API_BASE_URL);
    expect(resolveApiBaseUrl("   ", true)).toBe(SAME_ORIGIN_API_BASE_URL);
  });

  it("falls back to the local dev server off the browser when unset", () => {
    expect(resolveApiBaseUrl(undefined, false)).toBe(LOCAL_API_BASE_URL);
    expect(resolveApiBaseUrl("", false)).toBe(LOCAL_API_BASE_URL);
  });
});
