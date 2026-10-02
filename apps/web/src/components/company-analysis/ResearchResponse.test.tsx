/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { ResearchResponse } from "./ResearchResponse";
import { SAMPLE_ANALYSE_REQUEST } from "@/lib/intelligence/sampleRequest";
import { mapResearchView } from "@/lib/research/mapResearchView";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";

function mockResponse(): AnalyseResponse {
  return {
    ok: true,
    capability: "compose_intelligence",
    api_version: "0.2.0",
    platform_version: "1.0.0",
    pipeline_version: "1.0.0",
    correlation_id: "corr-response-test",
    limitations: ["No external AI citation stream"],
    errors: [],
    payload: {
      ok: true,
      has_valuation: true,
      has_business_quality: true,
      has_investment_recommendation: true,
      recommendation_summary: {
        decision: "HOLD",
        confidence: 0.7,
        margin_of_safety: 0.15,
      },
      stage_summaries: [
        {
          stage: "financial",
          status: "succeeded",
          has_result: true,
          score: 0.65,
          label: "Adequate",
        },
        {
          stage: "valuation",
          status: "succeeded",
          has_result: true,
          label: "Discounted Cash Flow",
          confidence: 0.7,
        },
      ],
      metadata: {
        total_elapsed_ms: 85,
        execution_order: ["financial", "valuation"],
        evidence_counts: { statements: 2 },
        confidence_summary: { overall: 0.7 },
      },
    },
  };
}

describe("ResearchResponse Component", () => {
  it("renders executive summary, deep research boundary note, and evidence counts", () => {
    const view = mapResearchView(
      mockResponse(),
      SAMPLE_ANALYSE_REQUEST,
      "2026-10-02T12:00:00.000Z",
    );

    render(<ResearchResponse view={view} />);

    expect(screen.getByText("Executive Summary")).toBeTruthy();
    expect(screen.getByText("Deep Research & AI Boundary")).toBeTruthy();
    expect(screen.getByText(/Provider Unavailable \(Deterministic Research Only\)/i)).toBeTruthy();
    expect(screen.getByText("Valuation")).toBeTruthy();
    expect(screen.getByText("Evidence & Sources")).toBeTruthy();
    expect(screen.getByText("statements")).toBeTruthy();
  });
});
