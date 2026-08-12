"use client";

/**
 * EPIC-011B — Research Intelligence route.
 * Supporting surface under Research — does not compete with Company Analysis.
 */

import dynamic from "next/dynamic";
import { Suspense } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
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
        description="Institutional research performance, timeline, calibration, and outcome validation over /api/v1/research/intelligence. Measurement only — missing feeds stay Data unavailable."
      />
      <Suspense fallback={<WorkspaceSkeleton />}>
        <ResearchIntelligenceWorkspace />
      </Suspense>
    </div>
  );
}
