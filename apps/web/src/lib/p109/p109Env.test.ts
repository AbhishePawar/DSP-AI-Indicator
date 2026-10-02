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
  it("A: prefers the canonical seed credential", () => {
    withEnv(
      {
        DSP_SEED_ADMIN_PASSWORD: "canonical-test-value",
        DSP_P109_PASSWORD: "legacy-test-value",
      },
      () => expect(resolveP109AdminPassword()).toBe("canonical-test-value"),
    );
  });

  it("B: accepts the legacy credential only as a fallback", () => {
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: undefined, DSP_P109_PASSWORD: "legacy-test-value" },
      () => expect(resolveP109AdminPassword()).toBe("legacy-test-value"),
    );
  });

  it("C: treats empty credential variables as missing", () => {
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: "", DSP_P109_PASSWORD: "" },
      () => {
        expect(resolveP109AdminPassword()).toBeUndefined();
        expect(() => resolveP109Config()).toThrowError(P109ConfigError);
      },
    );
  });

  it("D: explicitly loads .env.local without overriding shell values", () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "p109-env-"));
    const envFile = path.join(dir, ".env.local");
    fs.writeFileSync(
      envFile,
      [
        "DSP_SEED_ADMIN_PASSWORD=file-value",
        "DSP_P109_LOGIN=file-admin",
        "# comment",
        "export DSP_P109_TICKER=file-ticker",
      ].join("\n"),
      "utf8",
    );

    withEnv(
      {
        DSP_SEED_ADMIN_PASSWORD: "shell-value",
        DSP_P109_LOGIN: undefined,
        DSP_P109_TICKER: undefined,
      },
      () => {
        expect(loadP109LocalEnv(envFile)).toBe(true);
        expect(process.env.DSP_SEED_ADMIN_PASSWORD).toBe("shell-value");
        expect(process.env.DSP_P109_LOGIN).toBe("file-admin");
        expect(process.env.DSP_P109_TICKER).toBe("file-ticker");
      },
    );

    fs.rmSync(dir, { recursive: true, force: true });
  });

  it("E: reports a missing env file cleanly", () => {
    const missing = path.join(os.tmpdir(), `p109-missing-${Date.now()}.env`);
    expect(loadP109LocalEnv(missing)).toBe(false);
  });

  it("F: resolves documented non-secret fixture defaults", () => {
    withEnv(
      {
        DSP_SEED_ADMIN_PASSWORD: "test-only-value",
        DSP_P109_LOGIN: undefined,
        DSP_P109_TICKER: undefined,
        PLAYWRIGHT_API_BASE_URL: undefined,
        PLAYWRIGHT_BASE_URL: undefined,
      },
      () => {
        expect(resolveP109Config()).toMatchObject({
          adminLogin: "admin",
          ticker: "DSPFIX",
          apiBaseUrl: "http://127.0.0.1:8000/api/v1",
          baseUrl: "http://127.0.0.1:3000",
        });
      },
    );
  });

  it("G: preserves explicit fixture settings", () => {
    withEnv(
      {
        DSP_SEED_ADMIN_PASSWORD: "test-only-value",
        DSP_P109_LOGIN: "fixture-admin",
        DSP_P109_TICKER: "FIXTURE1",
        PLAYWRIGHT_API_BASE_URL: "http://127.0.0.1:8100/api/v1",
        PLAYWRIGHT_BASE_URL: "http://127.0.0.1:3100",
      },
      () => {
        expect(resolveP109Config()).toMatchObject({
          adminLogin: "fixture-admin",
          ticker: "FIXTURE1",
          apiBaseUrl: "http://127.0.0.1:8100/api/v1",
          baseUrl: "http://127.0.0.1:3100",
        });
      },
    );
  });

  it("H: missing credentials fail before browser use and never echo a secret", () => {
    withEnv(
      { DSP_SEED_ADMIN_PASSWORD: undefined, DSP_P109_PASSWORD: undefined },
      () => {
        try {
          resolveP109Config();
          throw new Error("expected P109ConfigError");
        } catch (error) {
          expect(error).toBeInstanceOf(P109ConfigError);
          expect((error as P109ConfigError).code).toBe("MISSING_PASSWORD");
          expect((error as Error).message).not.toMatch(/password\s*[:=]\s*\S+/i);
        }
      },
    );
  });
});
