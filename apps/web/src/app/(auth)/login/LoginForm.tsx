"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  AuthCard,
  AuthShell,
  MfaChallenge,
  OtpInput,
  ProviderButton,
  ResendCountdown,
  isPlausibleLoginIdentifier,
  isValidEmail,
  mapAuthError,
  normalizeIndiaMobileInput,
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

type Step = "chooser" | "password" | "otp-request" | "otp-verify";

/**
 * DSP client login — frozen UX:
 * chooser → Password | OTP | Continue with Google.
 * Uses Phase 2B enterprise endpoints only (no demo auth).
 */
export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { status, session } = useAuth();
  const { oauthAvailable } = useAuthProviders();

  const [step, setStep] = useState<Step>("chooser");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [otpIdentifier, setOtpIdentifier] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [otpChannel, setOtpChannel] = useState<"email" | "mobile" | null>(null);
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

  function resolveOtpIdentifier(raw: string): string | null {
    const trimmed = raw.trim();
    if (!trimmed) return null;
    if (trimmed.includes("@")) {
      return isValidEmail(trimmed) ? trimmed.toLowerCase() : null;
    }
    return normalizeIndiaMobileInput(trimmed);
  }

  async function onSendOtp(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setFieldError(null);
    const id = resolveOtpIdentifier(otpIdentifier);
    if (!id) {
      setFieldError("Enter a valid email or India mobile number (+91).");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.requestOtp(id);
      if (!envelope.result?.challenge_id) {
        throw new Error(envelope.error || "OTP request failed");
      }
      setChallengeId(envelope.result.challenge_id);
      const channel =
        envelope.result.channel === "email" || envelope.result.channel === "mobile"
          ? envelope.result.channel
          : id.includes("@")
            ? "email"
            : "mobile";
      setOtpChannel(channel);
      setOtpCode("");
      setStep("otp-verify");
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onResendOtp() {
    setError(null);
    const id = resolveOtpIdentifier(otpIdentifier);
    if (!id) {
      setError("Enter a valid email or India mobile number (+91).");
      return;
    }
    try {
      const envelope = await enterpriseAuthApi.resendOtp(id);
      if (envelope.result?.challenge_id) {
        setChallengeId(envelope.result.challenge_id);
      }
    } catch (err) {
      setError(mapAuthError(err));
    }
  }

  async function onVerifyOtp(code: string) {
    if (!challengeId) {
      setError("Request an OTP first.");
      return;
    }
    const trimmed = code.replace(/\D/g, "");
    if (trimmed.length !== 6) {
      setError("Enter the 6-digit code.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const envelope = await enterpriseAuthApi.verifyOtp({
        challenge_id: challengeId,
        code: trimmed,
        remember_me: rememberMe,
      });
      if (!envelope.ok || !envelope.result) {
        throw new Error(envelope.error || "OTP verification failed");
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
            <Button
              type="button"
              variant="secondary"
              className="w-full"
              disabled={pending}
              onClick={() => {
                setError(null);
                setStep("otp-request");
              }}
            >
              Login with OTP
            </Button>

            <div
              className="flex items-center gap-3 text-xs uppercase tracking-wide text-[var(--muted)]"
              role="separator"
            >
              <span className="h-px flex-1 bg-[var(--border)]" aria-hidden />
              OR
              <span className="h-px flex-1 bg-[var(--border)]" aria-hidden />
            </div>

            {googleProvider ? (
              <ProviderButton
                provider="GOOGLE"
                disabled={pending}
                onClick={() => void onGoogle()}
              />
            ) : (
              <Button
                type="button"
                variant="secondary"
                className="w-full"
                disabled
                title="Google sign-in is not configured on this deployment."
              >
                Continue with Google
              </Button>
            )}

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

  if (step === "password") {
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

  if (step === "otp-request") {
    return (
      <AuthShell>
        <AuthCard
          title="Login with OTP"
          description="We'll send a one-time code to your verified email or India mobile number."
        >
          <Stack gap={4}>
            <form className="space-y-4" onSubmit={onSendOtp} noValidate>
              <FormField
                label="Email or Mobile"
                htmlFor="otp-identifier"
                required
                hint="Email address or +91 mobile starting 6–9"
              >
                <Input
                  id="otp-identifier"
                  value={otpIdentifier}
                  onChange={(e) => setOtpIdentifier(e.target.value)}
                  autoComplete="username"
                  placeholder="email@example.com or 9876543210"
                  required
                  disabled={pending}
                />
              </FormField>
              <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
                <Checkbox
                  checked={rememberMe}
                  onCheckedChange={(v) => setRememberMe(v === true)}
                  aria-label="Remember me on this device"
                  disabled={pending}
                />
                Remember me
              </label>
              {fieldError ? (
                <ValidationMessage tone="error">{fieldError}</ValidationMessage>
              ) : null}
              {error ? (
                <ValidationMessage tone="error">{error}</ValidationMessage>
              ) : null}
              <Button
                type="submit"
                className="w-full"
                disabled={pending || !otpIdentifier.trim()}
              >
                {pending ? "Sending…" : "Send OTP"}
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

  // otp-verify
  const destinationHint =
    otpChannel === "email"
      ? otpIdentifier.trim().toLowerCase()
      : resolveOtpIdentifier(otpIdentifier) || otpIdentifier.trim();

  return (
    <AuthShell>
      <AuthCard
        title="Enter OTP"
        description={`Enter the 6-digit code sent to ${destinationHint}.`}
      >
        <Stack gap={4}>
          <OtpInput
            label="One-time code"
            value={otpCode}
            onChange={setOtpCode}
            onComplete={(code) => {
              if (!pending) void onVerifyOtp(code);
            }}
            disabled={pending}
            autoFocus
          />
          {error ? (
            <ValidationMessage tone="error">{error}</ValidationMessage>
          ) : null}
          <Button
            type="button"
            className="w-full"
            disabled={pending || otpCode.replace(/\D/g, "").length !== 6}
            onClick={() => void onVerifyOtp(otpCode)}
          >
            {pending ? "Verifying…" : "Verify & Login"}
          </Button>
          <ResendCountdown
            seconds={30}
            disabled={pending}
            onResend={onResendOtp}
          />
          <Button
            type="button"
            variant="ghost"
            className="w-full"
            disabled={pending}
            onClick={() => {
              setError(null);
              setOtpCode("");
              setChallengeId(null);
              setStep("otp-request");
            }}
          >
            Back
          </Button>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
