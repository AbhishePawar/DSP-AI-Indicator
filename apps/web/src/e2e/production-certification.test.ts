/**
 * Living version alignment smoke (P8.0 release engineering channel).
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
  it("aligns frontend 2.0.0 with backend target 2.0.0", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
    expect(FRONTEND_FOUNDATION_EPIC).toBe("P8.0");
    expect(FRONTEND_FOUNDATION_STATUS).toBe("production");
    expect(BACKEND_PLATFORM_TARGET).toBe("dsp_platform@2.0.0");
    expect(API_CONTRACT_TARGET).toBe("v1.0.0");
    expect(env.frontendVersion).toBe("2.0.0");
    expect(manifest.appVersion).toBe("2.0.0");
    expect(manifest.backend).toBe("dsp_platform@2.0.0");
  });

  it("keeps P7 certification and release-engineering docs", () => {
    for (const rel of [
      ["docs", "P7_PRODUCTION_DEPLOYMENT.md"],
      ["docs", "P7_PRODUCTION_CERTIFICATION.md"],
      ["docs", "ENGINEERING_STATUS.md"],
      ["docs", "REPOSITORY_AUDIT.md"],
      ["docs", "VERSION_GOVERNANCE_REPORT.md"],
      ["scripts", "release", "validate_release.py"],
      ["scripts", "ops", "certify_p7_2.py"],
    ]) {
      const path = join(repoRoot, ...rel);
      expect(readFileSync(path, "utf8").length).toBeGreaterThan(100);
    }
  });
});
