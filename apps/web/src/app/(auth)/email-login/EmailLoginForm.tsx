"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";

import { AuthCard, AuthShell, isValidEmail, mapAuthError } from "@/components/auth";
import {
  Alert,
  Button,
  FormField,
  Input,
  Stack,
  ValidationMessage,
} from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import { normalizePath } from "@/lib/auth/routeGuards";
import { useAuthProviders } from "@/lib/auth/useAuthProviders";

/**
 * Email passwordless sign-in via the EnterpriseAuthPlatform "magic link"
 * capability (`/auth/enterprise/magic-link/*`). This is the real backend
 * primitive for email-based passwordless login today — there is no
 * numeric email-OTP endpoint on the server, so we surface the actual
 * "secure link" flow rather than inventing a code-entry step that nothing
 * on the backend would verify. Gated by `DSP_AUTH_MAGIC_LINK`; hidden/labelled
 * automatically per the discovery contract, never hardcoded.
 */
export default function EmailLoginForm() {
  const searchParams = useSearchParams();
  const nextPath = normalizePath(searchParams.get("next") || "/dashboard");

  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(false);
  const [devToken, setDevToken] = useState<string | null>(null);
  const { magicLinkStatus: status, magicLinkMessage: statusMessage } = useAuthProviders();

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!isValidEmail(email)) {
      setError("Enter a valid email address.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.requestEmailLink(email.trim());
      if (!envelope.ok && !envelope.result?.ok) {
        throw new Error(envelope.error || "Unable to send sign-in link");
      }
      setDevToken(envelope.result?.magic_token || null);
      setSent(true);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell>
      <AuthCard
        title="Sign in with email"
        description="We'll send a secure, one-time sign-in link to your email address."
      >
        <Stack gap={4}>
          {status !== "available" ? (
            <Alert variant={status === "unavailable" ? "warning" : "info"} title={status === "unavailable" ? "Unavailable" : "Coming Soon"}>
              {statusMessage || "Email link sign-in is not yet enabled on this deployment."}
            </Alert>
          ) : sent ? (
            <>
              <Alert variant="success" title="Check your email">
                If {email.trim()} is eligible, a secure sign-in link was sent. The
                link expires in 15 minutes. Open it on this device to finish
                signing in.
              </Alert>
              {devToken ? (
                <Alert variant="info" title="Development link">
                  <Link
                    href={`/email-login/verify?token=${encodeURIComponent(devToken)}`}
                    className="underline"
                  >
                    Continue with development sign-in link
                  </Link>
                </Alert>
              ) : null}
              <Button type="button" variant="ghost" className="w-full" onClick={() => setSent(false)}>
                Use a different email
              </Button>
            </>
          ) : (
            <form className="space-y-4" onSubmit={onSubmit} noValidate>
              <FormField label="Email address" htmlFor="email-login-address" required>
                <Input
                  id="email-login-address"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                  disabled={pending}
                />
              </FormField>
              {error ? <ValidationMessage tone="error">{error}</ValidationMessage> : null}
              <Button type="submit" className="w-full" disabled={pending || !email.trim()}>
                {pending ? "Sending…" : "Send sign-in link"}
              </Button>
            </form>
          )}
          <p className="text-center text-sm text-[var(--muted)]">
            <Link
              href={`/login?next=${encodeURIComponent(nextPath)}`}
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Back to sign in
            </Link>
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
