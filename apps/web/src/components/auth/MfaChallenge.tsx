"use client";

import { useEffect, useRef, useState } from "react";
import { Alert, Button, Stack, ValidationMessage } from "@/components/ds";
import { enterpriseAuthApi } from "@/lib/api/enterpriseAuth";
import { ApiClientError } from "@/lib/api/types";
import type { MfaChallengeInfo } from "@/lib/auth/types";
import { OtpInput } from "./OtpInput";
import { PasskeyIcon } from "./ProviderIcons";

export type MfaChallengeProps = {
  challenge: MfaChallengeInfo;
  /** Called once the step-up is satisfied (or the user chooses to skip, if permitted). */
  onDone: () => void;
};

const METHOD_LABEL: Record<string, string> = {
  totp: "Authenticator App",
  sms: "SMS",
  email: "Email",
  passkey: "Passkey",
  webauthn: "Passkey",
};

/**
 * Post-password MFA step-up, rendered inline (no page refresh) when the
 * EnterpriseAuthPlatform login response carries `mfa_required`. Methods are
 * driven entirely by what the backend actually reports as enrolled
 * (`challenge.methods`) — nothing is hardcoded or assumed available.
 *
 * The verification endpoints (`/auth/mfa/*`) are currently reserved
 * (HTTP 501) until `DSP_AUTH_MFA=true` and a real adapter is configured; this
 * component calls the real endpoint and surfaces that state honestly rather
 * than pretending to authenticate.
 */
export function MfaChallenge({ challenge, onDone }: MfaChallengeProps) {
  const methods = challenge.methods.length ? challenge.methods : ["totp"];
  const [selected, setSelected] = useState<string>(methods[0] ?? "totp");
  const [code, setCode] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notConfigured, setNotConfigured] = useState<string | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

  // This step replaces the login form's content inline (no page navigation
  // and no true modal overlay behind it), so move focus to the new heading
  // on mount rather than using role="dialog" — which implies focus-trapping
  // behaviour this component does not provide.
  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  async function verifyTotp(value: string) {
    if (!challenge.mfaToken) {
      setError("Missing MFA session token. Please sign in again.");
      return;
    }
    setPending(true);
    setError(null);
    setNotConfigured(null);
    try {
      const envelope = await enterpriseAuthApi.mfaTotpVerify({
        mfa_token: challenge.mfaToken,
        code: value,
      });
      if (!envelope.ok) {
        throw new Error(envelope.error || "Verification failed");
      }
      onDone();
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 501) {
        setNotConfigured(
          "Multi-factor verification is reserved but not yet configured on this deployment. Contact your administrator, or continue — your primary sign-in already succeeded.",
        );
      } else {
        setError("Invalid or expired code. Please try again.");
      }
    } finally {
      setPending(false);
    }
  }

  async function verifyPasskey() {
    setPending(true);
    setError(null);
    setNotConfigured(null);
    try {
      const envelope = await enterpriseAuthApi.webauthnAuthenticateBegin();
      if (!envelope.ok) throw new Error(envelope.error || "Passkey verification failed");
      onDone();
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 501) {
        setNotConfigured(
          "Passkey step-up is reserved but not yet configured on this deployment. Contact your administrator, or continue — your primary sign-in already succeeded.",
        );
      } else {
        setError("Passkey verification failed. Please try again.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <div
      role="group"
      aria-labelledby="mfa-challenge-title"
      aria-describedby="mfa-challenge-desc"
      className="rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-5"
    >
      <Stack gap={4}>
        <div>
          <h2
            id="mfa-challenge-title"
            ref={headingRef}
            tabIndex={-1}
            className="text-lg font-medium text-[var(--fg)] focus-visible:outline-none"
          >
            Choose verification
          </h2>
          <p id="mfa-challenge-desc" className="mt-1 text-sm text-[var(--muted)]">
            Your account requires an additional verification step.
          </p>
        </div>

        {methods.length > 1 ? (
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Verification method">
            {methods.map((m) => (
              <Button
                key={m}
                type="button"
                size="sm"
                variant={selected === m ? "primary" : "outline"}
                role="tab"
                aria-selected={selected === m}
                onClick={() => {
                  setSelected(m);
                  setCode("");
                  setError(null);
                  setNotConfigured(null);
                }}
              >
                {METHOD_LABEL[m] ?? m}
              </Button>
            ))}
          </div>
        ) : null}

        {notConfigured ? (
          <Alert variant="info" title="Not yet configured">
            {notConfigured}
            <div className="mt-3">
              <Button type="button" size="sm" onClick={onDone}>
                Continue
              </Button>
            </div>
          </Alert>
        ) : selected === "passkey" || selected === "webauthn" ? (
          <Stack gap={3}>
            <p className="flex items-center gap-2 text-sm text-[var(--muted)]">
              <PasskeyIcon /> Use your device passkey to finish signing in.
            </p>
            {error ? <ValidationMessage tone="error">{error}</ValidationMessage> : null}
            <Button type="button" disabled={pending} onClick={verifyPasskey} className="w-full">
              {pending ? "Waiting for passkey…" : "Verify with Passkey"}
            </Button>
          </Stack>
        ) : (
          <Stack gap={3}>
            <OtpInput
              id="mfa-code"
              label={`${METHOD_LABEL[selected] ?? selected} code`}
              length={6}
              value={code}
              onChange={setCode}
              onComplete={verifyTotp}
              disabled={pending}
              autoFocus
              error={error ?? undefined}
            />
            {error ? <ValidationMessage tone="error">{error}</ValidationMessage> : null}
            <Button
              type="button"
              disabled={pending || code.length < 6}
              onClick={() => verifyTotp(code)}
              className="w-full"
            >
              {pending ? "Verifying…" : "Verify"}
            </Button>
          </Stack>
        )}
      </Stack>
    </div>
  );
}
