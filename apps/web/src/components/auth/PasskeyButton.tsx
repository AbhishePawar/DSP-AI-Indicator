"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ds";
import { cn } from "@/lib/utils";
import { PasskeyIcon } from "./ProviderIcons";

export type PasskeyButtonProps = {
  /** Server-reported WebAuthn availability (EnterpriseProvidersStatus.mfa.webauthn_available). */
  serverAvailable: boolean;
  serverMessage?: string | null;
  pending?: boolean;
  onAuthenticate: () => void | Promise<void>;
  className?: string;
};

function browserSupportsWebAuthn(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.PublicKeyCredential !== "undefined"
  );
}

/**
 * "Continue with Passkey" — uses the browser WebAuthn API when both the
 * browser and the EnterpriseAuthPlatform report support; otherwise falls
 * back gracefully to a disabled, clearly labelled state instead of a dead
 * or mocked control. Today the platform's WebAuthn adapter is reserved
 * (architecture-only — see auth/mfa.py NullWebAuthnAdapter), so this
 * renders as "Coming Soon" until a real adapter is configured server-side.
 */
export function PasskeyButton({
  serverAvailable,
  serverMessage,
  pending,
  onAuthenticate,
  className,
}: PasskeyButtonProps) {
  const [browserOk, setBrowserOk] = useState(true);

  useEffect(() => {
    setBrowserOk(browserSupportsWebAuthn());
  }, []);

  const available = serverAvailable && browserOk;
  const reason = !browserOk
    ? "Passkeys are not supported in this browser."
    : serverMessage || "Passkey sign-in is not yet enabled on this deployment.";

  return (
    <Button
      type="button"
      variant="secondary"
      className={cn("w-full justify-center", !available && "opacity-70", className)}
      disabled={!available || pending}
      title={available ? undefined : reason}
      aria-disabled={!available}
      aria-label={
        available ? "Continue with Passkey" : `Continue with Passkey — ${reason}`
      }
      onClick={() => onAuthenticate()}
    >
      <PasskeyIcon />
      <span>
        {pending
          ? "Waiting for passkey…"
          : available
            ? "Continue with Passkey"
            : "Passkey — Coming Soon"}
      </span>
    </Button>
  );
}
