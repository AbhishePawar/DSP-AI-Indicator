/**
 * Educational Business & Buffett Analysis — presentation tests.
 */

import { describe, expect, it } from "vitest";

import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import { buildDemoAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import { mapResearchView } from "@/lib/research/mapResearchView";
import {
  conclusionHasProhibitedVerdict,
  detectBusinessType,
  mapBusinessEducation,
  preferredMetrics,
} from "@/lib/business-education";

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
        warnings: ["Client concentration elevated"],
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
        score: 68,
        label: "Moderate",
        decision: null,
        confidence: 0.65,
        error: null,
        warnings: [],
      },
      {
        stage: "business_quality",
        status: "succeeded",
        has_result: true,
        score: 76,
        label: "Good",
        decision: null,
        confidence: 0.7,
        error: null,
        warnings: [],
      },
    ],
    recommendation_summary: {
      action: "hold",
      confidence: 0.6,
      margin_of_safety: 0.15,
    },
  },
};

describe("business education mapper", () => {
  it("generates all 12 educational sections", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple Inc",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    const report = view.businessEducation;
    expect(report.sections).toHaveLength(12);
    expect(report.title).toBe("Business & Buffett Analysis");
    expect(report.writesValuation).toBe(false);
    expect(report.writesBuffettScore).toBe(false);
    expect(report.readOnly).toBe(true);
  });

  it("handles missing stage data with Data unavailable", () => {
    const empty: AnalyseResponse = {
      ok: true,
      capability: "analyse",
      payload: {
        ok: true,
        metadata: {},
        stage_summaries: [],
      },
    };
    const request = buildDemoAnalyseRequest("XYZ", {
      company: "Unknown Co",
      exchange: "NSE",
    });
    const view = mapResearchView(empty, request, null);
    const report = mapBusinessEducation(view);
    const strengths = report.sections.find((s) => s.id === "the_real_strengths");
    expect(strengths?.claims.some((c) => c.text.includes("Data unavailable"))).toBe(
      true,
    );
  });

  it("selects bank metrics for banking business type", () => {
    expect(detectBusinessType("HDFC Bank Limited banking")).toBe("bank");
    expect(preferredMetrics("bank")).toContain("nim");
    expect(preferredMetrics("bank")).toContain("gnpa");
  });

  it("selects it_saas metrics for software companies", () => {
    expect(detectBusinessType("Infosys IT services software")).toBe("it_saas");
    expect(preferredMetrics("it_saas")).toContain("arr");
  });

  it("does not invent valuation outputs on the educational report", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple Inc",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    const json = JSON.stringify(view.businessEducation);
    expect(json).not.toMatch(/"intrinsicValue"\s*:/);
    expect(json).not.toMatch(/"buffettScore"\s*:/);
    expect(json).not.toMatch(/"marketPrice"\s*:/);
    expect(view.businessEducation.writesValuation).toBe(false);
    // Quantitative view fields remain authoritative and separate
    expect(view.valuation.intrinsicValue).toBeTruthy();
    expect(view.buffett.overallRating).toBeTruthy();
  });

  it("educational conclusion strips prohibited recommendation language", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple Inc",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    const conclusion = view.businessEducation.sections.find(
      (s) => s.id === "educational_conclusion",
    );
    expect(conclusion).toBeTruthy();
    expect(conclusionHasProhibitedVerdict(conclusion!.summary)).toBe(false);
  });

  it("includes Buffett checklist without computing a score", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple Inc",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    const checklist = view.businessEducation.sections.find(
      (s) => s.id === "the_buffett_checklist",
    );
    expect(checklist?.checklist).toHaveLength(9);
    expect(JSON.stringify(checklist)).toContain("not a Buffett score");
  });

  it("surfaces three key risks", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple Inc",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    const risks = view.businessEducation.sections.find(
      (s) => s.id === "key_risks_to_understand",
    );
    expect(risks?.risks).toHaveLength(3);
  });
});
