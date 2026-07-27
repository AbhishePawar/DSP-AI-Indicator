import { describe, expect, it } from "vitest";

import {
  buildPipelineStages,
  PIPELINE_STAGE_DEFS,
} from "@/lib/analysis/pipelineStages";
import {
  clearRecentAnalyses,
  loadRecentAnalyses,
  pushRecentAnalysis,
} from "@/lib/analysis/recentAnalyses";

describe("pipeline stages", () => {
  it("defines the terminal pipeline order", () => {
    expect(PIPELINE_STAGE_DEFS.map((s) => s.label)).toEqual([
      "Financial Analysis",
      "Valuation",
      "Economic Moat",
      "Management Quality",
      "Financial Strength",
      "Earnings Quality",
      "Growth Quality",
      "Recommendation",
      "Committee",
    ]);
  });

  it("maps API stage statuses to UI labels", () => {
    const stages = buildPipelineStages([
      {
        stage: "financial",
        status: "succeeded",
        has_result: true,
      },
      {
        stage: "valuation",
        status: "failed",
        has_result: false,
        error: "missing",
      },
    ]);
    expect(stages[0]?.status).toBe("Completed");
    expect(stages[1]?.status).toBe("Failed");
    expect(stages[2]?.status).toBe("Pending");
  });
});

describe("recent analyses session store", () => {
  it("pushes and dedupes by ticker", () => {
    clearRecentAnalyses();
    pushRecentAnalysis({
      ticker: "AAPL",
      company: "Apple",
      exchange: "NASDAQ",
      recommendation: "Buy",
      analysedAt: "2026-07-27T00:00:00.000Z",
    });
    const next = pushRecentAnalysis({
      ticker: "AAPL",
      company: "Apple",
      exchange: "NASDAQ",
      recommendation: "Hold",
      analysedAt: "2026-07-27T01:00:00.000Z",
    });
    expect(next).toHaveLength(1);
    expect(next[0]?.recommendation).toBe("Hold");
    expect(loadRecentAnalyses()).toHaveLength(1);
    clearRecentAnalyses();
  });
});
