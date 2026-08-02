/** A009 RBAC auth client — consumes /auth/rbac/* (EPIC-016 cookie-aware). */

import { env } from "@/lib/env";
import { ApiClientError, type ApiErrorBody } from "@/lib/api/types";
import {
  cookieAuthPreferred,
  cookieFetchInit,
} from "@/lib/auth/cookieSession";
import { COOKIE_TOKEN_PLACEHOLDER } from "@/lib/auth/sessionStore";
import type {
  RbacEnvelope,
  RbacLoginResult,
  RbacSession,
  RbacTokens,
  RbacUser,
} from "@/lib/api/rbacTypes";

export type RbacRequestOptions = {
  token?: string | null;
  signal?: AbortSignal;
};

async function rbacRequest<T>(
  path: string,
  init: RequestInit = {},
  options: RbacRequestOptions = {},
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
    response = await fetch(url, {
      ...fetchInit,
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

export const rbacAuthApi = {
  login: (body: {
    username: string;
    password: string;
    created_at?: string;
    session_id?: string;
    remember_me?: boolean;
  }) =>
    rbacRequest<RbacLoginResult>("/auth/rbac/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  logout: (body: { session_id: string; updated_at?: string }) =>
    rbacRequest<{ ok: boolean; session: RbacSession }>("/auth/rbac/logout", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  refresh: (body: {
    refresh_token?: string | null;
    created_at?: string;
    access_jti?: string;
  }) =>
    rbacRequest<RbacLoginResult>("/auth/rbac/refresh", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  me: (token?: string | null, options?: RbacRequestOptions) =>
    rbacRequest<RbacUser>("/auth/rbac/me", { method: "GET" }, {
      ...options,
      token: token ?? undefined,
    }),

  listSessions: (token: string, userId?: string) => {
    const q = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
    return rbacRequest<RbacSession[]>(
      `/admin/sessions${q}`,
      { method: "GET" },
      { token },
    );
  },

  evaluate: (
    token: string,
    body: { user_id: string; permission: string },
  ) =>
    rbacRequest<{
      user_id: string;
      permission: string;
      allowed: boolean;
      roles: string[];
      permissions: string[];
    }>("/auth/rbac/evaluate", {
      method: "POST",
      body: JSON.stringify(body),
    }, { token }),
};

export type { RbacTokens };
