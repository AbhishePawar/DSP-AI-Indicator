"use client";

import { PortfolioSync } from "@/components/persistence/PortfolioSync";
import { PortfolioMarketSummary } from "@/components/market/PortfolioMarketSummary";
import { usePortfolio } from "@/lib/portfolio/PortfolioProvider";
import { ActivityTimeline } from "./ActivityTimeline";
import { AllocationCard } from "./AllocationCard";
import { EmptyPortfolio } from "./EmptyPortfolio";
import { HoldingsTable } from "./HoldingsTable";
import { PageHeader } from "@/components/layout/PageHeader";
import { PortfolioActions } from "./PortfolioActions";
import { PortfolioAnalytics } from "./PortfolioAnalytics";
import { PortfolioStatus } from "./PortfolioStatus";

export function PortfolioFoundation() {
  const { view, isEmpty } = usePortfolio();

  return (
    <div className="space-y-8">
      <PageHeader
        title="Portfolio"
        description="Manage your investment portfolio."
      />

      {isEmpty ? (
        <>
          <EmptyPortfolio />
          <PortfolioActions />
        </>
      ) : (
        <>
          <PortfolioStatus
            totalHoldings={view.summary.totalHoldings}
            sectorCount={view.summary.sectorCount}
            researchCoverage={view.summary.researchCoverage}
            portfolioStatus={view.summary.portfolioStatus}
          />

          <PortfolioMarketSummary holdings={view.holdings} />

          <PortfolioAnalytics holdings={view.holdings} />

          <section aria-label="Allocation overview" className="space-y-3">
            <h2 className="font-[family-name:var(--font-display)] text-xl tracking-tight">
              Allocation Overview
            </h2>
            <div className="grid gap-4 lg:grid-cols-3">
              <AllocationCard
                title="By Sector"
                segments={view.allocations.bySector}
              />
              <AllocationCard
                title="By Market Cap"
                segments={view.allocations.byMarketCap}
              />
              <AllocationCard
                title="By Geography"
                segments={view.allocations.byGeography}
              />
            </div>
          </section>

          <HoldingsTable holdings={view.holdings} />

          <div className="grid gap-4 lg:grid-cols-2">
            <ActivityTimeline activities={view.activities} />
            <div className="space-y-4">
              <PortfolioSync />
              <PortfolioActions />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
