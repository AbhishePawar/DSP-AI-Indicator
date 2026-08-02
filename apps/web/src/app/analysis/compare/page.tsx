"use client";

/**
 * EPIC-012/013 — Institutional Company Comparison route.
 * Supporting intelligence under Company Analysis — decision workspace, not flagship research.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { WorkspaceSkeleton } from "@/components/company-comparison";
import { EmptyState } from "@/components/ds";
import { featureFlags } from "@/lib/featureFlags";

const CompanyComparisonWorkspace = dynamic(
  () =>
    import("@/components/company-comparison").then((m) => ({
      default: m.CompanyComparisonWorkspace,
    })),
  {
    ssr: false,
    loading: () => <WorkspaceSkeleton />,
  },
);

export default function CompanyComparisonPage() {
  if (!featureFlags.companyComparison) {
    return (
      <EmptyState
        title="Company Comparison is disabled"
        description="Set NEXT_PUBLIC_COMPANY_COMPARISON=true to enable the institutional comparison workspace."
      />
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Institutional Company Comparison"
        description="Investment Decision Workspace over frozen /api/v1/analyse packs. Assists decisions — never makes them. No client-side scoring."
      />
      <Suspense fallback={<WorkspaceSkeleton />}>
        <CompanyComparisonWorkspace />
      </Suspense>
    </div>
  );
}
