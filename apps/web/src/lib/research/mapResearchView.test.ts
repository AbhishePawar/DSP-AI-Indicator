import { describe, expect, it } from "vitest";

import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";
import { buildDemoAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import {
  mapDomainScores,
  mapMarginOfSafety,
  mapResearchView,
  mapStrengthsWeaknesses,
  money,
} from "@/lib/research/mapResearchView";
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

describe("buildDemoAnalyseRequest", () => {
  it("explicit demo fixture may reuse sample statements (tests only)", () => {
    const req = buildDemoAnalyseRequest("msft");
    expect(req.ticker).toBe("MSFT");
    expect(req.financial_statements.period.period_type).toBe(
      SAMPLE_ANALYSE_REQUEST.financial_statements.period.period_type,
    );
    expect(req.company).toContain("demo fixture");
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

describe("mapDomainScores (Figma weighted domain scorecard)", () => {
  it("maps existing stage scores and aggregator engine_weights without inventing values", () => {
    const rows = mapDomainScores(
      [
        { stage: "economic_moat", status: "succeeded", has_result: true, score: 88 },
        { stage: "management_quality", status: "degraded", has_result: true, score: 84 },
        { stage: "financial_strength", status: "failed", has_result: false, score: null },
        // growth_quality intentionally absent; earnings_quality has no score.
        { stage: "earnings_quality", status: "succeeded", has_result: true, score: null },
      ],
      { economic_moat: 0.25, management_quality: 0.2, financial_strength: 0.2, earnings_quality: 0.2 },
    );
    expect(rows.map((r) => r.id)).toEqual([
      "economic_moat",
      "management_quality",
      "financial_strength",
      "earnings_quality",
      "growth_quality",
    ]);
    expect(rows[0]).toMatchObject({ scoreValue: 88, weight: "25%", weightValue: 25, status: "succeeded" });
    expect(rows[1]).toMatchObject({ scoreValue: 84, weight: "20%", status: "degraded" });
    // Failed stage: score unavailable, weight still reported from the aggregator.
    expect(rows[2]).toMatchObject({ scoreValue: null, weight: "20%", status: "unavailable" });
    expect(rows[2].score).not.toMatch(/\d/);
    // Succeeded but no score → unavailable, never fabricated.
    expect(rows[3]).toMatchObject({ scoreValue: null, status: "unavailable" });
    // Missing stage and missing weight → both Unavailable.
    expect(rows[4]).toMatchObject({ scoreValue: null, weightValue: null, weight: "Unavailable" });
  });

  it("treats malformed engine_weights as unavailable", () => {
    const rows = mapDomainScores([], "not-an-object");
    expect(rows.every((r) => r.weightValue === null && r.scoreValue === null)).toBe(true);
  });
});

describe("mapMarginOfSafety (Figma S10, RS-005 — presentation only)", () => {
  it("prefers the engine assessment and never recomputes MoS in the browser", () => {
    const view = mapMarginOfSafety(
      {
        decision: "BUY",
        margin_of_safety: 0.3,
        margin_of_safety_assessment: {
          intrinsic_value_per_share: 1000,
          current_market_price: 700,
          margin_of_safety: 0.3,
          premium_discount: -0.3,
          valuation_confidence: 0.6,
          classification: "POSITIVE",
          reasoning: "Price is 30% below intrinsic value.",
        },
      },
      // Conflicting server_valuation values must NOT override the engine.
      { intrinsic_value_per_share: 999, current_market_price: 1 },
      "INR",
    );
    expect(view.value).toBe(0.3);
    expect(view.status).toBe("discount");
    expect(view.classification).toBe("POSITIVE");
    expect(view.reasoning).toBe("Price is 30% below intrinsic value.");
    expect(view.intrinsicValue).toBe(money(1000, "INR"));
    expect(view.currentPrice).toBe(money(700, "INR"));
    expect(view.valuationConfidence).toBe("60.0%");
  });

  it("falls back to server_valuation for IV/price and marks premiums", () => {
    const view = mapMarginOfSafety(
      { decision: "HOLD", margin_of_safety: -0.12 },
      { intrinsic_value_per_share: 100, current_market_price: 112 },
      null,
    );
    expect(view.status).toBe("premium");
    expect(view.classification).toBe("Unavailable");
    expect(view.reasoning).toBeNull();
    // No currency known → bare number, never an invented symbol.
    expect(view.intrinsicValue).toBe((100).toLocaleString());
    expect(view.premiumDiscount).toBe("Unavailable");
  });

  it("is honest when nothing was calculated", () => {
    const view = mapMarginOfSafety(null, null, "USD");
    expect(view).toMatchObject({
      value: null,
      display: "Unavailable",
      status: "unavailable",
      intrinsicValue: "Unavailable",
      currentPrice: "Unavailable",
    });
  });
});

describe("mapStrengthsWeaknesses (Figma S12 — engine-published factors only)", () => {
  it("merges recommendation factors with aggregator strengths and records sources", () => {
    const view = mapStrengthsWeaknesses(
      {
        decision: "BUY",
        positive_factors: ["Strong FCF", "Wide moat"],
        negative_factors: ["Valuation stretched"],
      },
      {
        authority: "server",
        strengths: ["Wide moat", "Low leverage"],
        weaknesses: [],
      },
    );
    expect(view.strengths).toEqual(["Strong FCF", "Wide moat", "Low leverage"]);
    expect(view.weaknesses).toEqual(["Valuation stretched"]);
    expect(view.sources).toEqual([
      "investment_recommendation",
      "business_quality_aggregator",
    ]);
  });

  it("returns empty lists (not generic text) when the backend publishes nothing", () => {
    const view = mapStrengthsWeaknesses(null, null);
    expect(view).toEqual({ strengths: [], weaknesses: [], sources: [] });
  });
});

describe("mapResearchView Figma deep-dive fields", () => {
  it("surfaces MoS, strengths/weaknesses, investment context and currency from the payload", () => {
    const response = sampleResponse();
    response.payload = {
      ...response.payload!,
      recommendation_summary: {
        decision: "BUY",
        confidence: 0.8,
        margin_of_safety: 0.3,
        margin_of_safety_assessment: {
          intrinsic_value_per_share: 1000,
          current_market_price: 700,
          margin_of_safety: 0.3,
          classification: "POSITIVE",
          reasoning: "Discount.",
        },
        positive_factors: ["Strong FCF"],
        negative_factors: ["Cyclical demand"],
        key_drivers: ["Margins"],
        decision_summary: "BUY at a discount.",
      },
      business_quality: {
        authority: "server",
        score: 82,
        rating: "High",
        engine_weights: null,
        strengths: ["Wide moat"],
        weaknesses: [],
      },
      source_evidence: { reporting_currency: "inr" },
    } as typeof response.payload;
    const view = mapResearchView(response, SAMPLE_ANALYSE_REQUEST, "2024-01-01T00:00:00Z");
    expect(view.currency).toBe("INR");
    expect(view.marginOfSafetyView.status).toBe("discount");
    expect(view.marginOfSafetyView.classification).toBe("POSITIVE");
    expect(view.strengthsWeaknesses.strengths).toEqual(["Strong FCF", "Wide moat"]);
    expect(view.strengthsWeaknesses.weaknesses).toEqual(["Cyclical demand"]);
    expect(view.investmentContext.valuation).toBe("POSITIVE");
    expect(view.investmentContext.marginOfSafety).toBe("30.0%");
    expect(view.investmentContext.decisionSummary).toBe("BUY at a discount.");
    expect(view.investmentContext.keyDrivers).toEqual(["Margins"]);
    expect(view.investmentContext.confidence).toBe("80.0%");
  });

  it("keeps every deep-dive field unavailable when the payload omits them", () => {
    const view = mapResearchView(
      sampleResponse(),
      SAMPLE_ANALYSE_REQUEST,
      "2024-01-01T00:00:00Z",
    );
    expect(view.currency).toBeNull();
    // margin_of_safety is a flat ratio in the fixture → presentation only.
    expect(view.marginOfSafetyView.value).toBe(0.3);
    expect(view.marginOfSafetyView.classification).toBe("Unavailable");
    expect(view.strengthsWeaknesses).toEqual({ strengths: [], weaknesses: [], sources: [] });
    expect(view.investmentContext.valuation).toBe("Unavailable");
    expect(view.investmentContext.decisionSummary).toBeNull();
    expect(view.investmentContext.keyDrivers).toEqual([]);
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
      "Research Hub",
      "ACM",
    ]);
  });
});
