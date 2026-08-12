/**
 * EPIC-F008 — A010 Administration API client.
 * Consumes frozen /api/v1/admin/* only. No client administration logic.
 */

import { env } from "@/lib/env";
import { ApiClientError, type ApiErrorBody } from "@/lib/api/types";
import type {
  AdminAuditExport,
  AdminAuditFilters,
  AdminConfiguration,
  AdminDashboard,
  AdminEntity,
  AdminEnvelope,
  AdminFeatureFlags,
  AdminHealthPanel,
  AdminMetrics,
  AdminRole,
  AdminSchema,
  AdminSearchResult,
  AdminSearchScope,
  AdminSession,
  AdminTimelineItem,
  AdminUser,
  AdminVersions,
} from "@/lib/api/adminTypes";

export type AdminRequestOptions = {
  token?: string | null;
  signal?: AbortSignal;
};

async function adminRequest<T>(
  path: string,
  init: RequestInit = {},
  options: AdminRequestOptions = {},
  mode: "result" | "schema" = "result",
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
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
  let data: AdminEnvelope<T> | null = null;
  if (text) {
    try {
      data = JSON.parse(text) as AdminEnvelope<T>;
    } catch {
      data = null;
    }
  }

  if (!response.ok || data?.ok === false) {
    throw new ApiClientError(
      data?.error || data?.message || `HTTP ${response.status}`,
      response.status,
      {
        ok: false,
        error: data?.error || `HTTP_${response.status}`,
        detail: data?.message || "Data unavailable.",
        message: data?.message || "Data unavailable.",
        api_version: "v1",
        status_code: response.status,
      } satisfies ApiErrorBody,
    );
  }

  if (mode === "schema") {
    if (data?.schema === undefined) {
      throw new ApiClientError("Data unavailable.", response.status, {
        ok: false,
        error: "MISSING_SCHEMA",
        detail: "Data unavailable.",
        message: "Data unavailable.",
        api_version: "v1",
        status_code: response.status,
      });
    }
    return data.schema as T;
  }

  if (data?.result === undefined) {
    throw new ApiClientError("Data unavailable.", response.status, {
      ok: false,
      error: "MISSING_RESULT",
      detail: "Data unavailable.",
      message: "Data unavailable.",
      api_version: "v1",
      status_code: response.status,
    });
  }

  return data.result;
}

function auditQuery(filters?: AdminAuditFilters): string {
  if (!filters) return "";
  const params = new URLSearchParams();
  if (filters.query) params.set("query", filters.query);
  if (filters.subject) params.set("subject", filters.subject);
  if (filters.workflow_id) params.set("workflow_id", filters.workflow_id);
  if (filters.event_type) params.set("event_type", filters.event_type);
  const q = params.toString();
  return q ? `?${q}` : "";
}

export const adminApi = {
  schema: (options?: AdminRequestOptions) =>
    adminRequest<AdminSchema>("/admin/schema", { method: "GET" }, options, "schema"),

  dashboard: (options?: AdminRequestOptions, generatedAt?: string) => {
    const q = generatedAt
      ? `?generated_at=${encodeURIComponent(generatedAt)}`
      : "";
    return adminRequest<AdminDashboard>(
      `/admin/dashboard${q}`,
      { method: "GET" },
      options,
    );
  },

  listUsers: (options?: AdminRequestOptions) =>
    adminRequest<AdminUser[]>("/admin/users", { method: "GET" }, options),

  getUser: (userId: string, options?: AdminRequestOptions) =>
    adminRequest<AdminUser>(
      `/admin/users/${encodeURIComponent(userId)}`,
      { method: "GET" },
      options,
    ),

  listRoles: (options?: AdminRequestOptions) =>
    adminRequest<AdminRole[]>("/admin/roles", { method: "GET" }, options),

  listPermissions: (options?: AdminRequestOptions) =>
    adminRequest<string[]>("/admin/permissions", { method: "GET" }, options),

  listSessions: (options?: AdminRequestOptions, userId?: string) => {
    const q = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
    return adminRequest<AdminSession[]>(
      `/admin/sessions${q}`,
      { method: "GET" },
      options,
    );
  },

  listAudit: (filters?: AdminAuditFilters, options?: AdminRequestOptions) =>
    adminRequest<AdminEntity[]>(
      `/admin/audit${auditQuery(filters)}`,
      { method: "GET" },
      options,
    ),

  exportAudit: (filters?: AdminAuditFilters, options?: AdminRequestOptions) =>
    adminRequest<AdminAuditExport>(
      `/admin/audit/export${auditQuery(filters)}`,
      { method: "GET" },
      options,
    ),

  workflowHistory: (options?: AdminRequestOptions) =>
    adminRequest<AdminEntity[]>(
      "/admin/workflow-history",
      { method: "GET" },
      options,
    ),

  researchArchive: (options?: AdminRequestOptions) =>
    adminRequest<AdminEntity[]>(
      "/admin/research-archive",
      { method: "GET" },
      options,
    ),

  timeline: (limit = 100, options?: AdminRequestOptions) =>
    adminRequest<AdminTimelineItem[]>(
      `/admin/timeline?limit=${encodeURIComponent(String(limit))}`,
      { method: "GET" },
      options,
    ),

  search: (
    query: string,
    scope: AdminSearchScope = "audit",
    options?: AdminRequestOptions,
  ) =>
    adminRequest<AdminSearchResult>(
      "/admin/search",
      {
        method: "POST",
        body: JSON.stringify({ query, scope }),
      },
      options,
    ),

  health: (options?: AdminRequestOptions) =>
    adminRequest<AdminHealthPanel>("/admin/health", { method: "GET" }, options),

  configuration: (options?: AdminRequestOptions) =>
    adminRequest<AdminConfiguration>(
      "/admin/configuration",
      { method: "GET" },
      options,
    ),

  versions: (options?: AdminRequestOptions) =>
    adminRequest<AdminVersions>("/admin/versions", { method: "GET" }, options),

  featureFlags: (options?: AdminRequestOptions) =>
    adminRequest<AdminFeatureFlags>(
      "/admin/feature-flags",
      { method: "GET" },
      options,
    ),

  metrics: (options?: AdminRequestOptions) =>
    adminRequest<AdminMetrics>("/admin/metrics", { method: "GET" }, options),
};
