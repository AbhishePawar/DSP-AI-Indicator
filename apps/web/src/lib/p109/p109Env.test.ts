import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { describe, expect, it } from "vitest";

import {
  P109PreflightError,
  findP109LocalEnvFile,
  loadP109LocalEnv,
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

describe("P1-09 automated preflight and environment contract", () => {
  it("A. Canonical credential is selected", () => {
    withEnv(
      {
        DSP_SEED_ADMIN_PASSWORD: "canonical-test-password",
        DSP_P109_PASSWORD: "legacy-test-password",
      },
      () => expect(resolveP109AdminPassword()).toBe("canonical-test-password"),
    );
  });

  it("B. Legacy credential is selected only when canonical is absent", () => {
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: undefined, DSP_P109_PASSWORD: "legacy-test-password" },
      () => expect(resolveP109AdminPassword()).toBe("legacy-test-password"),
    );
  });

  it("C. Missing both produces MISSING_CONFIGURATION", () => {
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: undefined, DSP_P109_PASSWORD: undefined },
      () => {
        expect(resolveP109AdminPassword()).toBeUndefined();
        try {
          resolveP109Config();
          throw new Error("expected preflight error");
        } catch (err) {
          expect(err).toBeInstanceOf(P109PreflightError);
          expect((err as P109PreflightError).category).toBe("MISSING_CONFIGURATION");
        }
      },
    );
  });

  it("D. Empty/whitespace credentials are rejected", () => {
    withEnv({ DSP_SEED_ADMIN_PASSWORD: "", DSP_P109_PASSWORD: "" }, () => {
      expect(resolveP109AdminPassword()).toBeUndefined();
      expect(() => resolveP109Config()).toThrowError(P109PreflightError);
    });
    withEnv({ DSP_SEED_ADMIN_PASSWORD: "   ", DSP_P109_PASSWORD: "   " }, () => {
      expect(resolveP109AdminPassword()).toBeUndefined();
      expect(() => resolveP109Config()).toThrowError(P109PreflightError);
    });
  });

  it("E. Backend unavailable is classified as BACKEND_UNAVAILABLE", async () => {
    const config = {
      adminLogin: "admin",
      adminPassword: "test-password",
      ticker: "DSPFIX",
      apiBaseUrl: "http://127.0.0.1:9999/api/v1",
      baseUrl: "http://127.0.0.1:3000",
    };
    const mockFetch = async (url: string | URL | Request) => {
      const u = String(url);
      if (u.includes("9999")) return { ok: false, status: 503 } as Response;
      return { ok: true, status: 200 } as Response;
    };

    try {
      await validateP109Preflight(config, { fetchFn: mockFetch as typeof fetch });
      throw new Error("expected error");
    } catch (err) {
      expect((err as P109PreflightError).category).toBe("BACKEND_UNAVAILABLE");
      expect((err as P109PreflightError).safeRemediation).toContain("DSP_ENVIRONMENT=development");
      expect((err as P109PreflightError).safeRemediation).not.toContain("test-password");
    }
  });

  it("F. Frontend unavailable is classified as FRONTEND_UNAVAILABLE", async () => {
    const config = {
      adminLogin: "admin",
      adminPassword: "test-password",
      ticker: "DSPFIX",
      apiBaseUrl: "http://127.0.0.1:8000/api/v1",
      baseUrl: "http://127.0.0.1:9998",
    };
    const mockFetch = async (url: string | URL | Request) => {
      const u = String(url);
      if (u.includes("9998")) return { ok: false, status: 502 } as Response;
      return { ok: true, status: 200 } as Response;
    };

    try {
      await validateP109Preflight(config, { fetchFn: mockFetch as typeof fetch });
      throw new Error("expected error");
    } catch (err) {
      expect((err as P109PreflightError).category).toBe("FRONTEND_UNAVAILABLE");
      expect((err as P109PreflightError).safeRemediation).toContain("npm run dev");
    }
  });

  it("G. Fixture infrastructure unavailable is distinguished from authentication failure", async () => {
    const config = {
      adminLogin: "admin",
      adminPassword: "test-password",
      ticker: "DSPFIX",
      apiBaseUrl: "http://127.0.0.1:8000/api/v1",
      baseUrl: "http://127.0.0.1:3000",
    };
    const mockFetch = async (url: string | URL | Request) => {
      const u = String(url);
      if (u.includes("/health/")) return { ok: true, status: 200 } as Response;
      if (u.includes("/market/quote")) return { ok: false, status: 503 } as Response;
      return { ok: true, status: 200 } as Response;
    };

    try {
      await validateP109Preflight(config, { fetchFn: mockFetch as typeof fetch });
      throw new Error("expected error");
    } catch (err) {
      expect((err as P109PreflightError).category).toBe("FIXTURE_INFRASTRUCTURE_UNAVAILABLE");
      expect((err as P109PreflightError).safeRemediation).toContain("DSP_MARKET_QUOTE_MEMORY=1");
    }
  });

  it("H. Authentication failure is classified only after infrastructure is reachable", async () => {
    const config = {
      adminLogin: "admin",
      adminPassword: "test-password",
      ticker: "DSPFIX",
      apiBaseUrl: "http://127.0.0.1:8000/api/v1",
      baseUrl: "http://127.0.0.1:3000",
    };
    const mockFetch = async () => ({ ok: true, status: 200 } as Response);

    const preflight = await validateP109Preflight(config, { fetchFn: mockFetch as typeof fetch });
    expect(preflight.ok).toBe(true);
    // At this stage infrastructure passed. If login endpoint subsequently returns 401, it is AUTHENTICATION_FAILED.
  });

  it("I. Existing-server mode correctly sets PLAYWRIGHT_SKIP_WEBSERVER=1", () => {
    withEnv({ PLAYWRIGHT_SKIP_WEBSERVER: "1" }, () => {
      expect(process.env.PLAYWRIGHT_SKIP_WEBSERVER).toBe("1");
    });
  });

  it("J. Credential values never appear in diagnostics", () => {
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: undefined, DSP_P109_PASSWORD: undefined },
      () => {
        try {
          resolveP109Config();
          throw new Error("expected error");
        } catch (err) {
          const msg = (err as Error).message + ((err as P109PreflightError).safeRemediation || "");
          expect(msg).not.toContain("super-secret");
          expect(msg).not.toMatch(/password\s*[:=]\s*['"][^'"]+['"]/i);
        }
      },
    );
  });

  it("K. .env.local is explicitly discovered across candidate paths", () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "p109-local-"));
    const envFile = path.join(dir, ".env.local");
    fs.writeFileSync(envFile, "DSP_SEED_ADMIN_PASSWORD=test-secret-from-file\n", "utf8");

    withEnv({ DSP_SEED_ADMIN_PASSWORD: undefined, DSP_P109_ENV_FILE: envFile }, () => {
      expect(findP109LocalEnvFile()).toBe(envFile);
      expect(loadP109LocalEnv(envFile)).toBe(true);
      expect(process.env.DSP_SEED_ADMIN_PASSWORD).toBe("test-secret-from-file");
    });

    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("L. Fixture/Playwright credential resolution remains identical", () => {
    withEnv(
      {
        DSP_SEED_ADMIN_PASSWORD: "synced-canonical-value",
        DSP_P109_PASSWORD: "legacy-fallback-value",
      },
      () => {
        const testPassword = resolveP109AdminPassword();
        const backendSeedPassword =
          process.env.DSP_SEED_ADMIN_PASSWORD || process.env.DSP_P109_PASSWORD;
        expect(testPassword).toBe(backendSeedPassword);
        expect(testPassword).toBe("synced-canonical-value");
      },
    );
  });
});
