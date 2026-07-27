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
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const url = `${env.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;

  let response: Response;
  try {
    response = await fetch(url, { ...init, headers, signal: options.signal });
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
    api_key_id?: string;
    api_key_secret?: string;
  }) =>
    request<ApiResponse<LoginPayload>>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),

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
};
