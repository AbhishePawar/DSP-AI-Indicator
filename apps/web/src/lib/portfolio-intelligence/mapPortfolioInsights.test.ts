import { describe, expect, it } from "vitest";

import {
  mapConcentrationView,
  mapDiversificationView,
  mapDriftView,
  mapHealthScoreView,
  mapOpportunitiesView,
  mapPortfolioInsightsView,
  mapRecommendations,
  mapRiskSummaryView,
  mapScenarioView,
  mapValuationHeatmapView,
} from "./mapPortfolioInsights";

describe("mapHealthScoreView", () => {
  it("is honestly unavailable for a null payload", () => {
    const view = mapHealthScoreView(null);
    expect(view.available).toBe(false);
    expect(view.scoreLabel).toBe("Data unavailable.");
  });

  it("formats score and components", () => {
    const view = mapHealthScoreView({
      status: "partial",
      score: 62.4,
      components: [
        {
          name: "diversification",
          available: true,
          score: 70,
          weight: 0.2,
          contribution: 14,
          explanation: "test",
        },
        {
          name: "cash_allocation",
          available: false,
          score: null,
          weight: 0.05,
          contribution: null,
          explanation: "Data unavailable. No caller-declared cash weight supplied.",
        },
      ],
      method_id: "test",
      limitations: ["Data unavailable. No caller-declared cash weight supplied."],
    });
    expect(view.available).toBe(true);
    expect(view.scoreLabel).toBe("62/100");
    expect(view.components).toHaveLength(2);
    expect(view.components[0]?.score).toBe("70/100");
    expect(view.components[1]?.score).toBe("Data unavailable.");
  });
});

describe("mapConcentrationView", () => {
  it("is honestly unavailable when status is unavailable", () => {
    const view = mapConcentrationView({
      status: "unavailable",
      largest_holdings: [],
      sector_concentration: [],
      industry_concentration: [],
      style_concentration: [],
      country_concentration: [],
      herfindahl_index: null,
      flags: [],
      limitations: ["no portfolio holdings supplied."],
    });
    expect(view.available).toBe(false);
  });

  it("formats largest holdings and flags", () => {
    const view = mapConcentrationView({
      status: "complete",
      largest_holdings: [{ symbol: "AAPL", weight: 0.6, weight_pct_of_portfolio: 0.6 }],
      sector_concentration: [{ label: "Information Technology", weight: 0.6, symbols: ["AAPL"] }],
      industry_concentration: [],
      style_concentration: [],
      country_concentration: [],
      herfindahl_index: 0.36,
      flags: [
        { kind: "position", label: "AAPL", weight: 0.6, threshold: 0.1, symbols: ["AAPL"] },
      ],
      limitations: [],
    });
    expect(view.largestHoldings).toEqual([{ symbol: "AAPL", weight: "60.0%" }]);
    expect(view.flags).toHaveLength(1);
    expect(view.herfindahlIndex).toBe("0.360");
  });
});

describe("mapValuationHeatmapView", () => {
  it("labels valuation classes for display", () => {
    const view = mapValuationHeatmapView({
      status: "partial",
      rows: [
        {
          symbol: "AAPL",
          weight: 0.6,
          valuation_class: "undervalued",
          margin_of_safety: 0.25,
          confidence: 0.7,
          message: null,
        },
        {
          symbol: "XOM",
          weight: 0.4,
          valuation_class: "unavailable",
          margin_of_safety: null,
          confidence: null,
          message: "Data unavailable. No linked valuation for XOM.",
        },
      ],
      undervalued_weight: 0.6,
      fairly_valued_weight: 0,
      overvalued_weight: 0,
      unavailable_weight: 0.4,
      method_id: "test",
      limitations: [],
    });
    expect(view.rows[0]?.valuationClass).toBe("Undervalued");
    expect(view.rows[1]?.valuationClass).toBe("Data unavailable.");
    expect(view.rows[1]?.message).toContain("Data unavailable");
  });
});

describe("mapRiskSummaryView", () => {
  it("is honestly unavailable for a null payload", () => {
    const view = mapRiskSummaryView(null);
    expect(view.available).toBe(false);
    expect(view.beta).toBe("Data unavailable.");
    expect(view.conditionalValueAtRisk95).toBe("Data unavailable.");
  });

  it("formats risk fields and highlights", () => {
    const view = mapRiskSummaryView({
      status: "partial",
      beta: 1.1,
      annualized_volatility: 0.2,
      max_drawdown: -0.3,
      tracking_error: 0.05,
      value_at_risk_95: 0.18,
      value_at_risk_method: "Monte Carlo p5",
      conditional_value_at_risk_95: null,
      stress_test_count: 2,
      monte_carlo_available: true,
      highest_risk_holdings: [
        { symbol: "TSLA", weight: 0.3, volatility: 0.5, risk_contribution_pct: 60 },
      ],
      limitations: [],
    });
    expect(view.beta).toBe("1.10");
    expect(view.valueAtRisk95).toBe("18.0%");
    expect(view.valueAtRiskMethod).toBe("Monte Carlo p5");
    expect(view.highestRiskHoldings[0]?.symbol).toBe("TSLA");
    expect(view.conditionalValueAtRisk95).toBe("Data unavailable.");
  });
});

describe("mapRecommendations", () => {
  it("maps actions to display labels", () => {
    const recs = mapRecommendations([
      {
        symbol: "AAPL",
        action: "increase",
        reason: "test reason",
        supporting_metrics: {},
        confidence: 0.8,
      },
    ]);
    expect(recs[0]?.actionLabel).toBe("Increase");
    expect(recs[0]?.confidence).toBe("80.0%");
  });

  it("returns empty array for null payload", () => {
    expect(mapRecommendations(null)).toEqual([]);
  });
});

describe("mapDriftView", () => {
  it("labels drift directions and lists missing sectors", () => {
    const view = mapDriftView({
      status: "partial",
      sector_drift: [
        {
          label: "Information Technology",
          weight: 0.9,
          baseline_weight: 0.09,
          direction: "overweight",
        },
      ],
      missing_sectors: ["Energy", "Utilities"],
      style_drift: [],
      cap_drift: [],
      limitations: ["Data unavailable. No caller-supplied style labels."],
    });
    expect(view.sectorDrift[0]?.direction).toBe("Overweight");
    expect(view.missingSectors).toEqual(["Energy", "Utilities"]);
  });
});

describe("mapDiversificationView", () => {
  it("is honestly unavailable when score is null", () => {
    const view = mapDiversificationView({
      status: "unavailable",
      score: null,
      holding_count: 0,
      sector_count: 0,
      average_pairwise_correlation: null,
      largest_position_weight: null,
      position_herfindahl_index: null,
      risk_herfindahl_index: null,
      explanation: [],
      limitations: ["no portfolio holdings supplied."],
    });
    expect(view.available).toBe(false);
    expect(view.score).toBe("Data unavailable.");
  });
});

describe("mapOpportunitiesView", () => {
  it("formats ranking entries per dimension", () => {
    const view = mapOpportunitiesView({
      status: "partial",
      highest_margin_of_safety: [{ symbol: "AAPL", value: 0.25, weight: 0.6 }],
      highest_expected_cagr: [],
      best_quality: [{ symbol: "AAPL", value: 82, weight: 0.6 }],
      lowest_risk: [],
      highest_conviction: [],
      limitations: ["Data unavailable. No single-company forward-looking equity CAGR..."],
    });
    expect(view.highestMarginOfSafety[0]?.value).toBe("25.0%");
    expect(view.bestQuality[0]?.value).toBe("82/100");
    expect(view.highestExpectedCagr).toEqual([]);
  });
});

describe("mapScenarioView", () => {
  it("labels bull/base/bear cases and surfaces bases", () => {
    const view = mapScenarioView({
      status: "partial",
      cases: [
        { case: "bear", implied_return_pct: 0.05 },
        { case: "base", implied_return_pct: 0.15 },
        { case: "bull", implied_return_pct: 0.25 },
      ],
      expected_cagr: 0.1,
      expected_cagr_basis: "Trailing realized annualized portfolio return — historical, not a forecast.",
      worst_case_drawdown: -0.2,
      worst_case_drawdown_basis: "Trailing realized maximum drawdown — historical.",
      confidence: 0.4,
      confidence_basis: "test basis",
      limitations: [],
    });
    expect(view.cases.map((c) => c.case)).toEqual(["Bear", "Base", "Bull"]);
    expect(view.expectedCagrBasis).toContain("historical");
  });
});

describe("mapPortfolioInsightsView", () => {
  it("is honestly unavailable for a null payload", () => {
    const view = mapPortfolioInsightsView(null);
    expect(view.available).toBe(false);
    expect(view.message).toBe("Data unavailable.");
    expect(view.health.available).toBe(false);
  });

  it("maps every section from the full payload", () => {
    const view = mapPortfolioInsightsView({
      ok: true,
      available: true,
      message: null,
      service_version: "1.0.0",
      holding_count: 1,
      health_score: {
        status: "partial",
        score: 50,
        components: [],
        method_id: "test",
        limitations: [],
      },
      limitations: [],
    });
    expect(view.available).toBe(true);
    expect(view.holdingCount).toBe(1);
    expect(view.health.scoreLabel).toBe("50/100");
  });
});
