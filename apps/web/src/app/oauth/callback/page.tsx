"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { AuthCard, AuthShell, mapAuthError } from "@/components/auth";
import { Alert, Button, Stack } from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import { persistSession, sessionFromRbacLogin } from "@/lib/auth/sessionStore";

export default function OAuthCallbackPage() {
  const [error, setError] = useState<string | null>(null);

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
        const result = envelope.result as typeof envelope.result & {
          csrf_token?: string;
          cookie_auth?: boolean;
        };
        const next = sessionFromRbacLogin(result, Boolean(pending.remember_me));
        persistSession(next);
        window.location.assign(pending.next || "/dashboard");
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
