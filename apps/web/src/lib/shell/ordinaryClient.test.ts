import { describe, expect, it } from "vitest";

import { featureFlags } from "@/lib/featureFlags";
import { getPrimaryNav, PRIMARY_NAV } from "@/lib/navigation";
import {
  AUX_ROUTES,
  SHELL_NAV,
  filterShellNav,
  searchableRoutes,
} from "@/lib/shell/navigationRegistry";
import {
  ORDINARY_ANALYSIS_SECTION_IDS,
  ORDINARY_SHELL_ITEM_IDS,
  isPaletteHiddenPath,
  isOperatorUser,
  ordinaryClientShellEnabled,
  showOperationalChrome,
} from "@/lib/shell/ordinaryClient";
import { RESEARCH_QUICK_ACTIONS } from "@/lib/research-canvas/quickActions";
import { visibleAnalysisSections } from "@/lib/company-analysis/sections";

describe("SIMPLE-2 ordinary client profile", () => {
  it("enables the ordinary-client shell by default", () => {
    expect(featureFlags.ordinaryClientShell).toBe(true);
    expect(ordinaryClientShellEnabled()).toBe(true);
    expect(showOperationalChrome()).toBe(false);
  });

  it("keeps full SHELL_NAV recoverable while ordinary filter is minimal", () => {
    expect(SHELL_NAV.map((n) => n.id)).toEqual(
      expect.arrayContaining([
        "dashboard",
        "analysis",
        "research",
        "portfolio",
        "admin",
        "ops",
        "settings",
      ]),
    );
    const analyst = filterShellNav(["read_research"], ["research_analyst"]);
    expect(analyst.map((i) => i.id).sort()).toEqual(
      ["analysis", "dashboard", "settings"].sort(),
    );
    expect(analyst.every((i) => ORDINARY_SHELL_ITEM_IDS.has(i.id))).toBe(true);
  });

  it("still shows Administration for operators, not Ops or Diagnostics", () => {
    expect(isOperatorUser(["manage_users"], ["administrator"])).toBe(true);
    const admin = filterShellNav(
      ["manage_users", "read_research"],
      ["administrator"],
    );
    expect(admin.some((i) => i.id === "admin")).toBe(true);
    expect(admin.some((i) => i.id === "ops")).toBe(false);
    expect(admin.some((i) => i.id === "portfolio")).toBe(false);
  });

  it("hides secondary products from the command palette", () => {
    const hidden = [
      "/intelligence",
      "/companies",
      "/screening",
      "/copilot",
      "/ops",
      "/diagnostics",
      "/advisor",
      "/platform",
      "/launch",
      "/beta",
      "/health",
      "/research",
      "/portfolio",
      "/documentation",
      "/docs",
    ];
    for (const path of hidden) {
      expect(isPaletteHiddenPath(path), path).toBe(true);
    }
    const paths = searchableRoutes(["read_research"], ["research_analyst"]).map(
      (r) => r.path,
    );
    for (const path of hidden) {
      expect(paths).not.toContain(path);
    }
    expect(AUX_ROUTES.some((r) => r.path === "/intelligence")).toBe(true);
    expect(RESEARCH_QUICK_ACTIONS.some((a) => a.id === "qa-canvas")).toBe(true);
  });

  it("limits getPrimaryNav while PRIMARY_NAV remains the recoverability map", () => {
    expect(getPrimaryNav().map((n) => n.href)).toEqual([
      "/dashboard",
      "/analysis",
      "/settings",
    ]);
    expect(PRIMARY_NAV.some((n) => n.href === "/intelligence")).toBe(true);
    expect(PRIMARY_NAV.some((n) => n.href === "/copilot")).toBe(true);
  });

  it("orders ordinary analysis sections as the recommended report", () => {
    expect([...ORDINARY_ANALYSIS_SECTION_IDS]).toEqual([
      "summary",
      "quality",
      "financial",
      "management",
      "moat",
      "risk",
      "valuation",
      "buffett",
      "evidence",
      "explainability",
      "export",
    ]);
    expect(visibleAnalysisSections().map((s) => s.id)).toEqual([
      ...ORDINARY_ANALYSIS_SECTION_IDS,
    ]);
  });
});
