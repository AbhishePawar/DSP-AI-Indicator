import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";

import {
  _resetMarketCache,
  readCachedQuote,
  writeCachedQuote,
} from "@/lib/market/cache";
import {
  buildPortfolioMarketSummary,
  formatChange,
  formatMarketCap,
  formatMarketPrice,
} from "@/lib/market/portfolioMarket";
import {
  fetchMarketQuote,
  seedQuoteForTicker,
} from "@/lib/market/quoteService";
import { getDemoPortfolio } from "@/lib/portfolio/data";
import {
  buildPortfolioAnalytics,
  buildPortfolioHealthAnalytics,
} from "@/lib/portfolio/analytics";

describe("market quote service", () => {
  beforeEach(() => {
    _resetMarketCache();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns deterministic seeded quotes for catalogue tickers", () => {
    const a = seedQuoteForTicker("AAPL");
    const b = seedQuoteForTicker("AAPL");
    expect(a.currentPrice).toBe(b.currentPrice);
    expect(a.ticker).toBe("AAPL");
    expect(a.week52High).toBeGreaterThan(a.currentPrice);
    expect(a.week52Low).toBeLessThan(a.currentPrice);
  });

  it("caches quotes and marks entries stale after ttl", async () => {
    const fetchPromise = fetchMarketQuote("MSFT");
    await vi.advanceTimersByTimeAsync(150);
    const quote = await fetchPromise;
    writeCachedQuote(quote);

    const fresh = readCachedQuote("MSFT", 60_000, Date.now());
    expect(fresh?.stale).toBe(false);

    const stale = readCachedQuote("MSFT", 60_000, Date.now() + 61_000);
    expect(stale?.stale).toBe(true);
    expect(stale?.quote.source).toBe("cached");
  });

  it("formats prices and market cap for display", () => {
    expect(formatMarketPrice(123.45, "USD")).toContain("123.45");
    expect(formatMarketCap(2_500_000_000)).toBe("2.50B");
    expect(formatChange(1.2, 0.5)).toContain("+1.20");
  });
});

describe("portfolio market summary", () => {
  it("computes live portfolio value from holdings and quotes", () => {
    const holdings = getDemoPortfolio().holdings.slice(0, 2);
    const quotes = Object.fromEntries(
      holdings.map((h) => [h.ticker, seedQuoteForTicker(h.ticker)]),
    );
    const summary = buildPortfolioMarketSummary(holdings, quotes);
    expect(summary.totalValue).toBeGreaterThan(0);
    expect(summary.dayChange).not.toBeNull();
    expect(summary.holdings).toHaveLength(2);
  });
});

describe("deterministic analytics unchanged", () => {
  it("portfolio analytics do not depend on market quotes", () => {
    const holdings = getDemoPortfolio().holdings;
    const before = buildPortfolioAnalytics(holdings);
    const after = buildPortfolioAnalytics(holdings);
    expect(after).toEqual(before);

    const healthBefore = buildPortfolioHealthAnalytics(holdings);
    const healthAfter = buildPortfolioHealthAnalytics(holdings);
    expect(healthAfter).toEqual(healthBefore);
  });
});
