"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import {
  AuthCard,
  AuthShell,
  PasswordStrengthMeter,
  mapAuthError,
} from "@/components/auth";
import {
  Alert,
  Button,
  FormField,
  PasswordInput,
  Spinner,
  Stack,
  ValidationMessage,
} from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") || "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!token.trim() || !password) {
      setError("Token and new password are required.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.resetPassword(
        token.trim(),
        password,
      );
      if (!envelope.ok) {
        throw new Error(envelope.error || "Reset failed");
      }
      setDone(true);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthCard
      title="Reset password"
      description="Set a new password using your reset token."
    >
      <Stack gap={4}>
        {done ? (
          <>
            <Alert variant="success" title="Password updated">
              You can sign in with your new password.
            </Alert>
            <Link href="/login">
              <Button className="w-full">Sign in</Button>
            </Link>
          </>
        ) : (
          <form className="space-y-4" onSubmit={onSubmit} noValidate>
            <FormField label="Reset token" htmlFor="reset-token" required>
              <PasswordInput
                id="reset-token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
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
            {error ? (
              <ValidationMessage tone="error">{error}</ValidationMessage>
            ) : null}
            <Button type="submit" className="w-full" disabled={pending}>
              {pending ? "Updating…" : "Update password"}
            </Button>
          </form>
        )}
      </Stack>
    </AuthCard>
  );
}

export default function ResetPasswordPage() {
  return (
    <AuthShell>
      <Suspense
        fallback={
          <AuthCard title="Reset password" description="Loading…">
            <Spinner label="Loading…" />
          </AuthCard>
        }
      >
        <ResetPasswordForm />
      </Suspense>
    </AuthShell>
  );
}
