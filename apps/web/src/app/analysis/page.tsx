import { Suspense } from "react";

import { WorkspaceSkeleton } from "@/components/company-analysis/WorkspacePrimitives";

import { AnalysisRouteClient } from "./AnalysisRouteClient";

/**
 * Server page so App Router can complete the RSC payload.
 * Client searchParams stay inside AnalysisRouteClient + Suspense.
 */
export default function AnalysisPage() {
  return (
    <Suspense fallback={<WorkspaceSkeleton />}>
      <AnalysisRouteClient />
    </Suspense>
  );
}
