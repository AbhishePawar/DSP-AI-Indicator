"use client";

/**
 * Institutional Company Workspace — News tab.
 *
 * No news data source exists anywhere in the platform (no package, port, or
 * adapter) — honest, wired empty state, not mocked headlines.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import { SectionCard, WorkspaceEmpty } from "../WorkspacePrimitives";

export function NewsSection({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-4">
      <SectionCard
        title={`News — ${view.company}`}
        description="No connected news provider exists in the platform yet — no package, port, or adapter."
      >
        <WorkspaceEmpty description="Data unavailable — no data source connected." />
      </SectionCard>
    </div>
  );
}
