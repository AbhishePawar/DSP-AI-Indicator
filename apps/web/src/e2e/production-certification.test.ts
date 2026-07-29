/**
 * Living version alignment smoke (tracks current foundation).
 */
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import {
  API_CONTRACT_TARGET,
  BACKEND_PLATFORM_TARGET,
  FRONTEND_FOUNDATION_EPIC,
  FRONTEND_FOUNDATION_STATUS,
  FRONTEND_FOUNDATION_VERSION,
} from "@/foundation/version";
import { env } from "@/lib/env";
import manifest from "../../VERSION_MANIFEST.json";

const repoRoot = join(__dirname, "..", "..", "..", "..");

describe("Living production/version certification", () => {
  it("aligns frontend 2.0.0-rc with backend target 1.6.0", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0-rc");
    expect(FRONTEND_FOUNDATION_EPIC).toBe("P6.1");
    expect(FRONTEND_FOUNDATION_STATUS).toBe("release_candidate");
    expect(BACKEND_PLATFORM_TARGET).toBe("dsp_platform@1.6.0");
    expect(API_CONTRACT_TARGET).toBe("v1.0.0-rc1");
    expect(env.frontendVersion).toBe("2.0.0-rc");
    expect(manifest.appVersion).toBe("2.0.0-rc");
    expect(manifest.backend).toBe("dsp_platform@1.6.0");
  });

  it("keeps P1.1 / P5.1 / P5.2 / P6.1 certification docs", () => {
    for (const rel of [
      ["docs", "P1_1_PRODUCTION_DEPLOYMENT_CERTIFICATION.md"],
      ["docs", "P5_1_CLOSED_BETA_LAUNCH.md"],
      ["docs", "P5_2_BETA_STABILISATION.md"],
      ["docs", "P6_1_COMMERCIAL_READINESS.md"],
      ["docs", "ops", "BACKUP_AND_RECOVERY.md"],
      ["docs", "ops", "runbooks", "INCIDENT_RESPONSE.md"],
    ]) {
      const path = join(repoRoot, ...rel);
      expect(readFileSync(path, "utf8").length).toBeGreaterThan(100);
    }
  });
});
