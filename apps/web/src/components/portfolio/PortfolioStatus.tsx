"use client";

import { PortfolioCard } from "./PortfolioCard";

export function PortfolioStatus({
  totalHoldings,
  sectorCount,
  researchCoverage,
  portfolioStatus,
}: {
  totalHoldings: number;
  sectorCount: number;
  researchCoverage: string;
  portfolioStatus: string;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <PortfolioCard label="Total Holdings" value={totalHoldings} />
      <PortfolioCard label="Sector Count" value={sectorCount} />
      <PortfolioCard label="Research Coverage" value={researchCoverage} />
      <PortfolioCard label="Portfolio Status" value={portfolioStatus} />
    </div>
  );
}
