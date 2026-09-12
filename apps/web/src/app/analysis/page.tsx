"use client";

/**
 * EPIC-F005 — Company Analysis Workspace route.
 * Flagship module — frozen /api/v1 only.
 *
 * P1-09 — use a static import for the workspace. The previous
 * next/dynamic({ ssr: false }) path left the route stuck on the skeleton
 * in production builds (critical journey could not mount).
 */

import { Suspense } from "react";

import { CompanyAnalysisWorkspace } from "@/components/company-analysis";
import { WorkspaceSkeleton } from "@/components/company-analysis/WorkspacePrimitives";
import { PageHeader } from "@/components/layout/PageHeader";

export default function AnalysisRoute() {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Company Research"
        description="Search a company or ticker, then review certified /api/v1 analysis. No client-side scoring or valuation math."
      />
      <Suspense fallback={<WorkspaceSkeleton />}>
        <CompanyAnalysisWorkspace />
      </Suspense>
    </div>
  );
}
