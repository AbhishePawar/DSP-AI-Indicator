"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  AuthCard,
  AuthShell,
  MfaChallenge,
  MobileIcon,
  EmailLinkIcon,
  PasskeyButton,
  ProviderButton,
  mapAuthError,
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

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, status, session } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const {
    oauthAvailable: oauthProviders,
    oauthComingSoon: comingSoonProviders,
    smsStatus: otpStatus,
    magicLinkStatus: emailLinkStatus,
    webauthnAvailable,
    webauthnMessage,
  } = useAuthProviders();
  const [passkeyPending, setPasskeyPending] = useState(false);
  const [mfaChallenge, setMfaChallenge] = useState<MfaChallengeInfo | null>(null);

  const nextPath = normalizePath(searchParams.get("next") || "/dashboard");
  const expired = searchParams.get("expired") === "1";
  const verified = searchParams.get("verified") === "1";

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

  async function onPasswordSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setFieldError(null);
    if (!identifier.trim() || !password) {
      setFieldError("Email/username and password are required.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.login({
        identifier: identifier.trim(),
        password,
        remember_me: rememberMe,
      });
      if (!envelope.ok || !envelope.result?.tokens?.access_token) {
        throw new Error(envelope.error || "Login failed");
      }
      finishEnterpriseLogin(envelope.result);
    } catch (enterpriseErr) {
      // Fall back to legacy / A009 RBAC accounts — preserves pre-existing
      // login for users not (yet) provisioned in the enterprise store.
      try {
        await login({
          username: identifier.trim(),
          password,
          rememberMe,
          useEnterprise: false,
          useRbac: true,
        });
        router.replace(isAuthPublicPath(nextPath) ? "/dashboard" : nextPath);
      } catch (fallbackErr) {
        setError(mapAuthError(fallbackErr ?? enterpriseErr));
      }
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

  async function onPasskey() {
    setPasskeyPending(true);
    setError(null);
    try {
      const envelope = await enterpriseAuthApi.webauthnAuthenticateBegin();
      if (!envelope.ok) {
        throw new Error(envelope.error || "Passkey sign-in is unavailable.");
      }
    } catch (err) {
      setError(
        webauthnMessage ||
          "Passkey sign-in is not yet configured on this deployment.",
      );
      void err;
    } finally {
      setPasskeyPending(false);
    }
  }

  if (mfaChallenge) {
    return (
      <AuthShell>
        <AuthCard title="Verify your identity" description="One more step to finish signing in.">
          <MfaChallenge challenge={mfaChallenge} onDone={() => navigateAfterLogin(nextPath)} />
        </AuthCard>
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <AuthCard
        title="Sign in"
        description="Institutional access via email/username, social SSO, mobile, or passkey. Destination is preserved after authentication."
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

          {oauthProviders.length || comingSoonProviders.length ? (
            <div className="grid gap-2">
              {oauthProviders.map((p) => (
                <ProviderButton
                  key={p.provider}
                  provider={p.provider}
                  disabled={pending}
                  onClick={() => onOAuth(p.provider)}
                />
              ))}
              {comingSoonProviders.map((p) => (
                <ProviderButton
                  key={`soon-${p.provider}`}
                  provider={p.provider}
                  comingSoon
                  disabled
                  title={p.message || "Coming Soon"}
                />
              ))}
            </div>
          ) : null}

          {oauthProviders.length || comingSoonProviders.length ? (
            <div className="flex items-center gap-3 text-xs uppercase tracking-wide text-[var(--muted)]" role="separator">
              <span className="h-px flex-1 bg-[var(--border)]" aria-hidden />
              OR
              <span className="h-px flex-1 bg-[var(--border)]" aria-hidden />
            </div>
          ) : null}

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
            {error ? <ValidationMessage tone="error">{error}</ValidationMessage> : null}
            <Button type="submit" disabled={pending} className="w-full">
              {pending ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          {otpStatus !== "unavailable" ||
          emailLinkStatus !== "unavailable" ||
          webauthnAvailable ? (
            <div className="space-y-2 border-t border-[var(--border)] pt-4">
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
                Alternative login
              </p>
              <div className="grid gap-2">
                {otpStatus !== "unavailable" ? (
                  <Button asChild variant="secondary" className="w-full justify-center">
                    <Link href={`/mobile-login?next=${encodeURIComponent(nextPath)}`}>
                      <MobileIcon />
                      <span>
                        {otpStatus === "coming_soon"
                          ? "Continue with Mobile Number — Coming Soon"
                          : "Continue with Mobile Number"}
                      </span>
                    </Link>
                  </Button>
                ) : null}
                {emailLinkStatus !== "unavailable" ? (
                  <Button asChild variant="secondary" className="w-full justify-center">
                    <Link href={`/email-login?next=${encodeURIComponent(nextPath)}`}>
                      <EmailLinkIcon />
                      <span>
                        {emailLinkStatus === "coming_soon"
                          ? "Continue with Email Link — Coming Soon"
                          : "Continue with Email Link"}
                      </span>
                    </Link>
                  </Button>
                ) : null}
                <PasskeyButton
                  serverAvailable={webauthnAvailable}
                  serverMessage={webauthnMessage}
                  pending={passkeyPending}
                  onAuthenticate={onPasskey}
                />
              </div>
            </div>
          ) : null}

          <p className="text-center text-sm text-[var(--muted)]">
            Don&apos;t have an account?{" "}
            <Link
              href="/signup"
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Request access
            </Link>
            {" · "}
            <Link
              href="/register"
              className="text-[var(--accent)] underline-offset-2 hover:underline"
            >
              Register
            </Link>
          </p>
          <p className="text-xs text-[var(--muted)]">
            Research Mode content on public routes does not require sign-in.
            Providers without credentials are hidden; intentionally disabled
            providers show Coming Soon.
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
