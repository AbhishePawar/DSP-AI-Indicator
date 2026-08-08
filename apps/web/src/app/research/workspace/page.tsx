"use client";

import { Suspense, lazy } from "react";

import { Skeleton } from "@/components/ds";
import { PageHeader } from "@/components/layout/PageHeader";

const InstitutionalResearchWorkspace = lazy(() =>
  import("@/components/institutional-research-workspace").then((m) => ({
    default: m.InstitutionalResearchWorkspace,
  })),
);

export default function ResearchWorkspacePlatformPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-4 p-6">
          <PageHeader
            title="Research Workspace"
            description="Loading institutional workspace…"
          />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      }
    >
      <InstitutionalResearchWorkspace />
    </Suspense>
  );
}
