"use client";

/**
 * EPIC-F005 — Company Analysis Workspace route.
 * Flagship module — frozen /api/v1 only.
 *
 * P1-09 — static import for the workspace. The previous
 * next/dynamic({ ssr: false }) path left the route stuck on the skeleton.
 * SIMPLE-9 — keep useSearchParams inside this client subtree so the
 * server page can finish RSC instead of hanging on analysis/loading.tsx.
 */

import { Suspense } from "react";

import { CompanyAnalysisWorkspace } from "@/components/company-analysis";
import { WorkspaceSkeleton } from "@/components/company-analysis/WorkspacePrimitives";
import { PageHeader } from "@/components/layout/PageHeader";

export function AnalysisRouteClient() {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Analysis"
        description="Search a company and receive one structured DSP report. No client-side scoring or valuation math."
      />
      <Suspense fallback={<WorkspaceSkeleton />}>
        <CompanyAnalysisWorkspace />
      </Suspense>
    </div>
  );
}
