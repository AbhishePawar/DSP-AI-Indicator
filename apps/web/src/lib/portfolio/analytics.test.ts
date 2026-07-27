import { describe, expect, it } from "vitest";

import {
  addHoldingToView,
  getDemoPortfolio,
  getEmptyPortfolio,
  removeHoldingFromView,
} from "@/lib/portfolio/data";
import {
  buildPortfolioAnalytics,
  buildPortfolioHealthAnalytics,
  buildRecommendationDistribution,
  buildSectorAllocationBuckets,
  normalizeRecommendation,
} from "@/lib/portfolio/analytics";

describe("portfolio analytics", () => {
  it("maps recommendations into fixed buckets", () => {
    expect(normalizeRecommendation("Buy")).toBe("Buy");
    expect(normalizeRecommendation("STRONG BUY")).toBe("Strong Buy");
    expect(normalizeRecommendation("approve")).toBe("Buy");
    expect(normalizeRecommendation("unknown")).toBe("Hold");
  });

  it("builds sector buckets including Consumer and Others", () => {
    const segments = buildSectorAllocationBuckets(getDemoPortfolio().holdings);
    expect(segments.map((s) => s.name)).toEqual([
      "Technology",
      "Financials",
      "Consumer",
      "Healthcare",
      "Industrials",
      "Others",
    ]);
    const tech = segments.find((s) => s.name === "Technology");
    expect(tech?.percent ?? 0).toBeGreaterThan(0);
  });

  it("counts recommendation distribution", () => {
    const distribution = buildRecommendationDistribution(
      getDemoPortfolio().holdings,
    );
    expect(distribution.Buy + distribution.Hold).toBeGreaterThan(0);
    expect(distribution["Strong Sell"]).toBe(0);
  });

  it("marks empty portfolio health", () => {
    const health = buildPortfolioHealthAnalytics([]);
    expect(health.primary).toBe("Empty");
    expect(health.labels).toContain("Empty");
  });

  it("updates analytics after add and remove", () => {
    let view = getEmptyPortfolio();
    view = addHoldingToView(view, {
      company: "Apple",
      ticker: "AAPL",
      sector: "Technology",
      recommendation: "Buy",
      researchAvailable: true,
    })!;
    view = addHoldingToView(view, {
      company: "HDFC Bank",
      ticker: "HDFCBANK",
      sector: "Financials",
      recommendation: "Hold",
      researchAvailable: true,
    })!;

    let analytics = buildPortfolioAnalytics(view.holdings);
    expect(analytics.quality.companiesWithResearch).toBe(2);
    expect(analytics.researchCoverage.coveragePercent).toBe(100);
    expect(analytics.diversification.sectorCount).toBe(2);
    expect(analytics.diversification.exchangeCount).toBe(2);
    expect(analytics.diversification.countryCount).toBe(2);
    expect(analytics.health.labels).toContain("Research Complete");

    view = removeHoldingFromView(view, "HDFCBANK")!;
    analytics = buildPortfolioAnalytics(view.holdings);
    expect(analytics.quality.companiesWithResearch).toBe(1);
    expect(analytics.diversification.sectorCount).toBe(1);
    expect(analytics.health.labels).toContain("Concentrated");
  });

  it("flags research incomplete when coverage is partial", () => {
    let view = getEmptyPortfolio();
    view = addHoldingToView(view, {
      company: "Apple",
      ticker: "AAPL",
      sector: "Technology",
      researchAvailable: true,
    })!;
    view = addHoldingToView(view, {
      company: "Sparse Co",
      ticker: "SPARSE",
      sector: "Materials",
      researchAvailable: false,
    })!;
    const analytics = buildPortfolioAnalytics(view.holdings);
    expect(analytics.researchCoverage.researchMissing).toBe(1);
    expect(analytics.health.labels).toContain("Research Incomplete");
  });
});
