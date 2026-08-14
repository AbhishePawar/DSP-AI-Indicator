"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { AuthCard, AuthShell, MfaChallenge, mapAuthError } from "@/components/auth";
import { Alert, Button, Stack } from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import {
  extractMfaChallenge,
  navigateAfterLogin,
  persistEnterpriseSession,
} from "@/lib/auth/finishEnterpriseSession";
import type { MfaChallengeInfo } from "@/lib/auth/types";

export default function OAuthCallbackPage() {
  const [error, setError] = useState<string | null>(null);
  const [mfaChallenge, setMfaChallenge] = useState<MfaChallengeInfo | null>(null);
  const [nextPath, setNextPath] = useState("/dashboard");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");
    const oauthError = params.get("error");
    if (oauthError) {
      setError(params.get("error_description") || oauthError);
      return;
    }
    if (!code) {
      setError("Missing authorization code.");
      return;
    }
    const pendingRaw = sessionStorage.getItem("dsp.oauth.pending");
    if (!pendingRaw) {
      setError("OAuth session missing. Start sign-in again from the login page.");
      return;
    }
    let pending: {
      provider: string;
      state?: string | null;
      redirect_uri: string;
      remember_me?: boolean;
      next?: string;
    };
    try {
      pending = JSON.parse(pendingRaw) as typeof pending;
    } catch {
      setError("Corrupt OAuth session.");
      return;
    }
    sessionStorage.removeItem("dsp.oauth.pending");
    setNextPath(pending.next || "/dashboard");

    enterpriseAuthApi
      .oauthCallback({
        provider: pending.provider,
        code,
        state: state || pending.state,
        redirect_uri: pending.redirect_uri,
        remember_me: Boolean(pending.remember_me),
      })
      .then((envelope) => {
        if (!envelope.ok || !envelope.result) {
          throw new Error(envelope.error || "OAuth login failed");
        }
        persistEnterpriseSession(envelope.result, Boolean(pending.remember_me));
        const challenge = extractMfaChallenge(envelope.result);
        if (challenge) {
          setMfaChallenge(challenge);
          return;
        }
        navigateAfterLogin(pending.next || "/dashboard");
      })
      .catch((err) => setError(mapAuthError(err)));
  }, []);

  return (
    <AuthShell>
      <AuthCard title="Completing sign-in" description="Finishing OAuth provider handshake.">
        <Stack gap={4}>
          {error ? (
            <>
              <Alert variant="error" title="Sign-in failed">
                {error}
              </Alert>
              <Link href="/login">
                <Button className="w-full">Back to login</Button>
              </Link>
            </>
          ) : mfaChallenge ? (
            <MfaChallenge challenge={mfaChallenge} onDone={() => navigateAfterLogin(nextPath)} />
          ) : (
            <Alert variant="info" title="Please wait">
              Contacting the identity provider and establishing your session…
            </Alert>
          )}
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
