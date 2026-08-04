"use client";

import Link from "next/link";
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
import { SUPPORT_CONTACT } from "@/lib/commercial";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const [devToken, setDevToken] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!isValidEmail(email)) {
      setError("Enter a valid email.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.forgotPassword(email.trim());
      const token = (envelope.result as { reset_token?: string } | undefined)
        ?.reset_token;
      if (token) setDevToken(token);
      setDone(true);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell>
      <AuthCard
        title="Forgot password"
        description="Request a password reset token. Production deployments deliver email via the configured mailer."
      >
        <Stack gap={4}>
          {done ? (
            <>
              <Alert variant="success" title="If an account exists">
                A reset token was issued when the email matches an account.
              </Alert>
              {devToken ? (
                <Alert variant="info" title="Development reset token">
                  <Link
                    href={`/reset-password?token=${encodeURIComponent(devToken)}`}
                    className="underline"
                  >
                    Continue to reset password
                  </Link>
                </Alert>
              ) : null}
              <Link href="/login">
                <Button className="w-full">Back to sign in</Button>
              </Link>
            </>
          ) : (
            <form className="space-y-4" onSubmit={onSubmit} noValidate>
              <FormField label="Work email" htmlFor="forgot-email" required>
                <Input
                  id="forgot-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={pending}
                />
              </FormField>
              {error ? (
                <ValidationMessage tone="error">{error}</ValidationMessage>
              ) : null}
              <Button type="submit" className="w-full" disabled={pending}>
                {pending ? "Submitting…" : "Request reset"}
              </Button>
            </form>
          )}
          <p className="text-xs text-[var(--muted)]">
            {SUPPORT_CONTACT.channelsPublished
              ? `Support: ${SUPPORT_CONTACT.email}`
              : SUPPORT_CONTACT.unpublishedNote}
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
