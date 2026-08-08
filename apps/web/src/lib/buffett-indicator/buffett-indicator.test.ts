/**
 * ARCH-001 — Buffett Indicator report mapper tests.
 * Presentation synthesis only — no scoring engines.
 */

import { describe, expect, it } from "vitest";

import {
  buffettActionFromExistingDecision,
  letterGradeFromExistingScore,
  mapBuffettReport,
} from "@/lib/buffett-indicator";
import { mapResearchView } from "@/lib/research/mapResearchView";
import { buildDemoAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";

const sampleResponse: AnalyseResponse = {
  ok: true,
  capability: "analyse",
  payload: {
    ok: true,
    metadata: {
      pipeline_version: "1.0.0-test",
      platform_version: "1.0.0",
    },
    stage_summaries: [
      {
        stage: "financial",
        status: "succeeded",
        has_result: true,
        score: 72,
        label: "Solid",
        decision: null,
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
        warnings: [],
      },
      {
        stage: "management_quality",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Capable",
        decision: null,
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
        decision: null,
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
        decision: null,
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
        decision: null,
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
        decision: null,
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
        decision: "buy",
        confidence: 0.65,
        error: null,
        warnings: [],
      },
      {
        stage: "investment_committee",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Hold for research",
        decision: "hold",
        confidence: 0.6,
        error: null,
        warnings: [],
      },
    ],
    recommendation_summary: {
      decision: "buy",
      confidence: 0.65,
      margin_of_safety: 0.22,
      label: "Buy",
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
  correlation_id: "corr-buffett-1",
};

describe("ARCH-001 Buffett Indicator report", () => {
  it("maps letter grades from existing scores without inventing numbers", () => {
    expect(letterGradeFromExistingScore("85")).toBe("A");
    expect(letterGradeFromExistingScore("Unavailable")).toBe("Unavailable");
  });

  it("maps Buffett Action from existing decisions only", () => {
    expect(buffettActionFromExistingDecision("buy")).toBe("BUY");
    expect(buffettActionFromExistingDecision("hold")).toBe("HOLD");
    expect(buffettActionFromExistingDecision("strong_sell")).toBe("AVOID");
    expect(buffettActionFromExistingDecision("Unavailable")).toBe("Unavailable");
  });

  it("synthesizes report from ResearchView with evidence references", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(sampleResponse, request, "2026-07-28T12:00:00.000Z");
    const report = view.buffett;
    expect(report.kind).toBe("buffett_indicator_report");
    expect(report.economicMoat.evidenceSources).toContain("economic_moat");
    expect(report.decisionMatrix).toHaveLength(10);
    expect(report.scorecard.some((r) => r.dimension === "Overall Buffett Rating")).toBe(
      true,
    );
    expect(report.verdict).toContain("Apple");
    expect(report.disclaimer.toLowerCase()).toContain("server-authoritative");
    // High ROE must stay honest when not exposed
    const roe = report.decisionMatrix.find((m) => m.criterion === "High ROE");
    expect(roe?.state).toBe("unavailable");
  });

  it("P1-05: overall rating remaps server business_quality score only", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(sampleResponse, request);
    // Sample BQ score=76 → letter band B+ (not an average of other grades).
    expect(view.buffett.overallRating).toBe("B+");
    expect(letterGradeFromExistingScore(view.businessQuality.score)).toBe(
      view.buffett.overallRating,
    );
    const overallRow = view.buffett.scorecard.find(
      (r) => r.dimension === "Overall Buffett Rating",
    );
    expect(overallRow?.evidence.toLowerCase()).toContain("business_quality_aggregator");
    expect(overallRow?.evidence.toLowerCase()).not.toContain("average");
  });

  it("P1-05: unavailable business_quality yields unavailable overall rating", () => {
    const unavailable: AnalyseResponse = {
      ...sampleResponse,
      payload: {
        ...sampleResponse.payload,
        stage_summaries: (
          sampleResponse.payload.stage_summaries as Array<Record<string, unknown>>
        ).map((s) =>
          s.stage === "business_quality_aggregator"
            ? {
                ...s,
                status: "failed",
                has_result: false,
                score: null,
                label: null,
              }
            : s,
        ),
      },
    };
    const request = buildDemoAnalyseRequest("AAPL", { company: "Apple" });
    const report = mapResearchView(unavailable, request).buffett;
    expect(report.overallRating).toBe("Unavailable");
  });

  it("is deterministic for the same inputs", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const a = mapResearchView(sampleResponse, request).buffett;
    const b = mapResearchView(sampleResponse, request).buffett;
    expect(a).toEqual(b);
    const { buffett: _omit, ...rest } = mapResearchView(sampleResponse, request);
    expect(mapBuffettReport(rest)).toEqual(a);
  });
});
