"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { AuthCard, AuthShell, isValidEmail } from "@/components/auth";
import {
  Alert,
  Button,
  FormField,
  Input,
  Stack,
  SuccessState,
  ValidationMessage,
} from "@/components/ds";
import { SUPPORT_CONTACT } from "@/lib/commercial";

/** UI-only forgot password — no backend reset endpoint in frozen APIs. */
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!isValidEmail(email)) {
      setError("Enter a valid work email.");
      return;
    }
    setPending(true);
    window.setTimeout(() => {
      setPending(false);
      setSubmitted(true);
    }, 350);
  }

  return (
    <AuthShell>
      <AuthCard
        title="Forgot password"
        description="Self-service password reset is not available through the API in this release. Contact your administrator to restore access."
      >
        <Stack gap={4}>
          {submitted ? (
            <SuccessState
              title="Request recorded"
              description="No reset email was sent by the platform. Share this request with your administrator. If a reset token was issued offline, use Reset password."
              action={
                <div className="flex flex-wrap justify-center gap-2">
                  <Link href="/reset-password">
                    <Button variant="secondary">I have a reset token</Button>
                  </Link>
                  <Link href="/login">
                    <Button>Back to sign in</Button>
                  </Link>
                </div>
              }
            />
          ) : (
            <>
              <Alert variant="info" title="Administrator restore">
                This screen does not call a password-reset endpoint. It captures
                your email so you can coordinate restore with your organisation.
              </Alert>
              <form className="space-y-4" onSubmit={onSubmit} noValidate>
                <FormField label="Work email" htmlFor="forgot-email" required>
                  <Input
                    id="forgot-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                    disabled={pending}
                  />
                </FormField>
                {error ? (
                  <ValidationMessage tone="error">{error}</ValidationMessage>
                ) : null}
                <Button type="submit" className="w-full" disabled={pending}>
                  {pending ? "Recording…" : "Continue"}
                </Button>
              </form>
            </>
          )}
          <p className="text-center text-sm">
            <Link
              href="/login"
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Back to sign in
            </Link>
          </p>
          <p className="text-xs text-[var(--muted)]">
            Support:{" "}
            <a
              className="text-[var(--accent)] underline"
              href={`mailto:${SUPPORT_CONTACT.email}`}
            >
              {SUPPORT_CONTACT.email}
            </a>
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
