"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { env } from "@/lib/env";
import {
  DEFAULT_MARKET_CONFIG,
  fetchMarketQuote,
  fetchMarketQuotes,
  readCachedQuote,
  type MarketDataConfig,
  type MarketDataStatus,
  type MarketQuote,
} from "@/lib/market";

type MarketDataContextValue = {
  config: MarketDataConfig;
  refreshTicker: (ticker: string) => Promise<void>;
  refreshTickers: (tickers: string[]) => Promise<void>;
};

const MarketDataContext = createContext<MarketDataContextValue | null>(null);

function statusFromQuery(
  isLoading: boolean,
  isError: boolean,
  stale: boolean,
  hasData: boolean,
): MarketDataStatus {
  if (isLoading) return "loading";
  if (isError) return "error";
  if (stale && hasData) return "stale";
  if (hasData) return "success";
  return "idle";
}

export function MarketDataProvider({
  children,
  config = DEFAULT_MARKET_CONFIG,
}: {
  children: ReactNode;
  config?: MarketDataConfig;
}) {
  const queryClient = useQueryClient();

  const refreshTicker = useCallback(
    async (ticker: string) => {
      await queryClient.fetchQuery({
        queryKey: ["market", "quote", ticker.toUpperCase()],
        queryFn: () => fetchMarketQuote(ticker),
      });
    },
    [queryClient],
  );

  const refreshTickers = useCallback(
    async (tickers: string[]) => {
      const quotes = await fetchMarketQuotes(tickers);
      for (const [ticker, quote] of Object.entries(quotes)) {
        queryClient.setQueryData(["market", "quote", ticker], quote);
      }
    },
    [queryClient],
  );

  const value = useMemo(
    () => ({ config, refreshTicker, refreshTickers }),
    [config, refreshTicker, refreshTickers],
  );

  return (
    <MarketDataContext.Provider value={value}>
      {children}
    </MarketDataContext.Provider>
  );
}

export function useMarketDataContext(): MarketDataContextValue {
  const ctx = useContext(MarketDataContext);
  if (!ctx) {
    throw new Error("useMarketDataContext must be used within MarketDataProvider");
  }
  return ctx;
}

export function useMarketQuote(ticker: string | null | undefined) {
  const normalized = ticker?.trim().toUpperCase() ?? "";
  const { config, refreshTicker } = useMarketDataContext();
  const cached = normalized
    ? readCachedQuote(normalized, config.cacheTtlMs)
    : null;

  const query = useQuery({
    queryKey: ["market", "quote", normalized],
    queryFn: () => fetchMarketQuote(normalized),
    enabled: Boolean(normalized),
    staleTime: config.cacheTtlMs,
    refetchInterval: config.autoRefreshMs,
    initialData: cached?.quote,
    initialDataUpdatedAt: cached ? Date.now() - (cached.stale ? config.cacheTtlMs + 1 : 0) : undefined,
  });

  const status = statusFromQuery(
    query.isLoading,
    query.isError,
    query.isStale,
    Boolean(query.data),
  );

  return {
    quote: (query.data as MarketQuote | undefined) ?? null,
    status,
    error: query.error instanceof Error ? query.error.message : null,
    refresh: () => refreshTicker(normalized),
    isRefreshing: query.isFetching,
  };
}

export function useMarketQuotes(tickers: string[]) {
  const normalized = useMemo(
    () => [
      ...new Set(tickers.map((t) => t.trim().toUpperCase()).filter(Boolean)),
    ],
    [tickers],
  );
  const { config, refreshTickers } = useMarketDataContext();

  const query = useQuery({
    queryKey: ["market", "quotes", normalized.join(",")],
    queryFn: () => fetchMarketQuotes(normalized),
    enabled: normalized.length > 0,
    staleTime: config.cacheTtlMs,
    refetchInterval: config.autoRefreshMs,
  });

  const quotes = (query.data as Record<string, MarketQuote> | undefined) ?? {};
  const status = statusFromQuery(
    query.isLoading,
    query.isError,
    query.isStale,
    Object.keys(quotes).length > 0,
  );

  return {
    quotes,
    status,
    error: query.error instanceof Error ? query.error.message : null,
    refresh: () => refreshTickers(normalized),
    isRefreshing: query.isFetching,
    lastUpdated: Object.values(quotes)[0]?.lastUpdated ?? null,
  };
}

export function getMarketRefreshLabel(config: MarketDataConfig): string {
  const seconds = Math.round(config.autoRefreshMs / 1000);
  return `Auto-refresh every ${seconds}s · ${env.appName} market layer`;
}
