"use client";

import Link from "next/link";
import { useState } from "react";

import {
  AuthCard,
  AuthShell,
  ProviderButton,
  mapAuthError,
  oauthRedirectUri,
} from "@/components/auth";
import { Stack, ValidationMessage } from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";

export default function RegisterPage() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onGoogle() {
    setPending(true);
    setError(null);
    try {
      const redirectUri = oauthRedirectUri(window.location.origin);
      const envelope = await enterpriseAuthApi.oauthBegin("GOOGLE", redirectUri);
      const result = envelope.result;
      if (!result?.available || !result.authorization_url) {
        throw new Error(
          result?.message ||
            "Google sign-up is currently unavailable. Please try again shortly.",
        );
      }
      sessionStorage.setItem(
        "dsp.oauth.pending",
        JSON.stringify({
          provider: "GOOGLE",
          state: result.state,
          redirect_uri: redirectUri,
          remember_me: false,
          next: "/dashboard",
        }),
      );
      window.location.assign(result.authorization_url);
    } catch (err) {
      setError(`Google sign-up failed: ${mapAuthError(err)}`);
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell>
      <AuthCard
        title="Create your DSP AI Indicator account"
        description="Use your Google account to create an account securely."
      >
        <Stack gap={4}>
          {error ? <ValidationMessage tone="error">{error}</ValidationMessage> : null}
          <ProviderButton
            provider="GOOGLE"
            disabled={pending}
            onClick={() => void onGoogle()}
          />
          <p className="text-center text-sm text-[var(--muted)]">
            Google is the only available sign-up method.
          </p>
          <p className="text-center text-sm text-[var(--muted)]">
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Sign in
            </Link>
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
