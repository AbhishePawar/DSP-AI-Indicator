/**
 * Closed beta programme smoke (flags/criteria) — versions track living P6.1 channel.
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
import { BETA_SUCCESS_CRITERIA, ISSUE_STATUSES } from "@/lib/beta/betaModel";
import { featureFlags } from "@/lib/featureFlags";
import { env } from "@/lib/env";
import manifest from "../../VERSION_MANIFEST.json";

const repoRoot = join(__dirname, "..", "..", "..", "..");

describe("Closed beta programme (living channel)", () => {
  it("aligns versions and epic", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
    expect(FRONTEND_FOUNDATION_EPIC).toBe("P8.0");
    expect(FRONTEND_FOUNDATION_STATUS).toBe("production");
    expect(BACKEND_PLATFORM_TARGET).toBe("dsp_platform@2.0.0");
    expect(API_CONTRACT_TARGET).toBe("v1.0.0");
    expect(env.frontendVersion).toBe("2.0.0");
    expect(manifest.foundationEpic).toBe("P8.0");
    expect(manifest.channel).toBe("ga-candidate");
  });

  it("exposes closed beta feature flags and issue workflow", () => {
    expect("closedBeta" in featureFlags).toBe(true);
    expect(ISSUE_STATUSES).toEqual([
      "new",
      "triaged",
      "in_progress",
      "resolved",
      "closed",
    ]);
    expect(BETA_SUCCESS_CRITERIA.criticalBugsMax).toBe(0);
    expect(BETA_SUCCESS_CRITERIA.averageFeedbackMin).toBe(4.0);
  });

  it("documents P5.2 stabilisation programme", () => {
    const path = join(repoRoot, "docs", "P5_2_BETA_STABILISATION.md");
    const body = readFileSync(path, "utf8");
    expect(body).toMatch(/READY WITH MINOR CONDITIONS/);
    expect(body).toMatch(/Issue resolution/);
    expect(body).toMatch(/Release Candidate/);
  });
});
