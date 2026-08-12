"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";

import { AuthCard, AuthShell, MfaChallenge, OtpInput, ResendCountdown, mapAuthError } from "@/components/auth";
import {
  Alert,
  Button,
  Checkbox,
  FormField,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Stack,
  ValidationMessage,
} from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import { normalizePath } from "@/lib/auth/routeGuards";
import {
  extractMfaChallenge,
  navigateAfterLogin,
  persistEnterpriseSession,
} from "@/lib/auth/finishEnterpriseSession";
import type { MfaChallengeInfo } from "@/lib/auth/types";
import { useAuthProviders } from "@/lib/auth/useAuthProviders";

const COUNTRY_CODES = [
  { code: "+91", label: "+91 India" },
  { code: "+1", label: "+1 US / Canada" },
  { code: "+44", label: "+44 United Kingdom" },
  { code: "+61", label: "+61 Australia" },
  { code: "+971", label: "+971 UAE" },
  { code: "+65", label: "+65 Singapore" },
  { code: "+81", label: "+81 Japan" },
  { code: "+49", label: "+49 Germany" },
  { code: "+33", label: "+33 France" },
  { code: "+86", label: "+86 China" },
] as const;

type Step = "enter" | "verify";

export default function MobileLoginForm() {
  const searchParams = useSearchParams();
  const nextPath = normalizePath(searchParams.get("next") || "/dashboard");

  const [step, setStep] = useState<Step>("enter");
  const [countryCode, setCountryCode] = useState<string>("+91");
  const [mobile, setMobile] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const { smsStatus: otpStatus, smsMessage: statusMessage } = useAuthProviders();
  const [mfaChallenge, setMfaChallenge] = useState<MfaChallengeInfo | null>(null);

  const fullMobile = `${countryCode}${mobile.replace(/\D/g, "")}`;

  async function onSendOtp(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setDevOtpHint(null);
    if (mobile.replace(/\D/g, "").length < 6) {
      setError("Enter a valid mobile number.");
      return;
    }
    setPending(true);
    try {
      const envelope = await enterpriseAuthApi.requestOtp(fullMobile);
      if (!envelope.result?.challenge_id) {
        throw new Error(envelope.error || "OTP request failed");
      }
      setChallengeId(envelope.result.challenge_id);
      const debug = envelope.result.sms?.debug_code;
      if (debug) setDevOtpHint(`Dev SMS adapter code: ${debug}`);
      setStep("verify");
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  async function onResend() {
    setError(null);
    try {
      const envelope = await enterpriseAuthApi.resendOtp(fullMobile);
      if (envelope.result?.challenge_id) setChallengeId(envelope.result.challenge_id);
      const debug = envelope.result?.sms?.debug_code;
      if (debug) setDevOtpHint(`Dev SMS adapter code: ${debug}`);
    } catch (err) {
      setError(mapAuthError(err));
    }
  }

  async function onVerify(code: string) {
    if (!challengeId) {
      setError("Request an OTP first.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const envelope = await enterpriseAuthApi.verifyOtp({
        challenge_id: challengeId,
        code: code.trim(),
        remember_me: rememberMe,
      });
      if (!envelope.ok || !envelope.result) {
        throw new Error(envelope.error || "OTP verification failed");
      }
      persistEnterpriseSession(envelope.result, rememberMe);
      const challenge = extractMfaChallenge(envelope.result);
      if (challenge) {
        setMfaChallenge(challenge);
      } else {
        navigateAfterLogin(nextPath);
      }
    } catch (err) {
      setError(mapAuthError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell>
      <AuthCard
        title="Sign in with mobile"
        description="We'll text a 6-digit one-time code to verify your number."
      >
        <Stack gap={4}>
          {mfaChallenge ? (
            <MfaChallenge challenge={mfaChallenge} onDone={() => navigateAfterLogin(nextPath)} />
          ) : otpStatus === "unavailable" ? (
            <Alert variant="warning" title="Mobile OTP unavailable">
              {statusMessage || "Mobile OTP is not configured on this deployment."}
            </Alert>
          ) : otpStatus === "coming_soon" ? (
            <Alert variant="info" title="Coming Soon">
              {statusMessage || "Mobile OTP is intentionally disabled."}
            </Alert>
          ) : step === "enter" ? (
            <form className="space-y-4" onSubmit={onSendOtp} noValidate>
              <div className="flex gap-2">
                <div className="w-36">
                  <FormField label="Country" htmlFor="mobile-country">
                    <Select value={countryCode} onValueChange={setCountryCode}>
                      <SelectTrigger id="mobile-country" disabled={pending}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {COUNTRY_CODES.map((c) => (
                          <SelectItem key={c.code} value={c.code}>
                            {c.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormField>
                </div>
                <div className="flex-1">
                  <FormField label="Mobile number" htmlFor="mobile-number" required>
                    <Input
                      id="mobile-number"
                      value={mobile}
                      onChange={(e) => setMobile(e.target.value)}
                      inputMode="tel"
                      autoComplete="tel-national"
                      placeholder="98XXXXXXXX"
                      required
                      disabled={pending}
                    />
                  </FormField>
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
                <Checkbox
                  checked={rememberMe}
                  onCheckedChange={(v) => setRememberMe(v === true)}
                  aria-label="Remember me on this device"
                  disabled={pending}
                />
                Remember me
              </label>
              {error ? <ValidationMessage tone="error">{error}</ValidationMessage> : null}
              <Button type="submit" className="w-full" disabled={pending || !mobile.trim()}>
                {pending ? "Sending…" : "Send OTP"}
              </Button>
            </form>
          ) : (
            <Stack gap={4}>
              <p className="text-sm text-[var(--muted)]">
                Enter the 6-digit code sent to {fullMobile}.
              </p>
              {devOtpHint ? (
                <Alert variant="info" title="Development SMS">
                  {devOtpHint}
                </Alert>
              ) : null}
              <OtpInput
                id="mobile-otp"
                label="6-digit OTP"
                length={6}
                value={otpCode}
                onChange={setOtpCode}
                onComplete={onVerify}
                disabled={pending}
                autoFocus
                error={error ?? undefined}
              />
              <ResendCountdown seconds={30} onResend={onResend} disabled={pending} />
              {error ? <ValidationMessage tone="error">{error}</ValidationMessage> : null}
              <Button
                type="button"
                className="w-full"
                disabled={pending || otpCode.length < 6}
                onClick={() => onVerify(otpCode)}
              >
                {pending ? "Verifying…" : "Verify & sign in"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                disabled={pending}
                onClick={() => {
                  setStep("enter");
                  setOtpCode("");
                  setChallengeId(null);
                  setError(null);
                }}
              >
                Use a different number
              </Button>
            </Stack>
          )}

          {!mfaChallenge ? (
            <p className="text-center text-sm text-[var(--muted)]">
              <Link href={`/login?next=${encodeURIComponent(nextPath)}`} className="text-[var(--accent)] underline-offset-2 hover:underline">
                Back to sign in
              </Link>
            </p>
          ) : null}
        </Stack>
      </AuthCard>
    </AuthShell>
  );
}
