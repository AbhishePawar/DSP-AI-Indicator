"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { DiversificationAnalytics } from "@/lib/portfolio/analytics";
import { PortfolioCard } from "./PortfolioCard";

export function DiversificationPanel({
  diversification,
}: {
  diversification: DiversificationAnalytics;
}) {
  return (
    <Card>
      <CardHeader
        title="Diversification"
        description="Sector, exchange, and geography breadth"
      />
      <CardBody>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <PortfolioCard
            label="Sector Count"
            value={diversification.sectorCount}
          />
          <PortfolioCard
            label="Exchange Count"
            value={diversification.exchangeCount}
          />
          <PortfolioCard
            label="Country Count"
            value={diversification.countryCount}
          />
          <PortfolioCard
            label="Largest Sector"
            value={
              diversification.largestSector === "—"
                ? "—"
                : `${diversification.largestSector} (${diversification.largestSectorPercent}%)`
            }
          />
        </div>
      </CardBody>
    </Card>
  );
}
