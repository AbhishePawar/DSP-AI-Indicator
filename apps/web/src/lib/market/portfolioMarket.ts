import type { PortfolioHolding } from "@/lib/portfolio/model";
import type { MarketQuote, PortfolioMarketSummary } from "./types";

const BASE_PORTFOLIO_VALUE = 1_245_000;

export function buildPortfolioMarketSummary(
  holdings: PortfolioHolding[],
  quotes: Record<string, MarketQuote | null | undefined>,
): PortfolioMarketSummary {
  if (!holdings.length) {
    return {
      totalValue: null,
      dayChange: null,
      dayChangePercent: null,
      lastUpdated: null,
      holdings: [],
    };
  }

  let totalValue = 0;
  let previousValue = 0;
  let latestUpdated: string | null = null;

  const rows = holdings.map((holding) => {
    const quote = quotes[holding.ticker.toUpperCase()] ?? null;
    const weight = holding.allocationPercent / 100;
    const holdingValue = BASE_PORTFOLIO_VALUE * weight;
    const holdingPrev =
      quote && quote.previousClose > 0
        ? holdingValue * (quote.previousClose / quote.currentPrice)
        : holdingValue;

    totalValue += holdingValue;
    previousValue += holdingPrev;

    if (
      quote &&
      (!latestUpdated || quote.lastUpdated > latestUpdated)
    ) {
      latestUpdated = quote.lastUpdated;
    }

    return {
      ticker: holding.ticker,
      company: holding.company,
      allocationPercent: holding.allocationPercent,
      quote,
    };
  });

  const dayChange = totalValue - previousValue;
  const dayChangePercent =
    previousValue > 0 ? (dayChange / previousValue) * 100 : null;

  return {
    totalValue,
    dayChange,
    dayChangePercent,
    lastUpdated: latestUpdated,
    holdings: rows,
  };
}

export function formatMarketPrice(
  value: number | null | undefined,
  currency = "USD",
): string {
  if (value == null || !Number.isFinite(value)) return "—";
  const locale = currency === "INR" ? "en-IN" : "en-US";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatMarketCap(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  if (value >= 1_000_000_000_000) {
    return `${(value / 1_000_000_000_000).toFixed(2)}T`;
  }
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(2)}B`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M`;
  }
  return value.toLocaleString();
}

export function formatChange(
  value: number | null | undefined,
  percent?: number | null,
): string {
  if (value == null || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : "";
  const pct =
    percent != null && Number.isFinite(percent)
      ? ` (${sign}${percent.toFixed(2)}%)`
      : "";
  return `${sign}${value.toFixed(2)}${pct}`;
}
