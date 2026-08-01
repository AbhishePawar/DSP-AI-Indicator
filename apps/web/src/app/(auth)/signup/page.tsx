"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";

import {
  AuthCard,
  AuthShell,
  PasswordStrengthMeter,
  evaluatePasswordStrength,
  isValidEmail,
} from "@/components/auth";
import {
  Alert,
  Button,
  FormField,
  Input,
  PasswordInput,
  Stack,
  SuccessState,
  ValidationMessage,
} from "@/components/ds";
import { SUPPORT_CONTACT } from "@/lib/commercial";

/**
 * Sign-up / access request — UI experience only.
 * No public self-service registration API in the frozen auth surface.
 */
export default function SignUpPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const strength = useMemo(
    () => evaluatePasswordStrength(password),
    [password],
  );

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError("Full name is required.");
      return;
    }
    if (!isValidEmail(email)) {
      setError("Enter a valid work email.");
      return;
    }
    if (strength.score < 2) {
      setError("Choose a stronger password before continuing.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setPending(true);
    window.setTimeout(() => {
      setPending(false);
      setSubmitted(true);
    }, 400);
  }

  return (
    <AuthShell>
      <AuthCard
        title="Request access"
        description="Self-service registration is not open on this release. Submit your details to prepare an administrator-provisioned account."
      >
        <Stack gap={4}>
          {submitted ? (
            <SuccessState
              title="Request recorded"
              description="No registration API was called. An administrator must provision access. You can continue to verification pending for the expected next step."
              action={
                <div className="flex flex-wrap justify-center gap-2">
                  <Link href="/verification-pending">
                    <Button>View pending state</Button>
                  </Link>
                  <Link href="/login">
                    <Button variant="secondary">Sign in</Button>
                  </Link>
                </div>
              }
            />
          ) : (
            <>
              <Alert variant="info" title="Administrator provisioning">
                Accounts are created by your organisation administrator. This
                form captures intent only — credentials are not created here.
              </Alert>
              <form className="space-y-4" onSubmit={onSubmit} noValidate>
                <FormField label="Full name" htmlFor="signup-name" required>
                  <Input
                    id="signup-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="name"
                    required
                    disabled={pending}
                  />
                </FormField>
                <FormField label="Work email" htmlFor="signup-email" required>
                  <Input
                    id="signup-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                    disabled={pending}
                  />
                </FormField>
                <FormField
                  label="Proposed password"
                  htmlFor="signup-password"
                  required
                >
                  <PasswordInput
                    id="signup-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                    required
                    disabled={pending}
                  />
                </FormField>
                <PasswordStrengthMeter password={password} />
                <FormField
                  label="Confirm password"
                  htmlFor="signup-confirm"
                  required
                >
                  <PasswordInput
                    id="signup-confirm"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    autoComplete="new-password"
                    required
                    disabled={pending}
                  />
                </FormField>
                {error ? (
                  <ValidationMessage tone="error">{error}</ValidationMessage>
                ) : null}
                <Button type="submit" className="w-full" disabled={pending}>
                  {pending ? "Submitting…" : "Submit access request"}
                </Button>
              </form>
            </>
          )}
          <p className="text-center text-sm text-[var(--muted)]">
            Already provisioned?{" "}
            <Link
              href="/login"
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Sign in
            </Link>
          </p>
          <p className="text-xs text-[var(--muted)]">
            Sales:{" "}
            <a
              className="text-[var(--accent)] underline"
              href={`mailto:${SUPPORT_CONTACT.salesEmail}`}
            >
              {SUPPORT_CONTACT.salesEmail}
            </a>
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
