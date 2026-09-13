"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  AuthCard,
  AuthShell,
  ProviderButton,
  mapAuthError,
  oauthRedirectUri,
} from "@/components/auth";
import { Alert, Stack, ValidationMessage } from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import { useAuth } from "@/lib/auth/AuthProvider";
import { isAuthPublicPath, normalizePath } from "@/lib/auth/routeGuards";
import { useAuthProviders } from "@/lib/auth/useAuthProviders";
import { env } from "@/lib/env";

/** Public login surface: Google OAuth only. */
export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { status, session } = useAuth();
  const { oauthAvailable } = useAuthProviders();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const nextPath = normalizePath(searchParams.get("next") || "/dashboard");
  const expired = searchParams.get("expired") === "1";
  const verified = searchParams.get("verified") === "1";
  const googleProvider = useMemo(
    () =>
      oauthAvailable.find(
        (provider) => String(provider.provider || "").toUpperCase() === "GOOGLE",
      ) ?? null,
    [oauthAvailable],
  );

  useEffect(() => {
    if (status === "authenticated" && session) {
      router.replace(isAuthPublicPath(nextPath) ? "/dashboard" : nextPath);
    }
  }, [status, session, nextPath, router]);

  async function onGoogle() {
    setPending(true);
    setError(null);
    try {
      const redirectUri = oauthRedirectUri(window.location.origin);
      const envelope = await enterpriseAuthApi.oauthBegin("GOOGLE", redirectUri);
      const result = envelope.result;
      if (!result?.available || !result.authorization_url) {
        setError(
          result?.message ||
            "Google sign-in is unavailable. Configure Google OAuth on the API.",
        );
        return;
      }
      sessionStorage.setItem(
        "dsp.oauth.pending",
        JSON.stringify({
          provider: "GOOGLE",
          state: result.state,
          redirect_uri: redirectUri,
          remember_me: true,
          next: nextPath,
        }),
      );
      window.location.assign(result.authorization_url);
    } catch (err) {
      setError(`Google sign-in failed: ${mapAuthError(err)}`);
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell>
      <AuthCard title={env.appName} description="Sign in securely with Google.">
        <Stack gap={4}>
          {expired ? (
            <Alert variant="warning" title="Session expired">
              Your session is no longer valid. Sign in again to continue where
              you left off.
            </Alert>
          ) : null}
          {verified ? (
            <Alert variant="info" title="Email verified">
              Your email was verified. Continue with Google to sign in.
            </Alert>
          ) : null}
          {error ? (
            <ValidationMessage tone="error">{error}</ValidationMessage>
          ) : null}
          <ProviderButton
            provider="GOOGLE"
            disabled={pending}
            onClick={() => void onGoogle()}
          />
          {!googleProvider ? (
            <p className="text-center text-xs text-[var(--muted)]">
              Google sign-in is not configured on the API yet.
            </p>
          ) : null}
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
