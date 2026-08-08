import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";

const marketQuoteMock = vi.fn();

vi.mock("@/lib/api/client", () => ({
  api: {
    marketQuote: (...args: unknown[]) => marketQuoteMock(...args),
  },
}));

import {
  _resetMarketCache,
  readCachedQuote,
} from "@/lib/market/cache";
import {
  buildPortfolioMarketSummary,
  formatChange,
  formatMarketCap,
  formatMarketPrice,
} from "@/lib/market/portfolioMarket";
import {
  MARKET_DATA_UNAVAILABLE,
  fetchMarketQuote,
  marketQuoteFromAuthenticated,
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
    marketQuoteMock.mockReset();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("demo seed is offline-only and never labeled live (P0-03)", () => {
    const a = seedQuoteForTicker("AAPL");
    const b = seedQuoteForTicker("AAPL");
    expect(a.currentPrice).toBe(b.currentPrice);
    expect(a.ticker).toBe("AAPL");
    expect(a.source).toBe("offline");
    expect(a.source).not.toBe("live");
  });

  it("maps authenticated API quotes as live without fabricating fields", () => {
    const quote = marketQuoteFromAuthenticated({
      ok: true,
      available: true,
      authenticated: true,
      symbol: "MSFT",
      currency: "USD",
      fields: {
        current_price: 420.5,
        previous_close: 418.0,
        week_52_high: 450,
        week_52_low: 300,
        volume: 12_000_000,
        market_cap: 3_000_000_000_000,
      },
      provenance: { retrieved_at: "2026-08-08T12:00:00.000Z" },
    });
    expect(quote).not.toBeNull();
    expect(quote!.ticker).toBe("MSFT");
    expect(quote!.currentPrice).toBe(420.5);
    expect(quote!.source).toBe("live");
  });

  it("does not map unavailable authenticated payloads", () => {
    expect(
      marketQuoteFromAuthenticated({
        ok: true,
        available: false,
        authenticated: false,
        fields: null,
        message: "Data unavailable.",
      }),
    ).toBeNull();
  });

  it("fetchMarketQuote uses authenticated API and caches live quotes", async () => {
    marketQuoteMock.mockResolvedValue({
      ok: true,
      available: true,
      authenticated: true,
      symbol: "MSFT",
      currency: "USD",
      fields: {
        current_price: 100,
        previous_close: 98,
        week_52_high: 120,
        week_52_low: 80,
      },
      provenance: { retrieved_at: "2026-08-08T12:00:00.000Z" },
    });

    const quote = await fetchMarketQuote("MSFT");
    expect(marketQuoteMock).toHaveBeenCalled();
    expect(quote.source).toBe("live");
    expect(quote.currentPrice).toBe(100);

    const fresh = readCachedQuote("MSFT", 60_000, Date.now());
    expect(fresh?.stale).toBe(false);
    expect(fresh?.quote.source).toBe("live");
  });

  it("fetchMarketQuote fails closed when API has no authenticated quote", async () => {
    marketQuoteMock.mockResolvedValue({
      ok: true,
      available: false,
      authenticated: false,
      fields: null,
      message: "Data unavailable.",
    });
    await expect(fetchMarketQuote("ZZZZ")).rejects.toThrow(
      MARKET_DATA_UNAVAILABLE,
    );
  });

  it("never returns a live-labeled seed when API is unavailable", async () => {
    marketQuoteMock.mockResolvedValue({
      ok: true,
      available: false,
      authenticated: false,
      fields: null,
    });
    await expect(fetchMarketQuote("AAPL")).rejects.toThrow(
      MARKET_DATA_UNAVAILABLE,
    );
    // Production path must not fall back to seedQuoteForTicker.
    expect(seedQuoteForTicker("AAPL").source).not.toBe("live");
  });

  it("formats prices and market cap for display", () => {
    expect(formatMarketPrice(123.45, "USD")).toContain("123.45");
    expect(formatMarketCap(2_500_000_000)).toBe("2.50B");
    expect(formatChange(1.2, 0.5)).toContain("+1.20");
  });
});

describe("portfolio market summary", () => {
  it("computes portfolio value from holdings and quotes", () => {
    const holdings = getDemoPortfolio().holdings.slice(0, 2);
    const quotes = Object.fromEntries(
      holdings.map((h) => [h.ticker, seedQuoteForTicker(h.ticker)]),
    );
    const summary = buildPortfolioMarketSummary(holdings, quotes);
    expect(summary.totalValue).toBeGreaterThan(0);
    expect(summary.dayChange).not.toBeNull();
    expect(summary.holdings).toHaveLength(2);
    expect(Object.values(quotes).every((q) => q.source === "offline")).toBe(
      true,
    );
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
