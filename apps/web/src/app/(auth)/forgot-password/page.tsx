"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import {
  AuthCard,
  AuthShell,
  OtpInput,
  PasswordStrengthMeter,
  isPlausibleLoginIdentifier,
  mapAuthError,
  normalizeLoginIdentifier,
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
import { SUPPORT_CONTACT } from "@/lib/commercial";

type Step = "identifier" | "otp" | "password" | "emailSent" | "emailUnavailable" | "done";

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<Step>("identifier");
  const [identifier, setIdentifier] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [otpCode, setOtpCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);

  async function onRequest(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const id = normalizeLoginIdentifier(identifier);
    if (!id || !isPlausibleLoginIdentifier(identifier)) {
      setError("Enter a valid username, email address or India mobile number.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.forgotPassword(id);
      if (!envelope.ok) {
        throw new Error(envelope.error || "Unable to start password recovery.");
      }
      if (id.includes("@")) {
        // The backend reports provider availability before account lookup, so
        // this status does not reveal whether the email belongs to an account.
        setStep(
          envelope.result?.recovery_available === false
            ? "emailUnavailable"
            : "emailSent",
        );
        return;
      }
      const cid = envelope.result?.challenge_id;
      if (!cid) {
        throw new Error(envelope.error || "Unable to start password recovery.");
      }
      setChallengeId(cid);
      const debug = envelope.result?.sms?.debug_code;
      if (debug) setDevOtpHint(debug);
      setOtpCode("");
      setStep("otp");
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onVerifyOtp(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const code = otpCode.replace(/\D/g, "");
    if (code.length !== 6) {
      setError("Enter the 6-digit code.");
      return;
    }
    setStep("password");
  }

  async function onReset(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!challengeId) {
      setError("Request a verification code first.");
      return;
    }
    const code = otpCode.replace(/\D/g, "");
    if (password !== confirm) {
      setError("Password confirmation does not match.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.resetPasswordOtp({
        challenge_id: challengeId,
        code,
        new_password: password,
        confirm_password: confirm,
      });
      if (!envelope.ok) {
        throw new Error(envelope.error || "Unable to change password.");
      }
      setStep("done");
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell>
      <AuthCard
        title="Forgot password"
        description="Recover access using the email address or verified mobile number already stored on your account."
      >
        <Stack gap={4}>
          {step === "emailUnavailable" ? (
            <>
              <Alert variant="info" title="Email recovery unavailable">
                Email password recovery is not configured for this deployment.
                Contact your administrator or support team to regain access.
              </Alert>
              <Link href="/login">
                <Button className="w-full">Back to sign in</Button>
              </Link>
            </>
          ) : null}

          {step === "emailSent" ? (
            <>
              <Alert variant="success" title="Check your email">
                If an account with that email exists, a password reset link has been sent.
                Check your inbox and spam folder.
              </Alert>
              <Link href="/login">
                <Button className="w-full">Back to sign in</Button>
              </Link>
            </>
          ) : null}

          {step === "done" ? (
            <>
              <Alert variant="success" title="Password updated">
                You can sign in with your new password.
              </Alert>
              <Link href="/login">
                <Button className="w-full">Back to sign in</Button>
              </Link>
            </>
          ) : null}

          {step === "identifier" ? (
            <form className="space-y-4" onSubmit={onRequest} noValidate>
              <FormField
                label="Username, Email or Mobile Number"
                htmlFor="forgot-identifier"
                required
              >
                <Input
                  id="forgot-identifier"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  autoComplete="username"
                  required
                  disabled={pending}
                />
              </FormField>
              {error ? (
                <ValidationMessage tone="error">{error}</ValidationMessage>
              ) : null}
              <Button type="submit" className="w-full" disabled={pending}>
                {pending ? "Sending…" : identifier.includes("@") ? "Send reset link" : "Send OTP"}
              </Button>
            </form>
          ) : null}

          {step === "otp" ? (
            <form className="space-y-4" onSubmit={onVerifyOtp} noValidate>
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
              {error ? (
                <ValidationMessage tone="error">{error}</ValidationMessage>
              ) : null}
              <Button type="submit" className="w-full" disabled={pending}>
                Continue
              </Button>
            </form>
          ) : null}

          {step === "password" ? (
            <form className="space-y-4" onSubmit={onReset} noValidate>
              <FormField label="New password" htmlFor="forgot-password" required>
                <PasswordInput
                  id="forgot-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                  disabled={pending}
                />
              </FormField>
              <PasswordStrengthMeter password={password} />
              <FormField
                label="Confirm new password"
                htmlFor="forgot-confirm"
                required
              >
                <PasswordInput
                  id="forgot-confirm"
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
              <Button type="submit" className="w-full" disabled={pending}>
                {pending ? "Updating…" : "Change password"}
              </Button>
            </form>
          ) : null}

          {step !== "done" && step !== "emailSent" && step !== "emailUnavailable" ? (
            <Link href="/login" className="text-center text-sm text-[var(--accent)] underline">
              Back to sign in
            </Link>
          ) : null}
          <p className="text-xs text-[var(--muted)]">
            {SUPPORT_CONTACT.channelsPublished
              ? `Support: ${SUPPORT_CONTACT.email}`
              : SUPPORT_CONTACT.unpublishedNote}
          </p>
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
