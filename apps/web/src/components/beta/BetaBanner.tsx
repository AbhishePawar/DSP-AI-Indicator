"use client";

import Link from "next/link";

import { featureFlags } from "@/lib/featureFlags";
import { env } from "@/lib/env";

/** P5.1 — Closed beta version banner. */
export function BetaBanner({
  text,
  expiryAt,
}: {
  text?: string | null;
  expiryAt?: string | null;
}) {
  if (!featureFlags.betaBanner && !featureFlags.closedBeta) return null;

  const campaign = text?.trim() || null;
  const immutableDisclaimer =
    "Research tools only — not investment advice.";

  return (
    <div
      role="status"
      className="border-b border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-center text-xs text-[var(--muted)]"
      data-testid="beta-banner"
    >
      <span className="font-medium text-[var(--fg)]">Beta v{env.frontendVersion}</span>
      {" · "}
      {campaign ? (
        <>
          {campaign}
          {" · "}
        </>
      ) : null}
      <span className="text-[var(--fg)]">{immutableDisclaimer}</span>
      {" · Feedback welcome"}
      {featureFlags.betaReadOnlySafeguards ? (
        <>
          {" · "}
          <span>Read-only production safeguards on</span>
        </>
      ) : null}
      {expiryAt ? (
        <>
          {" · "}
          Expires {expiryAt.slice(0, 10)}
        </>
      ) : null}
      {" · "}
      <Link className="text-[var(--accent)] underline" href="/beta">
        Beta hub
      </Link>
    </div>
  );
}
