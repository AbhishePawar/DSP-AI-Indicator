import { describe, expect, it } from "vitest";

import type { SavedAnalysis } from "@/lib/persistence/types";
import { buildResearchObjectsFromSavedAnalyses } from "./researchObjectsAdapter";

function analysis(overrides: Partial<SavedAnalysis> = {}): SavedAnalysis {
  return {
    id: "1",
    ticker: "AAPL",
    company: "Apple",
    exchange: "NASDAQ",
    recommendation: "Data unavailable.",
    analysedAt: "2024-01-01T00:00:00Z",
    savedAt: "2024-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("buildResearchObjectsFromSavedAnalyses", () => {
  it("returns null when no saved analyses have usable signals", () => {
    expect(buildResearchObjectsFromSavedAnalyses([])).toBeNull();
    expect(buildResearchObjectsFromSavedAnalyses([analysis()])).toBeNull();
  });

  it("never fabricates a section when the underlying field is absent", () => {
    const result = buildResearchObjectsFromSavedAnalyses([
      analysis({
        response: {
          ok: true,
          capability: "compose_intelligence",
          payload: { recommendation_summary: { margin_of_safety: null, confidence: null } },
          limitations: [],
          errors: [],
          api_version: "v1",
          platform_version: null,
          pipeline_version: null,
          correlation_id: null,
        } as unknown as SavedAnalysis["response"],
      }),
    ]);
    expect(result).toBeNull();
  });

  it("reshapes recommendation_summary margin_of_safety and confidence", () => {
    const result = buildResearchObjectsFromSavedAnalyses([
      analysis({
        response: {
          ok: true,
          capability: "compose_intelligence",
          payload: {
            recommendation_summary: { margin_of_safety: 0.22, confidence: 0.71 },
            stage_summaries: [
              { stage: "business_quality_aggregator", status: "ok", has_result: true, score: 78 },
            ],
          },
          limitations: [],
          errors: [],
          api_version: "v1",
          platform_version: null,
          pipeline_version: null,
          correlation_id: null,
        } as unknown as SavedAnalysis["response"],
      }),
    ]) as Record<string, Record<string, unknown>>;

    expect(result).not.toBeNull();
    const doc = result!.AAPL as Record<string, unknown>;
    expect((doc.margin_of_safety as { payload: { margin_of_safety: number } }).payload.margin_of_safety).toBe(0.22);
    expect((doc.recommendation as { payload: { confidence: number } }).payload.confidence).toBe(0.71);
    expect((doc.business_quality as { payload: { score: number } }).payload.score).toBe(78);
  });

  it("normalizes ticker casing and skips missing tickers", () => {
    const result = buildResearchObjectsFromSavedAnalyses([
      analysis({
        ticker: "  msft ",
        response: {
          ok: true,
          capability: "compose_intelligence",
          payload: { recommendation_summary: { margin_of_safety: 0.1, confidence: 0.5 } },
          limitations: [],
          errors: [],
          api_version: "v1",
          platform_version: null,
          pipeline_version: null,
          correlation_id: null,
        } as unknown as SavedAnalysis["response"],
      }),
    ]) as Record<string, unknown>;
    expect(Object.keys(result!)).toEqual(["MSFT"]);
  });

  it("skips a stage score for a different stage name", () => {
    const result = buildResearchObjectsFromSavedAnalyses([
      analysis({
        response: {
          ok: true,
          capability: "compose_intelligence",
          payload: {
            recommendation_summary: { margin_of_safety: 0.1, confidence: 0.5 },
            stage_summaries: [
              { stage: "economic_moat", status: "ok", has_result: true, score: 90 },
            ],
          },
          limitations: [],
          errors: [],
          api_version: "v1",
          platform_version: null,
          pipeline_version: null,
          correlation_id: null,
        } as unknown as SavedAnalysis["response"],
      }),
    ]) as Record<string, Record<string, unknown>>;
    expect(result!.AAPL.business_quality).toBeUndefined();
  });
});
