"use client";

/**
 * EPIC-F007 — Institutional Research Workspace landing page.
 * RC3-004 — dynamic import for workspace code-splitting.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { WorkspaceSkeleton } from "@/components/research-workspace/Primitives";
import { PageHeader } from "@/components/layout/PageHeader";

const ResearchWorkspace = dynamic(
  () =>
    import("@/components/research-workspace").then((m) => ({
      default: m.ResearchWorkspace,
    })),
  {
    ssr: false,
    loading: () => <WorkspaceSkeleton />,
  },
);

export default function ResearchPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Research Workspace"
        description="Browse, inspect, and export research from certified /api/v1/analyse outputs and local session history. No client-side research generation."
      />
      <Suspense fallback={<WorkspaceSkeleton />}>
        <ResearchWorkspace />
      </Suspense>
    </div>
  );
}
