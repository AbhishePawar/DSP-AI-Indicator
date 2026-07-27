"use client";

import { useEffect, useRef } from "react";

import { MarketDataCard } from "@/components/market/MarketDataCard";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody } from "@/components/ui/Card";
import { AddToPortfolioButton } from "@/components/portfolio/AddToPortfolioButton";
import { COMPANY_CATALOGUE } from "@/lib/companies/catalogue";
import { formatPct } from "@/lib/intelligence/mapResponse";
import { usePortfolio } from "@/lib/portfolio/PortfolioProvider";
import { DeterministicAnalysisLabel } from "@/components/market/MarketStatusIndicator";

export function CompanyHeader({ view }: { view: ResearchView }) {
  const { recordResearchOpened } = usePortfolio();
  const recorded = useRef<string | null>(null);
  const catalogueEntry = COMPANY_CATALOGUE.find(
    (c) => c.ticker.toUpperCase() === view.ticker.toUpperCase(),
  );

  useEffect(() => {
    if (recorded.current === view.ticker) return;
    recorded.current = view.ticker;
    recordResearchOpened(view.company || view.ticker);
  }, [view.ticker, view.company, recordResearchOpened]);

  return (
    <div className="space-y-4">
      <Card>
        <CardBody className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs uppercase tracking-wider text-[var(--muted)]">
                Company Research
              </p>
              <DeterministicAnalysisLabel />
            </div>
          <h1 className="mt-1 font-[family-name:var(--font-display)] text-3xl tracking-tight">
            {view.company}
          </h1>
          <p className="mt-1 font-mono text-sm text-[var(--muted)]">
            {view.ticker} · {view.exchange}
          </p>
          <div className="mt-3">
            <AddToPortfolioButton
              company={view.company}
              ticker={view.ticker}
              sector={catalogueEntry?.sector ?? "Unknown"}
              recommendation={view.recommendation}
              researchAvailable={view.ok}
              size="md"
            />
          </div>
        </div>
        <div className="grid gap-2 text-right sm:grid-cols-2">
          <div>
            <p className="text-xs text-[var(--muted)]">Recommendation</p>
            <p className="font-[family-name:var(--font-display)] text-xl">
              {view.recommendation}
            </p>
          </div>
          <div>
            <p className="text-xs text-[var(--muted)]">Overall Rating</p>
            <p className="font-[family-name:var(--font-display)] text-xl">
              {view.businessQualityLabel}
            </p>
          </div>
          <div className="sm:col-span-2">
            <p className="text-xs text-[var(--muted)]">Last Analysis</p>
            <p className="font-mono text-sm">
              {view.analysedAt
                ? new Date(view.analysedAt).toLocaleString()
                : "—"}
            </p>
            <div className="mt-2 flex flex-wrap justify-end gap-2">
              <Badge tone={view.ok ? "success" : "danger"}>
                {view.ok ? "Pipeline OK" : "Issues"}
              </Badge>
              <Badge tone="neutral">
                Confidence {formatPct(view.recommendationConfidence)}
              </Badge>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>

      <MarketDataCard ticker={view.ticker} />
    </div>
  );
}
