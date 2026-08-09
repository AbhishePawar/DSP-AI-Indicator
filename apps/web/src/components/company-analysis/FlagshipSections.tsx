"use client";

/**
 * P9.4 / EPIC-005 — Dedicated flagship workspace modules.
 * RC3-001 — Display-only over ResearchView. No client scoring. No cross-stage aliases.
 */

import Link from "next/link";

import { Accordion, Button } from "@/components/ds";
import { ExplainableRatingItem } from "./ExplainableRatingItem";
import { formatPct } from "@/lib/intelligence/mapResponse";
import type { RiskCategoryPayload } from "@/lib/api/compositionTypes";
import type { ResearchView } from "@/lib/research/mapResearchView";
import {
  FieldRow,
  firstStageMetric,
  SectionCard,
  StageSectionCard,
  stageMetricValue,
  WorkspaceEmpty,
} from "./WorkspacePrimitives";

function ListBlock({
  title,
  items,
  description,
}: {
  title: string;
  items: string[];
  description?: string;
}) {
  return (
    <SectionCard title={title} description={description}>
      {items.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
      ) : (
        <ul className="list-disc space-y-1 pl-4 text-sm">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

export function ManagementSection({ view }: { view: ResearchView }) {
  const m = view.management;
  return (
    <div className="space-y-4">
      <SectionCard
        title="Management"
        description="REP-002 Book 05 — values from management_quality stage only. Missing metrics show Data unavailable. Never fall back to stage decision as a sub-dimension."
      >
        <dl>
          <FieldRow label="Management Quality" value={m.label} />
          <FieldRow
            label="Corporate Governance"
            value={firstStageMetric(m, [
              "Corporate Governance",
              "Governance",
            ])}
          />
          <FieldRow
            label="Integrity"
            value={stageMetricValue(m, "Integrity")}
          />
          <FieldRow
            label="Execution Capability"
            value={firstStageMetric(m, [
              "Execution Capability",
              "Execution",
            ])}
          />
          <FieldRow
            label="Shareholder Orientation"
            value={firstStageMetric(m, [
              "Shareholder Orientation",
              "Shareholder Alignment",
            ])}
          />
          <FieldRow
            label="Leadership Quality"
            value={firstStageMetric(m, [
              "Leadership Quality",
              "Leadership",
            ])}
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

export function MoatSection({ view }: { view: ResearchView }) {
  const moat = view.moat;
  return (
    <div className="space-y-4">
      <SectionCard
        title="Economic Moat"
        description="REP-002 Book 06 — values from economic_moat stage only. Synonym labels stay on the same stage; never substitute other engines."
      >
        <dl>
          <FieldRow label="Economic Moat" value={moat.label} />
          <FieldRow
            label="Brand Strength"
            value={firstStageMetric(moat, ["Brand Strength", "Brand"])}
          />
          <FieldRow
            label="Network Effects"
            value={firstStageMetric(moat, [
              "Network Effects",
              "Network Effect",
            ])}
          />
          <FieldRow
            label="Switching Costs"
            value={stageMetricValue(moat, "Switching Costs")}
          />
          <FieldRow
            label="Distribution Advantage"
            value={firstStageMetric(moat, [
              "Distribution Advantage",
              "Distribution",
            ])}
          />
          <FieldRow
            label="Cost-Based Moat"
            value={firstStageMetric(moat, [
              "Cost-Based Moat",
              "Cost Advantage",
            ])}
          />
          <FieldRow
            label="Moat Durability"
            value={firstStageMetric(moat, [
              "Moat Durability",
              "Durability",
            ])}
          />
          <FieldRow label="Score" value={moat.score} />
          <FieldRow label="Confidence" value={moat.confidence} />
        </dl>
      </SectionCard>
      <StageSectionCard title="Moat stage detail" section={moat} />
    </div>
  );
}

function riskLevelLabel(value: string | null | undefined): string {
  if (!value) return "Data unavailable.";
  return value
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function RiskCategoryRow({
  label,
  category,
}: {
  label: string;
  category: RiskCategoryPayload | undefined;
}) {
  if (!category || !category.available) {
    return (
      <FieldRow
        label={label}
        value={category?.message ?? "Data unavailable."}
      />
    );
  }
  const detail = category.source_stage
    ? `${riskLevelLabel(category.level)} (from ${category.source_stage})`
    : riskLevelLabel(category.level);
  return <FieldRow label={label} value={detail} />;
}

export function RiskSection({ view }: { view: ResearchView }) {
  const risk = view.risk;

  return (
    <div className="space-y-4">
      <SectionCard
        title="Risk"
        description="Composition Risk stage — structural aggregation of existing financial_strength / economic_moat ratings only. No new risk-scoring algorithm. Categories with no connected data source are honestly reported unavailable."
        action={
          risk ? (
            <span className="text-xs text-[var(--muted)]">
              {risk.categories_available}/{risk.categories_total} categories
              covered
            </span>
          ) : undefined
        }
      >
        <dl>
          <RiskCategoryRow label="Business Risk" category={risk?.business_risk} />
          <RiskCategoryRow label="Financial Risk" category={risk?.financial_risk} />
          <RiskCategoryRow label="Regulatory Risk" category={risk?.regulatory_risk} />
          <RiskCategoryRow label="Technology Risk" category={risk?.technology_risk} />
          <RiskCategoryRow label="Currency Risk" category={risk?.currency_risk} />
          <RiskCategoryRow
            label="Customer Concentration Risk"
            category={risk?.customer_concentration_risk}
          />
          <FieldRow
            label="Overall Risk Level"
            value={riskLevelLabel(risk?.overall_risk_level)}
          />
        </dl>
        {risk?.limitations?.length ? (
          <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-[var(--muted)]">
            {risk.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        ) : null}
      </SectionCard>
      <ListBlock
        title="Key risks"
        description="Pipeline warnings / mapped IntelligenceView.risks — narrative, not the typed Risk stage above"
        items={view.risks}
      />
      <ListBlock title="Weaknesses" items={view.weaknesses} />
      <StageSectionCard
        title="Financial strength stage (source for Financial Risk above)"
        section={view.financialStrength}
      />
    </div>
  );
}

export function FinancialSection({ view }: { view: ResearchView }) {
  const fin = view.financial;
  return (
    <div className="space-y-4">
      <SectionCard
        title="Financial Performance"
        description="Values from the financial stage only — line-item history requires filings APIs not wired here. No cross-stage substitutes."
      >
        <dl>
          <FieldRow
            label="Revenue"
            value={stageMetricValue(fin, "Revenue")}
          />
          <FieldRow label="Profit" value={stageMetricValue(fin, "Profit")} />
          <FieldRow
            label="Cash Flow"
            value={stageMetricValue(fin, "Cash Flow")}
          />
          <FieldRow
            label="Margins"
            value={stageMetricValue(fin, "Margins")}
          />
          <FieldRow label="Debt" value={stageMetricValue(fin, "Debt")} />
          <FieldRow label="ROE" value={stageMetricValue(fin, "ROE")} />
          <FieldRow label="ROCE" value={stageMetricValue(fin, "ROCE")} />
          <FieldRow label="Financial label" value={fin.label} />
          <FieldRow label="Financial score" value={fin.score} />
          <FieldRow label="Confidence" value={fin.confidence} />
        </dl>
      </SectionCard>
      <StageSectionCard title="Financial stage" section={fin} />
      <p className="text-xs text-[var(--muted)]">
        Growth and Earnings Quality are separate stages — not Financial
        Performance substitutes.
      </p>
      <SectionCard title="Historical trends">
        <WorkspaceEmpty description="Data unavailable. No multi-period financial series is exposed on AnalyseResponse for charting in this workspace." />
      </SectionCard>
    </div>
  );
}

export function ExplainabilitySection({ view }: { view: ResearchView }) {
  const modules = view.explainability.modules;
  const first = modules[0];
  const contradictory = [
    ...view.committee.opposingReasons,
    ...view.weaknesses,
    ...view.risks,
  ];
  return (
    <div className="space-y-4">
      <SectionCard
        title="Reasoning path"
        description={view.explainability.disclaimer}
      >
        <dl>
          <FieldRow label="Recommendation" value={view.recommendation} />
          <FieldRow
            label="Confidence"
            value={formatPct(view.recommendationConfidence)}
          />
          <FieldRow
            label="One-line summary"
            value={first?.oneLineSummary ?? "Data unavailable."}
          />
          <FieldRow
            label="Framework version"
            value={view.explainability.version}
          />
        </dl>
      </SectionCard>
      <SectionCard
        title="Evidence chain"
        description="Expandable module explainability — presentation map only"
      >
        {modules.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <Accordion type="multiple" className="space-y-2" defaultValue={[]}>
            {modules.map((item) => (
              <ExplainableRatingItem key={item.moduleId} item={item} />
            ))}
          </Accordion>
        )}
      </SectionCard>
      <SectionCard title="Confidence contributors">
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
      <ListBlock
        title="Supporting strengths"
        description="Stage strengths from analyse response — not filed citations. Document attachments remain Data unavailable."
        items={view.strengths}
      />
      <ListBlock
        title="Contradictory evidence"
        description="Opposing committee notes, weaknesses, and risks — never omitted when present"
        items={contradictory}
      />
    </div>
  );
}

export function EvidenceSection({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Research objects"
        description="Mapped analyse metadata — no fabricated filings or documents"
      >
        <dl>
          <FieldRow label="Analysis ID" value={view.analysisId} />
          <FieldRow label="Audit reference" value={view.auditReference} />
          <FieldRow label="Correlation ID" value={view.correlationId} />
          <FieldRow label="Pipeline version" value={view.pipelineVersion} />
          <FieldRow label="Platform version" value={view.platformVersion} />
          <FieldRow
            label="Recommendation stage"
            value={view.recommendationStage.status}
          />
        </dl>
      </SectionCard>
      <ListBlock
        title="Supporting strengths"
        description="Analyse strengths list — not a document catalogue"
        items={view.strengths}
      />
      <ListBlock title="Research object warnings" items={view.warnings} />
      <SectionCard title="Documents">
        <WorkspaceEmpty description="Data unavailable. Document attachments are not exposed on the frozen analyse contract." />
      </SectionCard>
      <SectionCard title="Datasets">
        <WorkspaceEmpty description="Data unavailable. Dataset catalogue is not wired in the thin client." />
      </SectionCard>
      <SectionCard title="Financial statements">
        <WorkspaceEmpty description="Data unavailable. Statement line items require filings endpoints not used here." />
      </SectionCard>
      <SectionCard
        title="Related research"
        action={
          <Link href="/research/institutional">
            <Button size="sm" variant="secondary">
              Institutional reports
            </Button>
          </Link>
        }
      >
        <p className="text-sm text-[var(--muted)]">
          Open Institutional Reports for the publishing trust ladder. This panel
          stays honest about missing document payloads.
        </p>
      </SectionCard>
    </div>
  );
}
