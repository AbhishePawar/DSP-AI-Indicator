"use client";

import {
  CommitteeConsensusCard,
  RecommendationCard,
} from "@/components/intelligence/DecisionCards";
import { MetricsPanel } from "@/components/intelligence/EvidencePanels";
import { PipelineTimeline } from "@/components/intelligence/PipelineTimeline";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { CanonicalMoatDimensionsSection } from "./CanonicalMoatDimensionsSection";
import { CompanyHeader } from "./CompanyHeader";
import { MetricGrid, ResearchSection } from "./ResearchSection";
import { ResearchSidebar } from "./ResearchSidebar";

export function CompanyResearchLayout({ view }: { view: ResearchView }) {
  return (
    <div className="flex gap-6">
      <ResearchSidebar />
      <div className="min-w-0 flex-1 space-y-6">
        <CompanyHeader view={view} />

        <section id="overview" className="scroll-mt-24 space-y-4">
          <Card>
            <CardHeader
              title="Overview"
              description="Summary from the composition pipeline"
            />
            <CardBody className="space-y-4">
              <div>
                <h4 className="text-sm font-medium">Investment Thesis</h4>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  {view.committeeConsensus ||
                    view.recommendation ||
                    "No thesis summary returned by the API."}
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <h4 className="text-sm font-medium">Key Highlights</h4>
                  {view.strengths.length ? (
                    <ul className="mt-1 list-inside list-disc text-sm text-[var(--muted)]">
                      {view.strengths.slice(0, 5).map((s) => (
                        <li key={s}>{s}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-sm text-[var(--muted)]">None reported</p>
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-medium">Key Risks</h4>
                  {view.risks.length || view.weaknesses.length ? (
                    <ul className="mt-1 list-inside list-disc text-sm text-[var(--muted)]">
                      {[...view.risks, ...view.weaknesses].slice(0, 5).map((r) => (
                        <li key={r}>{r}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-sm text-[var(--muted)]">None reported</p>
                  )}
                </div>
              </div>
            </CardBody>
          </Card>
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

        <CanonicalMoatDimensionsSection
          dimensions={view.canonicalMoatDimensions}
          overallMoat={view.moat}
        />

        <ResearchSection
          id="business-quality"
          title="Business Quality"
          description="Aggregator and component stage labels"
          section={view.businessQuality}
        />

        <ResearchSection
          id="financial-strength"
          title="Financial Strength"
          description="Stage summary from financial_strength"
          section={view.financialStrength}
        />

        <ResearchSection
          id="management"
          title="Management Quality"
          description="Stage summary from management_quality"
          section={view.management}
        />

        <ResearchSection
          id="earnings"
          title="Earnings Quality"
          description="Stage summary from earnings_quality"
          section={view.earnings}
        />

        <ResearchSection
          id="growth"
          title="Growth Quality"
          description="Stage summary from growth_quality"
          section={view.growth}
        />

        <section id="committee" className="scroll-mt-24 space-y-4">
          <CommitteeConsensusCard
            decision={view.committeeDecision}
            confidence={view.committeeConfidence}
            consensus={view.committeeConsensus}
            minorityNotes={view.minorityNotes}
          />
          <Card>
            <CardHeader title="Committee Detail" />
            <CardBody className="space-y-4">
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
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <h4 className="text-sm font-medium">Supporting Reasons</h4>
                  {view.committee.supportingReasons.length ? (
                    <ul className="mt-1 list-inside list-disc text-sm text-[var(--muted)]">
                      {view.committee.supportingReasons.map((r) => (
                        <li key={r}>{r}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-sm text-[var(--muted)]">None reported</p>
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-medium">Opposing Reasons</h4>
                  {view.committee.opposingReasons.length ? (
                    <ul className="mt-1 list-inside list-disc text-sm text-[var(--muted)]">
                      {view.committee.opposingReasons.map((r) => (
                        <li key={r}>{r}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-sm text-[var(--muted)]">None reported</p>
                  )}
                </div>
              </div>
            </CardBody>
          </Card>
        </section>

        <section id="pipeline" className="scroll-mt-24">
          <PipelineTimeline stages={view.stages} />
        </section>
      </div>
    </div>
  );
}
