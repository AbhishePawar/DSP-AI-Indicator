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

/** RC1 M6 — one dashboard widget section from GET /dashboards/{role}. */
export type DashboardWidgetSection = {
  available?: boolean;
  source?: string;
  data?: unknown;
  message?: string | null;
};

/** RC1 M8 — Research Workspace API envelope. */
export type ResearchWorkspaceEnvelope = {
  ok: boolean;
  action?: string;
  result?: Record<string, unknown>;
  message?: string | null;
  error?: string;
  provenance?: Record<string, unknown>;
};

export type ResearchWorkspaceNoteInput = {
  title?: string;
  body?: string;
  format?: string;
  folder_id?: string;
  status?: string;
  company?: string;
  portfolio_id?: string;
  research_object_id?: string;
  document_refs?: string[];
  attachments?: unknown[];
  tag_ids?: string[];
  assignee_id?: string;
  created_by?: string;
  ai_generated?: boolean;
};

/** RC1 M9 — Commercial SaaS Platform API envelope. */
export type SaasEnvelope = {
  ok: boolean;
  action?: string;
  result?: Record<string, unknown>;
  message?: string | null;
  error?: string;
  provenance?: Record<string, unknown>;
};

/** Shared envelope shape returned by every Data Connector Framework endpoint. */
type ConnectorIdentity = {
  symbol?: string;
  exchange?: string | null;
  company_name?: string | null;
  isin?: string | null;
  provider_company_id?: string | null;
  currency?: string | null;
} | null;

type ConnectorProvenance = {
  provider_id?: string;
  provider_name?: string;
  source_type?: string;
  retrieved_at?: string;
  as_of?: string | null;
  request_id?: string | null;
  cache_hit?: boolean;
  auth_mode?: string;
} | null;

/** Authenticated news payload from GET /api/v1/news. */
export type NewsPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: ConnectorIdentity;
  articles?: Array<{
    article_id?: string;
    headline?: string;
    url?: string;
    source?: string;
    published_at?: string;
    summary?: string | null;
    sentiment?: string | null;
    related_symbols?: string[];
    image_url?: string | null;
  }> | null;
  provenance?: ConnectorProvenance;
  attempted_provider_ids?: string[] | null;
  message?: string | null;
};

/** Authenticated regulatory filings payload from GET /api/v1/filings. */
export type FilingsPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: ConnectorIdentity;
  filings?: Array<{
    filing_id?: string;
    filing_type?: string;
    title?: string;
    url?: string;
    filed_at?: string;
    period_of_report?: string | null;
    accession_number?: string | null;
    source?: string | null;
  }> | null;
  provenance?: ConnectorProvenance;
  attempted_provider_ids?: string[] | null;
  message?: string | null;
};

/** Authenticated shareholding pattern payload from GET /api/v1/ownership. */
export type OwnershipPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: ConnectorIdentity;
  as_of?: string | null;
  stakes?: Array<{
    holder_type?: string;
    holder_name?: string | null;
    percent_held?: number | null;
    shares_held?: number | null;
  }> | null;
  promoter_holding_percent?: number | null;
  institutional_holding_percent?: number | null;
  public_holding_percent?: number | null;
  provenance?: ConnectorProvenance;
  attempted_provider_ids?: string[] | null;
  message?: string | null;
};

/** Authenticated insider trading payload from GET /api/v1/insider-trading. */
export type InsiderTradingPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: ConnectorIdentity;
  transactions?: Array<{
    transaction_id?: string;
    insider_name?: string;
    role?: string | null;
    transaction_type?: string;
    shares?: number | null;
    price?: number | null;
    value?: number | null;
    transaction_date?: string;
    filed_at?: string | null;
    source?: string | null;
  }> | null;
  provenance?: ConnectorProvenance;
  attempted_provider_ids?: string[] | null;
  message?: string | null;
};

/** Authenticated ESG score payload from GET /api/v1/esg. */
export type EsgPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: ConnectorIdentity;
  as_of?: string | null;
  environmental_score?: number | null;
  social_score?: number | null;
  governance_score?: number | null;
  total_score?: number | null;
  controversy_level?: string | null;
  provenance?: ConnectorProvenance;
  attempted_provider_ids?: string[] | null;
  message?: string | null;
};

/** Authenticated earnings call transcripts payload from GET /api/v1/transcripts. */
export type TranscriptsPayload = {
  ok?: boolean;
  available?: boolean;
  authenticated?: boolean;
  symbol?: string;
  identity?: ConnectorIdentity;
  transcripts?: Array<{
    transcript_id?: string;
    quarter?: number | null;
    year?: number | null;
    call_date?: string | null;
    title?: string;
    url?: string | null;
    content?: string | null;
    participants?: string[];
    source?: string | null;
  }> | null;
  provenance?: ConnectorProvenance;
  attempted_provider_ids?: string[] | null;
  message?: string | null;
};

type AuthFailureHandler = (status: 401 | 403) => void;
let authFailureHandler: AuthFailureHandler | null = null;

/** Wire AuthProvider session expiry / forbidden handling into the API client. */
export function setApiAuthFailureHandler(
  handler: AuthFailureHandler | null,
): void {
  authFailureHandler = handler;
}

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
    if (
      (response.status === 401 || response.status === 403) &&
      authFailureHandler
    ) {
      try {
        authFailureHandler(response.status);
      } catch {
        // Never block error propagation on handler failure.
      }
    }
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

  /** P1-06 / P1-12 — fetch server-owned investment provenance by analysis_id. */
  analyseProvenance: (analysisId: string, options?: RequestOptions) =>
    request<{
      ok: boolean;
      capability?: string;
      audit_reference?: string;
      provenance?: Record<string, unknown>;
      message?: string | null;
      error?: string;
      error_code?: string;
    }>(
      `/analyse/provenance/${encodeURIComponent(analysisId)}`,
      { method: "GET" },
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

  /**
   * RC1 Milestone 7 — Copilot 2.0 orchestration chat.
   * Explains existing engine outputs only; never invents numbers.
   */
  copilotV2Chat: (
    body: import("@/lib/api/copilotTypes").CopilotV2RequestBody,
    options?: RequestOptions,
  ) =>
    request<import("@/lib/api/copilotTypes").CopilotV2ResponseBody>(
      "/copilot/chat",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  copilotV2Company: (
    body: import("@/lib/api/copilotTypes").CopilotV2RequestBody,
    options?: RequestOptions,
  ) =>
    request<import("@/lib/api/copilotTypes").CopilotV2ResponseBody>(
      "/copilot/company",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  copilotV2Portfolio: (
    body: import("@/lib/api/copilotTypes").CopilotV2RequestBody,
    options?: RequestOptions,
  ) =>
    request<import("@/lib/api/copilotTypes").CopilotV2ResponseBody>(
      "/copilot/portfolio",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  copilotV2Valuation: (
    body: import("@/lib/api/copilotTypes").CopilotV2RequestBody,
    options?: RequestOptions,
  ) =>
    request<import("@/lib/api/copilotTypes").CopilotV2ResponseBody>(
      "/copilot/valuation",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  copilotV2Comparison: (
    body: import("@/lib/api/copilotTypes").CopilotV2RequestBody,
    options?: RequestOptions,
  ) =>
    request<import("@/lib/api/copilotTypes").CopilotV2ResponseBody>(
      "/copilot/comparison",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  copilotV2Document: (
    body: import("@/lib/api/copilotTypes").CopilotV2RequestBody,
    options?: RequestOptions,
  ) =>
    request<import("@/lib/api/copilotTypes").CopilotV2ResponseBody>(
      "/copilot/document",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  copilotHistoryList: (options?: RequestOptions) =>
    request<{
      ok: boolean;
      conversations: Array<{
        conversation_id: string;
        title?: string;
        turn_count?: number;
        updated_at?: string | null;
        context?: Record<string, unknown>;
      }>;
    }>("/copilot/history", { method: "GET" }, options),

  copilotHistoryGet: (conversationId: string, options?: RequestOptions) =>
    request<{
      ok: boolean;
      result: {
        conversation_id: string;
        context: Record<string, unknown>;
        turns: Array<Record<string, unknown>>;
      };
    }>(`/copilot/history/${encodeURIComponent(conversationId)}`, { method: "GET" }, options),

  copilotHistoryDelete: (conversationId: string, options?: RequestOptions) =>
    request<{ ok: boolean; deleted?: boolean; message?: string | null }>(
      `/copilot/history/${encodeURIComponent(conversationId)}`,
      { method: "DELETE" },
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

  /** Opt-in Indian listing selection via existing /fundamentals/resolve. */
  selectIndianListing: (
    symbol: string,
    options?: RequestOptions & { exchange?: string | null },
  ) => {
    const params = new URLSearchParams({
      symbol: symbol.trim().toUpperCase(),
      select_listing: "true",
    });
    if (options?.exchange) params.set("exchange", options.exchange);
    return request<{
      ok: boolean;
      available?: boolean;
      status?: string | null;
      symbol?: string;
      exchange?: string | null;
      isin?: string | null;
      detail?: string | null;
      identity?: { exchange?: string | null } | null;
      message?: string | null;
    }>(`/fundamentals/resolve?${params.toString()}`, { method: "GET" }, options);
  },

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

  // -- Data Connector Framework: News/Filings/Ownership/Insider/ESG/
  // Transcripts. Each additive endpoint tries every configured provider in
  // priority order (automatic failover) and returns HTTP 200 with
  // `available: false` when no provider has data — never fabricated.

  /** Authenticated company news — never invents headlines. */
  news: (
    symbol: string,
    options?: RequestOptions & { exchange?: string | null; limit?: number },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.limit != null) params.set("limit", String(options.limit));
    return request<NewsPayload>(`/news?${params.toString()}`, { method: "GET" }, options);
  },

  newsHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; providers: Record<string, unknown> }>(
      "/news/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated regulatory/corporate filings — never invents documents. */
  filings: (
    symbol: string,
    options?: RequestOptions & {
      exchange?: string | null;
      filing_types?: string | null;
      start_date?: string | null;
      end_date?: string | null;
      limit?: number;
    },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.filing_types) params.set("filing_types", options.filing_types);
    if (options?.start_date) params.set("start_date", options.start_date);
    if (options?.end_date) params.set("end_date", options.end_date);
    if (options?.limit != null) params.set("limit", String(options.limit));
    return request<FilingsPayload>(`/filings?${params.toString()}`, { method: "GET" }, options);
  },

  filingsHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; providers: Record<string, unknown> }>(
      "/filings/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated shareholding pattern — never invents holders. */
  ownership: (
    symbol: string,
    options?: RequestOptions & { exchange?: string | null; as_of?: string | null },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.as_of) params.set("as_of", options.as_of);
    return request<OwnershipPayload>(
      `/ownership?${params.toString()}`,
      { method: "GET" },
      options,
    );
  },

  ownershipHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; providers: Record<string, unknown> }>(
      "/ownership/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated insider trading activity — never invents transactions. */
  insiderTrading: (
    symbol: string,
    options?: RequestOptions & {
      exchange?: string | null;
      start_date?: string | null;
      end_date?: string | null;
      limit?: number;
    },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.start_date) params.set("start_date", options.start_date);
    if (options?.end_date) params.set("end_date", options.end_date);
    if (options?.limit != null) params.set("limit", String(options.limit));
    return request<InsiderTradingPayload>(
      `/insider-trading?${params.toString()}`,
      { method: "GET" },
      options,
    );
  },

  insiderTradingHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; providers: Record<string, unknown> }>(
      "/insider-trading/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated ESG score — never invents scores. */
  esg: (symbol: string, options?: RequestOptions & { exchange?: string | null }) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    return request<EsgPayload>(`/esg?${params.toString()}`, { method: "GET" }, options);
  },

  esgHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; providers: Record<string, unknown> }>(
      "/esg/health",
      { method: "GET" },
      options,
    ),

  /** Authenticated earnings call transcripts — never invents content. */
  transcripts: (
    symbol: string,
    options?: RequestOptions & {
      exchange?: string | null;
      year?: number | null;
      quarter?: number | null;
      limit?: number;
    },
  ) => {
    const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase() });
    if (options?.exchange) params.set("exchange", options.exchange);
    if (options?.year != null) params.set("year", String(options.year));
    if (options?.quarter != null) params.set("quarter", String(options.quarter));
    if (options?.limit != null) params.set("limit", String(options.limit));
    return request<TranscriptsPayload>(
      `/transcripts?${params.toString()}`,
      { method: "GET" },
      options,
    );
  },

  transcriptsHealth: (options?: RequestOptions) =>
    request<{ ok: boolean; providers: Record<string, unknown> }>(
      "/transcripts/health",
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
   * RC1 Milestone 10 — Production Operations (aggregation only).
   * Reuses /health and /metrics — never duplicates monitoring.
   */
  opsSchema: (options?: RequestOptions) =>
    request<{ ok: boolean; schema?: Record<string, unknown> }>(
      "/ops/schema",
      { method: "GET" },
      options,
    ),

  opsHealth: (options?: RequestOptions) =>
    request<SaasEnvelope>("/ops/health", { method: "GET" }, options),

  opsStatus: (options?: RequestOptions) =>
    request<SaasEnvelope>("/ops/status", { method: "GET" }, options),

  opsVersion: (options?: RequestOptions) =>
    request<SaasEnvelope>("/ops/version", { method: "GET" }, options),

  opsDependencies: (options?: RequestOptions) =>
    request<SaasEnvelope>("/ops/dependencies", { method: "GET" }, options),

  opsMetrics: (options?: RequestOptions) =>
    request<SaasEnvelope>("/ops/metrics", { method: "GET" }, options),

  opsDashboard: (options?: RequestOptions) =>
    request<SaasEnvelope>("/ops/dashboard", { method: "GET" }, options),

  opsObservability: (options?: RequestOptions) =>
    request<SaasEnvelope>("/ops/observability", { method: "GET" }, options),

  opsBackup: (options?: RequestOptions) =>
    request<SaasEnvelope>("/ops/backup", { method: "GET" }, options),

  /**
   * RC1 Milestone 11 — Super Admin Control Center (orchestration only).
   * Configuration registry overlays — never executes engines in the browser.
   */
  controlCenterSchema: (options?: RequestOptions) =>
    request<{ ok: boolean; schema?: Record<string, unknown> }>(
      "/admin/control-center/schema",
      { method: "GET" },
      options,
    ),

  controlCenterDashboard: (options?: RequestOptions) =>
    request<SaasEnvelope>(
      "/admin/control-center/dashboard",
      { method: "GET" },
      options,
    ),

  controlCenterRegistry: (
    moduleId?: string,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      moduleId
        ? `/admin/configuration/registry?module_id=${encodeURIComponent(moduleId)}`
        : "/admin/configuration/registry",
      { method: "GET" },
      options,
    ),

  controlCenterUpdateConfiguration: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/admin/configuration",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  controlCenterHistory: (
    params?: { module_id?: string; limit?: number },
    options?: RequestOptions,
  ) => {
    const qs = new URLSearchParams();
    if (params?.module_id) qs.set("module_id", params.module_id);
    if (params?.limit != null) qs.set("limit", String(params.limit));
    const q = qs.toString();
    return request<SaasEnvelope>(
      `/admin/configuration/history${q ? `?${q}` : ""}`,
      { method: "GET" },
      options,
    );
  },

  controlCenterRollback: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/admin/rollback",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  controlCenterBranding: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/admin/branding",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  controlCenterFeatureFlags: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/admin/feature-flags/overrides",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  controlCenterValuation: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/admin/valuation/config",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  controlCenterAi: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/admin/ai/config",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  controlCenterBusinessRules: (options?: RequestOptions) =>
    request<SaasEnvelope>("/admin/business-rules", { method: "GET" }, options),

  controlCenterUpsertBusinessRule: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/admin/business-rules",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  controlCenterSecurity: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/admin/security/config",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  controlCenterMonitoring: (options?: RequestOptions) =>
    request<SaasEnvelope>("/admin/monitoring", { method: "GET" }, options),

  controlCenterAudit: (options?: RequestOptions) =>
    request<SaasEnvelope>("/admin/audit/config", { method: "GET" }, options),

  /**
   * RC1 Milestone 9 — Commercial SaaS Platform (orchestration only).
   * Reuses enterprise orgs/IAM/billing ports — never fabricates payments.
   */
  saasSchema: (options?: RequestOptions) =>
    request<{ ok: boolean; schema?: Record<string, unknown> }>(
      "/saas/schema",
      { method: "GET" },
      options,
    ),

  saasDashboard: (options?: RequestOptions) =>
    request<SaasEnvelope>("/saas/dashboard", { method: "GET" }, options),

  saasPlans: (options?: RequestOptions) =>
    request<SaasEnvelope>("/saas/plans", { method: "GET" }, options),

  saasListOrganizations: (options?: RequestOptions) =>
    request<SaasEnvelope>("/saas/organizations", { method: "GET" }, options),

  saasCreateOrganization: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/saas/organization",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  saasGetOrganization: (orgId: string, options?: RequestOptions) =>
    request<SaasEnvelope>(
      `/saas/organization/${encodeURIComponent(orgId)}`,
      { method: "GET" },
      options,
    ),

  saasUpdateOrganization: (
    orgId: string,
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      `/saas/organization/${encodeURIComponent(orgId)}`,
      { method: "PUT", body: JSON.stringify(body) },
      options,
    ),

  saasArchiveOrganization: (
    orgId: string,
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      `/saas/organization/${encodeURIComponent(orgId)}/archive`,
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  saasGetSettings: (orgId: string, options?: RequestOptions) =>
    request<SaasEnvelope>(
      `/saas/organization/${encodeURIComponent(orgId)}/settings`,
      { method: "GET" },
      options,
    ),

  saasUpdateSettings: (
    orgId: string,
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      `/saas/organization/${encodeURIComponent(orgId)}/settings`,
      { method: "PUT", body: JSON.stringify(body) },
      options,
    ),

  saasCreateSubscription: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/saas/subscription",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  saasGetSubscription: (orgId: string, options?: RequestOptions) =>
    request<SaasEnvelope>(
      `/saas/organization/${encodeURIComponent(orgId)}/subscription`,
      { method: "GET" },
      options,
    ),

  saasAssignLicense: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/saas/license",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  saasGetLicense: (orgId: string, options?: RequestOptions) =>
    request<SaasEnvelope>(
      `/saas/organization/${encodeURIComponent(orgId)}/license`,
      { method: "GET" },
      options,
    ),

  saasCreateApiKey: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/saas/api-key",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  saasGetUsage: (orgId: string, options?: RequestOptions) =>
    request<SaasEnvelope>(
      `/saas/organization/${encodeURIComponent(orgId)}/usage`,
      { method: "GET" },
      options,
    ),

  saasRecordUsage: (
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      "/saas/usage",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  saasBillingStatus: (orgId: string, options?: RequestOptions) =>
    request<SaasEnvelope>(
      `/saas/organization/${encodeURIComponent(orgId)}/billing`,
      { method: "GET" },
      options,
    ),

  saasUpsertBillingProfile: (
    orgId: string,
    body: Record<string, unknown>,
    options?: RequestOptions,
  ) =>
    request<SaasEnvelope>(
      `/saas/organization/${encodeURIComponent(orgId)}/billing-profile`,
      { method: "PUT", body: JSON.stringify(body) },
      options,
    ),

  saasFeatureLimits: (orgId: string, options?: RequestOptions) =>
    request<SaasEnvelope>(
      `/saas/organization/${encodeURIComponent(orgId)}/limits`,
      { method: "GET" },
      options,
    ),

  saasCheckout: (body: Record<string, unknown>, options?: RequestOptions) =>
    request<SaasEnvelope>(
      "/saas/checkout",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  /**
   * RC1 Milestone 8 — Institutional Research Workspace (orchestration only).
   * Notes/folders/bookmarks/templates/search — no client research math.
   */
  researchWorkspaceSchema: (options?: RequestOptions) =>
    request<{ ok: boolean; schema?: Record<string, unknown> }>(
      "/research-workspace/schema",
      { method: "GET" },
      options,
    ),

  researchWorkspaceDashboard: (options?: RequestOptions) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace",
      { method: "GET" },
      options,
    ),

  researchWorkspaceListNotes: (options?: RequestOptions) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace/notes",
      { method: "GET" },
      options,
    ),

  researchWorkspaceGetNote: (noteId: string, options?: RequestOptions) =>
    request<ResearchWorkspaceEnvelope>(
      `/research-workspace/note/${encodeURIComponent(noteId)}`,
      { method: "GET" },
      options,
    ),

  researchWorkspaceCreateNote: (
    body: ResearchWorkspaceNoteInput,
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace/note",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  researchWorkspaceUpdateNote: (
    noteId: string,
    body: ResearchWorkspaceNoteInput,
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      `/research-workspace/note/${encodeURIComponent(noteId)}`,
      { method: "PUT", body: JSON.stringify(body) },
      options,
    ),

  researchWorkspaceDeleteNote: (noteId: string, options?: RequestOptions) =>
    request<ResearchWorkspaceEnvelope>(
      `/research-workspace/note/${encodeURIComponent(noteId)}`,
      { method: "DELETE" },
      options,
    ),

  researchWorkspaceNoteVersions: (noteId: string, options?: RequestOptions) =>
    request<ResearchWorkspaceEnvelope>(
      `/research-workspace/note/${encodeURIComponent(noteId)}/versions`,
      { method: "GET" },
      options,
    ),

  researchWorkspaceRestoreVersion: (
    noteId: string,
    version: number,
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      `/research-workspace/note/${encodeURIComponent(noteId)}/restore`,
      { method: "POST", body: JSON.stringify({ version }) },
      options,
    ),

  researchWorkspaceDiffVersions: (
    noteId: string,
    fromVersion: number,
    toVersion: number,
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      `/research-workspace/note/${encodeURIComponent(noteId)}/diff`,
      {
        method: "POST",
        body: JSON.stringify({
          from_version: fromVersion,
          to_version: toVersion,
        }),
      },
      options,
    ),

  researchWorkspaceListFolders: (options?: RequestOptions) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace/folders",
      { method: "GET" },
      options,
    ),

  researchWorkspaceCreateFolder: (
    body: { name: string; parent_id?: string },
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace/folder",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  researchWorkspaceUpdateFolder: (
    folderId: string,
    body: { name?: string; parent_id?: string; archived?: boolean },
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      `/research-workspace/folder/${encodeURIComponent(folderId)}`,
      { method: "PUT", body: JSON.stringify(body) },
      options,
    ),

  researchWorkspaceDeleteFolder: (
    folderId: string,
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      `/research-workspace/folder/${encodeURIComponent(folderId)}`,
      { method: "DELETE" },
      options,
    ),

  researchWorkspaceListBookmarks: (options?: RequestOptions) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace/bookmarks",
      { method: "GET" },
      options,
    ),

  researchWorkspaceCreateBookmark: (
    body: {
      kind: string;
      label: string;
      target_id?: string;
      company?: string;
      href?: string;
    },
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace/bookmark",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  researchWorkspaceDeleteBookmark: (
    bookmarkId: string,
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      `/research-workspace/bookmark/${encodeURIComponent(bookmarkId)}`,
      { method: "DELETE" },
      options,
    ),

  researchWorkspaceApplyTemplate: (
    body: {
      template_id: string;
      title?: string;
      company?: string;
      folder_id?: string;
      enrich_with_ai?: boolean;
    },
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace/template",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  researchWorkspaceAddComment: (
    body: {
      note_id: string;
      body: string;
      author_id?: string;
      mentions?: string[];
    },
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace/comment",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  researchWorkspaceResolveComment: (
    commentId: string,
    resolved?: boolean,
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      `/research-workspace/comment/${encodeURIComponent(commentId)}/resolve`,
      {
        method: "POST",
        body: JSON.stringify({ resolved: resolved ?? true }),
      },
      options,
    ),

  researchWorkspaceShare: (
    body: {
      note_id: string;
      user_ids?: string[];
      permission?: string;
      created_by?: string;
    },
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace/share",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  researchWorkspacePublish: (
    body: {
      note_id: string;
      status: string;
      actor_id?: string;
      reason?: string;
    },
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace/publish",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  researchWorkspaceSearch: (q: string, options?: RequestOptions) =>
    request<ResearchWorkspaceEnvelope>(
      `/research-workspace/search?q=${encodeURIComponent(q)}`,
      { method: "GET" },
      options,
    ),

  researchWorkspaceAi: (
    body: {
      note_id?: string;
      instruction: string;
      mode?: string;
      apply_to_note?: boolean;
      company?: string;
    },
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace/ai",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  researchWorkspaceUpsertTag: (
    body: {
      tag_id?: string;
      label: string;
      color?: string;
      kind?: string;
    },
    options?: RequestOptions,
  ) =>
    request<ResearchWorkspaceEnvelope>(
      "/research-workspace/tag",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  researchWorkspaceDeleteTag: (tagId: string, options?: RequestOptions) =>
    request<ResearchWorkspaceEnvelope>(
      `/research-workspace/tag/${encodeURIComponent(tagId)}`,
      { method: "DELETE" },
      options,
    ),

  /**
   * RC1 Milestone 6 — Enterprise role dashboards (aggregation only).
   * Thin client: never invents KPIs; missing sections stay Data unavailable.
   */
  enterpriseDashboardSchema: (options?: RequestOptions) =>
    request<{ ok: boolean; schema?: Record<string, unknown> }>(
      "/dashboards/schema",
      { method: "GET" },
      options,
    ),

  enterpriseDashboard: (
    role:
      | "research"
      | "portfolio-manager"
      | "wealth-advisor"
      | "family-office"
      | "executive",
    params?: {
      portfolio_id?: string;
      symbols?: string;
      watchlist_id?: string;
      client_portfolio_ids?: string;
      workflow_id?: string;
    },
    options?: RequestOptions,
  ) => {
    const q = new URLSearchParams();
    if (params?.portfolio_id) q.set("portfolio_id", params.portfolio_id);
    if (params?.symbols) q.set("symbols", params.symbols);
    if (params?.watchlist_id) q.set("watchlist_id", params.watchlist_id);
    if (params?.client_portfolio_ids) {
      q.set("client_portfolio_ids", params.client_portfolio_ids);
    }
    if (params?.workflow_id) q.set("workflow_id", params.workflow_id);
    const qs = q.toString();
    return request<{
      ok: boolean;
      result?: {
        role: string;
        generated_at?: string;
        widgets?: Record<string, DashboardWidgetSection>;
        provenance?: Record<string, unknown>;
      };
      message?: string | null;
      error?: string;
    }>(`/dashboards/${role}${qs ? `?${qs}` : ""}`, { method: "GET" }, options);
  },

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

  /**
   * Build a canonical Research Object from an existing `/analyse` response
   * (EPIC-R001). No new scoring — passes through the already-computed
   * analysis payload and optionally fetches the D005 data bundle.
   */
  researchObject: (
    body: {
      symbol: string;
      company?: string | null;
      exchange?: string | null;
      correlation_id?: string | null;
      analysis_id?: string | null;
      data_bundle?: Record<string, unknown> | null;
      analysis_payload?: Record<string, unknown> | null;
      valuation_signals?: Record<string, unknown> | null;
      fetch_data_bundle?: boolean;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      symbol?: string;
      research_object?: Record<string, unknown>;
      analysis_id?: string | null;
      message?: string | null;
      error?: string;
      error_code?: string;
    }>(
      "/research/object",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  /** Generate an Institutional Research Report from a Research Object (EPIC-R002). */
  researchReport: (
    body: {
      research_object: Record<string, unknown>;
      analysis_id?: string | null;
      report_id?: string | null;
      generated_at?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      symbol?: string;
      report?: Record<string, unknown>;
      analysis_id?: string | null;
      message?: string | null;
      error?: string;
      error_code?: string;
    }>(
      "/research/report",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  /** Export an Institutional Research Report to json/csv/xlsx/pdf/docx/pptx (EPIC-R003). */
  researchExport: (
    body: {
      report: Record<string, unknown>;
      analysis_id?: string | null;
      format: "json" | "csv" | "xlsx" | "pdf" | "docx" | "pptx";
      export_id?: string | null;
      exported_at?: string | null;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      export?: {
        metadata: {
          filename: string;
          content_type: string;
          [key: string]: unknown;
        };
        content_base64: string;
        [key: string]: unknown;
      };
      analysis_id?: string | null;
      message?: string | null;
      error?: string;
      error_code?: string;
    }>(
      "/research/export",
      { method: "POST", body: JSON.stringify(body) },
      options,
    ),

  /**
   * Peer comparison over pre-computed Decision Pack reports (EPIC — Peers tab).
   * Reuses `comparison.QualitativeComparisonEngine` server-side; the client
   * never re-derives peer eligibility or scores.
   */
  compare: (
    body: {
      report_ids: string[];
      allow_related?: boolean;
      allow_limited?: boolean;
    },
    options?: RequestOptions,
  ) =>
    request<{
      ok: boolean;
      result?: Record<string, unknown>;
      message?: string | null;
      error?: string;
    }>("/compare", { method: "POST", body: JSON.stringify(body) }, options),

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
