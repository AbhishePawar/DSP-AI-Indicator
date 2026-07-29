/**
 * P8.0 — GA certification / release-freeze smoke.
 */
import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import {
  API_CONTRACT_TARGET,
  BACKEND_PLATFORM_TARGET,
  FRONTEND_FOUNDATION_EPIC,
  FRONTEND_FOUNDATION_VERSION,
} from "@/foundation/version";
import manifest from "../../VERSION_MANIFEST.json";

const repoRoot = join(__dirname, "..", "..", "..", "..");

describe("P8.0 GA certification", () => {
  it("aligns foundation to GA candidate 2.0.0", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
    expect(FRONTEND_FOUNDATION_EPIC).toBe("P8.0");
    expect(BACKEND_PLATFORM_TARGET).toBe("dsp_platform@2.0.0");
    expect(API_CONTRACT_TARGET).toBe("v1.0.0");
    expect(manifest.appVersion).toBe("2.0.0");
    expect(manifest.channel).toBe("ga-candidate");
  });

  it("ships GA governance docs", () => {
    for (const name of [
      "GA_ARCHITECTURE_CERTIFICATION.md",
      "GA_TECHNICAL_DEBT.md",
      "RELEASE_FREEZE.md",
      "P8_GENERAL_AVAILABILITY.md",
    ]) {
      const body = readFileSync(join(repoRoot, "docs", name), "utf8");
      expect(body.length).toBeGreaterThan(200);
    }
  });

  it("ships certify_p8 and freeze markers", () => {
    expect(existsSync(join(repoRoot, "scripts", "ops", "certify_p8.py"))).toBe(true);
    const freeze = readFileSync(join(repoRoot, "docs", "RELEASE_FREEZE.md"), "utf8");
    expect(freeze).toContain("Frozen modules");
    expect(freeze).toContain("Emergency fix");
  });
});
