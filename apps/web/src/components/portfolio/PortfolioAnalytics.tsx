"use client";

import { useMemo } from "react";

import { buildPortfolioAnalytics } from "@/lib/portfolio/analytics";
import type { PortfolioHolding } from "@/lib/portfolio/model";
import { DiversificationPanel } from "./DiversificationPanel";
import { PortfolioHealth } from "./PortfolioHealth";
import { QualityPanel } from "./QualityPanel";
import { RecommendationDistribution } from "./RecommendationDistribution";
import { ResearchCoverage } from "./ResearchCoverage";
import { SectorAllocation } from "./SectorAllocation";

export function PortfolioAnalytics({
  holdings,
}: {
  holdings: PortfolioHolding[];
}) {
  const analytics = useMemo(
    () => buildPortfolioAnalytics(holdings),
    [holdings],
  );

  return (
    <section aria-label="Portfolio analytics" className="space-y-4">
      <div>
        <h2 className="font-[family-name:var(--font-display)] text-xl tracking-tight">
          Portfolio Analytics
        </h2>
        <p className="mt-0.5 text-sm text-[var(--muted)]">
          Derived from current in-memory holdings — no live prices or persistence.
        </p>
      </div>

      <QualityPanel quality={analytics.quality} />

      <div className="grid gap-4 lg:grid-cols-2">
        <SectorAllocation segments={analytics.sectorAllocation} />
        <RecommendationDistribution distribution={analytics.recommendations} />
      </div>

      <ResearchCoverage coverage={analytics.researchCoverage} />

      <div className="grid gap-4 lg:grid-cols-2">
        <DiversificationPanel diversification={analytics.diversification} />
        <PortfolioHealth health={analytics.health} />
      </div>
    </section>
  );
}
