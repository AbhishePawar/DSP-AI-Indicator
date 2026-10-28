import { describe, expect, it } from "vitest";

import {
  LOCAL_API_BASE_URL,
  resolveApiBaseUrl,
  SAME_ORIGIN_API_BASE_URL,
  buildApiUrl,
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

  it("normalizes base URL configured without /api/v1 by appending exactly one /api/v1", () => {
    expect(resolveApiBaseUrl("https://dspaiindicator.com", true)).toBe(
      "https://dspaiindicator.com/api/v1",
    );
    expect(resolveApiBaseUrl("https://dspaiindicator.com/", false)).toBe(
      "https://dspaiindicator.com/api/v1",
    );
  });

  it("prevents duplicated /api/v1 when base URL already includes it", () => {
    expect(resolveApiBaseUrl("https://dspaiindicator.com/api/v1", true)).toBe(
      "https://dspaiindicator.com/api/v1",
    );
    expect(resolveApiBaseUrl("https://dspaiindicator.com/api/v1/", false)).toBe(
      "https://dspaiindicator.com/api/v1",
    );
  });

  it("falls back to the same-origin path in a deployed browser when unset", () => {
    expect(resolveApiBaseUrl(undefined, true)).toBe(SAME_ORIGIN_API_BASE_URL);
    expect(resolveApiBaseUrl("", true)).toBe(SAME_ORIGIN_API_BASE_URL);
    expect(resolveApiBaseUrl("   ", true)).toBe(SAME_ORIGIN_API_BASE_URL);
  });

  it("falls back to the local dev server off the browser when unset", () => {
    expect(resolveApiBaseUrl(undefined, false)).toBe(LOCAL_API_BASE_URL);
    expect(resolveApiBaseUrl("", false)).toBe(LOCAL_API_BASE_URL);
  });
});

describe("buildApiUrl", () => {
  it("constructs URL with exactly one /api/v1 prefix regardless of path leading slash", () => {
    const url1 = buildApiUrl("/market/quote", "https://dspaiindicator.com");
    expect(url1).toBe("https://dspaiindicator.com/api/v1/market/quote");

    const url2 = buildApiUrl("market/quote", "https://dspaiindicator.com");
    expect(url2).toBe("https://dspaiindicator.com/api/v1/market/quote");
  });

  it("prevents duplicated /api/v1 when path itself already starts with /api/v1", () => {
    const url = buildApiUrl(
      "/api/v1/market/quote",
      "https://dspaiindicator.com/api/v1",
    );
    expect(url).toBe("https://dspaiindicator.com/api/v1/market/quote");

    const url2 = buildApiUrl("api/v1/market/quote", "https://dspaiindicator.com");
    expect(url2).toBe("https://dspaiindicator.com/api/v1/market/quote");
  });

  it("normalizes relative same-origin paths correctly", () => {
    const url = buildApiUrl("/auth/enterprise/login", "/api/v1");
    expect(url).toBe("/api/v1/auth/enterprise/login");
  });
});
