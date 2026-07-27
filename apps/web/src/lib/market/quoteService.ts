import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import type { MarketQuote } from "./types";
import { writeCachedQuote } from "./cache";

function hashTicker(ticker: string): number {
  const normalized = ticker.trim().toUpperCase();
  let hash = 0;
  for (let i = 0; i < normalized.length; i += 1) {
    hash = (hash * 31 + normalized.charCodeAt(i)) >>> 0;
  }
  return hash;
}

/** Deterministic base price for catalogue tickers — stable for tests and offline demo. */
export function seedQuoteForTicker(ticker: string): MarketQuote {
  const normalized = ticker.trim().toUpperCase();
  const catalogue = COMPANY_CATALOGUE.find(
    (c) => c.ticker.toUpperCase() === normalized,
  );
  const hash = hashTicker(normalized);
  const base = 40 + (hash % 460);
  const previousClose = Number((base * 0.985).toFixed(2));
  const currentPrice = Number((base * (1 + ((hash % 7) - 3) / 1000)).toFixed(2));
  const dailyChange = Number((currentPrice - previousClose).toFixed(2));
  const dailyChangePercent = Number(
    ((dailyChange / previousClose) * 100).toFixed(2),
  );
  const marketCapBillions =
    catalogue?.marketCapBucket === "large"
      ? 200 + (hash % 2800)
      : catalogue?.marketCapBucket === "mid"
        ? 20 + (hash % 180)
        : 2 + (hash % 18);

  const now = new Date().toISOString();
  return {
    ticker: normalized,
    currency: catalogue?.exchange === "NSE" ? "INR" : "USD",
    currentPrice,
    previousClose,
    dailyChange,
    dailyChangePercent,
    marketCap: marketCapBillions * 1_000_000_000,
    volume: 500_000 + (hash % 50_000_000),
    week52High: Number((currentPrice * 1.28).toFixed(2)),
    week52Low: Number((currentPrice * 0.72).toFixed(2)),
    lastUpdated: now,
    source: "live",
  };
}

/**
 * Fetch a market quote. Uses separated frontend provider until a dedicated
 * `/market/quote` API is available — does not touch /analyse contracts.
 */
export async function fetchMarketQuote(ticker: string): Promise<MarketQuote> {
  const normalized = ticker.trim().toUpperCase();
  if (!normalized) {
    throw new Error("Ticker is required");
  }

  // Simulated network latency for refresh UX.
  await new Promise((resolve) => setTimeout(resolve, 120));

  const quote = seedQuoteForTicker(normalized);
  writeCachedQuote(quote);
  return quote;
}

export async function fetchMarketQuotes(
  tickers: string[],
): Promise<Record<string, MarketQuote>> {
  const unique = [
    ...new Set(tickers.map((t) => t.trim().toUpperCase()).filter(Boolean)),
  ];
  const entries = await Promise.all(
    unique.map(async (ticker) => [ticker, await fetchMarketQuote(ticker)] as const),
  );
  return Object.fromEntries(entries);
}
