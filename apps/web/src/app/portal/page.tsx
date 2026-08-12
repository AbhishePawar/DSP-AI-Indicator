"use client";

/**
 * EPS-002 — Customer Portal landing page.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { featureFlags } from "@/lib/featureFlags";

const EnterprisePortal = dynamic(
  () =>
    import("@/components/enterprise-portal").then((m) => ({
      default: m.EnterprisePortal,
    })),
  {
    ssr: false,
    loading: () => (
      <p className="text-sm text-[var(--dsp-text-muted)]">Loading portal…</p>
    ),
  },
);

export default function CustomerPortalPage() {
  if (!featureFlags.enterprisePortal) {
    return (
      <div className="space-y-4">
        <PageHeader
          title="Customer Portal"
          description="Enterprise customer portal is disabled by feature flag."
        />
        <p className="text-sm text-[var(--dsp-text-muted)]" role="status">
          No organizations available.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Customer Portal"
        description="Organization, licenses, members, usage, invoices, and API keys from /api/v1/enterprise. Display-only — no client-side billing or secrets."
      />
      <Suspense
        fallback={
          <p className="text-sm text-[var(--dsp-text-muted)]">Loading portal…</p>
        }
      >
        <EnterprisePortal />
      </Suspense>
    </div>
  );
}
