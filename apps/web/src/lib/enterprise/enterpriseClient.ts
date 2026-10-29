/**
 * EPS-002 — Enterprise API client.
 * Consumes /api/v1/enterprise/* only. No client-side enterprise logic or secrets.
 */

import { buildApiUrl } from "@/lib/env";
import { ApiClientError, type ApiErrorBody } from "@/lib/api/types";
import { csrfHeaders } from "@/lib/auth/cookieSession";
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

export async function enterpriseRequest<T>(
  path: string,
  init: RequestInit = {},
  options: EnterpriseRequestOptions = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  // Never send X-User-Id — identity is cookie/Bearer only (P0-05).
  void options.userId;

  const method = (init.method || "GET").toUpperCase();
  const isMutating = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
  const cookieMode =
    process.env.NEXT_PUBLIC_COOKIE_AUTH !== "false" &&
    process.env.NEXT_PUBLIC_COOKIE_AUTH !== "0";

  if (cookieMode && isMutating && typeof window !== "undefined") {
    try {
      const csrf = csrfHeaders();
      for (const [k, v] of Object.entries(csrf)) {
        if (!headers.has(k)) headers.set(k, v);
      }
    } catch {
      // CSRF token storage unavailable
    }
  }

  const url = buildApiUrl(path);
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers,
      credentials: "include",
      signal: options.signal,
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
  return enterpriseRequest("/enterprise/schema", {}, options);
}

export async function listOrganizations(
  userId?: string | null,
  options?: EnterpriseRequestOptions,
): Promise<{ result: Organization[]; message: string | null }> {
  // userId ignored — server resolves actor from session (P0-05).
  void userId;
  const result = await enterpriseRequest<Organization[]>(
    "/enterprise/organizations",
    {},
    options,
  );
  return {
    result: Array.isArray(result) ? result : [],
    message: null,
  };
}

export async function fetchCustomerPortal(
  orgId: string,
  userId: string,
  options?: EnterpriseRequestOptions,
): Promise<CustomerPortal> {
  return enterpriseRequest(
    `/enterprise/organizations/${encodeURIComponent(orgId)}/portal`,
    {},
    { ...options, userId },
  );
}

export async function fetchOpsDashboard(
  options?: EnterpriseRequestOptions,
): Promise<OpsDashboard> {
  return enterpriseRequest("/enterprise/ops/dashboard", {}, options);
}

export async function fetchAdminOverview(
  options?: EnterpriseRequestOptions,
): Promise<Record<string, unknown>> {
  return enterpriseRequest("/enterprise/admin/overview", {}, options);
}
