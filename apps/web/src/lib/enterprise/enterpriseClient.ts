/**
 * EPS-002 — Enterprise API client.
 * Consumes /api/v1/enterprise/* only. No client-side enterprise logic or secrets.
 */

import { env } from "@/lib/env";
import { ApiClientError, type ApiErrorBody } from "@/lib/api/types";
import type {
  CustomerPortal,
  EnterpriseEnvelope,
  OpsDashboard,
  Organization,
} from "@/lib/enterprise/types";

export type EnterpriseRequestOptions = {
  userId?: string | null;
  signal?: AbortSignal;
};

async function enterpriseRequest<T>(
  path: string,
  init: RequestInit = {},
  options: EnterpriseRequestOptions = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (options.userId) {
    headers.set("X-User-Id", options.userId);
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
        error: "NetworkError",
        detail: aborted ? "Request cancelled" : "API unavailable",
        message: aborted ? "Request cancelled" : "API unavailable",
        api_version: "v1",
        status_code: aborted ? 408 : 0,
      } satisfies ApiErrorBody,
    );
  }

  let payload: EnterpriseEnvelope<T> | null = null;
  try {
    payload = (await response.json()) as EnterpriseEnvelope<T>;
  } catch {
    payload = null;
  }

  if (!response.ok || !payload?.ok) {
    throw new ApiClientError(
      payload?.error || payload?.message || "Enterprise request failed",
      response.status,
      {
        ok: false,
        error: payload?.error || "EnterpriseError",
        detail: payload?.message || "Data unavailable.",
        message: payload?.message || "Data unavailable.",
        api_version: "v1",
        status_code: response.status,
      },
    );
  }
  return (payload.result ?? payload.schema) as T;
}

export async function fetchEnterpriseSchema(
  options?: EnterpriseRequestOptions,
): Promise<Record<string, unknown>> {
  return enterpriseRequest("/api/v1/enterprise/schema", {}, options);
}

export async function listOrganizations(
  userId?: string | null,
  options?: EnterpriseRequestOptions,
): Promise<{ result: Organization[]; message: string | null }> {
  const qs = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
  const headers = new Headers();
  const url = `${env.apiBaseUrl}/api/v1/enterprise/organizations${qs}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    signal: options?.signal,
  });
  const payload = (await response.json()) as EnterpriseEnvelope<Organization[]>;
  return {
    result: payload.result ?? [],
    message: payload.message ?? null,
  };
}

export async function fetchCustomerPortal(
  orgId: string,
  userId: string,
  options?: EnterpriseRequestOptions,
): Promise<CustomerPortal> {
  return enterpriseRequest(
    `/api/v1/enterprise/organizations/${encodeURIComponent(orgId)}/portal`,
    {},
    { ...options, userId },
  );
}

export async function fetchOpsDashboard(
  options?: EnterpriseRequestOptions,
): Promise<OpsDashboard> {
  return enterpriseRequest("/api/v1/enterprise/ops/dashboard", {}, options);
}

export async function fetchAdminOverview(
  options?: EnterpriseRequestOptions,
): Promise<Record<string, unknown>> {
  return enterpriseRequest("/api/v1/enterprise/admin/overview", {}, options);
}
