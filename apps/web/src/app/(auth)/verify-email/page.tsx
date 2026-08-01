"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { AuthCard, AuthShell } from "@/components/auth";
import {
  Alert,
  Button,
  FormField,
  Input,
  Stack,
  SuccessState,
  ValidationMessage,
} from "@/components/ds";
import { WorkspaceLoading } from "@/components/loading/WorkspaceLoading";

function VerifyEmailForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialCode = searchParams.get("code") ?? searchParams.get("token") ?? "";

  const [code, setCode] = useState(initialCode);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!code.trim()) {
      setError("Enter the verification code from your administrator or email.");
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
        title="Email verification"
        description="Confirm your work email when your organisation issues a verification code. No verification API is called in this release."
      >
        <Stack gap={4}>
          {done ? (
            <SuccessState
              title="Verification request captured locally"
              description="No email-verification API ran in this release. Sign in when your administrator confirms the account is active — do not treat this step as verified email."
              action={
                <Button onClick={() => router.push("/login")}>
                  Continue to sign in
                </Button>
              }
            />
          ) : (
            <>
              <Alert variant="info" title="Verification UX">
                Codes are not validated against a live email-verification
                endpoint. Use administrator-issued codes only.
              </Alert>
              <form className="space-y-4" onSubmit={onSubmit} noValidate>
                <FormField
                  label="Verification code"
                  htmlFor="verify-code"
                  required
                >
                  <Input
                    id="verify-code"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    autoComplete="one-time-code"
                    required
                    disabled={pending}
                  />
                </FormField>
                {error ? (
                  <ValidationMessage tone="error">{error}</ValidationMessage>
                ) : null}
                <Button type="submit" className="w-full" disabled={pending}>
                  {pending ? "Verifying…" : "Verify email"}
                </Button>
              </form>
            </>
          )}
          <p className="text-center text-sm text-[var(--muted)]">
            Waiting on email?{" "}
            <Link
              href="/verification-pending"
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Verification pending
            </Link>
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <AuthShell>
          <AuthCard title="Email verification" description="Loading…">
            <WorkspaceLoading label="Loading verification…" />
          </AuthCard>
        </AuthShell>
      }
    >
      <VerifyEmailForm />
    </Suspense>
  );
}
