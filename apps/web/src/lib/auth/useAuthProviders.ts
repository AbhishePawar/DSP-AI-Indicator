"use client";

import { useEffect, useState } from "react";

import {
  enterpriseAuthApi,
  type EnterpriseProvidersStatus,
  type ProviderStatus,
  type ProviderUiStatus,
} from "@/lib/api/enterpriseAuth";

export type AuthProvidersState = {
  /** True until the first `/auth/enterprise/providers` response resolves. */
  loading: boolean;
  /** Branded OAuth providers the backend reports as ready to use. */
  oauthAvailable: ProviderStatus[];
  /** Branded OAuth providers that are intentionally disabled for now. */
  oauthComingSoon: ProviderStatus[];
  /** Mobile SMS OTP availability. */
  smsStatus: ProviderUiStatus;
  smsMessage: string | null;
  /** Email magic-link ("Email Link") availability. */
  magicLinkStatus: ProviderUiStatus;
  magicLinkMessage: string | null;
  /** WebAuthn / Passkey step-up availability, per MfaGateway.status(). */
  webauthnAvailable: boolean;
  webauthnMessage: string | null;
};

const INITIAL_STATE: AuthProvidersState = {
  loading: true,
  oauthAvailable: [],
  oauthComingSoon: [],
  smsStatus: "available",
  smsMessage: null,
  magicLinkStatus: "coming_soon",
  magicLinkMessage: null,
  webauthnAvailable: false,
  webauthnMessage: null,
};

function deriveState(result: EnterpriseProvidersStatus): AuthProvidersState {
  const oauth = result.oauth || [];
  return {
    loading: false,
    // Hide unavailable (missing credentials); keep available + coming_soon.
    // Unknown provider names (e.g. a future Enterprise SSO / OIDC connector)
    // render automatically via ProviderButton — nothing here hardcodes
    // Google / Microsoft / Facebook specifically.
    oauthAvailable: oauth.filter(
      (p) =>
        p.status === "available" ||
        (p.available && p.status !== "coming_soon" && p.status !== "unavailable"),
    ),
    oauthComingSoon: oauth.filter((p) => p.status === "coming_soon"),
    smsStatus:
      result.sms?.status || (result.sms?.available ? "available" : "unavailable"),
    smsMessage: result.sms?.message || null,
    magicLinkStatus:
      (result.magic_link?.status as ProviderUiStatus) ||
      (result.magic_link?.available ? "available" : "coming_soon"),
    magicLinkMessage: result.magic_link?.message || null,
    webauthnAvailable: Boolean(result.mfa?.webauthn_available),
    webauthnMessage: result.mfa?.message || null,
  };
}

/**
 * Fetches `/auth/enterprise/providers` once and exposes the dynamic
 * provider-availability contract that every login entry point (password,
 * mobile OTP, email link) needs to decide what to render. Centralising this
 * avoids re-implementing the same fetch + status-mapping logic per screen.
 */
export function useAuthProviders(): AuthProvidersState {
  const [state, setState] = useState<AuthProvidersState>(INITIAL_STATE);

  useEffect(() => {
    let cancelled = false;
    enterpriseAuthApi
      .providers()
      .then((envelope) => {
        if (cancelled || !envelope.result) return;
        setState(deriveState(envelope.result));
      })
      .catch(() => {
        if (cancelled) return;
        setState((prev) => ({
          ...prev,
          loading: false,
          oauthAvailable: [],
          oauthComingSoon: [],
          smsStatus: "unavailable",
          smsMessage: "Unable to load sign-in provider status from the API.",
        }));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
