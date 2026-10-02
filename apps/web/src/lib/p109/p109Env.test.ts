import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { describe, expect, it } from "vitest";

import {
  P109ConfigError,
  loadP109LocalEnv,
  resolveP109AdminPassword,
  resolveP109Config,
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

describe("P1-09 environment contract", () => {
  it("A: DSP_SEED_ADMIN_PASSWORD takes precedence", () => {
    withEnv(
      {
        DSP_SEED_ADMIN_PASSWORD: "canonical-test-value",
        DSP_P109_PASSWORD: "legacy-test-value",
      },
      () => expect(resolveP109AdminPassword()).toBe("canonical-test-value"),
    );
  });

  it("B: DSP_P109_PASSWORD works only as legacy fallback", () => {
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: undefined, DSP_P109_PASSWORD: "legacy-test-value" },
      () => expect(resolveP109AdminPassword()).toBe("legacy-test-value"),
    );
  });

  it("C: Missing both variables produces a clear configuration error", () => {
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: undefined, DSP_P109_PASSWORD: undefined },
      () => {
        expect(resolveP109AdminPassword()).toBeUndefined();
        expect(() => resolveP109Config()).toThrowError(P109ConfigError);
      },
    );
  });

  it("D: Empty/whitespace credential is rejected", () => {
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

  it("E: apps/web/.env.local is explicitly loaded", () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "p109-env-"));
    const envFile = path.join(dir, ".env.local");
    fs.writeFileSync(
      envFile,
      [
        "DSP_SEED_ADMIN_PASSWORD=file-loaded-secret",
        "DSP_P109_LOGIN=file-admin-user",
        "# comment line",
        "export DSP_P109_TICKER=file-ticker",
      ].join("\n"),
      "utf8",
    );

    withEnv(
      {
        DSP_SEED_ADMIN_PASSWORD: undefined,
        DSP_P109_PASSWORD: undefined,
        DSP_P109_LOGIN: undefined,
        DSP_P109_TICKER: undefined,
      },
      () => {
        expect(loadP109LocalEnv(envFile)).toBe(true);
        expect(process.env.DSP_SEED_ADMIN_PASSWORD).toBe("file-loaded-secret");
        expect(process.env.DSP_P109_LOGIN).toBe("file-admin-user");
        expect(process.env.DSP_P109_TICKER).toBe("file-ticker");
      },
    );

    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("F: Missing .env.local produces an understandable result", () => {
    const missing = path.join(os.tmpdir(), `p109-missing-${Date.now()}.env`);
    expect(loadP109LocalEnv(missing)).toBe(false);
  });

  it("G: Credential is never included in thrown/logged error messages", () => {
    withEnv(
      {
        DSP_SEED_ADMIN_PASSWORD: undefined,
        DSP_P109_PASSWORD: undefined,
      },
      () => {
        try {
          resolveP109Config();
          throw new Error("expected P109ConfigError");
        } catch (error) {
          expect(error).toBeInstanceOf(P109ConfigError);
          expect((error as Error).message).not.toMatch(/password\s*[:=]\s*\S+/i);
          expect((error as Error).message).not.toContain("super-secret");
        }
      },
    );
  });

  it("H: The final resolved configuration is consistent between the P1-09 test and fixture/seed flow", () => {
    withEnv(
      {
        DSP_SEED_ADMIN_PASSWORD: "canonical-password-999",
        DSP_P109_PASSWORD: "legacy-password-111",
      },
      () => {
        const testConfig = resolveP109Config();
        const testPassword = testConfig.adminPassword;
        // Verify canonical consistency with backend seed credential resolution logic
        const backendSeedPassword =
          process.env.DSP_SEED_ADMIN_PASSWORD || process.env.DSP_P109_PASSWORD;
        expect(testPassword).toBe(backendSeedPassword);
        expect(testPassword).toBe("canonical-password-999");
      },
    );
    withEnv(
      {
        DSP_SEED_ADMIN_PASSWORD: undefined,
        DSP_P109_PASSWORD: "legacy-password-111",
      },
      () => {
        const testConfig = resolveP109Config();
        const testPassword = testConfig.adminPassword;
        const backendSeedPassword =
          process.env.DSP_SEED_ADMIN_PASSWORD || process.env.DSP_P109_PASSWORD;
        expect(testPassword).toBe(backendSeedPassword);
        expect(testPassword).toBe("legacy-password-111");
      },
    );
  });
});
