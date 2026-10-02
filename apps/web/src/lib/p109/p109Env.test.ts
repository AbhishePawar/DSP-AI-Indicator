import { describe, expect, it } from "vitest";

import {
  P109ConfigError,
  P109PreflightError,
  resolveP109AdminPassword,
  resolveP109Config,
  validateP109Preflight,
} from "../../../e2e/browser/p109/env";

function withEnv(overrides: Record<string, string | undefined>, fn: () => void) {
  const previous = new Map<string, string | undefined>();
  for (const [key, value] of Object.entries(overrides)) {
    previous.set(key, process.env[key]);
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  try {
    fn();
  } finally {
    for (const [key, value] of previous) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

describe("P1-09 environment and preflight contract", () => {
  it("1. Missing credential produces a clear configuration error", () => {
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: undefined, DSP_P109_PASSWORD: undefined },
      () => {
        expect(resolveP109AdminPassword()).toBeUndefined();
        expect(() => resolveP109Config()).toThrowError(P109ConfigError);
      },
    );
  });

  it("2. Canonical credential takes precedence", () => {
    withEnv(
      {
        DSP_SEED_ADMIN_PASSWORD: "canonical-test-value",
        DSP_P109_PASSWORD: "legacy-test-value",
      },
      () => expect(resolveP109AdminPassword()).toBe("canonical-test-value"),
    );
  });

  it("3. Legacy fallback is used when canonical is absent", () => {
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: undefined, DSP_P109_PASSWORD: "legacy-test-value" },
      () => expect(resolveP109AdminPassword()).toBe("legacy-test-value"),
    );
  });

  it("4. Empty/whitespace credential rejection", () => {
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: "", DSP_P109_PASSWORD: "" },
      () => {
        expect(resolveP109AdminPassword()).toBeUndefined();
        expect(() => resolveP109Config()).toThrowError(P109ConfigError);
      },
    );
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: "   ", DSP_P109_PASSWORD: "   " },
      () => {
        expect(resolveP109AdminPassword()).toBeUndefined();
        expect(() => resolveP109Config()).toThrowError(P109ConfigError);
      },
    );
  });

  it("5. Backend unavailable is detected during preflight", async () => {
    const config = {
      adminLogin: "admin",
      adminPassword: "test-password",
      ticker: "DSPFIX",
      apiBaseUrl: "http://127.0.0.1:9999/api/v1",
      baseUrl: "http://127.0.0.1:3000",
    };
    const mockFetch = async (url: string | URL | Request) => {
      const u = String(url);
      if (u.includes("9999")) {
        return { ok: false, status: 503 } as Response;
      }
      return { ok: true, status: 200 } as Response;
    };

    await expect(
      validateP109Preflight(config, { fetchFn: mockFetch as typeof fetch }),
    ).rejects.toThrowError(P109PreflightError);

    try {
      await validateP109Preflight(config, { fetchFn: mockFetch as typeof fetch });
    } catch (err) {
      expect((err as P109PreflightError).category).toBe("BACKEND_UNAVAILABLE");
    }
  });

  it("6. Frontend unavailable is detected during preflight", async () => {
    const config = {
      adminLogin: "admin",
      adminPassword: "test-password",
      ticker: "DSPFIX",
      apiBaseUrl: "http://127.0.0.1:8000/api/v1",
      baseUrl: "http://127.0.0.1:9998",
    };
    const mockFetch = async (url: string | URL | Request) => {
      const u = String(url);
      if (u.includes("9998")) {
        return { ok: false, status: 502 } as Response;
      }
      return { ok: true, status: 200 } as Response;
    };

    try {
      await validateP109Preflight(config, { fetchFn: mockFetch as typeof fetch });
      throw new Error("expected P109PreflightError");
    } catch (err) {
      expect(err).toBeInstanceOf(P109PreflightError);
      expect((err as P109PreflightError).category).toBe("FRONTEND_UNAVAILABLE");
    }
  });

  it("7. Valid backend and frontend configuration passes preflight", async () => {
    const config = {
      adminLogin: "admin",
      adminPassword: "test-password",
      ticker: "DSPFIX",
      apiBaseUrl: "http://127.0.0.1:8000/api/v1",
      baseUrl: "http://127.0.0.1:3000",
    };
    const mockFetch = async () => ({ ok: true, status: 200 } as Response);

    const result = await validateP109Preflight(config, {
      fetchFn: mockFetch as typeof fetch,
    });
    expect(result.ok).toBe(true);
    expect(result.backendReady).toBe(true);
    expect(result.frontendReady).toBe(true);
  });

  it("8. Credential never appears in errors", () => {
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: undefined, DSP_P109_PASSWORD: undefined },
      () => {
        try {
          resolveP109Config();
          throw new Error("expected P109ConfigError");
        } catch (error) {
          expect(error).toBeInstanceOf(P109ConfigError);
          expect((error as Error).message).not.toMatch(/password\s*[:=]\s*\S+/i);
        }
      },
    );
  });

  it("9. Existing-server Playwright mode (PLAYWRIGHT_SKIP_WEBSERVER=1) is supported", () => {
    withEnv({ PLAYWRIGHT_SKIP_WEBSERVER: "1" }, () => {
      expect(process.env.PLAYWRIGHT_SKIP_WEBSERVER).toBe("1");
    });
  });

  it("10. Normal Playwright webServer behavior remains available when unflagged", () => {
    withEnv({ PLAYWRIGHT_SKIP_WEBSERVER: undefined }, () => {
      expect(process.env.PLAYWRIGHT_SKIP_WEBSERVER).toBeUndefined();
    });
  });
});
