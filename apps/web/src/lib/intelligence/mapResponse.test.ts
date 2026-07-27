import { describe, expect, it } from "vitest";

import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import {
  emptyIntelligenceView,
  formatPct,
  mapAnalyseResponse,
} from "@/lib/intelligence/mapResponse";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";
import { breadcrumbsFor, getPrimaryNav } from "@/lib/navigation";

describe("mapAnalyseResponse", () => {
  it("maps API payload fields without inventing scores", () => {
    const response: AnalyseResponse = {
      ok: true,
      capability: "compose_intelligence",
      payload: {
        ok: true,
        metadata: {
          pipeline_version: "1.0.0-epic-001",
          total_elapsed_ms: 12.5,
          evidence_counts: { economic_moat: 3 },
          confidence_summary: { economic_moat: 0.8 },
          warnings: ["note"],
          package_versions: { financial: "0.7.0" },
          execution_order: ["financial", "valuation"],
          failed_stage: null,
        },
        stage_summaries: [
          {
            stage: "business_quality_aggregator",
            status: "succeeded",
            has_result: true,
            score: 0.72,
            label: "Strong",
            confidence: 0.7,
          },
          {
            stage: "investment_recommendation",
            status: "succeeded",
            has_result: true,
            decision: "Buy",
          },
        ],
        recommendation_summary: {
          decision: "Buy",
          confidence: 0.66,
          margin_of_safety: 0.3,
        },
        committee_summary: {
          decision: "Approve",
          confidence: 0.7,
          consensus: "majority",
          rationale: "Risk officer dissent noted",
        },
        errors: [],
        limitations: ["API DTO boundary"],
      },
      limitations: [],
      errors: [],
      api_version: "v1",
      platform_version: "0.7.1",
      pipeline_version: "1.0.0-epic-001",
      correlation_id: "abc-123",
    };

    const view = mapAnalyseResponse(response);
    expect(view.ok).toBe(true);
    expect(view.recommendation).toBe("Buy");
    expect(view.marginOfSafety).toBe(0.3);
    expect(view.businessQualityLabel).toBe("Strong");
    expect(view.businessQualityScore).toBe(0.72);
    expect(view.committeeDecision).toBe("Approve");
    expect(view.minorityNotes.join(" ")).toContain("Risk officer");
    expect(view.correlationId).toBe("abc-123");
    expect(view.evidenceCounts.economic_moat).toBe(3);
  });

  it("returns empty placeholders when no result", () => {
    const empty = emptyIntelligenceView();
    expect(empty.recommendation).toBe("—");
    expect(empty.stages).toEqual([]);
  });

  it("formats percentages from API values only", () => {
    expect(formatPct(0.3)).toBe("30.0%");
    expect(formatPct(null)).toBe("Unavailable");
  });
});

describe("sample request", () => {
  it("includes ticker and valuation signals for /analyse", () => {
    expect(SAMPLE_ANALYSE_REQUEST.ticker).toBe("ACM");
    expect(
      SAMPLE_ANALYSE_REQUEST.valuation_signals?.intrinsic_value_per_share,
    ).toBe(100);
  });
});

describe("navigation routing", () => {
  it("includes Intelligence in primary nav", () => {
    const nav = getPrimaryNav();
    expect(nav.some((n) => n.href === "/intelligence")).toBe(true);
  });

  it("builds breadcrumbs for /intelligence", () => {
    const crumbs = breadcrumbsFor("/intelligence");
    expect(crumbs.at(-1)?.label).toBe("Intelligence");
  });

  it("includes terminal nav items", () => {
    const nav = getPrimaryNav();
    expect(nav.some((n) => n.href === "/companies")).toBe(true);
    expect(nav.some((n) => n.href === "/screening")).toBe(true);
    expect(nav.some((n) => n.href === "/research")).toBe(true);
    expect(nav.some((n) => n.href === "/documentation")).toBe(true);
  });

  it("builds breadcrumbs for /diagnostics", () => {
    const crumbs = breadcrumbsFor("/diagnostics");
    expect(crumbs.at(-1)?.label).toBe("Diagnostics");
  });
});
