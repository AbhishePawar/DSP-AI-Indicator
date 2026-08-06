/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  mapAllocationView,
  mapConstraintsView,
  mapRiskView,
  mapSimulationView,
  mapStressView,
  mapTaxView,
} from "@/lib/portfolio-intelligence/mapPortfolioAnalytics";
import {
  CorrelationMatrixSection,
  EfficientFrontierSection,
  FactorExposureSection,
  MonteCarloSection,
  PositionLimitsSection,
  ScenarioImpactSection,
  StressTestingSection,
  TaxOptimizationSection,
} from "./AnalyticsSections";

describe("Portfolio Intelligence Analytics sections — default unavailable state", () => {
  it("CorrelationMatrixSection shows honest unavailable with no data", () => {
    render(<CorrelationMatrixSection risk={mapRiskView(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("FactorExposureSection shows honest unavailable with no data", () => {
    render(<FactorExposureSection risk={mapRiskView(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("EfficientFrontierSection shows honest unavailable with no data", () => {
    render(
      <EfficientFrontierSection simulation={mapSimulationView(null)} isLoading={false} />,
    );
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("MonteCarloSection shows honest unavailable with no data", () => {
    render(<MonteCarloSection simulation={mapSimulationView(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("StressTestingSection shows honest unavailable with no data", () => {
    render(<StressTestingSection stress={mapStressView(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("ScenarioImpactSection shows honest unavailable with no data", () => {
    render(<ScenarioImpactSection stress={mapStressView(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("TaxOptimizationSection shows honest unavailable with no data", () => {
    render(<TaxOptimizationSection tax={mapTaxView(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("PositionLimitsSection shows honest unavailable with no data", () => {
    render(
      <PositionLimitsSection constraints={mapConstraintsView(null)} isLoading={false} />,
    );
    expect(screen.getByText(/no limits configured/i)).toBeTruthy();
  });
});

describe("Portfolio Intelligence Analytics sections — populated state", () => {
  it("CorrelationMatrixSection renders a matrix table when data is present", () => {
    const risk = mapRiskView({
      ok: true,
      available: true,
      message: null,
      risk_attribution: {
        status: "complete",
        rows: [],
        heatmap: [],
        correlation_matrix: {
          symbols: ["AAPL", "MSFT"],
          matrix: [
            [1, 0.4],
            [0.4, 1],
          ],
          window_days: 30,
        },
        limitations: [],
      },
      factor_exposure: { status: "unavailable", factors: [], limitations: [] },
    });
    render(<CorrelationMatrixSection risk={risk} isLoading={false} />);
    expect(screen.getByRole("table", { name: /correlation matrix/i })).toBeTruthy();
    expect(screen.getAllByText("AAPL").length).toBeGreaterThan(0);
  });

  it("MonteCarloSection renders percentiles when data is present", () => {
    const simulation = mapSimulationView({
      ok: true,
      available: true,
      message: null,
      monte_carlo: {
        status: "complete",
        paths: 500,
        horizon_days: 60,
        percentiles: { p5: -0.05, p50: 0.02, p95: 0.1 },
        mean_terminal_return: 0.02,
        method_id: "m",
        seed: 1,
        limitations: [],
      },
      efficient_frontier: null,
    });
    render(<MonteCarloSection simulation={simulation} isLoading={false} />);
    expect(screen.getByText("p50")).toBeTruthy();
  });

  it("StressTestingSection renders per-scenario results and catalog", () => {
    const stress = mapStressView({
      ok: true,
      available: true,
      message: null,
      scenarios: [],
      stress_tests: [
        {
          scenario_id: "covid_2020",
          available: true,
          description: "2020 COVID-19 crash",
          window_start: "2020-02-19",
          window_end: "2020-03-23",
          portfolio_return_pct: -0.3,
          per_position_return_pct: {},
          positions_with_history: 2,
          positions_beta_scaled: 0,
        },
      ],
      stress_window_catalog: {
        covid_2020: { start: "2020-02-19", end: "2020-03-23", description: "2020 COVID-19 crash" },
      },
    });
    render(<StressTestingSection stress={stress} isLoading={false} />);
    expect(screen.getAllByText(/2020 COVID-19 crash/i).length).toBeGreaterThan(0);
  });

  it("PositionLimitsSection renders breach rows when limits are configured", () => {
    const constraints = mapConstraintsView({
      ok: true,
      available: true,
      message: null,
      position_limits: {
        status: "complete",
        breaches: [],
        checks: [
          {
            label: "AAPL",
            limit_type: "max_position_weight",
            limit_value: 0.2,
            actual_value: 0.3,
            breached: true,
          },
        ],
      },
      rebalancing: { status: "unavailable", trades: [], total_drift: 0, disclaimer: "" },
    });
    render(<PositionLimitsSection constraints={constraints} isLoading={false} />);
    expect(screen.getByText(/breached/i)).toBeTruthy();
  });
});
