"use client";

/**
 * /research/intelligence — Figma Make `ResearchIntelligence.tsx`. Signals and
 * measurement values come from /api/v1 (thin client).
 */

import { EmptyState } from "@/components/ds";
import { FigmaSignalFeed } from "@/components/research-intelligence/FigmaSignalFeed";
import { featureFlags } from "@/lib/featureFlags";

export default function ResearchIntelligencePage() {
  if (!featureFlags.researchIntelligence) {
    return (
      <EmptyState
        title="Research Intelligence is disabled"
        description="Set NEXT_PUBLIC_RESEARCH_INTELLIGENCE=true to enable the signal feed."
      />
    );
  }

  return <FigmaSignalFeed />;
}
