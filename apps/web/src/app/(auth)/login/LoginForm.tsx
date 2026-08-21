"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  AuthCard,
  AuthShell,
  MfaChallenge,
  ProviderButton,
  isPlausibleLoginIdentifier,
  mapAuthError,
  normalizeLoginIdentifier,
} from "@/components/auth";
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
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  extractMfaChallenge,
  navigateAfterLogin,
  persistEnterpriseSession,
} from "@/lib/auth/finishEnterpriseSession";
import { isAuthPublicPath, normalizePath } from "@/lib/auth/routeGuards";
import type { MfaChallengeInfo } from "@/lib/auth/types";
import { useAuthProviders } from "@/lib/auth/useAuthProviders";
import { env } from "@/lib/env";

type Step = "chooser" | "password";

/**
 * DSP client login:
 * chooser → Password | Continue with Google.
 * Email sign-in is Google OAuth only (no numeric email OTP on this page).
 * Mobile OTP remains on /mobile-login.
 * Uses existing Enterprise/RBAC endpoints only (no demo auth).
 */
export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { status, session } = useAuth();
  const { oauthAvailable } = useAuthProviders();

  const [step, setStep] = useState<Step>("chooser");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [mfaChallenge, setMfaChallenge] = useState<MfaChallengeInfo | null>(null);

  const nextPath = normalizePath(searchParams.get("next") || "/dashboard");
  const expired = searchParams.get("expired") === "1";
  const verified = searchParams.get("verified") === "1";

  const googleProvider = useMemo(
    () =>
      oauthAvailable.find(
        (p) => String(p.provider || "").toUpperCase() === "GOOGLE",
      ) ?? null,
    [oauthAvailable],
  );

  useEffect(() => {
    if (status === "authenticated" && session && !mfaChallenge) {
      router.replace(isAuthPublicPath(nextPath) ? "/dashboard" : nextPath);
    }
  }, [status, session, mfaChallenge, nextPath, router]);

  const finishEnterpriseLogin = useCallback(
    (result: Parameters<typeof persistEnterpriseSession>[0]) => {
      persistEnterpriseSession(result, rememberMe);
      const challenge = extractMfaChallenge(result);
      if (challenge) {
        setMfaChallenge(challenge);
        return;
      }
      navigateAfterLogin(nextPath);
    },
    [nextPath, rememberMe],
  );

  function goChooser() {
    setError(null);
    setFieldError(null);
    setStep("chooser");
  }

  async function onPasswordSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setFieldError(null);
    const id = normalizeLoginIdentifier(identifier);
    if (!id || !password) {
      setFieldError("Username / email / mobile and password are required.");
      return;
    }
    if (!isPlausibleLoginIdentifier(identifier)) {
      setFieldError("Enter a valid username, email, or India mobile number.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.login({
        identifier: id,
        password,
        remember_me: rememberMe,
      });
      if (!envelope.ok || !envelope.result?.tokens?.access_token) {
        throw new Error(envelope.error || "Login failed");
      }
      finishEnterpriseLogin(envelope.result);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onGoogle() {
    setPending(true);
    setError(null);
    try {
      const redirectUri = `${window.location.origin}/oauth/callback`;
      const envelope = await enterpriseAuthApi.oauthBegin("GOOGLE", redirectUri);
      const result = envelope.result;
      if (!result?.available || !result.authorization_url) {
        setError(
          result?.message ||
            "Google sign-in is unavailable. Configure OAuth credentials on the API.",
        );
        return;
      }
      sessionStorage.setItem(
        "dsp.oauth.pending",
        JSON.stringify({
          provider: "GOOGLE",
          state: result.state,
          redirect_uri: redirectUri,
          remember_me: rememberMe,
          next: nextPath,
        }),
      );
      window.location.assign(result.authorization_url);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  if (mfaChallenge) {
    return (
      <AuthShell>
        <AuthCard
          title="Verify your identity"
          description="One more step to finish signing in."
        >
          <MfaChallenge
            challenge={mfaChallenge}
            onDone={() => navigateAfterLogin(nextPath)}
          />
        </AuthCard>
      </AuthShell>
    );
  }

  if (step === "chooser") {
    return (
      <AuthShell>
        <AuthCard
          title={env.appName}
          description="How would you like to login?"
        >
          <Stack gap={4}>
            {expired ? (
              <Alert variant="warning" title="Session expired">
                Your session is no longer valid. Sign in again to continue where
                you left off.
              </Alert>
            ) : null}
            {verified ? (
              <Alert variant="info" title="Email verified">
                Your email was verified. Choose a sign-in method to continue.
              </Alert>
            ) : null}
            {error ? (
              <ValidationMessage tone="error">{error}</ValidationMessage>
            ) : null}

            <Button
              type="button"
              className="w-full"
              disabled={pending}
              onClick={() => {
                setError(null);
                setStep("password");
              }}
            >
              Login with Password
            </Button>

            <div
              className="flex items-center gap-3 text-xs uppercase tracking-wide text-[var(--muted)]"
              role="separator"
            >
              <span className="h-px flex-1 bg-[var(--border)]" aria-hidden />
              OR
              <span className="h-px flex-1 bg-[var(--border)]" aria-hidden />
            </div>

            <ProviderButton
              provider="GOOGLE"
              disabled={pending}
              onClick={() => void onGoogle()}
            />
            {!googleProvider ? (
              <p className="text-center text-xs text-[var(--muted)]">
                If Google is not configured on the API, you will see an error
                after clicking Continue with Google.
              </p>
            ) : null}

            <p className="text-center text-sm text-[var(--muted)]">
              Prefer mobile OTP?{" "}
              <Link
                href="/mobile-login"
                className="text-[var(--accent)] underline-offset-2 hover:underline"
              >
                Sign in with mobile
              </Link>
            </p>

            <p className="text-center text-sm text-[var(--muted)]">
              Don&apos;t have an account?{" "}
              <Link
                href="/signup"
                className="text-[var(--accent)] underline-offset-2 hover:underline"
              >
                Request access
              </Link>
            </p>
          </Stack>
        </AuthCard>
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <AuthCard
        title="Login with Password"
        description="Sign in with your username, email, or verified mobile number."
      >
        <Stack gap={4}>
          <form className="space-y-4" onSubmit={onPasswordSubmit} noValidate>
            <FormField
              label="Identifier"
              htmlFor="login-identifier"
              required
              hint="Username, email, or India mobile"
            >
              <Input
                id="login-identifier"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                autoComplete="username"
                placeholder="Username / Email / Mobile"
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
              {pending ? "Signing in…" : "Login"}
            </Button>
          </form>
          <Button
            type="button"
            variant="ghost"
            className="w-full"
            disabled={pending}
            onClick={goChooser}
          >
            Back
          </Button>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
