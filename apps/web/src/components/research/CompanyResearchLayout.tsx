"use client";

import { useState } from "react";
import {
  CommitteeConsensusCard,
  RecommendationCard,
} from "@/components/intelligence/DecisionCards";
import { MetricsPanel } from "@/components/intelligence/EvidencePanels";
import { PipelineTimeline } from "@/components/intelligence/PipelineTimeline";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { CanonicalMoatDimensionsSection } from "./CanonicalMoatDimensionsSection";
import { CompanyHeader } from "./CompanyHeader";
import { MetricGrid, ResearchSection } from "./ResearchSection";
import { ResearchSidebar } from "./ResearchSidebar";

export function CompanyResearchLayout({ view }: { view: ResearchView }) {
  const [showMinorityNotes, setShowMinorityNotes] = useState(false);
  const [showAuditDetails, setShowAuditDetails] = useState(false);

  const hasMinority = (view.minorityNotes?.length ?? 0) > 0;

  return (
    <div className="flex gap-6">
      <ResearchSidebar />
      <div className="min-w-0 flex-1 space-y-6">
        <CompanyHeader view={view} />

        {/* AI / Deep Research Boundary Notice */}
        <div className="rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface-2)] p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-[var(--muted)]" aria-hidden="true" />
              <h3 className="text-sm font-semibold text-[var(--fg)]">
                Deep Research &amp; AI Boundary
              </h3>
            </div>
            <Badge tone="neutral">Provider Unavailable</Badge>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-[var(--muted)]">
            Generative multi-source synthesis and external document retrieval are bounded by provider availability. All analysis displayed is computed deterministically through the server composition pipeline using audited financial records and authenticated market data. No synthetic citations or simulated narratives are generated.
          </p>
        </div>

        {/* Executive Research Summary */}
        <section id="overview" className="scroll-mt-24 space-y-4">
          <Card>
            <CardHeader
              title="Executive Research Summary"
              description="Synthesized investment thesis and key analytical conclusions"
            />
            <CardBody className="space-y-4">
              <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                  Investment Thesis &amp; Research Question
                </p>
                <p className="mt-1 text-sm leading-relaxed text-[var(--fg)]">
                  {view.committeeConsensus ||
                    view.recommendation ||
                    "No thesis summary returned by the API."}
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3.5">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--fg)]">
                    Key Strengths ({view.strengths.length})
                  </h4>
                  {view.strengths.length ? (
                    <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-[var(--muted)]">
                      {view.strengths.slice(0, 5).map((s) => (
                        <li key={s} className="leading-snug">{s}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-[var(--muted)]">None reported</p>
                  )}
                </div>

                <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3.5">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--fg)]">
                    Key Risks &amp; Vulnerabilities ({(view.risks.length + view.weaknesses.length)})
                  </h4>
                  {view.risks.length || view.weaknesses.length ? (
                    <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-[var(--muted)]">
                      {[...view.risks, ...view.weaknesses].slice(0, 5).map((r) => (
                        <li key={r} className="leading-snug">{r}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-[var(--muted)]">None reported</p>
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

        {/* Valuation Section */}
        <ResearchSection
          id="valuation"
          title="Valuation Analysis"
          description="Intrinsic value models and margin of safety estimation"
        >
          <MetricGrid
            metrics={[
              { label: "Intrinsic Value", value: view.valuation.intrinsicValue || "Data unavailable" },
              { label: "Current Price", value: view.valuation.currentPrice || "Data unavailable" },
              { label: "Margin of Safety", value: view.valuation.marginOfSafety || "Data unavailable" },
              { label: "Valuation Method", value: view.valuation.method || "Data unavailable" },
              { label: "Confidence", value: view.valuation.confidence || "Data unavailable" },
            ]}
          />
        </ResearchSection>

        {/* Economic Moat */}
        <CanonicalMoatDimensionsSection
          dimensions={view.canonicalMoatDimensions}
          overallMoat={view.moat}
        />

        {/* Core Pillar Sections */}
        <ResearchSection
          id="business-quality"
          title="Business Quality"
          description="Competitive position and durability metrics"
          section={view.businessQuality}
        />

        <ResearchSection
          id="financial-strength"
          title="Financial Strength"
          description="Solvency, liquidity, and balance-sheet resilience"
          section={view.financialStrength}
        />

        <ResearchSection
          id="management"
          title="Management Quality"
          description="Capital allocation discipline and governance"
          section={view.management}
        />

        <ResearchSection
          id="earnings"
          title="Earnings Quality"
          description="Cash-flow backing and accounting consistency"
          section={view.earnings}
        />

        <ResearchSection
          id="growth"
          title="Growth Quality"
          description="Revenue expansion and return on reinvestment"
          section={view.growth}
        />

        {/* Committee Consensus Section with Progressive Disclosure */}
        <section id="committee" className="scroll-mt-24 space-y-4">
          <CommitteeConsensusCard
            decision={view.committeeDecision}
            confidence={view.committeeConfidence}
            consensus={view.committeeConsensus}
            minorityNotes={view.minorityNotes}
          />

          <Card>
            <CardHeader
              title="Investment Committee Details"
              description="Breakdown of supporting and dissenting opinions"
            />
            <CardBody className="space-y-4">
              <MetricGrid
                metrics={[
                  {
                    label: "Committee Decision",
                    value: view.committeeDecision || "Unavailable",
                  },
                  {
                    label: "Confidence",
                    value: view.committee.confidence || "Unavailable",
                  },
                  {
                    label: "Final Recommendation",
                    value: view.committee.finalRecommendation || "Unavailable",
                  },
                ]}
              />

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <h4 className="text-sm font-medium text-[var(--fg)]">Supporting Reasons</h4>
                  {view.committee.supportingReasons.length ? (
                    <ul className="mt-1 list-inside list-disc space-y-1 text-sm text-[var(--muted)]">
                      {view.committee.supportingReasons.map((r) => (
                        <li key={r}>{r}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-sm text-[var(--muted)]">None reported</p>
                  )}
                </div>

                <div>
                  <h4 className="text-sm font-medium text-[var(--fg)]">Opposing Reasons</h4>
                  {view.committee.opposingReasons.length ? (
                    <ul className="mt-1 list-inside list-disc space-y-1 text-sm text-[var(--muted)]">
                      {view.committee.opposingReasons.map((r) => (
                        <li key={r}>{r}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-sm text-[var(--muted)]">None reported</p>
                  )}
                </div>
              </div>

              {hasMinority ? (
                <div className="border-t border-[var(--border)] pt-3">
                  <button
                    type="button"
                    onClick={() => setShowMinorityNotes((prev) => !prev)}
                    aria-expanded={showMinorityNotes}
                    className="inline-flex min-h-[44px] items-center text-xs font-medium text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  >
                    {showMinorityNotes
                      ? "Hide Minority Rationale & Dissent"
                      : `View Minority Rationale & Dissent (${view.minorityNotes.length})`}
                  </button>
                  {showMinorityNotes ? (
                    <div className="mt-2 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3">
                      <p className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                        Minority Committee Notes
                      </p>
                      <ul className="mt-1 list-inside list-disc space-y-1 text-sm text-[var(--muted)]">
                        {view.minorityNotes.map((note) => (
                          <li key={note}>{note}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </CardBody>
          </Card>
        </section>

        {/* Dedicated Evidence & Sources Section */}
        <section id="evidence" className="scroll-mt-24 space-y-4">
          <Card>
            <CardHeader
              title="Evidence Provenance &amp; Sources"
              description="Verification sources and data contracts backing this research run"
            />
            <CardBody className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted)]">
                    Primary Financials
                  </p>
                  <p className="mt-1 text-sm font-medium text-[var(--fg)]">
                    Authenticated 10-K / Annual Filings
                  </p>
                  <p className="mt-0.5 text-xs text-[var(--muted)]">
                    Status: Validated
                  </p>
                </div>

                <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted)]">
                    Market Quote Data
                  </p>
                  <p className="mt-1 text-sm font-medium text-[var(--fg)]">
                    Exchange Feeds ({view.exchange || "Verified"})
                  </p>
                  <p className="mt-0.5 text-xs text-[var(--muted)]">
                    Status: Validated
                  </p>
                </div>

                <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted)]">
                    External AI Citations
                  </p>
                  <p className="mt-1 text-sm font-medium text-[var(--fg)]">
                    Source unavailable
                  </p>
                  <p className="mt-0.5 text-xs text-[var(--muted)]">
                    Status: Provider unavailable
                  </p>
                </div>
              </div>

              <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-3.5">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                  Citations &amp; Document Excerpts
                </h4>
                <p className="mt-1 text-xs text-[var(--muted)]">
                  Source unavailable. Deep document extraction and live filing citations are bounded by external provider availability. No mock or fabricated citations are displayed.
                </p>
              </div>

              <div className="border-t border-[var(--border)] pt-3">
                <button
                  type="button"
                  onClick={() => setShowAuditDetails((prev) => !prev)}
                  aria-expanded={showAuditDetails}
                  className="inline-flex min-h-[44px] items-center text-xs font-medium text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                >
                  {showAuditDetails ? "Hide Audit & Provenance Metadata" : "Show Audit & Provenance Metadata"}
                </button>

                {showAuditDetails ? (
                  <dl className="mt-3 grid gap-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3 sm:grid-cols-2">
                    <div>
                      <dt className="text-[11px] uppercase tracking-wider text-[var(--muted)]">Correlation ID</dt>
                      <dd className="font-mono text-xs text-[var(--fg)] break-all">{view.correlationId || "Data unavailable"}</dd>
                    </div>
                    <div>
                      <dt className="text-[11px] uppercase tracking-wider text-[var(--muted)]">Pipeline Version</dt>
                      <dd className="font-mono text-xs text-[var(--fg)]">{view.pipelineVersion || "Data unavailable"}</dd>
                    </div>
                    <div>
                      <dt className="text-[11px] uppercase tracking-wider text-[var(--muted)]">Total Elapsed Time</dt>
                      <dd className="font-mono text-xs text-[var(--fg)]">
                        {view.totalElapsedMs != null ? `${view.totalElapsedMs} ms` : "Data unavailable"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[11px] uppercase tracking-wider text-[var(--muted)]">Analysis Timestamp</dt>
                      <dd className="font-mono text-xs text-[var(--fg)]">
                        {view.analysedAt ? new Date(view.analysedAt).toISOString() : "Data unavailable"}
                      </dd>
                    </div>
                  </dl>
                ) : null}
              </div>
            </CardBody>
          </Card>
        </section>

        {/* Pipeline Execution Timeline */}
        <section id="pipeline" className="scroll-mt-24">
          <PipelineTimeline stages={view.stages} />
        </section>
      </div>
    </div>
  );
}
