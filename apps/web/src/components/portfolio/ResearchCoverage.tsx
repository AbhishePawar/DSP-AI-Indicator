"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { ResearchCoverageAnalytics } from "@/lib/portfolio/analytics";
import { PortfolioCard } from "./PortfolioCard";

export function ResearchCoverage({
  coverage,
}: {
  coverage: ResearchCoverageAnalytics;
}) {
  return (
    <Card>
      <CardHeader
        title="Research Coverage"
        description="How many holdings have research available"
      />
      <CardBody>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <PortfolioCard
            label="Companies Analysed"
            value={coverage.companiesAnalysed}
          />
          <PortfolioCard
            label="Research Available"
            value={coverage.researchAvailable}
          />
          <PortfolioCard
            label="Research Missing"
            value={coverage.researchMissing}
          />
          <PortfolioCard
            label="Coverage %"
            value={`${coverage.coveragePercent}%`}
          />
        </div>
      </CardBody>
    </Card>
  );
}
