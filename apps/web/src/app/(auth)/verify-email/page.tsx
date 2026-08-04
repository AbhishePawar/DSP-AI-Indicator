"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";

import { AuthCard, AuthShell, mapAuthError } from "@/components/auth";
import {
  Alert,
  Button,
  FormField,
  Input,
  Stack,
  ValidationMessage,
} from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";

function VerifyEmailForm() {
  const searchParams = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") || "");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const t = searchParams.get("token");
    if (t && !done && !pending) {
      setPending(true);
      enterpriseAuthApi
        .verifyEmail(t)
        .then((envelope) => {
          if (!envelope.ok) throw new Error(envelope.error || "Verification failed");
          setDone(true);
        })
        .catch((err) => setError(mapAuthError(err)))
        .finally(() => setPending(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- one-shot token verify
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!token.trim()) {
      setError("Verification token is required.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.verifyEmail(token.trim());
      if (!envelope.ok) throw new Error(envelope.error || "Verification failed");
      setDone(true);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthCard
      title="Verify email"
      description="Activate your account with the verification token from registration."
    >
      <Stack gap={4}>
        {done ? (
          <>
            <Alert variant="success" title="Email verified">
              Your account is active. You can sign in now.
            </Alert>
            <Link href="/login?verified=1">
              <Button className="w-full">Continue to sign in</Button>
            </Link>
          </>
        ) : (
          <form className="space-y-4" onSubmit={onSubmit} noValidate>
            <FormField label="Verification token" htmlFor="verify-token" required>
              <Input
                id="verify-token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
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
        )}
      </Stack>
    </AuthCard>
  );
}

export default function VerifyEmailPage() {
  return (
    <AuthShell>
      <Suspense fallback={<AuthCard title="Verify email" description="Loading…" />}>
        <VerifyEmailForm />
      </Suspense>
    </AuthShell>
  );
}
