/**
 * P8.0 / frontend v2.0.0 release smoke.
 */
import { describe, expect, it } from "vitest";

import {
  API_CONTRACT_TARGET,
  BACKEND_PLATFORM_TARGET,
  FRONTEND_FOUNDATION_EPIC,
  FRONTEND_FOUNDATION_STATUS,
  FRONTEND_FOUNDATION_VERSION,
} from "@/foundation/version";
import { env } from "@/lib/env";
import manifest from "../../VERSION_MANIFEST.json";

describe("P8.0 / frontend v2.0.0 release smoke", () => {
  it("aligns package channel to frontend v2.0.0", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0");
    expect(FRONTEND_FOUNDATION_EPIC).toBe("P8.0");
    expect(FRONTEND_FOUNDATION_STATUS).toBe("production");
    expect(env.frontendVersion).toBe("2.0.0");
    expect(env.foundationVersion).toBe("2.0.0");
    expect(manifest.appVersion).toBe("2.0.0");
    expect(manifest.foundationVersion).toBe("2.0.0");
    expect(manifest.foundationEpic).toBe("P8.0");
    expect(manifest.channel).toBe("ga-candidate");
  });

  it("targets backend 2.0.0 and stable API contract v1.0.0", () => {
    expect(BACKEND_PLATFORM_TARGET).toBe("dsp_platform@2.0.0");
    expect(API_CONTRACT_TARGET).toBe("v1.0.0");
    expect(manifest.backend).toBe("dsp_platform@2.0.0");
    expect(manifest.apiContract).toBe("v1.0.0");
  });
});
