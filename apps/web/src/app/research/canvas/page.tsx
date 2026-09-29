"use client";

/**
 * /research/canvas — Figma Make `ResearchCanvas.tsx`. Blocks persist through
 * the authenticated workspace canvas API (thin client).
 */

import { EmptyState } from "@/components/ds";
import { FigmaNotebook } from "@/components/research-canvas/FigmaNotebook";
import { featureFlags } from "@/lib/featureFlags";

export default function ResearchCanvasPage() {
  if (!featureFlags.researchCanvas) {
    return (
      <EmptyState
        title="Research Canvas is disabled"
        description="Set NEXT_PUBLIC_RESEARCH_CANVAS=true to enable the research canvas."
      />
    );
  }

  return <FigmaNotebook />;
}
