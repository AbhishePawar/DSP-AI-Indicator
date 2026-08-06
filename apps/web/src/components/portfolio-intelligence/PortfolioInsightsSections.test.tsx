/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

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
} from "@/lib/portfolio-intelligence/mapPortfolioInsights";
import {
  AiSummarySection,
  DiversificationAnalysisSection,
  HealthScoreSection,
  OpportunityRankingSection,
  RecommendationCardsSection,
  RiskSummarySection,
  ScenarioAnalysisSection,
  ValuationHeatmapSection,
} from "./PortfolioInsightsSections";

describe("Portfolio Intelligence Engine sections — default unavailable state", () => {
  it("HealthScoreSection shows honest unavailable with no data", () => {
    render(<HealthScoreSection health={mapHealthScoreView(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("AiSummarySection shows honest unavailable with no data", () => {
    render(<AiSummarySection insights={mapPortfolioInsightsView(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("RecommendationCardsSection shows honest unavailable with no data", () => {
    render(<RecommendationCardsSection recommendations={mapRecommendations(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("RiskSummarySection shows honest unavailable with no data", () => {
    render(<RiskSummarySection risk={mapRiskSummaryView(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("ValuationHeatmapSection shows honest unavailable with no data", () => {
    render(<ValuationHeatmapSection heatmap={mapValuationHeatmapView(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("OpportunityRankingSection shows honest unavailable with no data", () => {
    render(<OpportunityRankingSection opportunities={mapOpportunitiesView(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("DiversificationAnalysisSection shows honest unavailable with no data", () => {
    render(
      <DiversificationAnalysisSection
        diversification={mapDiversificationView(null)}
        concentration={mapConcentrationView(null)}
        drift={mapDriftView(null)}
        isLoading={false}
      />,
    );
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });

  it("ScenarioAnalysisSection shows honest unavailable with no data", () => {
    render(<ScenarioAnalysisSection scenario={mapScenarioView(null)} isLoading={false} />);
    expect(screen.getAllByText(/Data unavailable/i).length).toBeGreaterThan(0);
  });
});

describe("Portfolio Intelligence Engine sections — populated data", () => {
  it("HealthScoreSection renders the composite score and components", () => {
    const view = mapHealthScoreView({
      status: "complete",
      score: 72,
      components: [
        {
          name: "risk",
          available: true,
          score: 80,
          weight: 0.2,
          contribution: 16,
          explanation: "Derived from volatility and max drawdown.",
        },
      ],
      method_id: "test",
      limitations: [],
    });
    render(<HealthScoreSection health={view} isLoading={false} />);
    expect(screen.getByText("72/100")).toBeTruthy();
  });

  it("RecommendationCardsSection renders one card per holding", () => {
    const recs = mapRecommendations([
      {
        symbol: "AAPL",
        action: "increase",
        reason: "Undervalued with strong quality.",
        supporting_metrics: {},
        confidence: 0.75,
      },
      {
        symbol: "XOM",
        action: "reduce",
        reason: "Overvalued and concentrated.",
        supporting_metrics: {},
        confidence: 0.6,
      },
    ]);
    render(<RecommendationCardsSection recommendations={recs} isLoading={false} />);
    expect(screen.getByText("AAPL")).toBeTruthy();
    expect(screen.getByText("XOM")).toBeTruthy();
    expect(screen.getByText("Increase")).toBeTruthy();
    expect(screen.getByText("Reduce")).toBeTruthy();
  });

  it("ValuationHeatmapSection renders classification badges", () => {
    const view = mapValuationHeatmapView({
      status: "complete",
      rows: [
        {
          symbol: "AAPL",
          weight: 1.0,
          valuation_class: "undervalued",
          margin_of_safety: 0.25,
          confidence: 0.7,
          message: null,
        },
      ],
      undervalued_weight: 1.0,
      fairly_valued_weight: 0,
      overvalued_weight: 0,
      unavailable_weight: 0,
      method_id: "test",
      limitations: [],
    });
    render(<ValuationHeatmapSection heatmap={view} isLoading={false} />);
    expect(screen.getByText("Undervalued")).toBeTruthy();
  });

  it("ScenarioAnalysisSection renders bull/base/bear cases", () => {
    const view = mapScenarioView({
      status: "complete",
      cases: [
        { case: "bear", implied_return_pct: 0.05 },
        { case: "base", implied_return_pct: 0.15 },
        { case: "bull", implied_return_pct: 0.25 },
      ],
      expected_cagr: 0.1,
      expected_cagr_basis: "historical",
      worst_case_drawdown: -0.2,
      worst_case_drawdown_basis: "historical",
      confidence: 0.5,
      confidence_basis: "test",
      method_id: "test",
      limitations: [],
    });
    render(<ScenarioAnalysisSection scenario={view} isLoading={false} />);
    expect(screen.getByText("Bear")).toBeTruthy();
    expect(screen.getByText("Base")).toBeTruthy();
    expect(screen.getByText("Bull")).toBeTruthy();
  });
});
