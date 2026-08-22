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
  isPlausibleLoginIdentifier,
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

type Step = "chooser" | "password" | "mobile-otp" | "identifier-otp";
type OtpPhase = "request" | "verify";

/**
 * Public login: username+password, mobile OTP, username/mobile OTP, Google.
 * Uses existing Enterprise/RBAC endpoints only (no demo auth).
 */
export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { status, session } = useAuth();
  const { oauthAvailable } = useAuthProviders();

  const [step, setStep] = useState<Step>("chooser");
  const [otpPhase, setOtpPhase] = useState<OtpPhase>("request");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mobile, setMobile] = useState("");
  const [otpIdentifier, setOtpIdentifier] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);
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
    setOtpPhase("request");
    setChallengeId(null);
    setOtpCode("");
    setDevOtpHint(null);
    setStep("chooser");
  }

  async function onPasswordSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setFieldError(null);
    const id = username.trim();
    if (!id || !password) {
      setFieldError("Username and password are required.");
      return;
    }
    if (!isPlausibleLoginIdentifier(id) || id.includes("@")) {
      setFieldError("Enter a valid username.");
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

  async function requestOtp(identifier: string) {
    setError(null);
    setDevOtpHint(null);
    const envelope = await enterpriseAuthApi.requestOtp(identifier);
    if (!envelope.result?.challenge_id) {
      throw new Error(envelope.error || "OTP request failed");
    }
    setChallengeId(envelope.result.challenge_id);
    const debug = envelope.result.sms?.debug_code;
    if (debug) setDevOtpHint(debug);
    setOtpCode("");
    setOtpPhase("verify");
  }

  async function onMobileOtpRequest(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const normalized = normalizeIndiaMobileInput(mobile);
    if (!normalized) {
      setError("Enter a valid India mobile number.");
      return;
    }
    setPending(true);
    try {
      await requestOtp(normalized);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onIdentifierOtpRequest(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const id = normalizeLoginIdentifier(otpIdentifier);
    if (!id || !isPlausibleLoginIdentifier(otpIdentifier) || id.includes("@")) {
      setError("Enter a valid username or India mobile number.");
      return;
    }
    setPending(true);
    try {
      await requestOtp(id);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onOtpVerify(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!challengeId) {
      setError("Request an OTP first.");
      return;
    }
    const code = otpCode.replace(/\D/g, "");
    if (code.length !== 6) {
      setError("Enter the 6-digit code.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.verifyOtp({
        challenge_id: challengeId,
        code,
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
        <AuthCard title={env.appName} description="How would you like to login?">
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
              Username and password
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="w-full"
              disabled={pending}
              onClick={() => {
                setError(null);
                setOtpPhase("request");
                setStep("mobile-otp");
              }}
            >
              Mobile number and OTP
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="w-full"
              disabled={pending}
              onClick={() => {
                setError(null);
                setOtpPhase("request");
                setStep("identifier-otp");
              }}
            >
              Username or mobile OTP
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
              Don&apos;t have an account?{" "}
              <Link
                href="/register"
                className="text-[var(--accent)] underline-offset-2 hover:underline"
              >
                Create account
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
          title="Sign in"
          description="Sign in with your username and password."
        >
          <Stack gap={4}>
            <form className="space-y-4" onSubmit={onPasswordSubmit} noValidate>
              <FormField label="Username" htmlFor="login-username" required>
                <Input
                  id="login-username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  placeholder="Username"
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

  const otpTitle =
    step === "mobile-otp" ? "Mobile number and OTP" : "Username or mobile OTP";
  const otpDescription =
    otpPhase === "request"
      ? step === "mobile-otp"
        ? "We will send a one-time code to your verified mobile number."
        : "Enter your username or mobile number. The code is sent to the verified mobile on the account."
      : "Enter the one-time code to sign in.";

  return (
    <AuthShell>
      <AuthCard title={otpTitle} description={otpDescription}>
        <Stack gap={4}>
          {otpPhase === "request" ? (
            <form
              className="space-y-4"
              onSubmit={
                step === "mobile-otp" ? onMobileOtpRequest : onIdentifierOtpRequest
              }
              noValidate
            >
              {step === "mobile-otp" ? (
                <FormField label="Mobile number" htmlFor="login-mobile" required>
                  <Input
                    id="login-mobile"
                    value={mobile}
                    onChange={(e) => setMobile(e.target.value)}
                    inputMode="tel"
                    autoComplete="tel"
                    placeholder="9826912345"
                    required
                    disabled={pending}
                  />
                </FormField>
              ) : (
                <FormField
                  label="Username or Mobile Number"
                  htmlFor="login-otp-identifier"
                  required
                >
                  <Input
                    id="login-otp-identifier"
                    value={otpIdentifier}
                    onChange={(e) => setOtpIdentifier(e.target.value)}
                    autoComplete="username"
                    placeholder="Username or mobile number"
                    required
                    disabled={pending}
                  />
                </FormField>
              )}
              {error ? (
                <ValidationMessage tone="error">{error}</ValidationMessage>
              ) : null}
              <Button type="submit" disabled={pending} className="w-full">
                {pending ? "Sending…" : "Send OTP"}
              </Button>
            </form>
          ) : (
            <form className="space-y-4" onSubmit={onOtpVerify} noValidate>
              {devOtpHint ? (
                <Alert variant="info" title="Development OTP">
                  Code: {devOtpHint}
                </Alert>
              ) : null}
              <OtpInput
                label="OTP"
                value={otpCode}
                onChange={setOtpCode}
                disabled={pending}
                autoFocus
              />
              <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
                <Checkbox
                  checked={rememberMe}
                  onCheckedChange={(v) => setRememberMe(v === true)}
                  aria-label="Remember me on this device"
                  disabled={pending}
                />
                Remember me
              </label>
              {error ? (
                <ValidationMessage tone="error">{error}</ValidationMessage>
              ) : null}
              <Button type="submit" disabled={pending} className="w-full">
                {pending ? "Signing in…" : "Sign in"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                disabled={pending}
                onClick={() => {
                  setError(null);
                  setOtpPhase("request");
                  setChallengeId(null);
                  setOtpCode("");
                  setDevOtpHint(null);
                }}
              >
                Use a different identifier
              </Button>
            </form>
          )}
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
