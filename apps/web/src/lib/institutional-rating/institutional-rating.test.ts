/**
 * ARCH-002 — Institutional rating framework tests (presentation only).
 */

import { describe, expect, it } from "vitest";

import {
  investmentActionFromExisting,
  letterGradeFromExistingScore,
  mapInstitutionalRatings,
  scoreOutOf10FromExisting,
} from "@/lib/institutional-rating";
import { mapResearchView } from "@/lib/research/mapResearchView";
import { buildDemoAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";

const sampleResponse: AnalyseResponse = {
  ok: true,
  capability: "analyse",
  payload: {
    ok: true,
    metadata: { pipeline_version: "1.0.0-test", platform_version: "1.0.0" },
    stage_summaries: [
      {
        stage: "financial",
        status: "succeeded",
        has_result: true,
        score: 72,
        label: "Solid",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "economic_moat",
        status: "succeeded",
        has_result: true,
        score: 80,
        label: "Wide",
        decision: "durable",
        confidence: 0.75,
        error: null,
        warnings: ["Competition intensity rising"],
      },
      {
        stage: "management_quality",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Capable",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "financial_strength",
        status: "succeeded",
        has_result: true,
        score: 78,
        label: "Strong",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "earnings_quality",
        status: "succeeded",
        has_result: true,
        score: 74,
        label: "Consistent",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "growth_quality",
        status: "succeeded",
        has_result: true,
        score: 65,
        label: "Steady",
        confidence: 0.6,
        error: null,
        warnings: [],
      },
      {
        stage: "business_quality_aggregator",
        status: "succeeded",
        has_result: true,
        score: 76,
        label: "Good",
        confidence: 0.72,
        error: null,
        warnings: [],
      },
      {
        stage: "investment_recommendation",
        status: "succeeded",
        has_result: true,
        score: 68,
        label: "Accumulate",
        decision: "accumulate",
        confidence: 0.65,
        error: null,
        warnings: [],
      },
      {
        stage: "investment_committee",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Approve",
        decision: "hold",
        confidence: 0.6,
        error: null,
        warnings: [],
      },
    ],
    recommendation_summary: {
      decision: "accumulate",
      confidence: 0.65,
      margin_of_safety: 0.22,
      label: "Accumulate",
    },
    committee_summary: {
      decision: "hold",
      confidence: 0.6,
      consensus: "majority_hold",
    },
  },
  limitations: [],
  errors: [],
  api_version: "v1",
  platform_version: "1.0.0",
  pipeline_version: "1.0.0-test",
  correlation_id: "corr-arch002",
};

describe("ARCH-002 institutional rating framework", () => {
  it("remaps existing scores to /10 and letter grades", () => {
    expect(scoreOutOf10FromExisting("80")).toBe("8.0/10");
    expect(letterGradeFromExistingScore("80")).toBe("A");
    expect(scoreOutOf10FromExisting("Unavailable")).toBe("Unavailable");
  });

  it("maps investment actions from existing decisions", () => {
    expect(investmentActionFromExisting("accumulate")).toBe("ACCUMULATE");
    expect(investmentActionFromExisting("reduce")).toBe("REDUCE");
    expect(investmentActionFromExisting("Unavailable")).toBe("Unavailable");
  });

  it("builds framework with all modules and honest Unavailable for missing risk score", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(sampleResponse, request);
    const ratings = view.ratings;
    expect(ratings.kind).toBe("institutional_rating_framework");
    expect(ratings.scorecard.length).toBeGreaterThanOrEqual(11);
    expect(ratings.modules.riskAssessment.scoreOutOf10).toBe("Unavailable");
    expect(ratings.modules.financialFortress.dimensions.some((d) => d.label === "ROE")).toBe(
      true,
    );
    expect(
      ratings.modules.financialFortress.dimensions.find((d) => d.label === "ROE")?.value,
    ).toBe("Unavailable");
    expect(ratings.overall.recommendation).toBeTruthy();
    expect(ratings.disclaimer.toLowerCase()).toContain("does not recalculate");
  });

  it("is deterministic", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const a = mapResearchView(sampleResponse, request);
    const b = mapResearchView(sampleResponse, request);
    expect(a.ratings).toEqual(b.ratings);
    const { ratings: _r, ...rest } = a;
    expect(mapInstitutionalRatings(rest)).toEqual(a.ratings);
  });
});
