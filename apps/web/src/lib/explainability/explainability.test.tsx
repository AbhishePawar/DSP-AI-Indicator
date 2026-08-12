/**
 * @vitest-environment jsdom
 */
/**
 * P2.2 — Institutional Explainability Framework tests (presentation only).
 */

import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import {
  EXPLAINABILITY_FRAMEWORK_VERSION,
  mapModuleExplainability,
  truncateWords,
} from "@/lib/explainability";
import { mapResearchView } from "@/lib/research/mapResearchView";
import { buildAnalyseRequestForTicker } from "@/lib/research/buildAnalyseRequest";
import {
  researchViewToCsv,
  researchViewToHtml,
  researchViewToJson,
} from "@/lib/company-analysis";
import { InstitutionalRatingsSection } from "@/components/company-analysis/InstitutionalRatingsSection";
import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import type { ModuleRating } from "@/lib/institutional-rating";

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
      margin_of_safety: 0.1,
    },
    committee_summary: { decision: "hold", confidence: 0.6 },
  },
  limitations: [],
  errors: [],
  api_version: "v1",
  platform_version: "1.0.0",
  pipeline_version: "1.0.0-test",
  correlation_id: "corr-p22",
};

function emptyModule(overrides: Partial<ModuleRating> = {}): ModuleRating {
  return {
    id: "test_module",
    title: "Test Module",
    scoreOutOf10: "Unavailable",
    grade: "Unavailable",
    confidence: "Unavailable",
    evidence: [],
    strengths: [],
    weaknesses: [],
    explanation: "Unavailable",
    dimensions: [],
    sourceStages: [],
    ...overrides,
  };
}

describe("P2.2 explainability framework", () => {
  it("truncates explanations to at most 120 words", () => {
    const words = Array.from({ length: 150 }, (_, i) => `w${i}`).join(" ");
    const cut = truncateWords(words, 120);
    expect(cut.split(/\s+/).filter(Boolean).length).toBe(120);
    expect(cut.endsWith("…")).toBe(true);
  });

  it("maps modules without inventing strengths or weaknesses", () => {
    const mapped = mapModuleExplainability(
      emptyModule({
        dimensions: [
          { label: "ROE", value: "Unavailable", evidence: "financial_strength" },
        ],
      }),
    );
    expect(mapped.strengths).toEqual(["Unavailable"]);
    expect(mapped.weaknesses).toEqual(["Unavailable"]);
    expect(mapped.evidence[0]?.value).toBe("Unavailable");
    expect(mapped.evidence[0]?.sourceField).toBe("financial_strength");
    expect(mapped.oneLineSummary).toBe("Unavailable");
  });

  it("attaches explainability to ResearchView from existing ratings only", () => {
    const request = buildAnalyseRequestForTicker("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    expect(view.explainability.kind).toBe(
      "institutional_explainability_framework",
    );
    expect(view.explainability.version).toBe(EXPLAINABILITY_FRAMEWORK_VERSION);
    expect(view.explainability.modules.length).toBe(10);
    for (const m of view.explainability.modules) {
      expect(m.explanation.split(/\s+/).filter(Boolean).length).toBeLessThanOrEqual(
        120,
      );
      expect(m.evidence.length).toBeGreaterThan(0);
      for (const e of m.evidence) {
        expect(e.sourceField.length).toBeGreaterThan(0);
      }
    }
  });

  it("expands accordion to reveal evidence and collapses again", () => {
    const request = buildAnalyseRequestForTicker("AAPL", {
      company: "Apple",
      exchange: "NASDAQ",
    });
    const view = mapResearchView(
      sampleResponse,
      request,
      "2026-07-28T12:00:00.000Z",
    );
    render(
      <InstitutionalRatingsSection
        ratings={view.ratings}
        transparency={view.transparency}
        explainability={view.explainability}
      />,
    );
    expect(screen.getByText("Module Ratings · Explainability")).toBeTruthy();
    const first = view.explainability.modules[0]!;
    const trigger = screen.getByRole("button", {
      name: new RegExp(first.title, "i"),
    });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(trigger);
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    const region = screen.getByLabelText(`${first.title} evidence`);
    expect(within(region).getAllByRole("definition").length).toBeGreaterThan(0);
    fireEvent.click(trigger);
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
  });

  it("includes explainability in JSON/HTML and CSV summary only", () => {
    const request = buildAnalyseRequestForTicker("AAPL", {
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
    expect(json).toContain("explainability");
    expect(json).toContain("institutional_explainability_framework");
    expect(html).toContain("Explainability Framework");
    expect(html).toContain(view.explainability.modules[0]!.title);
    expect(csv).toContain("explainabilityModules");
    expect(csv).toContain("explainabilityVersion");
    expect(csv).not.toContain("Traceability");
  });
});
