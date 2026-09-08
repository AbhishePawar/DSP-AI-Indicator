/**
 * GA4 typed event helpers for DSP AI Indicator key user flows.
 *
 * All events are no-ops in development or when GA is not configured.
 * Import `trackEvent` from GoogleAnalytics for raw calls, or use these
 * typed helpers for structured, consistent event naming.
 */

import { trackEvent } from "@/components/analytics/GoogleAnalytics";

// ── Ticker Search ─────────────────────────────────────────────────────────────

/** Fired when the user submits a ticker/company search from the dashboard. */
export function trackTickerSearch(params: {
  query: string;
  symbol?: string;
  source: "dashboard" | "analysis_form" | "batch";
}): void {
  trackEvent("ticker_search", {
    search_query: params.query,
    resolved_symbol: params.symbol ?? null,
    search_source: params.source,
  });
}

/** Fired when the user selects a result from the search dropdown. */
export function trackSearchResultSelected(params: {
  symbol: string;
  company_name?: string | null;
  exchange?: string;
  confirmed_by_backend: boolean;
}): void {
  trackEvent("search_result_selected", {
    symbol: params.symbol,
    company_name: params.company_name ?? null,
    exchange: params.exchange ?? null,
    confirmed_by_backend: params.confirmed_by_backend,
  });
}

// ── Company Research View ─────────────────────────────────────────────────────

/** Fired when a company analysis is successfully loaded/rendered. */
export function trackCompanyResearchView(params: {
  symbol: string;
  source: "search" | "direct_url" | "recent" | "batch";
}): void {
  trackEvent("company_research_view", {
    symbol: params.symbol,
    research_source: params.source,
  });
}

/** Fired when the user submits the analysis form (API call initiated). */
export function trackAnalysisStarted(params: {
  symbol: string;
  date_range_days?: number;
}): void {
  trackEvent("analysis_started", {
    symbol: params.symbol,
    date_range_days: params.date_range_days ?? null,
  });
}

/** Fired when a batch analysis run is initiated. */
export function trackBatchAnalysisStarted(params: {
  ticker_count: number;
}): void {
  trackEvent("batch_analysis_started", {
    ticker_count: params.ticker_count,
  });
}

// ── Watchlist Operations ──────────────────────────────────────────────────────

/** Fired when a new watchlist is created. */
export function trackWatchlistCreated(params: {
  watchlist_name: string;
}): void {
  trackEvent("watchlist_created", {
    watchlist_name: params.watchlist_name,
  });
}

/** Fired when a ticker is added to a watchlist. */
export function trackWatchlistTickerAdded(params: {
  watchlist_id: string;
  ticker: string;
}): void {
  trackEvent("watchlist_ticker_added", {
    watchlist_id: params.watchlist_id,
    ticker: params.ticker,
  });
}

/** Fired when a ticker is removed from a watchlist. */
export function trackWatchlistTickerRemoved(params: {
  watchlist_id: string;
  ticker: string;
}): void {
  trackEvent("watchlist_ticker_removed", {
    watchlist_id: params.watchlist_id,
    ticker: params.ticker,
  });
}

/** Fired when a watchlist is deleted. */
export function trackWatchlistDeleted(params: {
  watchlist_id: string;
}): void {
  trackEvent("watchlist_deleted", {
    watchlist_id: params.watchlist_id,
  });
}

// ── Account Settings ──────────────────────────────────────────────────────────

/** Fired when the user saves account settings changes. */
export function trackAccountSettingsSaved(params: {
  changed_fields: string[];
}): void {
  trackEvent("account_settings_saved", {
    changed_fields: params.changed_fields.join(","),
    changed_field_count: params.changed_fields.length,
  });
}
