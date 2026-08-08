import { describe, expect, it } from "vitest";

import {
  buildEvidenceCompleteness,
  dashboardSurfaceTrust,
  emptySurfaceTrust,
  portfolioSurfaceTrust,
} from "./surfaceTrust";

describe("surfaceTrust", () => {
  it("applies blocking missing-data penalty when empty", () => {
    const e = buildEvidenceCompleteness(0, 4);
    expect(e.missingDataPenalty).toBe("blocking");
    expect(e.label).toContain("Data unavailable.");
  });

  it("builds dashboard idle trust without inventing confidence", () => {
    const s = dashboardSurfaceTrust({ widgetCount: 3 });
    expect(s.confidenceDisplay).toBe("Data unavailable.");
    expect(s.layers).toHaveLength(4);
    expect(s.researchMode).toBe(true);
  });

  it("portfolio trust reflects holdings coverage honestly", () => {
    const s = portfolioSurfaceTrust({
      holdingsCount: 2,
      researchCovered: 1,
      researchTotal: 2,
      intelStatus: "API linked research 1 · schema 1",
    });
    expect(s.evidence.missingDataPenalty).not.toBe("blocking");
    expect(s.layers[0].presence).toBe("available");
  });

  it("empty surface keeps contradictory list empty", () => {
    const s = emptySurfaceTrust("research_workspace");
    expect(s.contradictoryEvidence).toEqual([]);
    expect(s.auditTrail.length).toBeGreaterThan(0);
  });
});
