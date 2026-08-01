"use client";

/**
 * EPIC-F005 — Company Analysis Workspace route.
 * Flagship module — frozen /api/v1 only.
 * RC3-004 — dynamic import keeps initial route shell light.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { WorkspaceSkeleton } from "@/components/company-analysis/WorkspacePrimitives";
import { PageHeader } from "@/components/layout/PageHeader";

const CompanyAnalysisWorkspace = dynamic(
  () =>
    import("@/components/company-analysis").then((m) => ({
      default: m.CompanyAnalysisWorkspace,
    })),
  {
    ssr: false,
    loading: () => <WorkspaceSkeleton />,
  },
);

export default function AnalysisRoute() {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Company Analysis Workspace"
        description="Institutional research interface over certified /api/v1/analyse outputs. No client-side scoring or valuation math."
      />
      <Suspense fallback={<WorkspaceSkeleton />}>
        <CompanyAnalysisWorkspace />
      </Suspense>
    </div>
  );
}
