"use client";

/**
 * EPS-002 — Operations / Incident Center landing page.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { featureFlags } from "@/lib/featureFlags";

const OpsPortal = dynamic(
  () =>
    import("@/components/ops-portal").then((m) => ({
      default: m.OpsPortal,
    })),
  {
    ssr: false,
    loading: () => (
      <p className="text-sm text-[var(--dsp-text-muted)]">Loading ops…</p>
    ),
  },
);

export default function OpsPage() {
  if (!featureFlags.enterpriseOps) {
    return (
      <div className="space-y-4">
        <PageHeader
          title="Operations"
          description="Enterprise operations dashboard is disabled by feature flag."
        />
        <p className="text-sm text-[var(--dsp-text-muted)]" role="status">
          Data unavailable.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Operations"
        description="Enterprise health, incident center, services, and collaboration architecture. Honest unavailable states when infra ports are offline."
      />
      <Suspense
        fallback={
          <p className="text-sm text-[var(--dsp-text-muted)]">Loading ops…</p>
        }
      >
        <OpsPortal />
      </Suspense>
    </div>
  );
}
