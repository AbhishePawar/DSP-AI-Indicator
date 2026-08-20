/** Enterprise multi-provider auth client — `/auth/enterprise/*`. */

import { env } from "@/lib/env";
import { ApiClientError, type ApiErrorBody } from "@/lib/api/types";
import {
  cookieAuthPreferred,
  cookieFetchInit,
} from "@/lib/auth/cookieSession";
import { COOKIE_TOKEN_PLACEHOLDER } from "@/lib/auth/sessionStore";
import type { RbacEnvelope, RbacLoginResult } from "@/lib/api/rbacTypes";

export type ProviderUiStatus = "available" | "unavailable" | "coming_soon";

export type ProviderStatus = {
  id?: string;
  provider: string;
  status?: ProviderUiStatus;
  available: boolean;
  message?: string | null;
};

export type EnterpriseProvidersStatus = {
  providers?: ProviderStatus[];
  oauth: ProviderStatus[];
  sms: {
    provider: string;
    available: boolean;
    status?: ProviderUiStatus;
    message?: string | null;
  };
  magic_link?: {
    available: boolean;
    status?: ProviderUiStatus;
    message?: string;
  };
  /** MfaGateway.status() — see packages/auth/src/auth/mfa.py. */
  mfa?: {
    enabled: boolean;
    totp_available: boolean;
    webauthn_available: boolean;
    reserved_routes: string[];
    message?: string | null;
  };
};

/** Additive MFA fields merged onto a login/verify result when required. */
export type MfaAdditiveFields = {
  mfa_required?: boolean;
  mfa_token?: string | null;
  methods?: string[];
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
    enterpriseRequest<RbacLoginResult & MfaAdditiveFields>(
      "/auth/enterprise/login",
      { method: "POST", body: JSON.stringify(body) },
    ),

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
    enterpriseRequest<RbacLoginResult & MfaAdditiveFields>(
      "/auth/enterprise/oauth/callback",
      { method: "POST", body: JSON.stringify(body) },
    ),

  requestOtp: (identifier: string) =>
    enterpriseRequest<{
      challenge_id: string;
      channel?: "email" | "mobile";
      mobile?: string;
      email_hint?: string;
      expires_at: string;
      resend_available_at?: string;
      consumed?: boolean;
      email?: { ok?: boolean; detail?: string };
      sms?: { provider: string; debug_code?: string; detail?: string };
    }>("/auth/enterprise/otp/request", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    }),

  verifyOtp: (body: {
    challenge_id: string;
    code?: string;
    otp?: string;
    remember_me?: boolean;
    name?: string;
  }) =>
    enterpriseRequest<RbacLoginResult & MfaAdditiveFields>(
      "/auth/enterprise/otp/verify",
      { method: "POST", body: JSON.stringify(body) },
    ),

  /** Email "magic link" passwordless sign-in — gated by DSP_AUTH_MAGIC_LINK. */
  requestEmailLink: (email: string) =>
    enterpriseRequest<{
      ok: boolean;
      message?: string;
      /** Non-production only — see enterprise_platform.request_magic_link. */
      magic_token?: string;
    }>("/auth/enterprise/magic-link/request", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  verifyEmailLink: (body: { token: string; remember_me?: boolean }) =>
    enterpriseRequest<RbacLoginResult & MfaAdditiveFields>(
      "/auth/enterprise/magic-link/consume",
      { method: "POST", body: JSON.stringify(body) },
    ),

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
    }>("/auth/enterprise/password/strength", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),

  resendOtp: (identifier: string) =>
    enterpriseRequest<{
      challenge_id: string;
      channel?: "email" | "mobile";
      mobile?: string;
      email_hint?: string;
      expires_at: string;
      sms?: { provider: string; debug_code?: string };
      email?: { ok?: boolean; detail?: string };
    }>("/auth/otp/resend", {
      method: "POST",
      body: JSON.stringify({ identifier }),
    }),

  getProfile: (token?: string | null) =>
    enterpriseRequest<Record<string, unknown>>("/auth/me", {}, { token }),

  updateProfile: (
    body: { name?: string; avatar?: string },
    token?: string | null,
  ) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/me",
      { method: "PATCH", body: JSON.stringify(body) },
      { token },
    ),

  changePassword: (
    body: { current_password: string; new_password: string },
    token?: string | null,
  ) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/me/change-password",
      { method: "POST", body: JSON.stringify(body) },
      { token },
    ),

  changeEmail: (new_email: string, token?: string | null) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/me/change-email",
      { method: "POST", body: JSON.stringify({ new_email }) },
      { token },
    ),

  unlinkProvider: (provider: string, token?: string | null) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/me/providers/unlink",
      { method: "POST", body: JSON.stringify({ provider }) },
      { token },
    ),

  deleteAccount: (token?: string | null) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/me",
      { method: "DELETE" },
      { token },
    ),

  listDevices: (token?: string | null) =>
    enterpriseRequest<Record<string, unknown>[]>(
      "/auth/me/devices",
      {},
      { token },
    ),

  trustDevice: (deviceId: string, trusted: boolean, token?: string | null) =>
    enterpriseRequest<Record<string, unknown>>(
      `/auth/me/devices/${encodeURIComponent(deviceId)}/trust`,
      { method: "POST", body: JSON.stringify({ trusted }) },
      { token },
    ),

  revokeDevice: (deviceId: string, token?: string | null) =>
    enterpriseRequest<Record<string, unknown>>(
      `/auth/me/devices/${encodeURIComponent(deviceId)}`,
      { method: "DELETE" },
      { token },
    ),

  myLoginHistory: (token?: string | null) =>
    enterpriseRequest<Record<string, unknown>[]>(
      "/auth/me/login-history",
      {},
      { token },
    ),

  revokeMySessions: (token?: string | null) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/me/sessions/revoke-all",
      { method: "POST", body: "{}" },
      { token },
    ),

  adminProvisionUser: (
    body: {
      name: string;
      email: string;
      username?: string;
      password?: string;
      roles?: string[];
    },
    token?: string | null,
  ) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/enterprise/admin/users/provision",
      { method: "POST", body: JSON.stringify(body) },
      { token },
    ),

  adminUnlockUser: (userId: string, token?: string | null) =>
    enterpriseRequest<Record<string, unknown>>(
      `/auth/enterprise/admin/users/${encodeURIComponent(userId)}/unlock`,
      { method: "POST", body: "{}" },
      { token },
    ),

  adminRevokeSessions: (userId: string, token?: string | null) =>
    enterpriseRequest<Record<string, unknown>>(
      `/auth/enterprise/admin/users/${encodeURIComponent(userId)}/revoke-sessions`,
      { method: "POST", body: "{}" },
      { token },
    ),

  adminResetPassword: (
    userId: string,
    new_password: string,
    token?: string | null,
  ) =>
    enterpriseRequest<Record<string, unknown>>(
      `/auth/enterprise/admin/users/${encodeURIComponent(userId)}/reset-password`,
      { method: "POST", body: JSON.stringify({ new_password }) },
      { token },
    ),

  adminSetStatus: (userId: string, active: boolean, token?: string | null) =>
    enterpriseRequest<Record<string, unknown>>(
      `/auth/enterprise/admin/users/${encodeURIComponent(userId)}/status`,
      { method: "POST", body: JSON.stringify({ active }) },
      { token },
    ),

  // --- MFA / WebAuthn (Passkey) -----------------------------------------
  // Reserved server routes — return HTTP 501 until DSP_AUTH_MFA=true and a
  // real TOTP/WebAuthn adapter is configured (see auth/mfa.py). Calling them
  // is honest wiring to the real EnterpriseAuthPlatform contract, not a mock;
  // callers must handle the "not enabled" response gracefully.

  mfaTotpVerify: (body: { mfa_token: string; code: string }) =>
    enterpriseRequest<Record<string, unknown>>("/auth/mfa/totp/verify", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  webauthnAuthenticateBegin: (body: { identifier?: string } = {}) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/mfa/webauthn/authenticate",
      { method: "POST", body: JSON.stringify(body) },
    ),

  webauthnRegisterBegin: (token?: string | null) =>
    enterpriseRequest<Record<string, unknown>>(
      "/auth/mfa/webauthn/register",
      { method: "POST", body: "{}" },
      { token },
    ),
};
