"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import {
  AuthCard,
  AuthShell,
  OtpInput,
  PasswordStrengthMeter,
  isValidEmail,
  mapAuthError,
  normalizeIndiaMobileInput,
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

type Mode = "chooser" | "username" | "mobile" | "email";
type MobileStep = "request" | "verify";

export default function RegisterPage() {
  const [mode, setMode] = useState<Mode>("chooser");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const [doneMessage, setDoneMessage] = useState("");
  const [verifyToken, setVerifyToken] = useState<string | null>(null);

  // Username registration
  const [username, setUsername] = useState("");
  const [usernameName, setUsernameName] = useState("");
  const [usernamePassword, setUsernamePassword] = useState("");
  const [usernameConfirm, setUsernameConfirm] = useState("");

  // Mobile registration
  const [mobileStep, setMobileStep] = useState<MobileStep>("request");
  const [mobile, setMobile] = useState("");
  const [mobileName, setMobileName] = useState("");
  const [mobileUsername, setMobileUsername] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [otpCode, setOtpCode] = useState("");
  const [mobilePassword, setMobilePassword] = useState("");
  const [mobileConfirm, setMobileConfirm] = useState("");
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);

  // Email registration (existing)
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [emailUsername, setEmailUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");

  function resetFlowMessages() {
    setError(null);
    setDone(false);
    setDoneMessage("");
    setVerifyToken(null);
  }

  function goChooser() {
    resetFlowMessages();
    setMode("chooser");
    setMobileStep("request");
    setChallengeId(null);
    setOtpCode("");
    setDevOtpHint(null);
  }

  async function onUsernameSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!username.trim()) {
      setError("Username is required.");
      return;
    }
    if (usernamePassword !== usernameConfirm) {
      setError("Password confirmation does not match.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.registerUsername({
        username: username.trim(),
        password: usernamePassword,
        confirm_password: usernameConfirm,
        name: usernameName.trim() || undefined,
      });
      if (!envelope.ok) {
        throw new Error(envelope.error || "Registration failed");
      }
      setDoneMessage(
        String(
          (envelope.result as { message?: string } | undefined)?.message ||
            "Account created. You can sign in with your username and password.",
        ),
      );
      setDone(true);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onMobileRequest(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setDevOtpHint(null);
    const normalized = normalizeIndiaMobileInput(mobile);
    if (!normalized) {
      setError("Enter a valid India mobile number.");
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
      setMobileStep("verify");
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onMobileComplete(event: FormEvent) {
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
    if (mobilePassword !== mobileConfirm) {
      setError("Password confirmation does not match.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.registerMobileComplete({
        challenge_id: challengeId,
        code,
        password: mobilePassword,
        confirm_password: mobileConfirm,
        name: mobileName.trim() || undefined,
        username: mobileUsername.trim() || undefined,
      });
      if (!envelope.ok) {
        throw new Error(envelope.error || "Registration failed");
      }
      setDoneMessage(
        String(
          (envelope.result as { message?: string } | undefined)?.message ||
            "Account created. You can sign in with your mobile number and password.",
        ),
      );
      setDone(true);
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onEmailSubmit(event: FormEvent) {
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
        username: emailUsername.trim() || undefined,
      });
      if (!envelope.ok) {
        throw new Error(envelope.error || "Registration failed");
      }
      const token = (envelope.result as { verification_token?: string } | undefined)
        ?.verification_token;
      if (token) setVerifyToken(token);
      setDoneMessage(
        String(
          (envelope.result as { message?: string } | undefined)?.message ||
            "Registration accepted. Verify email before sign-in.",
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
          description="Choose how you want to register. You do not need both username and mobile."
        >
          <Stack gap={4}>
            <Button
              type="button"
              className="w-full"
              onClick={() => {
                resetFlowMessages();
                setMode("username");
              }}
            >
              Create account with Username
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="w-full"
              onClick={() => {
                resetFlowMessages();
                setMode("mobile");
                setMobileStep("request");
              }}
            >
              Create account with Mobile
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full"
              onClick={() => {
                resetFlowMessages();
                setMode("email");
              }}
            >
              Create account with Email
            </Button>
            <p className="text-center text-sm text-[var(--muted)]">
              Enterprise onboarding?{" "}
              <Link href="/signup" className="text-[var(--accent)] underline">
                Request access
              </Link>
            </p>
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

  if (mode === "username") {
    return (
      <AuthShell>
        <AuthCard
          title="Create account with Username"
          description="Choose a username and password. You can sign in with username + password."
        >
          <Stack gap={4}>
            <form className="space-y-4" onSubmit={onUsernameSubmit} noValidate>
              <FormField label="Username" htmlFor="reg-uname" required>
                <Input
                  id="reg-uname"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                  disabled={pending}
                  placeholder="your_username"
                />
              </FormField>
              <FormField label="Display name" htmlFor="reg-uname-name" hint="Optional">
                <Input
                  id="reg-uname-name"
                  value={usernameName}
                  onChange={(e) => setUsernameName(e.target.value)}
                  disabled={pending}
                />
              </FormField>
              <FormField label="Password" htmlFor="reg-uname-password" required>
                <PasswordInput
                  id="reg-uname-password"
                  value={usernamePassword}
                  onChange={(e) => setUsernamePassword(e.target.value)}
                  autoComplete="new-password"
                  required
                  disabled={pending}
                />
              </FormField>
              <PasswordStrengthMeter password={usernamePassword} />
              <FormField label="Confirm password" htmlFor="reg-uname-confirm" required>
                <PasswordInput
                  id="reg-uname-confirm"
                  value={usernameConfirm}
                  onChange={(e) => setUsernameConfirm(e.target.value)}
                  autoComplete="new-password"
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
            <Button type="button" variant="ghost" className="w-full" onClick={goChooser}>
              Back
            </Button>
          </Stack>
        </AuthCard>
      </AuthShell>
    );
  }

  if (mode === "mobile") {
    return (
      <AuthShell>
        <AuthCard
          title="Create account with Mobile"
          description={
            mobileStep === "request"
              ? "Verify your India mobile number with OTP, then choose a password."
              : "Enter the OTP and choose a password for mobile sign-in."
          }
        >
          <Stack gap={4}>
            {mobileStep === "request" ? (
              <form className="space-y-4" onSubmit={onMobileRequest} noValidate>
                <FormField
                  label="Mobile number"
                  htmlFor="reg-mobile"
                  required
                  hint="India mobile (+91 / 10 digits starting 6–9)"
                >
                  <Input
                    id="reg-mobile"
                    value={mobile}
                    onChange={(e) => setMobile(e.target.value)}
                    inputMode="tel"
                    autoComplete="tel"
                    placeholder="9876543210"
                    required
                    disabled={pending}
                  />
                </FormField>
                <FormField label="Display name" htmlFor="reg-mobile-name" hint="Optional">
                  <Input
                    id="reg-mobile-name"
                    value={mobileName}
                    onChange={(e) => setMobileName(e.target.value)}
                    disabled={pending}
                  />
                </FormField>
                {error ? (
                  <ValidationMessage tone="error">{error}</ValidationMessage>
                ) : null}
                <Button type="submit" disabled={pending} className="w-full">
                  {pending ? "Sending…" : "Send OTP"}
                </Button>
              </form>
            ) : (
              <form className="space-y-4" onSubmit={onMobileComplete} noValidate>
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
                <FormField
                  label="Username"
                  htmlFor="reg-mobile-username"
                  hint="Optional — defaults to a phone-based username"
                >
                  <Input
                    id="reg-mobile-username"
                    value={mobileUsername}
                    onChange={(e) => setMobileUsername(e.target.value)}
                    disabled={pending}
                  />
                </FormField>
                <FormField label="Password" htmlFor="reg-mobile-password" required>
                  <PasswordInput
                    id="reg-mobile-password"
                    value={mobilePassword}
                    onChange={(e) => setMobilePassword(e.target.value)}
                    autoComplete="new-password"
                    required
                    disabled={pending}
                  />
                </FormField>
                <PasswordStrengthMeter password={mobilePassword} />
                <FormField label="Confirm password" htmlFor="reg-mobile-confirm" required>
                  <PasswordInput
                    id="reg-mobile-confirm"
                    value={mobileConfirm}
                    onChange={(e) => setMobileConfirm(e.target.value)}
                    autoComplete="new-password"
                    required
                    disabled={pending}
                  />
                </FormField>
                {error ? (
                  <ValidationMessage tone="error">{error}</ValidationMessage>
                ) : null}
                <Button type="submit" disabled={pending} className="w-full">
                  {pending ? "Creating…" : "Verify & create account"}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  className="w-full"
                  disabled={pending}
                  onClick={() => {
                    setError(null);
                    setMobileStep("request");
                    setChallengeId(null);
                    setOtpCode("");
                  }}
                >
                  Change mobile number
                </Button>
              </form>
            )}
            <Button type="button" variant="ghost" className="w-full" onClick={goChooser}>
              Back
            </Button>
          </Stack>
        </AuthCard>
      </AuthShell>
    );
  }

  // Email registration (existing path)
  return (
    <AuthShell>
      <AuthCard
        title="Create account with Email"
        description="Self-service registration with email verification."
      >
        <Stack gap={4}>
          <form className="space-y-4" onSubmit={onEmailSubmit} noValidate>
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
                value={emailUsername}
                onChange={(e) => setEmailUsername(e.target.value)}
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
              {pending ? "Creating…" : "Create account"}
            </Button>
          </form>
          <Button type="button" variant="ghost" className="w-full" onClick={goChooser}>
            Back
          </Button>
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
