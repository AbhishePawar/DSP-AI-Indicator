/**
 * P6.1 / frontend v2.0.0-rc release smoke.
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

describe("P6.1 / frontend v2.0.0-rc release smoke", () => {
  it("aligns package channel to frontend v2.0.0-rc", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0-rc");
    expect(FRONTEND_FOUNDATION_EPIC).toBe("P6.1");
    expect(FRONTEND_FOUNDATION_STATUS).toBe("release_candidate");
    expect(env.frontendVersion).toBe("2.0.0-rc");
    expect(env.foundationVersion).toBe("2.0.0-rc");
    expect(manifest.appVersion).toBe("2.0.0-rc");
    expect(manifest.foundationVersion).toBe("2.0.0-rc");
    expect(manifest.foundationEpic).toBe("P6.1");
  });

  it("targets backend 1.6.0 and frozen API contract", () => {
    expect(BACKEND_PLATFORM_TARGET).toBe("dsp_platform@1.6.0");
    expect(API_CONTRACT_TARGET).toBe("v1.0.0-rc1");
    expect(manifest.backend).toBe("dsp_platform@1.6.0");
  });
});
