/** HTTP client for `/api/v1` only — no DSP Platform imports. */

import { env } from "@/lib/env";
import type {
  AnalyseRequest,
  AnalyseResponse,
  CapabilitiesResponse,
  ValidateResponse,
  VersionResponse,
} from "@/lib/api/compositionTypes";
import {
  ApiClientError,
  type ApiErrorBody,
  type ApiResponse,
  type AnalyzeCompanyPayload,
  type HealthResponse,
  type LoginPayload,
  type PlatformInfoResponse,
  type ReportResponse,
} from "@/lib/api/types";

export type RequestOptions = {
  token?: string | null;
  signal?: AbortSignal;
};

async function request<T>(
  path: string,
  init: RequestInit = {},
  options: RequestOptions = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = options.token;
  if (token && token !== "__cookie__") {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = `${env.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;

  let response: Response;
  try {
    const cookieMode =
      process.env.NEXT_PUBLIC_COOKIE_AUTH !== "false" &&
      process.env.NEXT_PUBLIC_COOKIE_AUTH !== "0";
    let csrf: Record<string, string> = {};
    if (cookieMode && typeof window !== "undefined") {
      try {
        const { csrfHeaders } = await import("@/lib/auth/cookieSession");
        csrf = csrfHeaders();
      } catch {
        csrf = {};
      }
      for (const [k, v] of Object.entries(csrf)) {
        if (!headers.has(k)) headers.set(k, v);
      }
    }
    response = await fetch(url, {
      ...init,
      headers,
      signal: options.signal,
      credentials: cookieMode ? "include" : init.credentials,
    });
  } catch (err) {
    const aborted =
      options.signal?.aborted ||
      (err instanceof DOMException && err.name === "AbortError");
    throw new ApiClientError(
      aborted ? "Request timed out or was cancelled" : "API unavailable",
      aborted ? 408 : 0,
      {
        ok: false,
        error: aborted ? "TIMEOUT" : "NETWORK_ERROR",
        detail: aborted
          ? "Request timed out or was cancelled"
          : "Unable to reach the API service",
        api_version: "v1",
        status_code: aborted ? 408 : 0,
      },
    );
  }

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text) as unknown;
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const body = (data as ApiErrorBody | null) ?? null;
    throw new ApiClientError(
      body?.message || body?.detail || body?.error || `HTTP ${response.status}`,
      response.status,
      body,
    );
  }

  return data as T;
}

export const api = {
  health: (options?: RequestOptions) =>
    request<HealthResponse>("/health", { method: "GET" }, options),

  platform: (options?: RequestOptions) =>
    request<PlatformInfoResponse>("/platform", { method: "GET" }, options),

  version: (options?: RequestOptions) =>
    request<VersionResponse>("/version", { method: "GET" }, options),

  capabilities: (options?: RequestOptions) =>
    request<CapabilitiesResponse>("/capabilities", { method: "GET" }, options),

  validateAnalyse: (body: AnalyseRequest, options?: RequestOptions) =>
    request<ValidateResponse>(
      "/validate",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  analyse: (body: AnalyseRequest, options?: RequestOptions) =>
    request<AnalyseResponse>(
      "/analyse",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  login: (body: {
    username?: string;
    password?: string;
    api_key_id?: string;
    api_key_secret?: string;
  }) =>
    request<ApiResponse<LoginPayload>>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  refresh: (body: { refresh_token: string }, options?: RequestOptions) =>
    request<
      ApiResponse<{
        access_token: string;
        refresh_token?: string;
        token_type: string;
        expires_in?: number;
        session_id?: string;
      }>
    >(
      "/auth/refresh",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  analyzeCompany: (
    body: {
      symbol: string;
      asset_class?: string;
      currency?: string;
      start: string;
      end: string;
      as_decision_pack?: boolean;
    },
    options?: RequestOptions,
  ) =>
    request<ApiResponse<AnalyzeCompanyPayload>>(
      "/analyze/company",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  getReport: (reportId: string, options?: RequestOptions) =>
    request<ReportResponse>(
      `/report/${encodeURIComponent(reportId)}`,
      { method: "GET" },
      options,
    ),

  copilotComplete: (
    body: import("@/lib/api/copilotTypes").CopilotCompleteRequestBody,
    options?: RequestOptions,
  ) =>
    request<import("@/lib/api/copilotTypes").CopilotCompleteResponseBody>(
      "/copilot/complete",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  copilotStream: async (
    body: import("@/lib/api/copilotTypes").CopilotCompleteRequestBody,
    options?: RequestOptions,
  ) => {
    const headers = new Headers();
    headers.set("Accept", "text/event-stream");
    headers.set("Content-Type", "application/json");
    if (options?.token) {
      headers.set("Authorization", `Bearer ${options.token}`);
    }
    const url = `${env.apiBaseUrl}/copilot/stream`;
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal: options?.signal,
    });
    if (!response.ok || !response.body) {
      throw new ApiClientError(`HTTP ${response.status}`, response.status);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const chunks: import("@/lib/api/copilotTypes").CopilotStreamChunkBody[] = [];
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          chunks.push(
            JSON.parse(line.slice(6)) as import("@/lib/api/copilotTypes").CopilotStreamChunkBody,
          );
        } catch {
          // ignore malformed chunks
        }
      }
    }
    return chunks;
  },

  copilotProviders: (options?: RequestOptions) =>
    request<import("@/lib/api/copilotTypes").CopilotProvidersResponseBody>(
      "/copilot/providers",
      { method: "GET" },
      options,
    ),

  /** Authenticated market quote (EPIC-D001) — never invents missing fields. */
  marketQuote: (
    symbol: string,
    options?: RequestOptions & { exchange?: string | null },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) {
      params.set("exchange", options.exchange);
    }
    return request<import("@/lib/institutional-dashboard/mapInstitutionalDashboard").MarketQuotePayload>(
      `/market/quote?${params.toString()}`,
      { method: "GET" },
      options,
    );
  },

  marketHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; provider: Record<string, unknown> }>(
      "/market/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated financial statements (EPIC-D002) — never invents missing fields. */
  financialStatements: (
    symbol: string,
    options?: RequestOptions & {
      exchange?: string | null;
      period_type?: string | null;
      limit?: number;
      include_restated?: boolean;
    },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.period_type) params.set("period_type", options.period_type);
    if (options?.limit != null) params.set("limit", String(options.limit));
    if (options?.include_restated != null) {
      params.set("include_restated", options.include_restated ? "true" : "false");
    }
    return request<
      import("@/lib/institutional-dashboard/mapInstitutionalDashboard").FinancialStatementsPayload
    >(`/fundamentals/statements?${params.toString()}`, { method: "GET" }, options);
  },

  fundamentalsHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; provider: Record<string, unknown> }>(
      "/fundamentals/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated corporate actions (EPIC-D003) — never invents events. */
  corporateActions: (
    symbol: string,
    options?: RequestOptions & {
      exchange?: string | null;
      action_type?: string | null;
      start_date?: string | null;
      end_date?: string | null;
      limit?: number;
    },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.action_type) params.set("action_type", options.action_type);
    if (options?.start_date) params.set("start_date", options.start_date);
    if (options?.end_date) params.set("end_date", options.end_date);
    if (options?.limit != null) params.set("limit", String(options.limit));
    return request<
      import("@/lib/institutional-dashboard/mapInstitutionalDashboard").CorporateActionsPayload
    >(`/corporate-actions?${params.toString()}`, { method: "GET" }, options);
  },

  corporateActionsHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; provider: Record<string, unknown> }>(
      "/corporate-actions/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated historical series (EPIC-D004) — never invents history. */
  historicalSeries: (
    symbol: string,
    seriesKind: string,
    options?: RequestOptions & {
      exchange?: string | null;
      frequency?: string | null;
      start_date?: string | null;
      end_date?: string | null;
      limit?: number;
    },
  ) => {
    const params = new URLSearchParams({
      symbol: symbol.trim().toUpperCase(),
      series_kind: seriesKind,
    });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.frequency) params.set("frequency", options.frequency);
    if (options?.start_date) params.set("start_date", options.start_date);
    if (options?.end_date) params.set("end_date", options.end_date);
    if (options?.limit != null) params.set("limit", String(options.limit));
    return request<
      import("@/lib/institutional-dashboard/mapInstitutionalDashboard").HistoricalSeriesPayload
    >(`/historical/series?${params.toString()}`, { method: "GET" }, options);
  },

  historicalHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; provider: Record<string, unknown> }>(
      "/historical/health",
      { method: "GET" },
      options,
    ),

  /** Unified authenticated data gateway (EPIC-D005). */
  dataBundle: (
    symbol: string,
    options?: RequestOptions & {
      exchange?: string | null;
      include_market_quote?: boolean;
      include_financial_statements?: boolean;
      include_corporate_actions?: boolean;
      include_historical_series?: boolean;
      historical_series_kind?: string;
      historical_frequency?: string | null;
      historical_limit?: number;
    },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.include_market_quote != null) {
      params.set("include_market_quote", String(options.include_market_quote));
    }
    if (options?.include_financial_statements != null) {
      params.set(
        "include_financial_statements",
        String(options.include_financial_statements),
      );
    }
    if (options?.include_corporate_actions != null) {
      params.set(
        "include_corporate_actions",
        String(options.include_corporate_actions),
      );
    }
    if (options?.include_historical_series != null) {
      params.set(
        "include_historical_series",
        String(options.include_historical_series),
      );
    }
    if (options?.historical_series_kind) {
      params.set("historical_series_kind", options.historical_series_kind);
    }
    if (options?.historical_frequency) {
      params.set("historical_frequency", options.historical_frequency);
    }
    if (options?.historical_limit != null) {
      params.set("historical_limit", String(options.historical_limit));
    }
    return request<{
      ok: boolean;
      symbol?: string;
      bundle?: import("@/lib/institutional-dashboard/mapInstitutionalDashboard").UnifiedDataBundlePayload;
      message?: string | null;
    }>(`/data/bundle?${params.toString()}`, { method: "GET" }, options);
  },

  dataHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; health: Record<string, unknown> }>(
      "/data/health",
      { method: "GET" },
      options,
    ),

  /**
   * Portfolio Intelligence (EPIC-A002 / P9.5) — summarize linked research only.
   * Client must not invent research_objects; pass holdings/watchlist metadata only.
   */
  portfolioIntelligence: (
    body: {
      portfolio?: Record<string, unknown> | null;
      watchlist?: Record<string, unknown> | null;
      research_objects?: Record<string, unknown> | unknown[] | null;
      reports?: Record<string, unknown> | unknown[] | null;
      snapshots?: Record<string, unknown> | unknown[] | null;
      snapshot_ids?: Record<string, string> | null;
      result_id?: string | null;
      created_at?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      result?: Record<string, unknown>;
      message?: string | null;
      error?: string;
    }>(
      "/portfolio/intelligence",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  portfolioIntelligenceSchema: (options?: RequestOptions) =>
    request<{ ok: boolean; schema?: Record<string, unknown> }>(
      "/portfolio/intelligence/schema",
      { method: "GET" },
      options,
    ),

  /**
   * Research Intelligence (EPIC-011B) — measurement & validation only.
   * Thin client: no outcome fabrication; missing feeds stay Data unavailable.
   */
  researchIntelligenceSchema: (options?: RequestOptions) =>
    request<{ ok: boolean; schema?: Record<string, unknown> }>(
      "/research/intelligence/schema",
      { method: "GET" },
      options,
    ),

  researchIntelligenceSnapshots: (
    params?: { symbol?: string; company?: string; limit?: number; offset?: number },
    options?: RequestOptions,
  ) => {
    const q = new URLSearchParams();
    if (params?.symbol) q.set("symbol", params.symbol);
    if (params?.company) q.set("company", params.company);
    if (params?.limit != null) q.set("limit", String(params.limit));
    if (params?.offset != null) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<{
      ok: boolean;
      total?: number;
      snapshots?: Record<string, unknown>[];
      windows_supported?: number[];
    }>(
      `/research/intelligence/snapshots${qs ? `?${qs}` : ""}`,
      { method: "GET" },
      options,
    );
  },

  researchIntelligenceTimeline: (
    params?: { symbol?: string; company?: string; limit?: number; offset?: number },
    options?: RequestOptions,
  ) => {
    const q = new URLSearchParams();
    if (params?.symbol) q.set("symbol", params.symbol);
    if (params?.company) q.set("company", params.company);
    if (params?.limit != null) q.set("limit", String(params.limit));
    if (params?.offset != null) q.set("offset", String(params.offset));
    const qs = q.toString();
    return request<{
      ok: boolean;
      total?: number;
      timeline?: Record<string, unknown>[];
      provenance?: Record<string, unknown>;
    }>(
      `/research/intelligence/timeline${qs ? `?${qs}` : ""}`,
      { method: "GET" },
      options,
    );
  },

  researchIntelligencePerformance: (
    body: {
      window_months?: number;
      horizon_prices?: Record<string, number | null>;
      result_id?: string;
      created_at?: string;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      dashboard?: Record<string, unknown>;
      message?: string | null;
      error?: string;
    }>(
      "/research/intelligence/performance",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  researchIntelligenceCalibration: (
    body: {
      window_months?: number;
      horizon_prices?: Record<string, number | null>;
      result_id?: string;
      created_at?: string;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      calibration?: Record<string, unknown>;
      message?: string | null;
      error?: string;
    }>(
      "/research/intelligence/calibration",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  researchIntelligenceInsights: (
    body: {
      window_months?: number;
      horizon_prices?: Record<string, number | null>;
      result_id?: string;
      top_n?: number;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      insights?: Record<string, unknown>;
      message?: string | null;
      error?: string;
    }>(
      "/research/intelligence/insights",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),
};
