"use client";

import {
  CommitteeConsensusCard,
  RecommendationCard,
} from "@/components/intelligence/DecisionCards";
import { MetricsPanel } from "@/components/intelligence/EvidencePanels";
import { PipelineTimeline } from "@/components/intelligence/PipelineTimeline";

import type { ResearchView } from "@/lib/research/mapResearchView";
import { CanonicalMoatDimensionsSection } from "./CanonicalMoatDimensionsSection";
import { CompanyHeader } from "./CompanyHeader";
import { MetricGrid, ResearchSection } from "./ResearchSection";
import { ResearchSidebar } from "./ResearchSidebar";

export function CompanyResearchLayout({ view }: { view: ResearchView }) {
  return (
    <div className="flex gap-8">
      <ResearchSidebar />

      {/* Main report body */}
      <div className="min-w-0 flex-1 space-y-12">
        <CompanyHeader view={view} />

        {/* 1. Executive Summary */}
        <section id="overview" className="scroll-mt-24 space-y-6">
          <div className="border-b border-[var(--border)] pb-3">
            <h2 className="font-[family-name:var(--font-display)] text-lg sm:text-xl tracking-tight text-[var(--fg)]">
              Executive Summary
            </h2>
            <p className="mt-0.5 text-sm text-[var(--muted)]">
              Investment thesis and key findings from the composition pipeline
            </p>
          </div>

          {/* Investment thesis — most prominent text block */}
          <div className="border-l-2 border-[var(--accent)] pl-5 py-1">
            <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-2">
              Investment Thesis
            </p>
            <p className="text-base leading-relaxed text-[var(--fg)]">
              {view.committeeConsensus ||
                view.recommendation ||
                "No thesis summary returned by the API."}
            </p>
          </div>

          {/* Key highlights and risks — side by side on sm+, stacked on mobile */}
          <div className="grid gap-8 sm:grid-cols-2">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-3">
                Key Highlights
              </h3>
              {view.strengths.length ? (
                <ul className="space-y-2">
                  {view.strengths.slice(0, 5).map((s) => (
                    <li key={s} className="flex gap-2.5 text-sm text-[var(--fg)]">
                      <span className="mt-1.5 inline-block h-1 w-1 rounded-full bg-[var(--accent)] shrink-0" aria-hidden />
                      <span className="leading-relaxed">{s}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-[var(--muted)]">None reported</p>
              )}
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-3">
                Key Risks
              </h3>
              {view.risks.length || view.weaknesses.length ? (
                <ul className="space-y-2">
                  {[...view.risks, ...view.weaknesses].slice(0, 5).map((r) => (
                    <li key={r} className="flex gap-2.5 text-sm text-[var(--fg)]">
                      <span className="mt-1.5 inline-block h-1 w-1 rounded-full bg-[var(--danger-fg)] shrink-0" aria-hidden />
                      <span className="leading-relaxed">{r}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-[var(--muted)]">None reported</p>
              )}
            </div>
          </div>

          {/* Recommendation and evidence panels */}
          <RecommendationCard
            decision={view.recommendation}
            confidence={view.recommendationConfidence}
            marginOfSafety={view.marginOfSafety}
          />
          <MetricsPanel
            strengths={view.strengths}
            weaknesses={view.weaknesses}
            risks={view.risks}
          />
        </section>

        {/* 2. Business Quality */}
        <ResearchSection
          id="business-quality"
          title="Business Quality"
          description="Aggregator and component stage labels"
          section={view.businessQuality}
        />

        {/* 3. Financial Strength */}
        <ResearchSection
          id="financial-strength"
          title="Financial Strength"
          description="Stage summary from financial_strength"
          section={view.financialStrength}
        />

        {/* 4. Management Quality */}
        <ResearchSection
          id="management"
          title="Management Quality"
          description="Stage summary from management_quality"
          section={view.management}
        />

        {/* 5. Earnings Quality */}
        <ResearchSection
          id="earnings"
          title="Earnings Quality"
          description="Stage summary from earnings_quality"
          section={view.earnings}
        />

        {/* 6. Growth Quality */}
        <ResearchSection
          id="growth"
          title="Growth Quality"
          description="Stage summary from growth_quality"
          section={view.growth}
        />

        {/* 7. Economic Moat — canonical six-dimension contract */}
        <CanonicalMoatDimensionsSection
          dimensions={view.canonicalMoatDimensions}
          overallMoat={view.moat}
        />

        {/* 8. Valuation */}
        <ResearchSection
          id="valuation"
          title="Valuation"
          description="Signals and stage summary from the API"
        >
          <MetricGrid
            metrics={[
              { label: "Intrinsic Value", value: view.valuation.intrinsicValue },
              { label: "Current Price", value: view.valuation.currentPrice },
              { label: "Margin of Safety", value: view.valuation.marginOfSafety },
              { label: "Valuation Method", value: view.valuation.method },
              { label: "Confidence", value: view.valuation.confidence },
            ]}
          />
        </ResearchSection>

        {/* 9. Investment Committee */}
        <section id="committee" className="scroll-mt-24 space-y-6">
          <div className="border-b border-[var(--border)] pb-3">
            <h2 className="font-[family-name:var(--font-display)] text-lg sm:text-xl tracking-tight text-[var(--fg)]">
              Investment Committee
            </h2>
            <p className="mt-0.5 text-sm text-[var(--muted)]">
              Multi-member committee deliberation and final decision
            </p>
          </div>

          <CommitteeConsensusCard
            decision={view.committeeDecision}
            confidence={view.committeeConfidence}
            consensus={view.committeeConsensus}
            minorityNotes={view.minorityNotes}
          />

          {/* Committee detail — document style, no extra card */}
          <div className="space-y-6">
            <MetricGrid
              metrics={[
                {
                  label: "Committee Decision",
                  value: view.committeeDecision,
                },
                {
                  label: "Confidence",
                  value: view.committee.confidence,
                },
                {
                  label: "Final Recommendation",
                  value: view.committee.finalRecommendation,
                },
              ]}
            />

            <div className="grid gap-8 sm:grid-cols-2 pt-2">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-3">
                  Supporting Reasons
                </h3>
                {view.committee.supportingReasons.length ? (
                  <ul className="space-y-2">
                    {view.committee.supportingReasons.map((r) => (
                      <li key={r} className="flex gap-2.5 text-sm text-[var(--fg)]">
                        <span className="mt-1.5 inline-block h-1 w-1 rounded-full bg-[var(--accent)] shrink-0" aria-hidden />
                        <span className="leading-relaxed">{r}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-[var(--muted)]">None reported</p>
                )}
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-3">
                  Opposing Reasons
                </h3>
                {view.committee.opposingReasons.length ? (
                  <ul className="space-y-2">
                    {view.committee.opposingReasons.map((r) => (
                      <li key={r} className="flex gap-2.5 text-sm text-[var(--fg)]">
                        <span className="mt-1.5 inline-block h-1 w-1 rounded-full bg-[var(--danger-fg)] shrink-0" aria-hidden />
                        <span className="leading-relaxed">{r}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-[var(--muted)]">None reported</p>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* 10. AI Analyst View */}
        <section id="pipeline" className="scroll-mt-24 space-y-6">
          <div className="border-b border-[var(--border)] pb-3">
            <h2 className="font-[family-name:var(--font-display)] text-lg sm:text-xl tracking-tight text-[var(--fg)]">
              AI Analyst View
            </h2>
            <p className="mt-0.5 text-sm text-[var(--muted)]">
              Pipeline stage execution and signal provenance
            </p>
          </div>
          <PipelineTimeline stages={view.stages} />
        </section>
      </div>
    </div>
  );
}
