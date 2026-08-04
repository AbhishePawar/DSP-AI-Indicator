/** Enterprise multi-provider auth client — `/auth/enterprise/*`. */

import { env } from "@/lib/env";
import { ApiClientError, type ApiErrorBody } from "@/lib/api/types";
import {
  cookieAuthPreferred,
  cookieFetchInit,
} from "@/lib/auth/cookieSession";
import { COOKIE_TOKEN_PLACEHOLDER } from "@/lib/auth/sessionStore";
import type { RbacEnvelope, RbacLoginResult } from "@/lib/api/rbacTypes";

export type ProviderStatus = {
  provider: string;
  available: boolean;
  message?: string | null;
};

export type EnterpriseProvidersStatus = {
  oauth: ProviderStatus[];
  sms: { provider: string; available: boolean };
  magic_link?: { available: boolean; message?: string };
};

async function enterpriseRequest<T>(
  path: string,
  init: RequestInit = {},
  options: { token?: string | null; signal?: AbortSignal } = {},
): Promise<RbacEnvelope<T>> {
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = options.token;
  if (token && token !== COOKIE_TOKEN_PLACEHOLDER) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = `${env.apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
  const fetchInit = cookieAuthPreferred()
    ? cookieFetchInit({ ...init, headers })
    : { ...init, headers };

  let response: Response;
  try {
    response = await fetch(url, { ...fetchInit, signal: options.signal });
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
  let data: RbacEnvelope<T> | null = null;
  if (text) {
    try {
      data = JSON.parse(text) as RbacEnvelope<T>;
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    throw new ApiClientError(
      data?.error || data?.message || `HTTP ${response.status}`,
      response.status,
      {
        ok: false,
        error: data?.error || `HTTP_${response.status}`,
        detail: data?.message || null,
        message: data?.message ?? undefined,
        api_version: "v1",
        status_code: response.status,
      } satisfies ApiErrorBody,
    );
  }

  return data ?? { ok: true };
}

export const enterpriseAuthApi = {
  providers: () =>
    enterpriseRequest<EnterpriseProvidersStatus>("/auth/enterprise/providers"),

  register: (body: {
    name: string;
    email: string;
    password: string;
    confirm_password: string;
    username?: string;
  }) =>
    enterpriseRequest<Record<string, unknown>>("/auth/enterprise/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  login: (body: {
    identifier: string;
    password: string;
    remember_me?: boolean;
  }) =>
    enterpriseRequest<RbacLoginResult>("/auth/enterprise/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  forgotPassword: (email: string) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/enterprise/password/forgot",
      { method: "POST", body: JSON.stringify({ email }) },
    ),

  resetPassword: (token: string, new_password: string) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/enterprise/password/reset",
      { method: "POST", body: JSON.stringify({ token, new_password }) },
    ),

  verifyEmail: (token: string) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/enterprise/verify-email",
      { method: "POST", body: JSON.stringify({ token }) },
    ),

  oauthBegin: (provider: string, redirect_uri: string) =>
    enterpriseRequest<{
      available: boolean;
      authorization_url?: string | null;
      message?: string | null;
      state?: string | null;
      provider: string;
    }>("/auth/enterprise/oauth/begin", {
      method: "POST",
      body: JSON.stringify({ provider, redirect_uri }),
    }),

  oauthCallback: (body: {
    provider: string;
    code: string;
    state?: string | null;
    redirect_uri: string;
    remember_me?: boolean;
  }) =>
    enterpriseRequest<RbacLoginResult>("/auth/enterprise/oauth/callback", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  requestOtp: (mobile: string) =>
    enterpriseRequest<{
      challenge_id: string;
      mobile: string;
      expires_at: string;
      resend_available_at?: string;
      sms?: { provider: string; debug_code?: string; detail?: string };
    }>("/auth/enterprise/otp/request", {
      method: "POST",
      body: JSON.stringify({ mobile }),
    }),

  verifyOtp: (body: {
    challenge_id: string;
    code: string;
    remember_me?: boolean;
    name?: string;
  }) =>
    enterpriseRequest<RbacLoginResult>("/auth/enterprise/otp/verify", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  submitAccessRequest: (body: {
    name: string;
    email: string;
    organization?: string;
    reason?: string;
  }) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/enterprise/access-requests",
      { method: "POST", body: JSON.stringify(body) },
    ),

  listAccessRequests: (token?: string | null, status?: string) =>
    enterpriseRequest<Record<string, unknown>[]>(
      `/auth/enterprise/access-requests${status ? `?status=${encodeURIComponent(status)}` : ""}`,
      {},
      { token },
    ),

  decideAccessRequest: (
    requestId: string,
    body: { approve: boolean; notes?: string; role?: string },
    token?: string | null,
  ) =>
    enterpriseRequest<Record<string, unknown>>(
      `/auth/enterprise/access-requests/${requestId}/decide`,
      { method: "POST", body: JSON.stringify(body) },
      { token },
    ),

  acceptInvitation: (body: {
    token: string;
    password: string;
    confirm_password: string;
    username?: string;
  }) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/enterprise/invitations/accept",
      { method: "POST", body: JSON.stringify(body) },
    ),

  passwordStrength: (password: string) =>
    enterpriseRequest<{
      score: number;
      max: number;
      label: string;
      checks: Record<string, boolean>;
    }>(
      `/auth/enterprise/password/strength?password=${encodeURIComponent(password)}`,
    ),
};
