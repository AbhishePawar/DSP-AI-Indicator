"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { PortfolioQualityAnalytics } from "@/lib/portfolio/analytics";
import { PortfolioCard } from "./PortfolioCard";

export function QualityPanel({ quality }: { quality: PortfolioQualityAnalytics }) {
  return (
    <Card>
      <CardHeader
        title="Portfolio Quality"
        description="Recommendation mix and research coverage — company quality scores come from /api/v1/analyse"
      />
      <CardBody>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <PortfolioCard
            label="Average Quality Score"
            value={quality.averageQualityScore}
          />
          <PortfolioCard
            label="Average Recommendation"
            value={quality.averageRecommendation}
          />
          <PortfolioCard
            label="Companies with Research"
            value={quality.companiesWithResearch}
          />
          <PortfolioCard
            label="Portfolio Status"
            value={quality.portfolioStatus}
          />
        </div>
      </CardBody>
    </Card>
  );
}
