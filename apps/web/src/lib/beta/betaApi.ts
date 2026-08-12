/**
 * P5.1 — Closed beta client helpers (thin /api/v1 beta + admin/beta).
 */

import { env } from "@/lib/env";

export type BetaStatusResult = {
  programme: {
    closed_beta_mode: boolean;
    beta_feature_flag: boolean;
    invitation_only: boolean;
    banner_enabled: boolean;
    banner_text: string;
    expiry_at: string | null;
    read_only_safeguards: boolean;
    expired?: boolean;
    version?: string;
  };
  access_allowed: boolean;
  feature_flag: boolean;
  banner: { enabled: boolean; text: string };
};

export type BetaDashboardResult = {
  active_beta_users: number;
  pending_invites: number;
  new_registrations: number;
  daily_active_users: number;
  reports_generated: number;
  failed_analyses: number;
  export_usage: number;
  feedback_received: number;
  average_feedback_rating: number | null;
  open_critical_issues: number;
  issue_counts_by_status: Record<string, number>;
  system_health_summary: Record<string, unknown>;
  programme: Record<string, unknown>;
  success_criteria: Record<string, number>;
};

async function betaFetch<T>(
  path: string,
  init?: RequestInit & { token?: string | null },
): Promise<T> {
  const { token, ...rest } = init || {};
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(rest.headers as Record<string, string> | undefined),
  };
  if (rest.body) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${env.apiBaseUrl}${path}`, { ...rest, headers });
  const json = (await res.json()) as { ok?: boolean; result?: T; message?: string };
  if (!res.ok || json.ok === false) {
    throw new Error(json.message || `Beta API unavailable (${res.status})`);
  }
  return json.result as T;
}

export const betaApi = {
  status: (identity?: string | null, isAdmin?: boolean) => {
    const params = new URLSearchParams();
    if (identity) params.set("identity", identity);
    if (isAdmin) params.set("is_admin", "true");
    const q = params.toString();
    return betaFetch<BetaStatusResult>(`/beta/status${q ? `?${q}` : ""}`);
  },

  submitFeedback: (
    body: Record<string, unknown>,
    token?: string | null,
  ) =>
    betaFetch<Record<string, unknown>>("/beta/feedback", {
      method: "POST",
      body: JSON.stringify(body),
      token,
    }),

  trackEvent: (
    body: {
      kind: string;
      ok?: boolean;
      duration_ms?: number;
      feature?: string;
    },
    token?: string | null,
  ) =>
    betaFetch<Record<string, unknown>>("/beta/analytics/event", {
      method: "POST",
      body: JSON.stringify(body),
      token,
    }),

  dashboard: (token?: string | null) =>
    betaFetch<BetaDashboardResult>("/admin/beta/dashboard", {
      method: "GET",
      token,
    }),

  invites: (token?: string | null) =>
    betaFetch<Record<string, unknown>[]>("/admin/beta/invites", {
      method: "GET",
      token,
    }),

  createInvite: (
    body: { email_or_username: string; role?: string; status?: string },
    token?: string | null,
  ) =>
    betaFetch<Record<string, unknown>>("/admin/beta/invites", {
      method: "POST",
      body: JSON.stringify(body),
      token,
    }),

  patchInvite: (
    id: string,
    status: string,
    token?: string | null,
  ) =>
    betaFetch<Record<string, unknown>>(`/admin/beta/invites/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
      token,
    }),

  issues: (token?: string | null) =>
    betaFetch<Record<string, unknown>[]>("/admin/beta/issues", {
      method: "GET",
      token,
    }),

  patchIssue: (
    id: string,
    body: Record<string, unknown>,
    token?: string | null,
  ) =>
    betaFetch<Record<string, unknown>>(`/admin/beta/issues/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
      token,
    }),

  analytics: (token?: string | null) =>
    betaFetch<Record<string, unknown>>("/admin/beta/analytics", {
      method: "GET",
      token,
    }),

  feedback: (token?: string | null) =>
    betaFetch<Record<string, unknown>[]>("/admin/beta/feedback", {
      method: "GET",
      token,
    }),

  snapshot: (token?: string | null) =>
    betaFetch<Record<string, unknown>>("/admin/beta/snapshot", {
      method: "GET",
      token,
    }),

  importSnapshot: (
    snapshot: Record<string, unknown>,
    merge: boolean,
    token?: string | null,
  ) =>
    betaFetch<Record<string, unknown>>("/admin/beta/snapshot/import", {
      method: "POST",
      body: JSON.stringify({ snapshot, merge }),
      token,
    }),

  rcAssessment: (token?: string | null) =>
    betaFetch<Record<string, unknown>>("/admin/beta/rc-assessment", {
      method: "GET",
      token,
    }),

  classifyIssue: (
    id: string,
    body: { disposition: string; rationale: string },
    token?: string | null,
  ) =>
    betaFetch<Record<string, unknown>>(`/admin/beta/issues/${id}/classify`, {
      method: "POST",
      body: JSON.stringify(body),
      token,
    }),
};
