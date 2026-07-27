/** Live market data types — presentation only; never mixed with analysis scores. */

export type MarketDataStatus =
  | "idle"
  | "loading"
  | "success"
  | "stale"
  | "error";

export type MarketQuoteSource = "live" | "cached" | "offline";

export type MarketQuote = {
  ticker: string;
  currency: string;
  currentPrice: number;
  previousClose: number;
  dailyChange: number;
  dailyChangePercent: number;
  marketCap: number | null;
  volume: number | null;
  week52High: number;
  week52Low: number;
  lastUpdated: string;
  source: MarketQuoteSource;
};

export type MarketDataConfig = {
  cacheTtlMs: number;
  autoRefreshMs: number;
};

export const DEFAULT_MARKET_CONFIG: MarketDataConfig = {
  cacheTtlMs: 60_000,
  autoRefreshMs: 60_000,
};

export type PortfolioMarketHolding = {
  ticker: string;
  company: string;
  allocationPercent: number;
  quote: MarketQuote | null;
};

export type PortfolioMarketSummary = {
  totalValue: number | null;
  dayChange: number | null;
  dayChangePercent: number | null;
  lastUpdated: string | null;
  holdings: PortfolioMarketHolding[];
};
