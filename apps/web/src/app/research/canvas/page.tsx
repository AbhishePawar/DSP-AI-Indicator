"use client";

/**
 * EPIC-014 — Institutional Research Canvas route.
 * Research OS hub — composes existing surfaces; does not replace Company Analysis.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { FigmaNotebook } from "@/components/research-canvas/FigmaNotebook";
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
        description="Notebook-style research environment. Blocks load and save through the workspace canvas API. The operating system below keeps the existing research surfaces."
      />
      <FigmaNotebook />
      <Suspense fallback={<WorkspaceSkeleton />}>
        <ResearchCanvasWorkspace />
      </Suspense>
    </div>
  );
}
