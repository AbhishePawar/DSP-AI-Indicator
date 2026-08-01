"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { AuthCard, AuthShell, mapAuthError } from "@/components/auth";
import {
  Alert,
  Button,
  Checkbox,
  FormField,
  Input,
  PasswordInput,
  Stack,
  ValidationMessage,
} from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";
import { isAuthPublicPath, normalizePath } from "@/lib/auth/routeGuards";

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, status, session } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const nextPath = normalizePath(searchParams.get("next") || "/dashboard");
  const expired = searchParams.get("expired") === "1";
  const verified = searchParams.get("verified") === "1";

  useEffect(() => {
    if (status === "authenticated" && session) {
      router.replace(isAuthPublicPath(nextPath) ? "/dashboard" : nextPath);
    }
  }, [status, session, nextPath, router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setFieldError(null);
    try {
      if (!username.trim() || !password) {
        setFieldError("Username and password are required.");
        return;
      }
      await login({
        username: username.trim(),
        password,
        rememberMe,
        useRbac: true,
      });
      router.replace(isAuthPublicPath(nextPath) ? "/dashboard" : nextPath);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell>
      <AuthCard
        title="Sign in"
        description="Use your institutional credentials to enter the research platform. Your destination is preserved after authentication."
      >
        <Stack gap={4}>
          {expired ? (
            <Alert variant="warning" title="Session expired">
              Your session is no longer valid. Sign in again to continue where
              you left off.
            </Alert>
          ) : null}
          {verified ? (
            <Alert variant="success" title="Email verified">
              Your email verification was recorded. You can sign in now.
            </Alert>
          ) : null}

          <form className="space-y-4" onSubmit={onSubmit} noValidate>
            <FormField label="Username" htmlFor="login-username" required>
              <Input
                id="login-username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
                aria-required="true"
                disabled={pending}
              />
            </FormField>
            <FormField label="Password" htmlFor="login-password" required>
              <PasswordInput
                id="login-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                aria-required="true"
                disabled={pending}
              />
            </FormField>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
                <Checkbox
                  checked={rememberMe}
                  onCheckedChange={(v) => setRememberMe(v === true)}
                  aria-label="Remember me on this device"
                  disabled={pending}
                />
                Remember me
              </label>
              <Link
                href="/forgot-password"
                className="text-sm text-[var(--accent)] underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
              >
                Forgot password?
              </Link>
            </div>
            {fieldError ? (
              <ValidationMessage tone="error">{fieldError}</ValidationMessage>
            ) : null}
            {error ? (
              <ValidationMessage tone="error">{error}</ValidationMessage>
            ) : null}
            <Button type="submit" disabled={pending} className="w-full">
              {pending ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <p className="text-center text-sm text-[var(--muted)]">
            Need an account?{" "}
            <Link
              href="/signup"
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Request access
            </Link>
          </p>
          <p className="text-xs text-[var(--muted)]">
            Authenticated via existing{" "}
            <code className="font-[family-name:var(--font-mono)]">
              POST /api/v1/auth/rbac/login
            </code>
            . Research Mode remains available on public routes.
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
