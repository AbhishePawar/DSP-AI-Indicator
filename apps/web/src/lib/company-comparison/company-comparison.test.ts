/**
 * EPIC-012/013 — mapping honesty, Buffett copy compliance, empty states.
 */
import { describe, expect, it } from "vitest";

import type { AnalyseResponse } from "@/lib/api/compositionTypes";
import { buildAnalyseRequestForTicker } from "@/lib/research/buildAnalyseRequest";
import { mapResearchView } from "@/lib/research/mapResearchView";
import {
  BUFFETT_FRAMEWORK_PREFIX,
  COMPARISON_SECTIONS,
  DATA_UNAVAILABLE,
  FORBIDDEN_BUFFETT_PHRASES,
  MAX_COMPANIES,
  MIN_COMPANIES,
  assignMedals,
  comparisonToCsv,
  comparisonToJson,
  containsForbiddenBuffettCopy,
  mapBuffettPreference,
  mapComparisonWorkspace,
  mapWinnerMatrix,
  parseExistingScore,
} from "@/lib/company-comparison";
import type { ComparisonCompanySlot } from "@/lib/company-comparison";

function sampleResponse(
  overrides?: Partial<{
    bq: number;
    moat: number;
    mgmt: number;
    decision: string;
  }>,
): AnalyseResponse {
  const bq = overrides?.bq ?? 78;
  const moat = overrides?.moat ?? 80;
  const mgmt = overrides?.mgmt ?? 75;
  const decision = overrides?.decision ?? "hold";
  return {
    ok: true,
    capability: "analyse",
    limitations: [],
    errors: [],
    api_version: "v1",
    platform_version: "1.0.0",
    pipeline_version: "1.0.0",
    correlation_id: "corr-cmp",
    payload: {
      ok: true,
      metadata: {
        pipeline_version: "1.0.0",
        platform_version: "1.0.0",
        execution_order: ["financial", "valuation"],
        confidence_summary: { valuation: 0.7 },
        warnings: [],
        total_elapsed_ms: 100,
      },
      stage_summaries: [
        {
          stage: "valuation",
          status: "succeeded",
          has_result: true,
          score: 72,
          label: "DCF",
          decision: "hold",
          confidence: 0.7,
        },
        {
          stage: "economic_moat",
          status: "succeeded",
          has_result: true,
          score: moat,
          label: "Wide",
          decision: "durable",
          confidence: 0.8,
        },
        {
          stage: "management_quality",
          status: "succeeded",
          has_result: true,
          score: mgmt,
          label: "Strong",
          decision: "aligned",
          confidence: 0.75,
        },
        {
          stage: "financial_strength",
          status: "succeeded",
          has_result: true,
          score: 70,
          label: "Solid",
          decision: "ok",
          confidence: 0.7,
        },
        {
          stage: "earnings_quality",
          status: "succeeded",
          has_result: true,
          score: 68,
          label: "Good",
          decision: "ok",
          confidence: 0.65,
        },
        {
          stage: "business_quality_aggregator",
          status: "succeeded",
          has_result: true,
          score: bq,
          label: "High",
          decision: "quality",
          confidence: 0.77,
        },
        {
          stage: "investment_recommendation",
          status: "succeeded",
          has_result: true,
          score: 60,
          label: "Hold",
          decision,
          confidence: 0.6,
        },
        {
          stage: "investment_committee",
          status: "succeeded",
          has_result: true,
          score: 62,
          label: "Consensus hold",
          decision,
          confidence: 0.62,
        },
        {
          stage: "financial",
          status: "succeeded",
          has_result: true,
          score: 71,
          label: "Healthy",
          decision: "ok",
          confidence: 0.7,
        },
        {
          stage: "growth_quality",
          status: "succeeded",
          has_result: true,
          score: 66,
          label: "Steady",
          decision: "ok",
          confidence: 0.66,
        },
      ],
      recommendation_summary: {
        decision,
        confidence: 0.6,
        margin_of_safety: 0.12,
        label: "Hold",
      },
      committee_summary: {
        decision,
        confidence: 0.62,
        consensus: "majority hold",
        rationale: "Minority prefers wait",
      },
    },
  };
}

function viewFor(ticker: string, response: AnalyseResponse) {
  const request = buildAnalyseRequestForTicker(ticker, {
    company: ticker,
    exchange: "NASDAQ",
  });
  return mapResearchView(response, request, "2026-08-02T12:00:00.000Z");
}

function readySlot(
  ticker: string,
  response: AnalyseResponse,
): ComparisonCompanySlot {
  const view = viewFor(ticker, response);
  return {
    symbol: ticker,
    company: ticker,
    exchange: "NASDAQ",
    pinned: false,
    status: "ready",
    analysedAt: "2026-08-02T12:00:00.000Z",
    correlationId: view.correlationId,
    error: null,
    view,
    intelligence: null,
  };
}

describe("EPIC-012/013 company comparison", () => {
  it("registers workspace sections including star modules", () => {
    expect(COMPARISON_SECTIONS.map((s) => s.id)).toEqual(
      expect.arrayContaining([
        "summary",
        "winnerMatrix",
        "tradeOffs",
        "buffett",
        "evidence",
        "explainability",
        "intelligence",
        "personal",
        "architecture",
      ]),
    );
    expect(MIN_COMPANIES).toBe(2);
    expect(MAX_COMPANIES).toBe(5);
  });

  it("ranks winners from server scores only and leaves ROCE unavailable", () => {
    const a = viewFor("AAA", sampleResponse({ bq: 90, moat: 60 }));
    const b = viewFor("BBB", sampleResponse({ bq: 50, moat: 85 }));
    const matrix = mapWinnerMatrix([a, b]);
    const bq = matrix.find((r) => r.id === "businessQuality")!;
    expect(bq.leader).toBe("AAA");
    expect(bq.cells.find((c) => c.symbol === "AAA")?.medal).toBe("gold");
    const roce = matrix.find((r) => r.id === "roce")!;
    expect(roce.leader).toBe(DATA_UNAVAILABLE);
    expect(roce.cells.every((c) => c.medal === null)).toBe(true);
    expect(roce.cells.every((c) => c.display === DATA_UNAVAILABLE)).toBe(true);
  });

  it("does not invent medals when scores are missing", () => {
    const medals = assignMedals([
      { symbol: "A", numeric: null },
      { symbol: "B", numeric: null },
    ]);
    expect(medals.A).toBeNull();
    expect(medals.B).toBeNull();
    expect(parseExistingScore("Unavailable")).toBeNull();
  });

  it("Buffett preference uses mandatory framing and forbids endorsement copy", () => {
    const a = viewFor("AAA", sampleResponse());
    const b = viewFor("BBB", sampleResponse({ bq: 40 }));
    const rows = mapBuffettPreference([a, b]);
    expect(rows.length).toBeGreaterThanOrEqual(8);
    for (const row of rows) {
      expect(row.framing).toContain(BUFFETT_FRAMEWORK_PREFIX);
      expect(containsForbiddenBuffettCopy(row.tradeOff)).toBe(false);
      for (const cell of row.cells) {
        expect(cell.reason).toContain(BUFFETT_FRAMEWORK_PREFIX);
        expect(containsForbiddenBuffettCopy(cell.reason)).toBe(false);
        for (const phrase of FORBIDDEN_BUFFETT_PHRASES) {
          expect(cell.reason.toLowerCase()).not.toContain(phrase);
        }
      }
    }
    expect(containsForbiddenBuffettCopy("Buffett would buy this stock")).toBe(
      true,
    );
  });

  it("workspace model shows honest empty / unavailable states", () => {
    const empty = mapComparisonWorkspace([]);
    expect(empty.executive.winnerSummary).toBe(DATA_UNAVAILABLE);
    expect(empty.winnerMatrix.every((r) => r.cells.length === 0)).toBe(true);
    expect(empty.winnerMatrix.every((r) => r.leader === DATA_UNAVAILABLE)).toBe(
      true,
    );
    expect(empty.scenarios).toEqual([]);
    expect(empty.tradeOffs).toEqual([]);

    const model = mapComparisonWorkspace([
      readySlot("AAA", sampleResponse({ bq: 88 })),
      readySlot("BBB", sampleResponse({ bq: 55, moat: 90 })),
    ]);
    expect(model.symbols).toEqual(["AAA", "BBB"]);
    expect(model.tradeOffs.length).toBeGreaterThan(0);
    expect(model.scenarios.every((s) => s.bull === "Analysis unavailable.")).toBe(
      true,
    );
    expect(model.valuation[0]?.historical).toBe(DATA_UNAVAILABLE);
    expect(model.buffettDisclaimer).toContain(BUFFETT_FRAMEWORK_PREFIX);
    expect(containsForbiddenBuffettCopy(model.buffettDisclaimer)).toBe(false);

    const json = comparisonToJson(model);
    expect(json).toContain("institutional company comparison");
    expect(json.toLowerCase()).not.toContain("buffett would buy");
    const csv = comparisonToCsv(model);
    expect(csv).toContain("Business Quality");
    expect(csv).toContain("AAA");
  });

  it("supports up to five companies without hardcoding two", () => {
    const slots = ["A", "B", "C", "D", "E"].map((t, i) =>
      readySlot(t, sampleResponse({ bq: 50 + i * 5 })),
    );
    const model = mapComparisonWorkspace(slots);
    expect(model.symbols).toHaveLength(5);
    const overall = model.winnerMatrix.find((r) => r.id === "businessQuality")!;
    expect(overall.cells).toHaveLength(5);
    expect(overall.leader).toBe("E");
  });
});
