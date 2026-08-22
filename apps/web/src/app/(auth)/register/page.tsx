"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";

import {
  AuthCard,
  AuthShell,
  OtpInput,
  PasswordStrengthMeter,
  ProviderButton,
  isValidEmail,
  mapAuthError,
  normalizeIndiaMobileInput,
  suggestedUsernameFromMobile,
} from "@/components/auth";
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
import { useAuthProviders } from "@/lib/auth/useAuthProviders";

type Mode = "chooser" | "create";
type CreateStep = "details" | "otp";

export default function RegisterPage() {
  const { oauthAvailable } = useAuthProviders();
  const googleProvider = useMemo(
    () =>
      oauthAvailable.find(
        (p) => String(p.provider || "").toUpperCase() === "GOOGLE",
      ) ?? null,
    [oauthAvailable],
  );

  const [mode, setMode] = useState<Mode>("chooser");
  const [step, setStep] = useState<CreateStep>("details");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const [doneMessage, setDoneMessage] = useState("");

  const [name, setName] = useState("");
  const [mobile, setMobile] = useState("");
  const [username, setUsername] = useState("");
  const [usernameEdited, setUsernameEdited] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [otpCode, setOtpCode] = useState("");
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);

  function onMobileChange(value: string) {
    setMobile(value);
    if (!usernameEdited) {
      setUsername(suggestedUsernameFromMobile(value));
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
          remember_me: false,
          next: "/dashboard",
        }),
      );
      window.location.assign(result.authorization_url);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onSendOtp(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError("Full name is required.");
      return;
    }
    if (!username.trim()) {
      setError("Username is required.");
      return;
    }
    const normalized = normalizeIndiaMobileInput(mobile);
    if (!normalized) {
      setError("Enter a valid India mobile number.");
      return;
    }
    if (!isValidEmail(email)) {
      setError("Enter a valid email or Gmail address.");
      return;
    }
    if (password !== confirm) {
      setError("Password confirmation does not match.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.registerMobileRequest(normalized);
      if (!envelope.result?.challenge_id) {
        throw new Error(envelope.error || "OTP request failed");
      }
      setChallengeId(envelope.result.challenge_id);
      const debug = envelope.result.sms?.debug_code;
      if (debug) setDevOtpHint(debug);
      setOtpCode("");
      setStep("otp");
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onCreateAccount(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!challengeId) {
      setError("Verify your mobile number first.");
      return;
    }
    const code = otpCode.replace(/\D/g, "");
    if (code.length !== 6) {
      setError("Enter the 6-digit code.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.registerMobileComplete({
        challenge_id: challengeId,
        code,
        password,
        confirm_password: confirm,
        name: name.trim(),
        username: username.trim(),
        email: email.trim(),
      });
      if (!envelope.ok) {
        throw new Error(envelope.error || "Registration failed");
      }
      setDoneMessage(
        String(
          (envelope.result as { message?: string } | undefined)?.message ||
            "Account created. You can sign in with your username, mobile OTP, or password.",
        ),
      );
      setDone(true);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  if (done) {
    return (
      <AuthShell>
        <AuthCard title="Account created" description={doneMessage}>
          <Stack gap={4}>
            <Link href="/login">
              <Button className="w-full">Back to sign in</Button>
            </Link>
          </Stack>
        </AuthCard>
      </AuthShell>
    );
  }

  if (mode === "chooser") {
    return (
      <AuthShell>
        <AuthCard
          title="Create account"
          description="Create an account with your details, or continue with Google."
        >
          <Stack gap={4}>
            {error ? (
              <ValidationMessage tone="error">{error}</ValidationMessage>
            ) : null}
            <Button
              type="button"
              className="w-full"
              onClick={() => {
                setError(null);
                setMode("create");
                setStep("details");
              }}
            >
              Create account
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
              Already have an account?{" "}
              <Link href="/login" className="text-[var(--accent)] underline">
                Sign in
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
        title="Create account"
        description={
          step === "details"
            ? "Enter your details. We will send an OTP to verify your mobile number."
            : "Enter the OTP sent to your mobile number to finish creating the account."
        }
      >
        <Stack gap={4}>
          {step === "details" ? (
            <form className="space-y-4" onSubmit={onSendOtp} noValidate>
              <FormField label="Full name" htmlFor="reg-name" required>
                <Input
                  id="reg-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                  required
                  disabled={pending}
                />
              </FormField>
              <FormField
                label="Mobile number"
                htmlFor="reg-mobile"
                required
                hint="India mobile. Username is suggested from this number and you can change it."
              >
                <Input
                  id="reg-mobile"
                  value={mobile}
                  onChange={(e) => onMobileChange(e.target.value)}
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="9826912345"
                  required
                  disabled={pending}
                />
              </FormField>
              <FormField
                label="Username"
                htmlFor="reg-username"
                required
                hint="Suggested from your mobile number. You may change it."
              >
                <Input
                  id="reg-username"
                  value={username}
                  onChange={(e) => {
                    setUsernameEdited(true);
                    setUsername(e.target.value);
                  }}
                  autoComplete="username"
                  required
                  disabled={pending}
                />
              </FormField>
              <FormField label="Email / Gmail" htmlFor="reg-email" required>
                <Input
                  id="reg-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                  disabled={pending}
                />
              </FormField>
              <FormField label="Password" htmlFor="reg-password" required>
                <PasswordInput
                  id="reg-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                  disabled={pending}
                />
              </FormField>
              <PasswordStrengthMeter password={password} />
              <FormField label="Confirm password" htmlFor="reg-confirm" required>
                <PasswordInput
                  id="reg-confirm"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  autoComplete="new-password"
                  required
                  disabled={pending}
                />
              </FormField>
              {error ? (
                <ValidationMessage tone="error">{error}</ValidationMessage>
              ) : null}
              <Button type="submit" disabled={pending} className="w-full">
                {pending ? "Sending…" : "Verify mobile"}
              </Button>
            </form>
          ) : (
            <form className="space-y-4" onSubmit={onCreateAccount} noValidate>
              {devOtpHint ? (
                <Alert variant="info" title="Development OTP">
                  Code: {devOtpHint}
                </Alert>
              ) : null}
              <OtpInput
                label="One-time code"
                value={otpCode}
                onChange={setOtpCode}
                disabled={pending}
                autoFocus
              />
              {error ? (
                <ValidationMessage tone="error">{error}</ValidationMessage>
              ) : null}
              <Button type="submit" disabled={pending} className="w-full">
                {pending ? "Creating…" : "Create account"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                disabled={pending}
                onClick={() => {
                  setError(null);
                  setStep("details");
                  setChallengeId(null);
                  setOtpCode("");
                  setDevOtpHint(null);
                }}
              >
                Change details
              </Button>
            </form>
          )}
          <Button
            type="button"
            variant="ghost"
            className="w-full"
            onClick={() => {
              setError(null);
              setMode("chooser");
            }}
          >
            Back
          </Button>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
