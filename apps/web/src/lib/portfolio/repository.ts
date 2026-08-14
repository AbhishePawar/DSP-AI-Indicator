/**
 * Portfolio Store repository (RC1 Milestone 3) — Repository -> API -> React
 * Query -> Workspace. Pure mapping/fetch functions only; no React state
 * here (see `usePortfolioRepository.ts` for the hook layer). This is the
 * only module that knows about the server DTOs (`ServerHolding`, etc.) —
 * everything above it keeps using the existing `PortfolioHolding` /
 * `WatchlistEntry` presentation shapes, unchanged.
 */

import {
  api,
  type RequestOptions,
  type ServerHolding,
  type ServerPortfolio,
  type ServerTransaction,
  type ServerWatchlistItem,
} from "@/lib/api/client";
import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import type { PortfolioHolding } from "@/lib/portfolio/model";

export type { ServerHolding, ServerPortfolio, ServerTransaction, ServerWatchlistItem };

function companyNameFor(ticker: string): string {
  const match = COMPANY_CATALOGUE.find((c) => c.ticker === ticker);
  return match?.name ?? ticker;
}

/** Server -> presentation. Never fabricates a recommendation/coverage flag —
 * those live only in session state today, so they default honestly. */
export function serverHoldingToPortfolioHolding(row: ServerHolding): PortfolioHolding {
  return {
    company: companyNameFor(row.symbol),
    ticker: row.symbol,
    sector: row.sector || "Unknown",
    allocationPercent: Math.round(row.weight * 1000) / 10,
    recommendation: "Data unavailable.",
    researchAvailable: false,
  };
}

/** Presentation -> server. `weight` is a 0..1 fraction (server contract). */
export function portfolioHoldingToServerPayload(holding: PortfolioHolding) {
  return {
    symbol: holding.ticker,
    weight: holding.allocationPercent / 100,
    sector: holding.sector === "Unknown" ? null : holding.sector,
  };
}

export type PortfolioRepositoryToken = string | null | undefined;

function opts(token: PortfolioRepositoryToken): RequestOptions {
  return { token };
}

/** Fetch the user's default portfolio, or `null` if they have none yet. */
export async function fetchDefaultPortfolio(
  token: PortfolioRepositoryToken,
): Promise<ServerPortfolio | null> {
  const response = await api.portfolioList(opts(token));
  const rows = response.result ?? [];
  return rows.find((p) => p.is_default) ?? rows[0] ?? null;
}

export async function fetchHoldings(
  token: PortfolioRepositoryToken,
  portfolioId: string,
): Promise<PortfolioHolding[]> {
  const response = await api.portfolioListHoldings(portfolioId, opts(token));
  return (response.result ?? []).map(serverHoldingToPortfolioHolding);
}

export async function fetchWatchlist(
  token: PortfolioRepositoryToken,
  portfolioId: string,
): Promise<ServerWatchlistItem[]> {
  const response = await api.portfolioListWatchlist(portfolioId, opts(token));
  return response.result ?? [];
}

/**
 * Migration strategy (RC1 Milestone 3): call unconditionally on first
 * authenticated load when no server portfolio exists yet. The backend is
 * idempotent — a retry after a server default already exists is a no-op
 * (`migrated: false`) and never overwrites server data. The caller's local
 * snapshot is never deleted by this call, regardless of the outcome.
 */
export async function migrateLocalPortfolio(
  token: PortfolioRepositoryToken,
  input: {
    name: string;
    holdings: PortfolioHolding[];
    watchlist?: Array<{ symbol: string; label?: string | null }>;
    benchmarkSymbol?: string | null;
  },
): Promise<{ migrated: boolean; portfolio: ServerPortfolio }> {
  const response = await api.portfolioMigrate(
    {
      name: input.name,
      holdings: input.holdings.map(portfolioHoldingToServerPayload),
      watchlist: input.watchlist ?? [],
      benchmark_symbol: input.benchmarkSymbol ?? null,
    },
    opts(token),
  );
  if (!response.ok || !response.result) {
    throw new Error(response.error || "Portfolio migration failed.");
  }
  return response.result;
}

/**
 * Reconcile the full holdings list with the server (upsert changed/added,
 * remove missing) — the server API is per-symbol, so this diffs against
 * the previously-known server state rather than requiring a bulk endpoint.
 */
export async function syncHoldings(
  token: PortfolioRepositoryToken,
  portfolioId: string,
  nextHoldings: PortfolioHolding[],
  previousServerSymbols: readonly string[],
): Promise<void> {
  const nextSymbols = new Set(nextHoldings.map((h) => h.ticker));
  const removed = previousServerSymbols.filter((s) => !nextSymbols.has(s));
  await Promise.all([
    ...nextHoldings.map((holding) =>
      api.portfolioUpsertHolding(
        portfolioId,
        portfolioHoldingToServerPayload(holding),
        opts(token),
      ),
    ),
    ...removed.map((symbol) =>
      api.portfolioRemoveHolding(portfolioId, symbol, opts(token)),
    ),
  ]);
}

export async function setPortfolioBenchmark(
  token: PortfolioRepositoryToken,
  portfolioId: string,
  benchmarkSymbol: string | null,
): Promise<ServerPortfolio> {
  const response = await api.portfolioSetBenchmark(
    portfolioId,
    benchmarkSymbol,
    opts(token),
  );
  if (!response.ok || !response.result) {
    throw new Error(response.error || "Failed to update benchmark.");
  }
  return response.result;
}

export async function addWatchlistSymbol(
  token: PortfolioRepositoryToken,
  portfolioId: string,
  symbol: string,
  label?: string | null,
): Promise<ServerWatchlistItem> {
  const response = await api.portfolioAddWatchlistSymbol(
    portfolioId,
    { symbol, label },
    opts(token),
  );
  if (!response.ok || !response.result) {
    throw new Error(response.error || "Failed to add watchlist symbol.");
  }
  return response.result;
}

export async function removeWatchlistSymbol(
  token: PortfolioRepositoryToken,
  portfolioId: string,
  symbol: string,
): Promise<boolean> {
  const response = await api.portfolioRemoveWatchlistSymbol(
    portfolioId,
    symbol,
    opts(token),
  );
  return response.result?.removed ?? false;
}

export async function recordTransaction(
  token: PortfolioRepositoryToken,
  portfolioId: string,
  input: {
    transaction_type: string;
    transaction_date: string;
    symbol?: string | null;
    quantity?: number | null;
    price?: number | null;
    amount?: number | null;
    currency?: string;
    notes?: string | null;
  },
): Promise<ServerTransaction> {
  const response = await api.portfolioRecordTransaction(portfolioId, input, opts(token));
  if (!response.ok || !response.result) {
    throw new Error(response.error || "Failed to record transaction.");
  }
  return response.result;
}

export async function fetchTransactions(
  token: PortfolioRepositoryToken,
  portfolioId: string,
  params?: { symbol?: string; limit?: number },
): Promise<ServerTransaction[]> {
  const response = await api.portfolioListTransactions(portfolioId, params, opts(token));
  return response.result ?? [];
}
