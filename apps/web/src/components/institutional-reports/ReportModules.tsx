"use client";

/**
 * P9.6 / EPIC-007 — Ontology-aligned report modules (Books 04–07, valuation, committee).
 * Display-only over ResearchView. No client scoring; no stage label aliasing.
 */

import { Badge } from "@/components/ds";
import { formatPct } from "@/lib/intelligence/mapResponse";
import type { ResearchView } from "@/lib/research/mapResearchView";
import {
  FieldRow,
  ListBlock,
  SectionCard,
  StageSectionCard,
  WorkspaceEmpty,
  firstMetric,
  metricValue,
} from "./Primitives";

function valuationMethodValue(
  methods: ResearchView["valuationTransparency"]["methods"],
  names: string[],
): string {
  for (const name of names) {
    const exact = methods.find(
      (m) => m.methodName.toLowerCase() === name.toLowerCase(),
    );
    if (exact) {
      return exact.intrinsicValue !== "Unavailable"
        ? exact.intrinsicValue
        : exact.status;
    }
  }
  for (const name of names) {
    const fuzzy = methods.find((m) =>
      m.methodName.toLowerCase().includes(name.toLowerCase()),
    );
    if (fuzzy) {
      return fuzzy.intrinsicValue !== "Unavailable"
        ? fuzzy.intrinsicValue
        : fuzzy.status;
    }
  }
  return "Unavailable";
}

export function ValuationModule({ view }: { view: ResearchView }) {
  const vt = view.valuationTransparency;
  return (
    <div className="space-y-4 report-module" data-report-module="valuation">
      <SectionCard
        title="Valuation"
        description="Mapped engine outputs only — no client recalculation. Missing methods show Data unavailable."
      >
        <dl>
          <FieldRow
            label="Intrinsic Value"
            value={view.valuation.intrinsicValue}
          />
          <FieldRow label="Current Price" value={view.valuation.currentPrice} />
          <FieldRow
            label="Margin of Safety"
            value={view.valuation.marginOfSafety}
          />
          <FieldRow
            label="DCF"
            value={valuationMethodValue(vt.methods, ["DCF"])}
          />
          <FieldRow
            label="Relative Valuation"
            value={valuationMethodValue(vt.methods, [
              "Relative Valuation",
              "Relative",
            ])}
          />
          <FieldRow
            label="Residual Income"
            value={valuationMethodValue(vt.methods, [
              "Residual Income",
              "Residual",
            ])}
          />
          <FieldRow
            label="EPV"
            value={valuationMethodValue(vt.methods, ["EPV"])}
          />
          <FieldRow
            label="Overall Valuation"
            value={
              vt.executive.valuationVerdict ||
              vt.consensus.consensusValue ||
              view.valuation.method
            }
          />
          <FieldRow label="Confidence" value={view.valuation.confidence} />
        </dl>
      </SectionCard>
      <SectionCard title="Method cards">
        {vt.methods.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No valuation method cards on AnalyseResponse." />
        ) : (
          <ul className="space-y-2" aria-label="Valuation methods">
            {vt.methods.slice(0, 40).map((m) => (
              <li
                key={m.methodName}
                className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2 text-sm"
              >
                <span className="font-medium">{m.methodName}</span>
                <span className="text-[var(--muted)]">
                  {m.intrinsicValue === "Unavailable"
                    ? "Data unavailable."
                    : m.intrinsicValue}
                </span>
                <Badge variant="outline">{m.status}</Badge>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}

export function BusinessQualityModule({ view }: { view: ResearchView }) {
  const bq = view.businessQuality;
  return (
    <div className="space-y-4 report-module" data-report-module="quality">
      <SectionCard
        title="Business Quality"
        description="REP-002 Book 04 labels — values from business_quality_aggregator stage metrics only; never invent sub-scores or alias other stages"
      >
        <dl>
          <FieldRow label="Overall" value={bq.label || bq.score} />
          <FieldRow
            label="Capital Allocation"
            value={firstMetric(bq, [
              "Capital Allocation Quality",
              "Capital Allocation",
            ])}
          />
          <FieldRow
            label="Industry Structure"
            value={firstMetric(bq, ["Industry Structure"])}
          />
          <FieldRow
            label="Operating Discipline"
            value={firstMetric(bq, ["Operating Discipline"])}
          />
          <FieldRow
            label="Franchise Durability"
            value={firstMetric(bq, ["Franchise Durability"])}
          />
          <FieldRow
            label="Reinvestment Opportunity"
            value={firstMetric(bq, ["Reinvestment Opportunity"])}
          />
          <FieldRow label="Confidence" value={bq.confidence} />
          <FieldRow label="Stage status" value={bq.status} />
        </dl>
      </SectionCard>
      <StageSectionCard title="Business Quality stage detail" section={bq} />
    </div>
  );
}

export function ManagementModule({ view }: { view: ResearchView }) {
  const m = view.management;
  return (
    <div className="space-y-4 report-module" data-report-module="management">
      <SectionCard
        title="Management"
        description="REP-002 Book 05 labels — values from management_quality stage only; never invent sub-scores"
      >
        <dl>
          <FieldRow label="Management Quality" value={m.label} />
          <FieldRow
            label="Corporate Governance"
            value={firstMetric(m, ["Corporate Governance", "Governance"])}
          />
          <FieldRow label="Integrity" value={metricValue(m, "Integrity")} />
          <FieldRow
            label="Execution Capability"
            value={firstMetric(m, ["Execution Capability", "Execution"])}
          />
          <FieldRow
            label="Leadership Quality"
            value={firstMetric(m, ["Leadership Quality", "Leadership"])}
          />
          <FieldRow
            label="Shareholder Orientation"
            value={metricValue(m, "Shareholder Orientation")}
          />
          <FieldRow label="Confidence" value={m.confidence} />
          <FieldRow label="Stage status" value={m.status} />
        </dl>
      </SectionCard>
      <StageSectionCard title="Management stage detail" section={m} />
      {m.warnings.length ? (
        <ListBlock title="Stage warnings" items={m.warnings} />
      ) : null}
    </div>
  );
}

export function MoatModule({ view }: { view: ResearchView }) {
  const moat = view.moat;
  return (
    <div className="space-y-4 report-module" data-report-module="moat">
      <SectionCard
        title="Economic Moat"
        description="REP-002 Book 06 labels — values from economic_moat stage only"
      >
        <dl>
          <FieldRow label="Economic Moat" value={moat.label} />
          <FieldRow
            label="Brand Strength"
            value={firstMetric(moat, ["Brand Strength", "Brand"])}
          />
          <FieldRow
            label="Network Effects"
            value={metricValue(moat, "Network Effects")}
          />
          <FieldRow
            label="Switching Costs"
            value={metricValue(moat, "Switching Costs")}
          />
          <FieldRow
            label="Distribution Advantage"
            value={firstMetric(moat, ["Distribution Advantage", "Distribution"])}
          />
          <FieldRow
            label="Cost-Based Moat"
            value={firstMetric(moat, [
              "Cost-Based Moat",
              "Cost Advantage",
            ])}
          />
          <FieldRow
            label="Moat Durability"
            value={firstMetric(moat, ["Moat Durability", "Durability"])}
          />
          <FieldRow label="Score" value={moat.score} />
          <FieldRow label="Confidence" value={moat.confidence} />
        </dl>
      </SectionCard>
      <StageSectionCard title="Moat stage detail" section={moat} />
    </div>
  );
}

export function RiskModule({ view }: { view: ResearchView }) {
  const riskStage =
    view.stages.find((s) =>
      ["risk", "risk_assessment", "risk_unit"].includes(s.stage.toLowerCase()),
    ) ?? null;
  // RC3-001 — Book 07 types never read from financial_strength / valuation / other stages.
  const emptyRisk = { metrics: [] as { label: string; value: string }[] };

  return (
    <div className="space-y-4 report-module" data-report-module="risk">
      <SectionCard
        title="Risk"
        description="REP-002 Book 07 — risk stage metrics only. Never alias Financial Strength, Management, Moat, or Valuation into risk types."
      >
        <dl>
          <FieldRow
            label="Business Risk"
            value={metricValue(emptyRisk, "Business Risk")}
          />
          <FieldRow
            label="Financial Risk"
            value={metricValue(emptyRisk, "Financial Risk")}
          />
          <FieldRow
            label="Operational Risk"
            value={metricValue(emptyRisk, "Operational Risk")}
          />
          <FieldRow
            label="Governance Risk"
            value={metricValue(emptyRisk, "Governance Risk")}
          />
          <FieldRow
            label="Permanent Capital Loss"
            value={metricValue(emptyRisk, "Permanent Capital Loss")}
          />
          <FieldRow
            label="Risk stage"
            value={
              riskStage
                ? `${riskStage.stage}: ${riskStage.status}`
                : "Coverage unavailable."
            }
          />
        </dl>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Typed Book 07 dimensions stay Data unavailable. until the analyse
          contract exposes dedicated risk metrics. Margin of Safety is under
          Valuation.
        </p>
      </SectionCard>
      <ListBlock
        title="Key risks"
        description="From pipeline stage warnings / mapped IntelligenceView.risks"
        items={view.risks}
      />
      <ListBlock title="Weaknesses" items={view.weaknesses} />
      <StageSectionCard
        title="Financial strength stage (separate engine — not Book 07 Risk)"
        section={view.financialStrength}
      />
    </div>
  );
}

export function AiCommitteeModule({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-4 report-module" data-report-module="ai">
      <SectionCard
        title="AI Committee"
        description="Committee decision from investment_committee stage — no local AI inference"
      >
        <dl>
          <FieldRow label="Decision" value={view.committeeDecision} />
          <FieldRow
            label="Reasoning"
            value={view.committee.finalRecommendation}
          />
          <FieldRow
            label="Confidence"
            value={formatPct(view.committeeConfidence)}
          />
          <FieldRow label="Consensus" value={view.committeeConsensus} />
          <FieldRow label="Status" value={view.committee.status} />
        </dl>
      </SectionCard>
      <ListBlock
        title="Supporting rationale"
        items={view.committee.supportingReasons}
      />
      <ListBlock
        title="Contradictory evidence"
        items={view.committee.opposingReasons}
      />
      <ListBlock title="Notes / minority opinions" items={view.minorityNotes} />
      <SectionCard title="Confidence summary">
        {Object.keys(view.confidenceSummary).length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <dl>
            {Object.entries(view.confidenceSummary).map(([key, value]) => (
              <FieldRow key={key} label={key} value={formatPct(value)} />
            ))}
          </dl>
        )}
      </SectionCard>
    </div>
  );
}
