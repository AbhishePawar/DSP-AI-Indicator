"use client";

/**
 * EPIC-011B — Research Intelligence route.
 * Supporting surface under Research — does not compete with Company Analysis.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { FigmaSignalFeed } from "@/components/research-intelligence/FigmaSignalFeed";
import { WorkspaceSkeleton } from "@/components/research-intelligence";
import { featureFlags } from "@/lib/featureFlags";
import { EmptyState } from "@/components/ds";

const ResearchIntelligenceWorkspace = dynamic(
  () =>
    import("@/components/research-intelligence").then((m) => ({
      default: m.ResearchIntelligenceWorkspace,
    })),
  {
    ssr: false,
    loading: () => <WorkspaceSkeleton />,
  },
);

export default function ResearchIntelligencePage() {
  if (!featureFlags.researchIntelligence) {
    return (
      <EmptyState
        title="Research Intelligence is disabled"
        description="Set NEXT_PUBLIC_RESEARCH_INTELLIGENCE=true to enable this measurement workspace."
      />
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Research Intelligence"
        description="Coverage signals from the authenticated service. Measurement sections below stay on /api/v1/research/intelligence."
      />
      <FigmaSignalFeed />
      <Suspense fallback={<WorkspaceSkeleton />}>
        <ResearchIntelligenceWorkspace />
      </Suspense>
    </div>
  );
}
