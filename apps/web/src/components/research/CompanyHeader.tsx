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
        <CardBody className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                Company Research
              </span>
              <DeterministicAnalysisLabel />
              <Badge tone="neutral">
                Deep Research: Provider Unavailable (Deterministic Pipeline Only)
              </Badge>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={view.ok ? "success" : "danger"}>
                {view.ok ? "Pipeline Succeeded" : "Pipeline Degraded / Issues"}
              </Badge>
              <Badge tone="neutral">
                Confidence {formatPct(view.recommendationConfidence)}
              </Badge>
            </div>
          </div>

          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 max-w-xl">
              <h1 className="font-[family-name:var(--font-display)] text-2xl font-bold tracking-tight text-[var(--fg)] sm:text-3xl">
                {view.company || view.ticker}
              </h1>
              <p className="mt-1 font-mono text-sm text-[var(--muted)]">
                {view.ticker} · {view.exchange || "Exchange unavailable"}
              </p>
              <div className="mt-3 inline-block min-h-[44px]">
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

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-2.5">
                <p className="text-[11px] font-medium uppercase tracking-wider text-[var(--muted)]">
                  Recommendation
                </p>
                <p className="mt-1 font-[family-name:var(--font-display)] text-lg font-semibold text-[var(--fg)]">
                  {view.recommendation || "Unavailable"}
                </p>
              </div>

              <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-2.5">
                <p className="text-[11px] font-medium uppercase tracking-wider text-[var(--muted)]">
                  Overall Rating
                </p>
                <p className="mt-1 font-[family-name:var(--font-display)] text-lg font-semibold text-[var(--fg)]">
                  {view.businessQualityLabel || "Unavailable"}
                </p>
              </div>

              <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-2.5">
                <p className="text-[11px] font-medium uppercase tracking-wider text-[var(--muted)]">
                  Analysed At
                </p>
                <p className="mt-1 font-mono text-xs text-[var(--fg)]">
                  {view.analysedAt
                    ? new Date(view.analysedAt).toLocaleString()
                    : "Data unavailable"}
                </p>
              </div>

              <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-2.5">
                <p className="text-[11px] font-medium uppercase tracking-wider text-[var(--muted)]">
                  Pipeline Version
                </p>
                <p className="mt-1 font-mono text-xs text-[var(--fg)]">
                  {view.pipelineVersion || "v1.0.0"}
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border)] pt-2 text-xs text-[var(--muted)]">
            <span className="font-mono break-all">
              Correlation ID: {view.correlationId || "Data unavailable"}
            </span>
            <span>
              Platform: {view.platformVersion || "v1.0.0"}
            </span>
          </div>
        </CardBody>
      </Card>

      <MarketDataCard ticker={view.ticker} />
    </div>
  );
}
