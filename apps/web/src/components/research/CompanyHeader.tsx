"use client";

import { useEffect, useRef, useState } from "react";

import { MarketDataCard } from "@/components/market/MarketDataCard";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { Badge } from "@/components/ui/Badge";
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

  const [analysedAtLabel, setAnalysedAtLabel] = useState<string>("—");
  useEffect(() => {
    if (view.analysedAt) {
      setAnalysedAtLabel(new Date(view.analysedAt).toLocaleString());
    } else {
      setAnalysedAtLabel("—");
    }
  }, [view.analysedAt]);

  useEffect(() => {
    if (recorded.current === view.ticker) return;
    recorded.current = view.ticker;
    recordResearchOpened(view.company || view.ticker);
  }, [view.ticker, view.company, recordResearchOpened]);

  return (
    <div className="space-y-6">
      {/* Company identity block — no card, let whitespace do the work */}
      <div className="border-b border-[var(--border)] pb-6">
        <div className="flex flex-col gap-6 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
          {/* Left: identity */}
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">
                Equity Research
              </span>
              <span className="text-[var(--border)] select-none" aria-hidden>·</span>
              <DeterministicAnalysisLabel />
            </div>

            {/* Company name — strongest visual element */}
            <h1 className="font-[family-name:var(--font-display)] text-3xl sm:text-4xl tracking-tight leading-tight text-[var(--fg)]">
              {view.company}
            </h1>

            {/* Ticker / exchange — subdued, monospace */}
            <p className="mt-2 flex flex-wrap items-center gap-1.5">
              <span className="font-mono text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                {view.ticker}
              </span>
              {view.exchange ? (
                <span className="text-[var(--border)] select-none" aria-hidden>·</span>
              ) : null}
              {view.exchange ? (
                <span className="font-mono text-xs text-[var(--muted)]">{view.exchange}</span>
              ) : null}
            </p>

            {/* Analysis timestamp */}
            <p className="mt-1 text-xs text-[var(--muted)]">
              Analysis as of{" "}
              <span className="font-mono">{analysedAtLabel}</span>
            </p>

            {/* Primary action */}
            <div className="mt-5">
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

          {/* Right: key signals — restrained, no excessive boxes */}
          <div className="flex flex-row flex-wrap gap-6 sm:flex-col sm:gap-5 sm:text-right sm:shrink-0 sm:min-w-[160px]">
            {/* Recommendation */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-1">
                Recommendation
              </p>
              <p className="font-[family-name:var(--font-display)] text-xl sm:text-2xl tracking-tight text-[var(--fg)]">
                {view.recommendation}
              </p>
            </div>

            {/* Business quality */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-1">
                Business Quality
              </p>
              <p className="font-[family-name:var(--font-display)] text-lg sm:text-xl tracking-tight text-[var(--fg)]">
                {view.businessQualityLabel}
              </p>
            </div>

            {/* Status badges */}
            <div className="flex flex-wrap sm:justify-end gap-1.5">
              <Badge tone={view.ok ? "success" : "danger"}>
                {view.ok ? "Pipeline OK" : "Issues"}
              </Badge>
              <Badge tone="neutral">
                {formatPct(view.recommendationConfidence)} confidence
              </Badge>
            </div>
          </div>
        </div>
      </div>

      <MarketDataCard ticker={view.ticker} />
    </div>
  );
}
