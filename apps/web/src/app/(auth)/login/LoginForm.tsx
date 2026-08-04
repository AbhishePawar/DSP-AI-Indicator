"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

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
import { enterpriseAuthApi, type ProviderStatus } from "@/lib/api/enterpriseAuth";
import { useAuth } from "@/lib/auth/AuthProvider";
import { isAuthPublicPath, normalizePath } from "@/lib/auth/routeGuards";
import {
  persistSession,
  sessionFromRbacLogin,
} from "@/lib/auth/sessionStore";

type Mode = "password" | "otp";

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, status, session } = useAuth();
  const [mode, setMode] = useState<Mode>("password");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [mobile, setMobile] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [oauthProviders, setOauthProviders] = useState<ProviderStatus[]>([]);
  const [smsAvailable, setSmsAvailable] = useState(true);
  const [smsMessage, setSmsMessage] = useState<string | null>(null);

  const nextPath = normalizePath(searchParams.get("next") || "/dashboard");
  const expired = searchParams.get("expired") === "1";
  const verified = searchParams.get("verified") === "1";

  useEffect(() => {
    if (status === "authenticated" && session) {
      router.replace(isAuthPublicPath(nextPath) ? "/dashboard" : nextPath);
    }
  }, [status, session, nextPath, router]);

  useEffect(() => {
    let cancelled = false;
    enterpriseAuthApi
      .providers()
      .then((envelope) => {
        if (cancelled || !envelope.result) return;
        setOauthProviders(envelope.result.oauth || []);
        setSmsAvailable(Boolean(envelope.result.sms?.available));
        if (!envelope.result.sms?.available) {
          setSmsMessage(
            "Mobile OTP unavailable — SMS provider credentials are not configured.",
          );
        }
      })
      .catch(() => {
        if (!cancelled) {
          setOauthProviders([
            { provider: "GOOGLE", available: false, message: "Provider status unavailable." },
            { provider: "MICROSOFT", available: false, message: "Provider status unavailable." },
            { provider: "FACEBOOK", available: false, message: "Provider status unavailable." },
          ]);
          setSmsAvailable(false);
          setSmsMessage("Unable to load provider status from API.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const finishEnterpriseLogin = useCallback(
    (result: Parameters<typeof sessionFromRbacLogin>[0] & {
      csrf_token?: string;
      cookie_auth?: boolean;
    }) => {
      const next = sessionFromRbacLogin(result, rememberMe);
      persistSession(next);
      window.location.assign(isAuthPublicPath(nextPath) ? "/dashboard" : nextPath);
    },
    [nextPath, rememberMe],
  );

  async function onPasswordSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setFieldError(null);
    try {
      if (!identifier.trim() || !password) {
        setFieldError("Email/username and password are required.");
        return;
      }
      await login({
        username: identifier.trim(),
        password,
        rememberMe,
        useEnterprise: true,
        useRbac: true,
      });
      router.replace(isAuthPublicPath(nextPath) ? "/dashboard" : nextPath);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onRequestOtp() {
    setPending(true);
    setError(null);
    setDevOtpHint(null);
    try {
      const envelope = await enterpriseAuthApi.requestOtp(mobile.trim());
      if (!envelope.result?.challenge_id) {
        throw new Error(envelope.error || "OTP request failed");
      }
      setChallengeId(envelope.result.challenge_id);
      const debug = envelope.result.sms?.debug_code;
      if (debug) {
        setDevOtpHint(`Dev SMS adapter code: ${debug}`);
      }
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onVerifyOtp(event: FormEvent) {
    event.preventDefault();
    if (!challengeId) {
      setFieldError("Request an OTP first.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const envelope = await enterpriseAuthApi.verifyOtp({
        challenge_id: challengeId,
        code: otpCode.trim(),
        remember_me: rememberMe,
      });
      if (!envelope.ok || !envelope.result) {
        throw new Error(envelope.error || "OTP verification failed");
      }
      finishEnterpriseLogin(
        envelope.result as Parameters<typeof sessionFromRbacLogin>[0] & {
          csrf_token?: string;
          cookie_auth?: boolean;
        },
      );
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onOAuth(provider: string) {
    setPending(true);
    setError(null);
    try {
      const redirectUri = `${window.location.origin}/oauth/callback`;
      const envelope = await enterpriseAuthApi.oauthBegin(provider, redirectUri);
      const result = envelope.result;
      if (!result?.available || !result.authorization_url) {
        setError(
          result?.message ||
            `${provider} sign-in is unavailable. Configure OAuth credentials on the API.`,
        );
        return;
      }
      sessionStorage.setItem(
        "dsp.oauth.pending",
        JSON.stringify({
          provider,
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

  const providerLabel = (p: string) => {
    switch (p.toUpperCase()) {
      case "GOOGLE":
        return "Continue with Google";
      case "MICROSOFT":
        return "Continue with Microsoft";
      case "FACEBOOK":
        return "Continue with Facebook";
      default:
        return `Continue with ${p}`;
    }
  };

  return (
    <AuthShell>
      <AuthCard
        title="Sign in"
        description="Institutional access via email/username, social SSO, or mobile OTP. Destination is preserved after authentication."
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
              Your email was verified. Sign in with your password to continue.
            </Alert>
          ) : null}

          <div className="grid gap-2">
            {oauthProviders.map((p) => (
              <Button
                key={p.provider}
                type="button"
                variant="secondary"
                className="w-full"
                disabled={pending || !p.available}
                onClick={() => onOAuth(p.provider)}
                title={p.available ? undefined : p.message || "Unavailable"}
              >
                {p.available
                  ? providerLabel(p.provider)
                  : `${providerLabel(p.provider)} (unavailable)`}
              </Button>
            ))}
            {!oauthProviders.length ? (
              <p className="text-xs text-[var(--muted)]">
                Loading social sign-in options…
              </p>
            ) : null}
          </div>

          <div className="flex gap-2 text-sm">
            <button
              type="button"
              className={
                mode === "password"
                  ? "font-medium text-[var(--accent)] underline"
                  : "text-[var(--muted)]"
              }
              onClick={() => setMode("password")}
            >
              Email / Username
            </button>
            <span className="text-[var(--muted)]">·</span>
            <button
              type="button"
              className={
                mode === "otp"
                  ? "font-medium text-[var(--accent)] underline"
                  : "text-[var(--muted)]"
              }
              onClick={() => setMode("otp")}
            >
              Mobile OTP
            </button>
          </div>

          {mode === "password" ? (
            <form className="space-y-4" onSubmit={onPasswordSubmit} noValidate>
              <FormField label="Email or username" htmlFor="login-identifier" required>
                <Input
                  id="login-identifier"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
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
          ) : (
            <form className="space-y-4" onSubmit={onVerifyOtp} noValidate>
              {!smsAvailable ? (
                <Alert variant="warning" title="Mobile OTP unavailable">
                  {smsMessage ||
                    "SMS provider is not configured. Use email/username sign-in or configure Twilio/MSG91."}
                </Alert>
              ) : null}
              <FormField label="India mobile (+91)" htmlFor="login-mobile" required>
                <Input
                  id="login-mobile"
                  value={mobile}
                  onChange={(e) => setMobile(e.target.value)}
                  placeholder="+9198XXXXXXXX"
                  autoComplete="tel"
                  required
                  disabled={pending || !smsAvailable}
                />
              </FormField>
              <Button
                type="button"
                variant="secondary"
                className="w-full"
                disabled={pending || !smsAvailable || !mobile.trim()}
                onClick={onRequestOtp}
              >
                Send OTP
              </Button>
              {devOtpHint ? (
                <Alert variant="info" title="Development SMS">
                  {devOtpHint}
                </Alert>
              ) : null}
              <FormField label="6-digit OTP" htmlFor="login-otp" required>
                <Input
                  id="login-otp"
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  required
                  disabled={pending || !challengeId}
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
                disabled={pending || !challengeId}
                className="w-full"
              >
                {pending ? "Verifying…" : "Verify & sign in"}
              </Button>
            </form>
          )}

          <p className="text-center text-sm text-[var(--muted)]">
            Need an account?{" "}
            <Link
              href="/register"
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Register
            </Link>
            {" · "}
            <Link
              href="/signup"
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Request access
            </Link>
          </p>
          <p className="text-xs text-[var(--muted)]">
            Research Mode content on public routes does not require sign-in.
            OAuth buttons stay disabled when vendor credentials are absent.
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
