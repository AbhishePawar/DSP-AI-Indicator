import { describe, expect, it } from "vitest";

import {
  API_CONTRACT_TARGET,
  BACKEND_PLATFORM_TARGET,
  FROZEN_FEATURE_ROUTES,
  FRONTEND_FOUNDATION_STATUS,
  FRONTEND_FOUNDATION_VERSION,
  apiStrategy,
  colorTokens,
  componentHierarchy,
  resolveListState,
  technologyDecisions,
} from "@/foundation";

describe("EPIC-F000 foundation freeze", () => {
  it("exposes foundation version 2.0.0-rc", () => {
    expect(FRONTEND_FOUNDATION_VERSION).toBe("2.0.0-rc");
    expect(FRONTEND_FOUNDATION_STATUS).toBe("release_candidate");
    expect(BACKEND_PLATFORM_TARGET).toBe("dsp_platform@1.6.0");
    expect(API_CONTRACT_TARGET).toBe("v1.0.0-rc1");
  });

  it("freezes feature routes without implementing them", () => {
    const frozen = FROZEN_FEATURE_ROUTES.filter((r) => r.status === "frozen");
    expect(frozen.map((r) => r.path)).toEqual(
      expect.arrayContaining([
        "/dashboard",
        "/analysis",
        "/portfolio",
        "/research",
        "/admin",
        "/settings",
        "/profile",
      ]),
    );
  });

  it("keeps PR1.2 accent (no purple brand)", () => {
    expect(colorTokens.light.accent).toBe("#0f6e56");
    expect(technologyDecisions.ui.choice).toContain("shadcn");
  });

  it("resolves list UX states deterministically", () => {
    expect(resolveListState(true, false, 0)).toBe("loading");
    expect(resolveListState(false, true, 0)).toBe("error");
    expect(resolveListState(false, false, 0)).toBe("empty");
    expect(resolveListState(false, false, 2)).toBe("success");
  });

  it("locks thin-client API rules", () => {
    expect(apiStrategy.prefix).toBe("/api/v1");
    expect(apiStrategy.rules.join(" ")).toMatch(/never fabricate/i);
    expect(componentHierarchy.rules.join(" ")).toMatch(/no engine logic/i);
  });
});
