"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";

import { Button, EmptyState } from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";
import { betaApi } from "@/lib/beta/betaApi";
import { featureFlags } from "@/lib/featureFlags";
import { env } from "@/lib/env";
import { BetaBanner } from "@/components/beta/BetaBanner";

/**
 * P5.1/P5.2 — Invitation-only gate when closed beta mode is enabled.
 * Admins always pass.
 * Production + invitation-only: fail closed if the beta API is unreachable.
 * Development/test: fail open so local feedback collection continues.
 */
export function ClosedBetaGate({ children }: { children: ReactNode }) {
  const { user, session, status } = useAuth();
  const [allowed, setAllowed] = useState(!featureFlags.closedBeta);
  const [checking, setChecking] = useState(featureFlags.closedBeta);
  const [bannerText, setBannerText] = useState<string | null>(null);
  const [expiryAt, setExpiryAt] = useState<string | null>(null);
  const [apiError, setApiError] = useState(false);

  const failClosed =
    featureFlags.closedBeta &&
    featureFlags.betaInvitationOnly &&
    env.environment === "production";

  useEffect(() => {
    if (!featureFlags.closedBeta) {
      setAllowed(true);
      setChecking(false);
      return;
    }
    if (status === "loading") return;

    const roles = user?.roles || session?.roles || [];
    const isAdmin = roles.includes("administrator");
    const identity =
      user?.email || user?.username || session?.email || session?.username || null;

    let cancelled = false;
    (async () => {
      try {
        const result = await betaApi.status(identity, isAdmin);
        if (cancelled) return;
        setApiError(false);
        setBannerText(result.banner?.text || null);
        setExpiryAt(result.programme?.expiry_at || null);
        if (!featureFlags.betaInvitationOnly) {
          setAllowed(true);
        } else {
          setAllowed(Boolean(result.access_allowed) || isAdmin);
        }
      } catch {
        if (cancelled) return;
        setApiError(true);
        if (isAdmin) {
          setAllowed(true);
        } else if (failClosed) {
          setAllowed(false);
        } else {
          // Dev/test fail-open — banner still shown.
          setAllowed(true);
        }
      } finally {
        if (!cancelled) setChecking(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [status, user, session, failClosed]);

  return (
    <>
      <BetaBanner text={bannerText} expiryAt={expiryAt} />
      {checking ? (
        <EmptyState
          title="Checking beta access…"
          description="Validating closed beta invitation status."
        />
      ) : !allowed ? (
        <EmptyState
          title={apiError && failClosed ? "Beta service unavailable" : "Invitation required"}
          description={
            apiError && failClosed
              ? "Closed beta cannot verify invitations while the API is unreachable. Try again shortly or contact an administrator."
              : "This deployment is in closed beta. Ask an administrator to approve your invite, then sign in again."
          }
          action={
            <div className="flex flex-wrap gap-2">
              <Link href="/login">
                <Button size="sm" variant="secondary">
                  Sign in
                </Button>
              </Link>
              <Link href="/docs/disclaimer">
                <Button size="sm" variant="ghost">
                  Disclaimer
                </Button>
              </Link>
            </div>
          }
        />
      ) : (
        children
      )}
    </>
  );
}
