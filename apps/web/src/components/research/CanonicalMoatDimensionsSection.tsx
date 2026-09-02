"use client";

import type { StageSectionView } from "@/lib/research/mapResearchView";
import type { CanonicalMoatDimensionView } from "@/lib/research/canonicalMoatDimensions";
import { MetricGrid, ResearchSection } from "./ResearchSection";

export function CanonicalMoatDimensionsSection({
  dimensions,
  overallMoat,
}: {
  dimensions: CanonicalMoatDimensionView[];
  overallMoat: StageSectionView;
}) {
  return (
    <ResearchSection
      id="economic-moat"
      title="Economic Moat"
      description="Canonical dimension ratings are DSP-owned. Missing ratings display N/A."
    >
      <div>
        <h4 className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
          Individual dimensions
        </h4>
        <dl className="mt-3 space-y-2">
          {dimensions.map((dimension) => (
            <div
              key={dimension.identifier}
              className="flex items-baseline justify-between gap-4"
            >
              <dt className="text-sm">{dimension.name}</dt>
              <dd className="font-mono text-sm">{dimension.displayRating}</dd>
            </div>
          ))}
        </dl>
      </div>
      <div className="border-t border-[var(--border)] pt-4">
        <h4 className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
          Overall economic moat
        </h4>
        <div className="mt-3">
          <MetricGrid metrics={overallMoat.metrics} />
        </div>
      </div>
    </ResearchSection>
  );
}
