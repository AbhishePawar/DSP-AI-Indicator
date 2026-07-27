"use client";

import type { PortfolioSummary as PortfolioSummaryModel } from "@/lib/portfolio/model";
import { PortfolioCard } from "./PortfolioCard";

export function PortfolioSummary({ summary }: { summary: PortfolioSummaryModel }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <PortfolioCard label="Total Holdings" value={summary.totalHoldings} />
      <PortfolioCard label="Portfolio Value" value={summary.portfolioValue} />
      <PortfolioCard label="Cash Allocation" value={summary.cashAllocation} />
      <PortfolioCard
        label="Average Quality Score"
        value={summary.averageQualityScore}
      />
      <PortfolioCard
        label="Average Recommendation"
        value={summary.averageRecommendation}
      />
    </div>
  );
}
