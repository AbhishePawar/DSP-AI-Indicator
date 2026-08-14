/**
 * @vitest-environment jsdom
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMock = vi.hoisted(() => ({
  portfolioList: vi.fn(),
  portfolioListHoldings: vi.fn(),
  portfolioListWatchlist: vi.fn(),
  portfolioMigrate: vi.fn(),
  portfolioUpsertHolding: vi.fn(),
  portfolioRemoveHolding: vi.fn(),
  portfolioSetBenchmark: vi.fn(),
  portfolioAddWatchlistSymbol: vi.fn(),
  portfolioRemoveWatchlistSymbol: vi.fn(),
  portfolioRecordTransaction: vi.fn(),
  portfolioListTransactions: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ api: apiMock }));

import {
  addWatchlistSymbol,
  fetchDefaultPortfolio,
  fetchHoldings,
  fetchTransactions,
  fetchWatchlist,
  migrateLocalPortfolio,
  portfolioHoldingToServerPayload,
  recordTransaction,
  removeWatchlistSymbol,
  serverHoldingToPortfolioHolding,
  setPortfolioBenchmark,
  syncHoldings,
} from "./repository";
import type { PortfolioHolding } from "./model";
import type { ServerHolding, ServerPortfolio } from "@/lib/api/client";

function makeServerHolding(overrides: Partial<ServerHolding> = {}): ServerHolding {
  return {
    holding_id: "hld_1",
    portfolio_id: "pf_1",
    symbol: "AAPL",
    weight: 0.5,
    units: null,
    cost_basis_per_unit: null,
    purchase_date: null,
    sector: "Technology",
    country: null,
    exchange: null,
    value_score: null,
    quality_score: null,
    momentum_score: null,
    size_score: null,
    volatility_score: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    ...overrides,
  };
}

function makeServerPortfolio(overrides: Partial<ServerPortfolio> = {}): ServerPortfolio {
  return {
    portfolio_id: "pf_1",
    user_id: "u1",
    org_id: null,
    name: "My Portfolio",
    is_default: true,
    benchmark_symbol: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    metadata: {},
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("server <-> presentation mapping", () => {
  it("maps a server holding into a PortfolioHolding honestly", () => {
    const holding = serverHoldingToPortfolioHolding(makeServerHolding({ weight: 0.6 }));
    expect(holding.ticker).toBe("AAPL");
    expect(holding.allocationPercent).toBe(60);
    expect(holding.sector).toBe("Technology");
    // Never fabricates recommendation/coverage — those are session-only.
    expect(holding.recommendation).toBe("Data unavailable.");
    expect(holding.researchAvailable).toBe(false);
  });

  it("falls back to the ticker as company name when not in the catalogue", () => {
    const holding = serverHoldingToPortfolioHolding(
      makeServerHolding({ symbol: "ZZZZ" }),
    );
    expect(holding.company).toBe("ZZZZ");
  });

  it("maps a PortfolioHolding into the server payload shape", () => {
    const holding: PortfolioHolding = {
      company: "Apple",
      ticker: "AAPL",
      sector: "Technology",
      allocationPercent: 45,
      recommendation: "Buy",
      researchAvailable: true,
    };
    const payload = portfolioHoldingToServerPayload(holding);
    expect(payload).toEqual({ symbol: "AAPL", weight: 0.45, sector: "Technology" });
  });

  it("maps an 'Unknown' sector to null (never fabricated)", () => {
    const holding: PortfolioHolding = {
      company: "Apple",
      ticker: "AAPL",
      sector: "Unknown",
      allocationPercent: 10,
      recommendation: "Data unavailable.",
      researchAvailable: false,
    };
    expect(portfolioHoldingToServerPayload(holding).sector).toBeNull();
  });
});

describe("fetchDefaultPortfolio", () => {
  it("returns the default portfolio when present", async () => {
    apiMock.portfolioList.mockResolvedValue({
      ok: true,
      result: [
        makeServerPortfolio({ portfolio_id: "pf_a", is_default: false }),
        makeServerPortfolio({ portfolio_id: "pf_b", is_default: true }),
      ],
    });
    const result = await fetchDefaultPortfolio("token");
    expect(result?.portfolio_id).toBe("pf_b");
  });

  it("returns null when the user has no portfolios", async () => {
    apiMock.portfolioList.mockResolvedValue({ ok: true, result: [] });
    expect(await fetchDefaultPortfolio("token")).toBeNull();
  });
});

describe("fetchHoldings / fetchWatchlist / fetchTransactions", () => {
  it("maps holdings list", async () => {
    apiMock.portfolioListHoldings.mockResolvedValue({
      ok: true,
      result: [makeServerHolding()],
    });
    const holdings = await fetchHoldings("token", "pf_1");
    expect(holdings).toHaveLength(1);
    expect(holdings[0]?.ticker).toBe("AAPL");
  });

  it("returns an empty array when watchlist is absent", async () => {
    apiMock.portfolioListWatchlist.mockResolvedValue({ ok: true, result: undefined });
    expect(await fetchWatchlist("token", "pf_1")).toEqual([]);
  });

  it("passes through transaction query params", async () => {
    apiMock.portfolioListTransactions.mockResolvedValue({ ok: true, result: [] });
    await fetchTransactions("token", "pf_1", { symbol: "AAPL", limit: 10 });
    expect(apiMock.portfolioListTransactions).toHaveBeenCalledWith(
      "pf_1",
      { symbol: "AAPL", limit: 10 },
      { token: "token" },
    );
  });
});

describe("migrateLocalPortfolio", () => {
  it("sends holdings/watchlist/benchmark and returns the server result", async () => {
    apiMock.portfolioMigrate.mockResolvedValue({
      ok: true,
      result: { migrated: true, portfolio: makeServerPortfolio() },
    });
    const holdings: PortfolioHolding[] = [
      {
        company: "Apple",
        ticker: "AAPL",
        sector: "Technology",
        allocationPercent: 100,
        recommendation: "Data unavailable.",
        researchAvailable: false,
      },
    ];
    const result = await migrateLocalPortfolio("token", {
      name: "My Portfolio",
      holdings,
      benchmarkSymbol: "SPY",
    });
    expect(result.migrated).toBe(true);
    expect(apiMock.portfolioMigrate).toHaveBeenCalledWith(
      {
        name: "My Portfolio",
        holdings: [{ symbol: "AAPL", weight: 1, sector: "Technology" }],
        watchlist: [],
        benchmark_symbol: "SPY",
      },
      { token: "token" },
    );
  });

  it("throws an honest error when the server call fails", async () => {
    apiMock.portfolioMigrate.mockResolvedValue({ ok: false, error: "boom" });
    await expect(
      migrateLocalPortfolio("token", { name: "X", holdings: [] }),
    ).rejects.toThrow("boom");
  });
});

describe("syncHoldings", () => {
  it("upserts current holdings and removes deleted ones", async () => {
    apiMock.portfolioUpsertHolding.mockResolvedValue({ ok: true, result: {} });
    apiMock.portfolioRemoveHolding.mockResolvedValue({ ok: true, result: { removed: true } });

    const holdings: PortfolioHolding[] = [
      {
        company: "Apple",
        ticker: "AAPL",
        sector: "Technology",
        allocationPercent: 50,
        recommendation: "Data unavailable.",
        researchAvailable: false,
      },
    ];
    await syncHoldings("token", "pf_1", holdings, ["AAPL", "MSFT"]);

    expect(apiMock.portfolioUpsertHolding).toHaveBeenCalledWith(
      "pf_1",
      { symbol: "AAPL", weight: 0.5, sector: "Technology" },
      { token: "token" },
    );
    expect(apiMock.portfolioRemoveHolding).toHaveBeenCalledWith(
      "pf_1",
      "MSFT",
      { token: "token" },
    );
    // AAPL was retained, not removed.
    expect(apiMock.portfolioRemoveHolding).not.toHaveBeenCalledWith(
      "pf_1",
      "AAPL",
      { token: "token" },
    );
  });
});

describe("benchmark + watchlist repository calls", () => {
  it("setPortfolioBenchmark returns the updated portfolio", async () => {
    apiMock.portfolioSetBenchmark.mockResolvedValue({
      ok: true,
      result: makeServerPortfolio({ benchmark_symbol: "QQQ" }),
    });
    const result = await setPortfolioBenchmark("token", "pf_1", "QQQ");
    expect(result.benchmark_symbol).toBe("QQQ");
  });

  it("setPortfolioBenchmark throws on failure", async () => {
    apiMock.portfolioSetBenchmark.mockResolvedValue({ ok: false, error: "nope" });
    await expect(setPortfolioBenchmark("token", "pf_1", "QQQ")).rejects.toThrow("nope");
  });

  it("addWatchlistSymbol / removeWatchlistSymbol delegate correctly", async () => {
    apiMock.portfolioAddWatchlistSymbol.mockResolvedValue({
      ok: true,
      result: {
        item_id: "wl_1",
        portfolio_id: "pf_1",
        symbol: "NVDA",
        label: null,
        added_at: "2024-01-01T00:00:00Z",
      },
    });
    apiMock.portfolioRemoveWatchlistSymbol.mockResolvedValue({
      ok: true,
      result: { removed: true },
    });
    const added = await addWatchlistSymbol("token", "pf_1", "NVDA");
    expect(added.symbol).toBe("NVDA");
    expect(await removeWatchlistSymbol("token", "pf_1", "NVDA")).toBe(true);
  });
});

describe("recordTransaction", () => {
  it("returns the recorded transaction", async () => {
    apiMock.portfolioRecordTransaction.mockResolvedValue({
      ok: true,
      result: {
        transaction_id: "txn_1",
        portfolio_id: "pf_1",
        transaction_type: "buy",
        transaction_date: "2024-01-01",
        symbol: "AAPL",
        quantity: 10,
        price: 150,
        amount: null,
        currency: "USD",
        notes: null,
        created_at: "2024-01-01T00:00:00Z",
      },
    });
    const txn = await recordTransaction("token", "pf_1", {
      transaction_type: "buy",
      transaction_date: "2024-01-01",
      symbol: "AAPL",
      quantity: 10,
      price: 150,
    });
    expect(txn.transaction_type).toBe("buy");
  });

  it("throws an honest error when recording fails", async () => {
    apiMock.portfolioRecordTransaction.mockResolvedValue({ ok: false, error: "invalid" });
    await expect(
      recordTransaction("token", "pf_1", {
        transaction_type: "buy",
        transaction_date: "2024-01-01",
      }),
    ).rejects.toThrow("invalid");
  });
});
