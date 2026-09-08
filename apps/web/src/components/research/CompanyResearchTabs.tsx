"use client";

import { useState, useRef, useCallback } from "react";
import type { KeyboardEvent } from "react";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { MetricGrid, ResearchSection } from "./ResearchSection";
import { Badge } from "@/components/ui/Badge";
import {
  CommitteeConsensusCard,
  RecommendationCard,
} from "@/components/intelligence/DecisionCards";
import { MetricsPanel } from "@/components/intelligence/EvidencePanels";
import { PipelineTimeline } from "@/components/intelligence/PipelineTimeline";

const TAB_IDS = [
  "valuation",
  "financials",
  "moat",
  "quality",
  "risk",
  "recommendation",
  "evidence",
] as const;

type TabId = (typeof TAB_IDS)[number];

const TAB_LABELS: Record<TabId, string> = {
  valuation: "Valuation",
  financials: "Financials",
  moat: "Moat",
  quality: "Quality",
  risk: "Risk",
  recommendation: "Recommendation",
  evidence: "Evidence",
};

function ValuationTab({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-8">
      <ResearchSection
        id="tab-valuation"
        title="Valuation"
        description="Intrinsic value, margin of safety, and method confidence"
        section={view.recommendationStage}
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
    </div>
  );
}

function FinancialsTab({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-8">
      <ResearchSection
        id="tab-financial"
        title="Financial Strength"
        description="Debt, liquidity, and cash flow quality"
        section={view.financialStrength}
      />
      <ResearchSection
        id="tab-earnings"
        title="Earnings Quality"
        description="Consistency, cash conversion, and accounting quality"
        section={view.earnings}
      />
      <ResearchSection
        id="tab-growth"
        title="Growth Quality"
        description="Revenue growth, profit growth, and reinvestment quality"
        section={view.growth}
      />
    </div>
  );
}

function MoatTab({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-8">
      <ResearchSection
        id="tab-moat"
        title="Economic Moat"
        description="Competitive position and moat durability"
        section={view.moat}
      />
    </div>
  );
}

function QualityTab({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-8">
      <ResearchSection
        id="tab-business-quality"
        title="Business Quality"
        description="Aggregated business quality score across all dimensions"
        section={view.businessQuality}
      />
      <ResearchSection
        id="tab-management"
        title="Management Quality"
        description="Capital allocation, governance, and shareholder alignment"
        section={view.management}
      />
    </div>
  );
}

function RiskTab({ view }: { view: ResearchView }) {
  const riskItems = view.risk;

  return (
    <div className="space-y-8">
      <section id="tab-risk" className="scroll-mt-24 space-y-6">
        <div className="border-b border-[var(--border)] pb-3">
          <h2 className="font-[family-name:var(--font-display)] text-lg sm:text-xl tracking-tight text-[var(--fg)]">
            Risk Assessment
          </h2>
          <p className="mt-0.5 text-sm text-[var(--muted)]">
            Structural risk aggregation from composition pipeline
          </p>
        </div>

        {/* Key risks list */}
        {view.risks.length > 0 ? (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-3">
              Identified Risks
            </h3>
            <ul className="space-y-2">
              {view.risks.map((r) => (
                <li key={r} className="flex gap-2.5 text-sm text-[var(--fg)]">
                  <span
                    className="mt-1.5 inline-block h-1 w-1 shrink-0 rounded-full bg-[var(--danger-fg)]"
                    aria-hidden
                  />
                  <span className="leading-relaxed">{r}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-sm text-[var(--muted)]">No risks identified.</p>
        )}

        {/* Weaknesses */}
        {view.weaknesses.length > 0 ? (
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-3">
              Weaknesses
            </h3>
            <ul className="space-y-2">
              {view.weaknesses.map((w) => (
                <li key={w} className="flex gap-2.5 text-sm text-[var(--fg)]">
                  <span
                    className="mt-1.5 inline-block h-1 w-1 shrink-0 rounded-full bg-[var(--warning-fg)]"
                    aria-hidden
                  />
                  <span className="leading-relaxed">{w}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {/* Structured risk payload if available */}
        {riskItems ? (
          <div className="rounded-lg border border-[var(--border)] p-4 space-y-3">
            <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">
              Risk Payload
            </p>
            <MetricGrid
              metrics={[
                {
                  label: "Overall Risk Level",
                  value: String(riskItems.overall_risk_level ?? "Unavailable"),
                },
                {
                  label: "Categories Available",
                  value: String(riskItems.categories_available ?? "—"),
                },
                {
                  label: "Categories Total",
                  value: String(riskItems.categories_total ?? "—"),
                },
              ]}
            />
          </div>
        ) : null}
      </section>
    </div>
  );
}

function RecommendationTab({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-8">
      {/* Investment thesis */}
      {(view.committeeConsensus || view.recommendation) ? (
        <div className="border-l-2 border-[var(--accent)] pl-5 py-1">
          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-2">
            Investment Thesis
          </p>
          <p className="text-base leading-relaxed text-[var(--fg)]">
            {view.committeeConsensus || view.recommendation}
          </p>
        </div>
      ) : null}

      <RecommendationCard
        decision={view.recommendation}
        confidence={view.recommendationConfidence}
        marginOfSafety={view.marginOfSafety}
      />

      {/* Committee deliberation */}
      <section id="tab-committee" className="scroll-mt-24 space-y-6">
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

        <MetricGrid
          metrics={[
            { label: "Committee Decision", value: view.committeeDecision },
            { label: "Confidence", value: view.committee.confidence },
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
                    <span
                      className="mt-1.5 inline-block h-1 w-1 shrink-0 rounded-full bg-[var(--accent)]"
                      aria-hidden
                    />
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
                    <span
                      className="mt-1.5 inline-block h-1 w-1 shrink-0 rounded-full bg-[var(--danger-fg)]"
                      aria-hidden
                    />
                    <span className="leading-relaxed">{r}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-[var(--muted)]">None reported</p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function EvidenceTab({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-8">
      {/* Strengths & weaknesses evidence */}
      <MetricsPanel
        strengths={view.strengths}
        weaknesses={view.weaknesses}
        risks={view.risks}
      />

      {/* Pipeline stage evidence */}
      <section id="tab-pipeline" className="scroll-mt-24 space-y-6">
        <div className="border-b border-[var(--border)] pb-3">
          <h2 className="font-[family-name:var(--font-display)] text-lg sm:text-xl tracking-tight text-[var(--fg)]">
            Pipeline Evidence
          </h2>
          <p className="mt-0.5 text-sm text-[var(--muted)]">
            Stage-by-stage execution trace and signal provenance
          </p>
        </div>
        <PipelineTimeline stages={view.stages} />
      </section>

      {/* Stage summary table */}
      <section id="tab-stages" className="scroll-mt-24 space-y-4">
        <div className="border-b border-[var(--border)] pb-3">
          <h2 className="font-[family-name:var(--font-display)] text-lg sm:text-xl tracking-tight text-[var(--fg)]">
            Stage Summary
          </h2>
          <p className="mt-0.5 text-sm text-[var(--muted)]">
            All pipeline stages with status and decision
          </p>
        </div>
        <div className="divide-y divide-[var(--border)] rounded-lg border border-[var(--border)] overflow-hidden">
          {view.stages.map((stage) => (
            <div
              key={stage.stage}
              className="flex items-center justify-between gap-4 px-4 py-3 bg-[var(--surface-1)] hover:bg-[var(--surface-2)] transition-colors"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-[var(--fg)] truncate">
                  {stage.stage}
                </p>
                {stage.label ? (
                  <p className="text-xs text-[var(--muted)] mt-0.5 truncate">
                    {stage.label}
                  </p>
                ) : null}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {stage.decision ? (
                  <span className="text-xs text-[var(--muted)] hidden sm:block">
                    {stage.decision}
                  </span>
                ) : null}
                <Badge
                  tone={
                    stage.status === "succeeded" ? "success"
                      : stage.status === "failed" ? "danger" : "neutral"
                  }
                >
                  {stage.status}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export function CompanyResearchTabs({ view }: { view: ResearchView }) {
  const [activeTab, setActiveTab] = useState<TabId>("valuation");
  // Wave 4: Ref map for tab panels to manage focus on tab switch
  const panelRefs = useRef<Partial<Record<TabId, HTMLDivElement | null>>>({});

  const handleTabChange = useCallback((id: TabId) => {
    setActiveTab(id);
    // Move focus to the panel after state update
    requestAnimationFrame(() => {
      panelRefs.current[id]?.focus();
    });
  }, []);

  // Wave 4: Keyboard navigation within tablist (arrow keys)
  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, id: TabId) {
    const currentIndex = TAB_IDS.indexOf(id);
    if (event.key === "ArrowRight") {
      event.preventDefault();
      const nextId = TAB_IDS[(currentIndex + 1) % TAB_IDS.length];
      handleTabChange(nextId);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      const prevId = TAB_IDS[(currentIndex - 1 + TAB_IDS.length) % TAB_IDS.length];
      handleTabChange(prevId);
    } else if (event.key === "Home") {
      event.preventDefault();
      handleTabChange(TAB_IDS[0]);
    } else if (event.key === "End") {
      event.preventDefault();
      handleTabChange(TAB_IDS[TAB_IDS.length - 1]);
    }
  }

  return (
    <div className="space-y-6">
      {/* Tab bar */}
      <div
        role="tablist"
        aria-label="Company research sections"
        className="flex gap-0.5 overflow-x-auto border-b border-[var(--border)] pb-px scrollbar-none"
      >
        {TAB_IDS.map((id) => {
          const selected = id === activeTab;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              id={`research-tab-${id}`}
              aria-selected={selected}
              aria-controls={`research-panel-${id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => handleTabChange(id)}
              onKeyDown={(e) => handleTabKeyDown(e, id)}
              className={[
                "shrink-0 px-4 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded-t",
                selected
                  ? "border-b-2 border-[var(--accent)] text-[var(--fg)]"
                  : "text-[var(--muted)] hover:text-[var(--fg)]",
              ].join(" ")}
            >
              {TAB_LABELS[id]}
            </button>
          );
        })}
      </div>

      {/* Tab panels — Wave 4: tabIndex={0} + ref for focus management */}
      {TAB_IDS.map((id) =>
        id === activeTab ? (
          <div
            key={id}
            role="tabpanel"
            id={`research-panel-${id}`}
            aria-labelledby={`research-tab-${id}`}
            tabIndex={0}
            ref={(el) => { panelRefs.current[id] = el; }}
            className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] rounded-[var(--radius-sm)]"
          >
            {id === "valuation" && <ValuationTab view={view} />}
            {id === "financials" && <FinancialsTab view={view} />}
            {id === "moat" && <MoatTab view={view} />}
            {id === "quality" && <QualityTab view={view} />}
            {id === "risk" && <RiskTab view={view} />}
            {id === "recommendation" && <RecommendationTab view={view} />}
            {id === "evidence" && <EvidenceTab view={view} />}
          </div>
        ) : null,
      )}
    </div>
  );
}
