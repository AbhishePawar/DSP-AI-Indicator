/**
 * @vitest-environment jsdom
 */
/**
 * P2.3 — Institutional Valuation Transparency tests (presentation only).
 */

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  VALUATION_TRANSPARENCY_VERSION,
  mapValuationTransparency,
} from "@/lib/valuation-transparency";
import { mapResearchView } from "@/lib/research/mapResearchView";
import { buildDemoAnalyseRequest } from "@/lib/research/buildAnalyseRequest";
import {
  researchViewToCsv,
  researchViewToHtml,
  researchViewToJson,
} from "@/lib/company-analysis";
import { ValuationTransparencySection } from "@/components/company-analysis/ValuationTransparencySection";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";

const sampleResponse: AnalyseResponse = {
  ok: true,
  capability: "analyse",
  payload: {
    ok: true,
    metadata: {
      pipeline_version: "1.0.0-test",
      platform_version: "1.0.0",
      package_versions: { investment_recommendation: "0.1.0" },
    },
    stage_summaries: [
      {
        stage: "financial",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Ok",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "valuation",
        status: "succeeded",
        has_result: true,
        score: 68,
        label: "DCF",
        decision: "fair",
        confidence: 0.65,
        error: null,
        warnings: ["Growth rate sensitivity"],
      },
      {
        stage: "economic_moat",
        status: "succeeded",
        has_result: true,
        score: 75,
        label: "Narrow",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "management_quality",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Ok",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "financial_strength",
        status: "succeeded",
        has_result: true,
        score: 72,
        label: "Ok",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "earnings_quality",
        status: "succeeded",
        has_result: true,
        score: 71,
        label: "Ok",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "growth_quality",
        status: "succeeded",
        has_result: true,
        score: 68,
        label: "Ok",
        confidence: 0.6,
        error: null,
        warnings: [],
      },
      {
        stage: "business_quality_aggregator",
        status: "succeeded",
        has_result: true,
        score: 73,
        label: "Good",
        confidence: 0.7,
        error: null,
        warnings: [],
      },
      {
        stage: "investment_recommendation",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Hold",
        decision: "hold",
        confidence: 0.66,
        error: null,
        warnings: [],
      },
      {
        stage: "investment_committee",
        status: "succeeded",
        has_result: true,
        score: 70,
        label: "Hold",
        decision: "hold",
        confidence: 0.6,
        error: null,
        warnings: [],
      },
    ],
    recommendation_summary: {
      decision: "hold",
      confidence: 0.66,
      margin_of_safety: 0.12,
    },
    committee_summary: { decision: "hold", confidence: 0.6 },
  },
  limitations: [],
  errors: [],
  api_version: "v1",
  platform_version: "1.0.0",
  pipeline_version: "1.0.0-test",
  correlation_id: "corr-p23",
};

describe("P2.3 valuation transparency", () => {
  it("maps transparency without inventing method weights or categories", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    expect(view.valuationTransparency.kind).toBe("valuation_transparency");
    expect(view.valuationTransparency.version).toBe(
      VALUATION_TRANSPARENCY_VERSION,
    );
    expect(view.valuationTransparency.methods).toHaveLength(8);
    const dcf = view.valuationTransparency.methods.find(
      (m) => m.methodName === "DCF",
    );
    expect(dcf?.status).toBe("Available");
    expect(dcf?.weight).toBe("Unavailable");
    expect(dcf?.contributionToConsensus).toBe("Unavailable");
    const reverse = view.valuationTransparency.methods.find(
      (m) => m.methodName === "Reverse DCF",
    );
    expect(reverse?.status).toBe("Unavailable");
    expect(reverse?.intrinsicValue).toBe("Unavailable");
    expect(view.valuationTransparency.consensus.highestValuation).toBe(
      "Unavailable",
    );
    expect(view.valuationTransparency.consensus.numberOfMethodsUsed).toBe(
      "Unavailable",
    );
    expect(view.valuationTransparency.marginOfSafety.valuationCategory).toBe(
      "Unavailable",
    );
  });

  it("never derives consensus statistics from a single intrinsic value", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    request.valuation_signals = {
      intrinsic_value_per_share: 200,
      current_market_price: 180,
      margin_of_safety: null,
      premium_discount: null,
      confidence: 0.7,
    };
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    const vt = mapValuationTransparency(view);
    expect(vt.consensus.dispersionIndicator).toBe("Unavailable");
    expect(vt.consensus.lowestValuation).toBe("Unavailable");
    expect(vt.marginOfSafety.valuationCategory).toBe("Unavailable");
  });

  it("renders executive card and method cards", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    render(
      <ValuationTransparencySection
        transparency={view.valuationTransparency}
      />,
    );
    expect(screen.getByText("Executive Valuation Card")).toBeTruthy();
    expect(screen.getByText("Valuation Method Cards")).toBeTruthy();
    expect(screen.getByText("Consensus Panel")).toBeTruthy();
    expect(screen.getByText("Margin of Safety Panel")).toBeTruthy();
    expect(screen.getByText("Method Confidence")).toBeTruthy();
    expect(screen.getByLabelText("DCF valuation method")).toBeTruthy();
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
  });

  it("includes valuation transparency in JSON/HTML and CSV summary", () => {
    const request = buildDemoAnalyseRequest("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    const json = researchViewToJson(view);
    const html = researchViewToHtml(view);
    const csv = researchViewToCsv(view);
    expect(json).toContain("valuationTransparency");
    expect(json).toContain("valuation_transparency");
    expect(html).toContain("Valuation Transparency");
    expect(html).toContain("DCF");
    expect(csv).toContain("valuationTransparencyVersion");
    expect(csv).toContain("valuationTransparencyMethods");
    expect(csv).not.toContain("Contribution to Consensus");
  });
});
