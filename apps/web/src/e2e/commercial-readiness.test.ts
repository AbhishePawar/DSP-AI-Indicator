/**
 * P6.1 — Commercial readiness client smoke (packaging, docs, support, versions).
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
import { TUTORIAL_STEPS } from "@/lib/beta/onboardingSteps";
import {
  PRODUCT_EDITIONS,
  SAMPLE_ANALYSIS_SYMBOL,
  SUPPORT_CONTACT,
} from "@/lib/commercial";
import { env } from "@/lib/env";
import manifest from "../../VERSION_MANIFEST.json";

const repoRoot = join(__dirname, "..", "..", "..", "..");

describe("P6.1 commercial readiness", () => {
  it("aligns versions and epic", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
    expect(FRONTEND_FOUNDATION_EPIC).toBe("P8.0");
    expect(FRONTEND_FOUNDATION_STATUS).toBe("production");
    expect(BACKEND_PLATFORM_TARGET).toBe("dsp_platform@2.0.0");
    expect(API_CONTRACT_TARGET).toBe("v1.0.0");
    expect(env.frontendVersion).toBe("2.0.0");
    expect(manifest.appVersion).toBe("2.0.0");
    expect(manifest.foundationEpic).toBe("P8.0");
    expect(manifest.channel).toBe("ga-candidate");
  });

  it("exposes product editions and support contacts", () => {
    expect(PRODUCT_EDITIONS.map((e) => e.id)).toEqual([
      "research",
      "professional",
      "enterprise",
    ]);
    expect(SUPPORT_CONTACT.email).toMatch(/support@/);
    expect(SUPPORT_CONTACT.salesEmail).toMatch(/sales@/);
    expect(SAMPLE_ANALYSIS_SYMBOL).toBe("AAPL");
  });

  it("keeps commercial onboarding tutorial steps", () => {
    expect(TUTORIAL_STEPS.length).toBeGreaterThanOrEqual(5);
    expect(TUTORIAL_STEPS[0]?.id).toBe("welcome");
    expect(TUTORIAL_STEPS.some((s) => s.id === "support")).toBe(true);
    expect(TUTORIAL_STEPS[0]?.body).toMatch(/Research Mode/i);
  });

  it("documents commercial readiness programme", () => {
    const path = join(repoRoot, "docs", "P6_1_COMMERCIAL_READINESS.md");
    const body = readFileSync(path, "utf8");
    expect(body).toMatch(/READY WITH MINOR CONDITIONS/);
    expect(body).toMatch(/Product packaging/i);
    expect(body).toMatch(/Operational runbooks/i);
    expect(body).toMatch(/\*\*PASS\*\*/);
  });

  it("keeps commercial documentation artifacts", () => {
    for (const rel of [
      ["docs", "commercial", "PRODUCT_PACKAGING.md"],
      ["docs", "commercial", "PRICING_STRATEGY.md"],
      ["docs", "commercial", "CUSTOMER_SUPPORT.md"],
      ["docs", "ops", "runbooks", "INCIDENT_RESPONSE.md"],
      ["docs", "ops", "runbooks", "DEPLOYMENT.md"],
      ["docs", "RELEASE_NOTES_v2.0.0.md"],
      ["docs", "media-kit", "README.md"],
    ]) {
      const path = join(repoRoot, ...rel);
      expect(readFileSync(path, "utf8").length).toBeGreaterThan(100);
    }
  });
});
