/**
 * Shared "finish login" helpers for every EnterpriseAuthPlatform entry point
 * (password, mobile OTP, email magic-link, OAuth callback). Keeping this in
 * one place avoids re-implementing the additive MFA contract per screen.
 */
import type { RbacLoginResult } from "@/lib/api/rbacTypes";
import type { MfaAdditiveFields } from "@/lib/api/enterpriseAuth";
import { isAuthPublicPath } from "./routeGuards";
import { persistSession, sessionFromRbacLogin } from "./sessionStore";
import type { MfaChallengeInfo } from "./types";

export type EnterpriseLoginResult = RbacLoginResult &
  MfaAdditiveFields & { csrf_token?: string; cookie_auth?: boolean };

/** The backend always issues full tokens even when a step-up is pending. */
export function persistEnterpriseSession(
  result: EnterpriseLoginResult,
  rememberMe: boolean,
): void {
  persistSession(sessionFromRbacLogin(result, rememberMe));
}

export function extractMfaChallenge(
  result: EnterpriseLoginResult,
): MfaChallengeInfo | null {
  if (!result.mfa_required) return null;
  return { mfaToken: result.mfa_token ?? null, methods: result.methods ?? [] };
}

export function navigateAfterLogin(nextPath: string): void {
  if (typeof window === "undefined") return;
  window.location.assign(isAuthPublicPath(nextPath) ? "/dashboard" : nextPath);
}
