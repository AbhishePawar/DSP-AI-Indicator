import { describe, expect, it } from "vitest";

import {
  addHoldingToView,
  buildAllocations,
  buildPortfolioSummary,
  getDemoPortfolio,
  getEmptyPortfolio,
  hasHolding,
  isPortfolioEmpty,
  removeHoldingFromView,
} from "@/lib/portfolio/data";

describe("portfolio foundation data", () => {
  it("returns demo holdings", () => {
    const view = getDemoPortfolio();
    expect(view.holdings.length).toBeGreaterThan(0);
    expect(view.summary.totalHoldings).toBe(view.holdings.length);
  });

  it("marks empty portfolio correctly", () => {
    const view = getEmptyPortfolio();
    expect(isPortfolioEmpty(view)).toBe(true);
    expect(view.summary.totalHoldings).toBe(0);
    expect(view.summary.portfolioStatus).toBe("Empty");
  });

  it("builds sector allocations from holdings", () => {
    const view = getDemoPortfolio();
    expect(view.allocations.bySector.length).toBeGreaterThan(0);
    const total = view.allocations.bySector.reduce(
      (sum, segment) => sum + segment.percent,
      0,
    );
    expect(total).toBeGreaterThan(0);
  });

  it("builds summary with management fields", () => {
    const summary = buildPortfolioSummary(getDemoPortfolio().holdings);
    expect(summary.totalHoldings).toBeGreaterThan(0);
    expect(summary.sectorCount).toBeGreaterThan(0);
    expect(summary.researchCoverage).toContain("%");
    expect(summary.portfolioStatus).toContain("Active");
  });

  it("builds geography allocation buckets", () => {
    const allocations = buildAllocations(getDemoPortfolio().holdings);
    expect(allocations.byGeography.some((s) => s.name === "India")).toBe(true);
    expect(allocations.byGeography.some((s) => s.name === "United States")).toBe(
      true,
    );
  });
});

describe("portfolio management workflows", () => {
  it("adds a company and updates summary", () => {
    const empty = getEmptyPortfolio();
    const next = addHoldingToView(empty, {
      company: "Apple",
      ticker: "AAPL",
      sector: "Technology",
      researchAvailable: true,
    });
    expect(next).not.toBeNull();
    expect(next!.holdings).toHaveLength(1);
    expect(next!.summary.totalHoldings).toBe(1);
    expect(next!.summary.sectorCount).toBe(1);
    expect(next!.activities[0]?.label).toBe("Added Apple");
  });

  it("prevents duplicate tickers", () => {
    const seed = addHoldingToView(getEmptyPortfolio(), {
      company: "Apple",
      ticker: "AAPL",
      sector: "Technology",
    });
    expect(seed).not.toBeNull();
    const duplicate = addHoldingToView(seed!, {
      company: "Apple Inc",
      ticker: "aapl",
      sector: "Technology",
    });
    expect(duplicate).toBeNull();
    expect(hasHolding(seed!.holdings, "AAPL")).toBe(true);
  });

  it("removes a holding and returns to empty", () => {
    const withHolding = addHoldingToView(getEmptyPortfolio(), {
      company: "Microsoft",
      ticker: "MSFT",
      sector: "Technology",
    });
    expect(withHolding).not.toBeNull();
    const cleared = removeHoldingFromView(withHolding!, "MSFT");
    expect(cleared).not.toBeNull();
    expect(cleared!.holdings).toHaveLength(0);
    expect(cleared!.summary.portfolioStatus).toBe("Empty");
    expect(cleared!.activities[0]?.label).toBe("Removed Microsoft");
  });

  it("rebalances allocations after add", () => {
    let view = getEmptyPortfolio();
    view = addHoldingToView(view, {
      company: "Apple",
      ticker: "AAPL",
      sector: "Technology",
    })!;
    view = addHoldingToView(view, {
      company: "TCS",
      ticker: "TCS",
      sector: "Technology",
    })!;
    const total = view.holdings.reduce(
      (sum, h) => sum + h.allocationPercent,
      0,
    );
    expect(Math.round(total)).toBe(100);
  });
});
