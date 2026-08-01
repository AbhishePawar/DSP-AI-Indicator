"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useMemo, useState } from "react";

import {
  AuthCard,
  AuthShell,
  PasswordStrengthMeter,
  evaluatePasswordStrength,
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
import { WorkspaceLoading } from "@/components/loading/WorkspaceLoading";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const tokenFromQuery = searchParams.get("token") ?? "";

  const [token, setToken] = useState(tokenFromQuery);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);

  const strength = useMemo(
    () => evaluatePasswordStrength(password),
    [password],
  );

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!token.trim()) {
      setError("A reset token from your administrator is required.");
      return;
    }
    if (strength.score < 2) {
      setError("Choose a stronger password.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setPending(true);
    window.setTimeout(() => {
      setPending(false);
      setDone(true);
    }, 400);
  }

  return (
    <AuthShell>
      <AuthCard
        title="Reset password"
        description="Enter an administrator-issued reset token and a new password. No password-reset API is called in this release."
      >
        <Stack gap={4}>
          {done ? (
            <SuccessState
              title="Reset instructions recorded"
              description="Data unavailable for automated password change. Ask your administrator to confirm the new credential, then sign in."
              action={
                <Link href="/login">
                  <Button>Go to sign in</Button>
                </Link>
              }
            />
          ) : (
            <>
              <Alert variant="warning" title="Offline / admin token flow">
                Tokens are not validated against a live reset endpoint here.
                Invalid tokens will not be rejected by the platform in this UI.
              </Alert>
              <form className="space-y-4" onSubmit={onSubmit} noValidate>
                <FormField label="Reset token" htmlFor="reset-token" required>
                  <Input
                    id="reset-token"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    autoComplete="one-time-code"
                    required
                    disabled={pending}
                  />
                </FormField>
                <FormField label="New password" htmlFor="reset-password" required>
                  <PasswordInput
                    id="reset-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                    required
                    disabled={pending}
                  />
                </FormField>
                <PasswordStrengthMeter password={password} />
                <FormField
                  label="Confirm new password"
                  htmlFor="reset-confirm"
                  required
                >
                  <PasswordInput
                    id="reset-confirm"
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
                  {pending ? "Recording…" : "Continue"}
                </Button>
              </form>
            </>
          )}
          <p className="text-center text-sm">
            <Link
              href="/forgot-password"
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Forgot password help
            </Link>
            {" · "}
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

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <AuthShell>
          <AuthCard title="Reset password" description="Loading…">
            <WorkspaceLoading label="Loading reset form…" />
          </AuthCard>
        </AuthShell>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
