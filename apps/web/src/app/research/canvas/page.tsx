"use client";

/**
 * EPIC-014 — Institutional Research Canvas route.
 * Research OS hub — composes existing surfaces; does not replace Company Analysis.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { WorkspaceSkeleton } from "@/components/research-canvas";
import { featureFlags } from "@/lib/featureFlags";
import { EmptyState } from "@/components/ds";

const ResearchCanvasWorkspace = dynamic(
  () =>
    import("@/components/research-canvas").then((m) => ({
      default: m.ResearchCanvasWorkspace,
    })),
  {
    ssr: false,
    loading: () => <WorkspaceSkeleton />,
  },
);

export default function ResearchCanvasPage() {
  if (!featureFlags.researchCanvas) {
    return (
      <EmptyState
        title="Research Canvas is disabled"
        description="Set NEXT_PUBLIC_RESEARCH_CANVAS=true to enable the Institutional Research Operating System."
      />
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Research Canvas"
        description="Institutional Research Operating System — unify Company Analysis, Comparison, Research Intelligence, Timeline, Evidence, Committee, and Notebook without rewriting engines."
      />
      <Suspense fallback={<WorkspaceSkeleton />}>
        <ResearchCanvasWorkspace />
      </Suspense>
    </div>
  );
}
