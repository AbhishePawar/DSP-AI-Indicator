/**
 * Shared "finish login" helpers for every EnterpriseAuthPlatform entry point
 * (password, mobile OTP, email magic-link, OAuth callback). Keeping this in
 * one place avoids re-implementing the additive MFA contract per screen.
 */
import type { RbacLoginResult } from "@/lib/api/rbacTypes";
import type { MfaAdditiveFields } from "@/lib/api/enterpriseAuth";
import { isAuthPublicPath, isMarketingPath } from "./routeGuards";
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

/**
 * Resolve the post-login destination safely.
 *
 * Defaults empty, `/`, marketing paths, and public auth screens to `/dashboard`.
 * Preserves valid authenticated deep links such as `/analysis?symbol=HDFCBANK`.
 * Prevents open-redirect vectors by neutralizing external, protocol-relative,
 * or backslash-prefixed destinations back to `/dashboard`.
 */
export function resolvePostLoginDestination(
  nextPath: string | null | undefined,
): string {
  if (!nextPath || typeof nextPath !== "string") {
    return "/dashboard";
  }
  const trimmed = nextPath.trim();
  if (
    trimmed === "" ||
    trimmed === "/" ||
    trimmed.startsWith("//") ||
    trimmed.startsWith("/\\") ||
    trimmed.includes("://") ||
    trimmed.startsWith("javascript:")
  ) {
    return "/dashboard";
  }

  // Must begin with a single slash
  if (!trimmed.startsWith("/")) {
    return "/dashboard";
  }

  // Extract path portion without query string or hash for guard matching
  const [pathname] = trimmed.split(/[?#]/);
  if (isAuthPublicPath(pathname) || isMarketingPath(pathname)) {
    return "/dashboard";
  }

  return trimmed;
}

export function navigateAfterLogin(nextPath: string): void {
  if (typeof window === "undefined") return;
  const destination = resolvePostLoginDestination(nextPath);
  window.location.assign(destination);
}
