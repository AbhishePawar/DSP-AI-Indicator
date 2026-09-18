"use client";

/**
 * EPIC-F005 — Company Analysis Workspace route.
 * Flagship module — frozen /api/v1 only.
 *
 * P1-09 — use a static import for the workspace. The previous
 * next/dynamic({ ssr: false }) path left the route stuck on the skeleton
 * in production builds (critical journey could not mount).
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

const CompanyAnalysisWorkspace = dynamic(
  () =>
    import("@/components/company-analysis").then((mod) => mod.CompanyAnalysisWorkspace),
  { loading: () => <WorkspaceSkeleton /> },
);
import { WorkspaceSkeleton } from "@/components/company-analysis/WorkspacePrimitives";
import { PageHeader } from "@/components/layout/PageHeader";

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
