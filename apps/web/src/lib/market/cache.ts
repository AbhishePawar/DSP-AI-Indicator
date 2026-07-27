import type { MarketQuote } from "./types";

type CacheEntry = {
  quote: MarketQuote;
  fetchedAt: number;
};

const cache = new Map<string, CacheEntry>();

export function cacheKey(ticker: string): string {
  return ticker.trim().toUpperCase();
}

export function readCachedQuote(
  ticker: string,
  ttlMs: number,
  now = Date.now(),
): { quote: MarketQuote; stale: boolean } | null {
  const entry = cache.get(cacheKey(ticker));
  if (!entry) return null;
  const age = now - entry.fetchedAt;
  if (age > ttlMs * 2) {
    cache.delete(cacheKey(ticker));
    return null;
  }
  return {
    quote: { ...entry.quote, source: age > ttlMs ? "cached" : entry.quote.source },
    stale: age > ttlMs,
  };
}

export function writeCachedQuote(quote: MarketQuote): void {
  cache.set(cacheKey(quote.ticker), {
    quote: { ...quote },
    fetchedAt: Date.now(),
  });
}

export function clearMarketCache(ticker?: string): void {
  if (ticker) {
    cache.delete(cacheKey(ticker));
    return;
  }
  cache.clear();
}

export function listCachedTickers(): string[] {
  return [...cache.keys()];
}

/** Test helper */
export function _resetMarketCache(): void {
  cache.clear();
}
