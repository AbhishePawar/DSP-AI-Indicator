import { describe, expect, it } from "vitest";

import {
  APPLICATION_VERSION,
  getBuildInfo,
  getEnabledModules,
  getFeatureFlagPlaceholders,
} from "./buildInfo";

describe("buildInfo", () => {
  it("exposes version and environment", () => {
    const info = getBuildInfo();
    expect(info.applicationVersion).toBe(APPLICATION_VERSION);
    expect(info.frontendVersion).toBeTruthy();
    expect(info.environment).toBeTruthy();
    expect(info.buildTimestamp).toBeTruthy();
  });

  it("lists enabled modules from navigation", () => {
    const modules = getEnabledModules();
    expect(modules.some((m) => m.route === "/dashboard")).toBe(true);
    expect(modules.some((m) => m.route === "/copilot")).toBe(true);
    modules.forEach((mod) => expect(mod.status).toBe("enabled"));
  });

  it("returns placeholder feature flags", () => {
    const flags = getFeatureFlagPlaceholders();
    expect(flags.some((f) => f.id === "copilot_llm" && !f.enabled)).toBe(true);
    expect(flags.some((f) => f.id === "research_mode" && f.enabled)).toBe(true);
  });
});
