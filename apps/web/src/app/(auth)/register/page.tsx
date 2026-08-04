"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { AuthCard, AuthShell, isValidEmail, mapAuthError } from "@/components/auth";
import {
  Alert,
  Button,
  FormField,
  Input,
  PasswordInput,
  Stack,
  ValidationMessage,
} from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const [verifyToken, setVerifyToken] = useState<string | null>(null);
  const [strength, setStrength] = useState<{
    score: number;
    label: string;
  } | null>(null);

  useEffect(() => {
    if (!password) {
      setStrength(null);
      return;
    }
    const handle = window.setTimeout(() => {
      enterpriseAuthApi
        .passwordStrength(password)
        .then((env) => {
          if (env.result) {
            setStrength({ score: env.result.score, label: env.result.label });
          }
        })
        .catch(() => setStrength(null));
    }, 250);
    return () => window.clearTimeout(handle);
  }, [password]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError("Full name is required.");
      return;
    }
    if (!isValidEmail(email)) {
      setError("Enter a valid email.");
      return;
    }
    if (password !== confirm) {
      setError("Password confirmation does not match.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.register({
        name: name.trim(),
        email: email.trim(),
        password,
        confirm_password: confirm,
        username: username.trim() || undefined,
      });
      if (!envelope.ok) {
        throw new Error(envelope.error || "Registration failed");
      }
      const token = (envelope.result as { verification_token?: string } | undefined)
        ?.verification_token;
      if (token) setVerifyToken(token);
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
        title="Create account"
        description="Self-service registration with email verification. Enterprise programmes may still use Request Access."
      >
        <Stack gap={4}>
          {done ? (
            <>
              <Alert variant="info" title="Verify your email">
                Registration accepted. Activate the account via the verification
                link before signing in.
              </Alert>
              {verifyToken ? (
                <Alert variant="info" title="Development verification token">
                  <Link
                    href={`/verify-email?token=${encodeURIComponent(verifyToken)}`}
                    className="underline"
                  >
                    Verify email now
                  </Link>
                </Alert>
              ) : null}
              <Link href="/login">
                <Button className="w-full">Back to sign in</Button>
              </Link>
            </>
          ) : (
            <form className="space-y-4" onSubmit={onSubmit} noValidate>
              <FormField label="Full name" htmlFor="reg-name" required>
                <Input
                  id="reg-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  disabled={pending}
                />
              </FormField>
              <FormField label="Email" htmlFor="reg-email" required>
                <Input
                  id="reg-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={pending}
                />
              </FormField>
              <FormField label="Username (optional)" htmlFor="reg-username">
                <Input
                  id="reg-username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={pending}
                />
              </FormField>
              <FormField label="Password" htmlFor="reg-password" required>
                <PasswordInput
                  id="reg-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={pending}
                />
              </FormField>
              {strength ? (
                <p className="text-xs text-[var(--muted)]">
                  Strength: {strength.label} ({strength.score}/5)
                </p>
              ) : null}
              <FormField label="Confirm password" htmlFor="reg-confirm" required>
                <PasswordInput
                  id="reg-confirm"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  required
                  disabled={pending}
                />
              </FormField>
              {error ? (
                <ValidationMessage tone="error">{error}</ValidationMessage>
              ) : null}
              <Button type="submit" disabled={pending} className="w-full">
                {pending ? "Creating…" : "Create account"}
              </Button>
            </form>
          )}
          <p className="text-center text-sm text-[var(--muted)]">
            Enterprise onboarding?{" "}
            <Link href="/signup" className="text-[var(--accent)] underline">
              Request access
            </Link>
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
