/**
 * Figma `Dashboard.tsx` view-model.
 *
 * Every figure comes from an authenticated `/api/v1` response or from the
 * browser session's real `/api/v1/analyse` results. Nothing is computed:
 * price, change and change % are provider-reported quote fields; the DSP
 * rating is the recommendation returned by the engine for that company.
 */

import type { RecentAnalysisEntry } from "@/lib/analysis/recentAnalyses";
import type {
  CoverageSignal,
  MarketIndicesResponse,
  RecentResearchItem,
  WatchlistItem,
} from "@/lib/api/workspaceTypes";
import type { ArchivedResearchSession } from "@/lib/copilot/sessionArchive";
import type { MarketQuotePayload } from "@/lib/institutional-dashboard/mapInstitutionalDashboard";
import { mapAnalyseResponse } from "@/lib/intelligence/mapResponse";
import type { PortfolioHolding } from "@/lib/portfolio/model";

export const WATCHLIST_MAX = 8;

export type WatchlistSymbol = {
  symbol: string;
  name: string | null;
  exchange: string | null;
  /** Where the symbol came from — shown as provenance, never as a rating. */
  origin: "watchlist" | "research" | "portfolio";
};

export type WatchlistRow = WatchlistSymbol & {
  price: string;
  change: string;
  /** Provider-reported direction; null when no change field was returned. */
  direction: "up" | "down" | "flat" | null;
  rating: string;
  quoteStatus: "loading" | "available" | "unavailable" | "unauthenticated";
};

export type RecentResearchRow = {
  symbol: string;
  company: string;
  recommendation: string;
  analysedAt: string;
  title?: string | null;
  tags?: string[];
  href?: string | null;
};

export type MarketBarCard = {
  label: string;
  /** Provider-reported index level, formatted; "Data unavailable." when absent. */
  value: string;
  /** Provider-reported day change ("+0.4%"); null when absent. */
  change: string | null;
  direction: "up" | "down" | "flat" | null;
  /** Provider close series (oldest → newest); empty when absent. */
  sparkline: number[];
  available: boolean;
  note: string | null;
};

/** Figma market bar labels — catalogue order is fixed by the server contract. */
export const MARKET_BAR_LABELS = ["NIFTY 50", "SENSEX", "NIFTY IT", "NIFTY BANK"] as const;

/** Loading / no-response state: four honest placeholders in Figma order. */
export const MARKET_BAR_PLACEHOLDERS: readonly MarketBarCard[] = MARKET_BAR_LABELS.map((label) => ({
  label,
  value: "Data unavailable.",
  change: null,
  direction: null,
  sparkline: [],
  available: false,
  note: null,
}));

/** GET /api/v1/market/indices → Figma market cards. Values are copied, never derived. */
export function mapMarketIndices(
  response: MarketIndicesResponse | null | undefined,
): MarketBarCard[] {
  const indices = response?.indices ?? [];
  if (indices.length === 0) return [...MARKET_BAR_PLACEHOLDERS];
  return indices.map((idx) => {
    const available = Boolean(idx.available && typeof idx.value === "number");
    const change = formatQuoteChange({ change: idx.change, change_percent: idx.change_percent });
    return {
      label: idx.label,
      value: available
        ? (idx.value as number).toLocaleString(undefined, { maximumFractionDigits: 2 })
        : "Data unavailable.",
      change: available && change.direction !== null ? change.text : null,
      direction: available ? change.direction : null,
      sparkline: available ? idx.sparkline.filter((v) => Number.isFinite(v)) : [],
      available,
      note: available ? null : response?.capability === "INVESTMENT_DATA_UNAVAILABLE"
        ? "No approved index feed configured"
        : "Index feed unavailable",
    };
  });
}

export type SignalRow = {
  id: string;
  symbol: string;
  label: string;
  /** Figma dot colour token by signal type. */
  color: "var(--c-profit)" | "var(--c-risk)" | "var(--c-valuation)";
  from: string | null;
  to: string | null;
  timestamp: string;
};

/** Server rating-change / risk / valuation signals → Figma DSP Signals rows. */
export function mapSignals(signals: readonly CoverageSignal[] | null | undefined, max = 6): SignalRow[] {
  return (signals ?? []).slice(0, max).map((s) => ({
    id: s.signal_id,
    symbol: s.symbol,
    label: s.label,
    color:
      s.type === "upgrade"
        ? "var(--c-profit)"
        : s.type === "valuation"
          ? "var(--c-valuation)"
          : "var(--c-risk)",
    from: s.from_rating ?? null,
    to: s.to_rating ?? null,
    timestamp: s.timestamp,
  }));
}

/** Server watchlist item (quote + coverage rating joined server-side) → row. */
export function mapServerWatchlistRow(item: WatchlistItem): WatchlistRow {
  const change = formatQuoteChange({
    change: item.quote.change,
    change_percent: item.quote.change_percent,
  });
  return {
    symbol: item.symbol,
    name: item.company_name,
    exchange: item.exchange,
    origin: item.origin === "research" ? "research" : "watchlist",
    price: formatPrice(item.quote.price, item.quote.currency),
    change: change.text,
    direction: change.direction,
    rating: item.rating ?? "—",
    quoteStatus: item.quote.available ? "available" : "unavailable",
  };
}

/** Server recent research (owner-scoped coverage records) → rows. */
export function mapServerRecentResearch(
  items: readonly RecentResearchItem[] | null | undefined,
  max = 6,
): RecentResearchRow[] {
  return (items ?? []).slice(0, max).map((r) => ({
    symbol: r.symbol.toUpperCase(),
    company: r.company_name || r.symbol.toUpperCase(),
    recommendation: r.rating ?? r.recommendation ?? "—",
    analysedAt: r.timestamp,
    title: r.title ?? null,
    tags: r.tags ?? [],
    href: r.href ?? null,
  }));
}

/** Session companies (analysed or held) become the watchlist — no seeded tickers. */
export function buildWatchlistSymbols(
  sessions: readonly ArchivedResearchSession[],
  holdings: readonly PortfolioHolding[],
  max = WATCHLIST_MAX,
): WatchlistSymbol[] {
  const seen = new Set<string>();
  const out: WatchlistSymbol[] = [];
  for (const s of sessions) {
    const symbol = s.ticker.trim().toUpperCase();
    if (!symbol || seen.has(symbol)) continue;
    seen.add(symbol);
    out.push({ symbol, name: s.company, exchange: s.exchange, origin: "research" });
  }
  for (const h of holdings) {
    const symbol = h.ticker.trim().toUpperCase();
    if (!symbol || seen.has(symbol)) continue;
    seen.add(symbol);
    out.push({ symbol, name: h.company || null, exchange: null, origin: "portfolio" });
  }
  return out.slice(0, max);
}

/** Engine recommendation for a session company, or "—" when never analysed. */
export function ratingForSymbol(
  symbol: string,
  sessions: readonly ArchivedResearchSession[],
): string {
  const match = sessions.find(
    (s) => s.ticker.trim().toUpperCase() === symbol.trim().toUpperCase(),
  );
  if (!match) return "—";
  const rec = mapAnalyseResponse(match.response).recommendation;
  return rec && rec !== "—" ? rec : "—";
}

function formatPrice(value: number | null | undefined, currency: string | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Data unavailable.";
  const code = currency?.trim().toUpperCase();
  if (code && /^[A-Z]{3}$/.test(code)) {
    try {
      return value.toLocaleString(undefined, {
        style: "currency",
        currency: code,
        maximumFractionDigits: 2,
      });
    } catch {
      /* unknown code → bare number */
    }
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

/** Provider-reported change only. Never derived from price − previous close. */
export function formatQuoteChange(
  fields:
    | Pick<NonNullable<MarketQuotePayload["fields"]>, "change" | "change_percent">
    | { change?: number | null; change_percent?: number | null }
    | null
    | undefined,
): { text: string; direction: WatchlistRow["direction"] } {
  const pct = fields?.change_percent;
  const abs = fields?.change;
  if (typeof pct === "number" && Number.isFinite(pct)) {
    const sign = pct > 0 ? "+" : "";
    return {
      text: `${sign}${pct.toLocaleString(undefined, { maximumFractionDigits: 2 })}%`,
      direction: pct > 0 ? "up" : pct < 0 ? "down" : "flat",
    };
  }
  if (typeof abs === "number" && Number.isFinite(abs)) {
    const sign = abs > 0 ? "+" : "";
    return {
      text: `${sign}${abs.toLocaleString(undefined, { maximumFractionDigits: 2 })}`,
      direction: abs > 0 ? "up" : abs < 0 ? "down" : "flat",
    };
  }
  return { text: "Data unavailable.", direction: null };
}

export function mapWatchlistRow(
  symbol: WatchlistSymbol,
  quote: MarketQuotePayload | null | undefined,
  status: WatchlistRow["quoteStatus"],
  sessions: readonly ArchivedResearchSession[],
): WatchlistRow {
  const available = Boolean(quote?.available !== false && quote?.fields);
  const fields = available ? quote?.fields : null;
  const change = formatQuoteChange(fields);
  return {
    ...symbol,
    price: formatPrice(fields?.current_price, quote?.currency),
    change: change.text,
    direction: change.direction,
    rating: ratingForSymbol(symbol.symbol, sessions),
    quoteStatus:
      status === "loading" ? "loading" : available ? "available" : status,
  };
}

export function mapRecentResearch(
  entries: readonly RecentAnalysisEntry[],
  max = 6,
): RecentResearchRow[] {
  return entries.slice(0, max).map((e) => ({
    symbol: e.ticker.toUpperCase(),
    company: e.company || e.ticker.toUpperCase(),
    recommendation: e.recommendation || "—",
    analysedAt: e.analysedAt,
    title: `${e.company || e.ticker.toUpperCase()} — Company Analysis`,
    tags: e.recommendation ? [e.recommendation] : [],
    href: `/analysis?symbol=${e.ticker.toUpperCase()}`,
  }));
}

/** Relative "2 hr ago" label — presentation only. */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "—";
  const diffMs = Math.max(0, now.getTime() - then);
  const min = Math.round(diffMs / 60_000);
  if (min < 1) return "Just now";
  if (min < 60) return `${min} min ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr} hr ago`;
  const day = Math.round(hr / 24);
  if (day === 1) return "Yesterday";
  return `${day} days ago`;
}
