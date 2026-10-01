"use client";

/**
 * EPIC-F007 — Institutional Research Workspace landing page.
 * RC3-004 — dynamic import for workspace code-splitting.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { ResearchHub } from "@/components/research-workspace/ResearchHub";
import { useSearchParams } from "next/navigation";

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

function ResearchRouteContent() {
  const params = useSearchParams();
  const isDetailedView = params.has("ticker") || params.has("section") || params.get("view") === "workspace";
  if (!isDetailedView) return <ResearchHub />;
  return (
    <div className="space-y-4">
      <PageHeader
        title="Research Workspace"
        description="Browse evidence, review saved analyses, and export research."
      />
      <Suspense fallback={<WorkspaceSkeleton />}>
        <ResearchWorkspace />
      </Suspense>
    </div>
  );
}

export default function ResearchPage() {
  return <Suspense fallback={<WorkspaceSkeleton />}><ResearchRouteContent /></Suspense>;
}
