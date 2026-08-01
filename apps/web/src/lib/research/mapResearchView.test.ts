import { describe, expect, it } from "vitest";

import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";
import { buildAnalyseRequestForTicker } from "@/lib/research/buildAnalyseRequest";
import { mapResearchView } from "@/lib/research/mapResearchView";
import { breadcrumbsFor, getPrimaryNav } from "@/lib/navigation";

function sampleResponse(): AnalyseResponse {
  return {
    ok: true,
    capability: "compose_intelligence",
    api_version: "0.2.0",
    platform_version: "0.7.1",
    pipeline_version: "1.0.0",
    correlation_id: "test-corr",
    limitations: [],
    errors: [],
    payload: {
      ok: true,
      has_valuation: true,
      has_business_quality: true,
      has_investment_recommendation: true,
      has_investment_committee: true,
      recommendation_summary: {
        decision: "BUY",
        confidence: 0.8,
        margin_of_safety: 0.3,
      },
      committee_summary: {
        decision: "APPROVE",
        confidence: 0.75,
        consensus: "majority",
        rationale: "Strong moat",
      },
      stage_summaries: [
        {
          stage: "financial",
          status: "succeeded",
          has_result: true,
          score: 0.7,
          label: "Solid",
        },
        {
          stage: "valuation",
          status: "succeeded",
          has_result: true,
          label: "DCF",
          confidence: 0.7,
        },
        {
          stage: "economic_moat",
          status: "succeeded",
          has_result: true,
          label: "Wide",
          decision: "Durable",
          score: 0.85,
        },
        {
          stage: "management_quality",
          status: "succeeded",
          has_result: true,
          label: "Strong capital allocation",
        },
        {
          stage: "financial_strength",
          status: "succeeded",
          has_result: true,
          label: "Conservative leverage",
          score: 0.8,
        },
        {
          stage: "earnings_quality",
          status: "succeeded",
          has_result: true,
          label: "High quality",
        },
        {
          stage: "growth_quality",
          status: "succeeded",
          has_result: true,
          label: "Sustainable",
        },
        {
          stage: "business_quality_aggregator",
          status: "succeeded",
          has_result: true,
          label: "High",
          score: 0.82,
          confidence: 0.77,
        },
        {
          stage: "investment_recommendation",
          status: "succeeded",
          has_result: true,
          decision: "BUY",
        },
        {
          stage: "investment_committee",
          status: "succeeded",
          has_result: true,
          decision: "APPROVE",
        },
      ],
      metadata: {
        total_elapsed_ms: 12.5,
        execution_order: ["financial", "valuation"],
        evidence_counts: { total: 3 },
        confidence_summary: { overall: 0.8 },
      },
    },
  };
}

describe("buildAnalyseRequestForTicker", () => {
  it("overrides ticker while keeping sample statements", () => {
    const req = buildAnalyseRequestForTicker("msft");
    expect(req.ticker).toBe("MSFT");
    expect(req.financial_statements.period.period_type).toBe(
      SAMPLE_ANALYSE_REQUEST.financial_statements.period.period_type,
    );
  });
});

describe("mapResearchView", () => {
  it("maps API payload into research sections without inventing scores", () => {
    const view = mapResearchView(
      sampleResponse(),
      SAMPLE_ANALYSE_REQUEST,
      "2026-07-27T00:00:00.000Z",
    );
    expect(view.ticker).toBe("ACM");
    expect(view.recommendation).toBe("BUY");
    expect(view.valuation.marginOfSafety).toContain("%");
    expect(view.businessQuality.metrics[0]?.label).toBe("Overall Score");
    expect(view.committee.finalRecommendation).toBe("BUY");
    expect(view.committee.supportingReasons.length).toBeGreaterThan(0);
    expect(view.stages).toHaveLength(10);
  });

  it("RC3-001 — does not alias Management/Moat into Business Quality metrics", () => {
    const view = mapResearchView(
      sampleResponse(),
      SAMPLE_ANALYSE_REQUEST,
      "2026-07-27T00:00:00.000Z",
    );
    const byLabel = Object.fromEntries(
      view.businessQuality.metrics.map((m) => [m.label, m.value]),
    );
    expect(byLabel["Capital Allocation Quality"]).toBe("Unavailable");
    expect(byLabel["Franchise Durability"]).toBe("Unavailable");
    expect(byLabel["Industry Structure"]).toBe("Unavailable");
    // Must not equal sibling stage labels/decisions
    expect(byLabel["Capital Allocation Quality"]).not.toBe(
      view.management.label,
    );
    expect(byLabel["Franchise Durability"]).not.toBe(view.moat.label);
    expect(byLabel["Industry Structure"]).not.toBe(view.moat.decision);
  });
});

describe("research routing breadcrumbs", () => {
  it("includes Research in primary nav", () => {
    expect(getPrimaryNav().some((n) => n.href === "/research")).toBe(true);
  });

  it("builds ticker crumbs for /research/[ticker]", () => {
    const crumbs = breadcrumbsFor("/research/acm");
    expect(crumbs.map((c) => c.label)).toEqual([
      "Home",
      "Research Workspace",
      "ACM",
    ]);
  });
});
