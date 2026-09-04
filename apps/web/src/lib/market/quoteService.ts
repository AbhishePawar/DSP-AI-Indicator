/**
 * Market quote loading for the thin client.
 *
 * P0-03 — Production never fabricates prices or labels hash seeds as "live".
 * Authenticated GET /api/v1/market/quote is the only production source.
 */

import { api } from "@/lib/api/client";
import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import { quoteCurrencyForExchange } from "@/lib/companies/listingSelection";
import type { MarketQuotePayload } from "@/lib/institutional-dashboard/mapInstitutionalDashboard";
import { writeCachedQuote } from "./cache";
import type { MarketQuote } from "./types";

export const MARKET_DATA_UNAVAILABLE = "Data unavailable.";

function hashTicker(ticker: string): number {
  const normalized = ticker.trim().toUpperCase();
  let hash = 0;
  for (let i = 0; i < normalized.length; i += 1) {
    hash = (hash * 31 + normalized.charCodeAt(i)) >>> 0;
  }
  return hash;
}

/**
 * Deterministic offline/demo fixture for tests only.
 *
 * P0-03 — Must not be used by production fetch paths, and must never claim
 * ``source: "live"``.
 */
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
    currency: quoteCurrencyForExchange(catalogue?.exchange),
    currentPrice,
    previousClose,
    dailyChange,
    dailyChangePercent,
    marketCap: marketCapBillions * 1_000_000_000,
    volume: 500_000 + (hash % 50_000_000),
    week52High: Number((currentPrice * 1.28).toFixed(2)),
    week52Low: Number((currentPrice * 0.72).toFixed(2)),
    lastUpdated: now,
    source: "offline",
  };
}

/** Map authenticated API payload → presentation quote; null when unavailable. */
export function marketQuoteFromAuthenticated(
  payload: MarketQuotePayload | null | undefined,
): MarketQuote | null {
  if (!payload?.available || !payload.authenticated || !payload.fields) {
    return null;
  }
  const currentPrice = payload.fields.current_price;
  if (currentPrice == null || !Number.isFinite(currentPrice)) {
    return null;
  }
  const previousClose =
    payload.fields.previous_close != null &&
    Number.isFinite(payload.fields.previous_close)
      ? Number(payload.fields.previous_close)
      : currentPrice;
  const dailyChange = Number((currentPrice - previousClose).toFixed(2));
  const dailyChangePercent =
    previousClose > 0
      ? Number(((dailyChange / previousClose) * 100).toFixed(2))
      : 0;
  const week52High =
    payload.fields.week_52_high != null &&
    Number.isFinite(payload.fields.week_52_high)
      ? Number(payload.fields.week_52_high)
      : null;
  const week52Low =
    payload.fields.week_52_low != null &&
    Number.isFinite(payload.fields.week_52_low)
      ? Number(payload.fields.week_52_low)
      : null;

  const retrievedAt =
    payload.provenance?.retrieved_at || payload.provenance?.as_of || null;
  if (!retrievedAt) {
    // Fail closed — do not invent timestamps (CV-001).
    return null;
  }
  const currency = (payload.currency || "").trim();
  if (!currency) {
    return null;
  }

  return {
    ticker: (payload.symbol || "").trim().toUpperCase(),
    currency,
    currentPrice: Number(currentPrice),
    previousClose,
    dailyChange,
    dailyChangePercent,
    marketCap:
      payload.fields.market_cap != null &&
      Number.isFinite(payload.fields.market_cap)
        ? Number(payload.fields.market_cap)
        : null,
    volume:
      payload.fields.volume != null && Number.isFinite(payload.fields.volume)
        ? Number(payload.fields.volume)
        : null,
    // Missing range stays unavailable — never clone currentPrice as 52w band.
    week52High,
    week52Low,
    lastUpdated: retrievedAt,
    // Authenticated provider response only — never a client-side seed.
    source: "live",
  };
}

/**
 * Fetch a market quote from authenticated GET /api/v1/market/quote.
 * Fails closed with {@link MARKET_DATA_UNAVAILABLE} — never fabricates.
 */
export async function fetchMarketQuote(ticker: string): Promise<MarketQuote> {
  const normalized = ticker.trim().toUpperCase();
  if (!normalized) {
    throw new Error("Ticker is required");
  }

  let payload: MarketQuotePayload;
  try {
    payload = await api.marketQuote(normalized);
  } catch {
    throw new Error(MARKET_DATA_UNAVAILABLE);
  }

  const quote = marketQuoteFromAuthenticated(payload);
  if (!quote || !quote.ticker) {
    throw new Error(payload?.message || MARKET_DATA_UNAVAILABLE);
  }

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
    unique.map(async (ticker) => {
      try {
        return [ticker, await fetchMarketQuote(ticker)] as const;
      } catch {
        return null;
      }
    }),
  );
  return Object.fromEntries(
    entries.filter((entry): entry is readonly [string, MarketQuote] => entry != null),
  );
}
