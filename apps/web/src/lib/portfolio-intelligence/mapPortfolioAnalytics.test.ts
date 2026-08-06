import { describe, expect, it } from "vitest";

import {
  buildPortfolioAnalyticsPortfolio,
  mapAllocationView,
  mapConstraintsView,
  mapPerformanceView,
  mapRiskView,
  mapSimulationView,
  mapStressView,
  mapTaxView,
} from "./mapPortfolioAnalytics";

describe("buildPortfolioAnalyticsPortfolio", () => {
  it("converts session holdings into weight-fraction request rows", () => {
    const portfolio = buildPortfolioAnalyticsPortfolio([
      {
        company: "Apple",
        ticker: "AAPL",
        sector: "Technology",
        allocationPercent: 60,
        recommendation: "Data unavailable.",
        researchAvailable: true,
      },
    ]);
    expect(portfolio.holdings).toEqual([
      { symbol: "AAPL", weight: 0.6, sector: "Technology" },
    ]);
  });

  it("never fabricates a weight for missing allocationPercent", () => {
    const portfolio = buildPortfolioAnalyticsPortfolio([
      {
        company: "Apple",
        ticker: "AAPL",
        sector: "Technology",
        allocationPercent: Number.NaN,
        recommendation: "Data unavailable.",
        researchAvailable: true,
      },
    ]);
    expect(portfolio.holdings[0]?.weight).toBe(0);
  });
});

describe("mapPerformanceView", () => {
  it("is honestly unavailable for a null payload", () => {
    const view = mapPerformanceView(null);
    expect(view.available).toBe(false);
    expect(view.sharpeRatio).toBe("Data unavailable.");
    expect(view.beta).toBe("Data unavailable.");
  });

  it("formats populated ratios as percent/ratio strings", () => {
    const view = mapPerformanceView({
      ok: true,
      available: true,
      message: null,
      benchmark_symbol: "SPY",
      result: {
        status: "complete",
        window_days: 252,
        sharpe_ratio: 1.2345,
        sortino_ratio: 1.5,
        treynor_ratio: 0.08,
        jensen_alpha: 0.02,
        beta: 0.95,
        tracking_error: 0.04,
        information_ratio: 0.3,
        max_drawdown: 0.12,
        annualized_return: 0.15,
        annualized_volatility: 0.18,
        risk_free_rate: 0,
        limitations: [],
      },
    });
    expect(view.available).toBe(true);
    expect(view.sharpeRatio).toBe("1.23");
    expect(view.beta).toBe("0.95");
    expect(view.maxDrawdown).toBe("12.00%");
    expect(view.benchmarkSymbol).toBe("SPY");
  });

  it("surfaces server limitations when beta/alpha are unavailable", () => {
    const view = mapPerformanceView({
      ok: true,
      available: true,
      message: null,
      result: {
        status: "partial",
        window_days: 10,
        sharpe_ratio: 1.0,
        sortino_ratio: null,
        treynor_ratio: null,
        jensen_alpha: null,
        beta: null,
        tracking_error: null,
        information_ratio: null,
        max_drawdown: 0.05,
        annualized_return: 0.1,
        annualized_volatility: 0.2,
        risk_free_rate: 0,
        limitations: ["benchmark_symbol not supplied"],
      },
    });
    expect(view.beta).toBe("Data unavailable.");
    expect(view.limitations).toContain("benchmark_symbol not supplied");
  });
});

describe("mapRiskView", () => {
  it("is honestly unavailable for a null payload", () => {
    const view = mapRiskView(null);
    expect(view.rows).toEqual([]);
    expect(view.correlationSymbols).toEqual([]);
    expect(view.factors).toEqual([]);
  });

  it("maps rows, heatmap, correlation matrix, and factors", () => {
    const view = mapRiskView({
      ok: true,
      available: true,
      message: null,
      risk_attribution: {
        status: "complete",
        rows: [
          {
            symbol: "AAPL",
            weight: 0.5,
            volatility: 0.2,
            correlation_to_portfolio: 0.9,
            risk_contribution_pct: 0.6,
          },
        ],
        heatmap: [
          { symbol: "AAPL", sector: "Technology", weight: 0.5, volatility: 0.2, risk_contribution_pct: 0.6 },
        ],
        correlation_matrix: { symbols: ["AAPL", "MSFT"], matrix: [[1, 0.5], [0.5, 1]], window_days: 30 },
        limitations: [],
      },
      factor_exposure: {
        status: "partial",
        factors: [
          { factor_name: "value", exposure_value: 0.3, contributing_positions: 1, total_positions: 2 },
        ],
        limitations: ["no positions supplied a momentum_score value"],
      },
    });
    expect(view.rows[0]?.symbol).toBe("AAPL");
    expect(view.correlationSymbols).toEqual(["AAPL", "MSFT"]);
    expect(view.factors[0]?.factorName).toBe("value");
    expect(view.limitations).toContain("no positions supplied a momentum_score value");
  });
});

describe("mapAllocationView", () => {
  it("is honestly unavailable for a null payload", () => {
    const view = mapAllocationView(null);
    expect(view.sector.buckets).toEqual([]);
    expect(view.country.buckets).toEqual([]);
  });

  it("maps sector and country buckets", () => {
    const view = mapAllocationView({
      ok: true,
      available: true,
      message: null,
      sector_allocation: {
        dimension: "sector",
        status: "complete",
        buckets: [{ label: "Technology", weight: 1, symbols: ["AAPL"] }],
        unclassified_weight: 0,
        limitations: [],
      },
      country_allocation: {
        dimension: "country",
        status: "unavailable",
        buckets: [],
        unclassified_weight: 1,
        limitations: ["1.0000 of total weight has no declared country"],
      },
    });
    expect(view.sector.buckets[0]?.label).toBe("Technology");
    expect(view.country.buckets).toEqual([]);
    expect(view.country.limitations[0]).toMatch(/no declared country/);
  });
});

describe("mapSimulationView", () => {
  it("is honestly unavailable for a null payload", () => {
    const view = mapSimulationView(null);
    expect(view.percentiles).toEqual([]);
    expect(view.frontierPoints).toEqual([]);
  });

  it("maps monte carlo percentiles and frontier points", () => {
    const view = mapSimulationView({
      ok: true,
      available: true,
      message: null,
      monte_carlo: {
        status: "complete",
        paths: 1000,
        horizon_days: 252,
        percentiles: { p50: 0.1, p5: -0.1, p95: 0.3 },
        mean_terminal_return: 0.1,
        method_id: "m",
        seed: 42,
        limitations: [],
      },
      efficient_frontier: {
        status: "complete",
        points: [{ expected_return: 0.1, volatility: 0.2, weights: { AAPL: 1 } }],
        current_portfolio_point: { expected_return: 0.08, volatility: 0.25, weights: {} },
        method_id: "f",
        samples: 200,
        limitations: [],
      },
    });
    expect(view.percentiles.map((p) => p.label)).toEqual(["p5", "p50", "p95"]);
    expect(view.frontierPoints).toHaveLength(1);
    expect(view.currentPortfolioPoint?.expectedReturn).toBe("8.00%");
  });
});

describe("mapStressView", () => {
  it("is honestly unavailable for a null payload", () => {
    const view = mapStressView(null);
    expect(view.scenarios).toEqual([]);
    expect(view.stressTests).toEqual([]);
  });

  it("maps scenario impacts and stress test availability", () => {
    const view = mapStressView({
      ok: true,
      available: true,
      message: null,
      scenarios: [
        {
          scenario_name: "Market -10%",
          shock_pct: -0.1,
          portfolio_impact_pct: -0.08,
          per_position_impact_pct: {},
          method_id: "s",
        },
      ],
      stress_tests: [
        { scenario_id: "unknown_window", available: false, message: "Unknown stress window id" },
      ],
      stress_window_catalog: {
        gfc_2008: { start: "2008-09-01", end: "2009-03-09", description: "2008 GFC" },
      },
    });
    expect(view.scenarios[0]?.name).toBe("Market -10%");
    expect(view.stressTests[0]?.available).toBe(false);
    expect(view.catalog[0]?.id).toBe("gfc_2008");
  });
});

describe("mapConstraintsView", () => {
  it("is honestly unavailable for a null payload", () => {
    const view = mapConstraintsView(null);
    expect(view.checks).toEqual([]);
    expect(view.trades).toEqual([]);
    expect(view.disclaimer).toMatch(/not a trade recommendation/i);
  });

  it("maps breaches and rebalancing trades", () => {
    const view = mapConstraintsView({
      ok: true,
      available: true,
      message: null,
      position_limits: {
        status: "complete",
        breaches: [{ label: "AAPL", limit_type: "max_position_weight", limit_value: 0.2, actual_value: 0.3, breached: true }],
        checks: [{ label: "AAPL", limit_type: "max_position_weight", limit_value: 0.2, actual_value: 0.3, breached: true }],
      },
      rebalancing: {
        status: "complete",
        trades: [
          {
            symbol: "AAPL",
            current_weight: 0.3,
            target_weight: 0.2,
            drift: 0.1,
            suggested_action: "decrease",
            suggested_delta_weight: -0.1,
          },
        ],
        total_drift: 0.1,
        disclaimer: "Analysis only — not a trade recommendation or order instruction.",
      },
    });
    expect(view.breaches[0]?.label).toBe("AAPL");
    expect(view.trades[0]?.action).toBe("decrease");
  });
});

describe("mapTaxView", () => {
  it("is honestly unavailable for a null payload", () => {
    const view = mapTaxView(null);
    expect(view.lots).toEqual([]);
  });

  it("maps tax lots, distinguishing available vs. unavailable positions", () => {
    const view = mapTaxView({
      ok: true,
      available: true,
      message: null,
      result: {
        status: "partial",
        lots: [
          {
            symbol: "AAPL",
            available: true,
            unrealized_gain_loss_pct: 0.25,
            unrealized_gain_loss_per_unit: 25,
            holding_period_days: 400,
            term: "long_term",
            harvesting_candidate: false,
            reason_unavailable: null,
          },
          {
            symbol: "MSFT",
            available: false,
            unrealized_gain_loss_pct: null,
            unrealized_gain_loss_per_unit: null,
            holding_period_days: null,
            term: null,
            harvesting_candidate: false,
            reason_unavailable: "cost_basis_per_unit not supplied.",
          },
        ],
        harvesting_candidates: [],
        limitations: ["Requires caller-supplied cost_basis_per_unit and purchase_date per position."],
      },
    });
    expect(view.lots[0]?.gainLossPct).toBe("25.00%");
    expect(view.lots[1]?.reasonUnavailable).toMatch(/cost_basis_per_unit/);
  });
});
