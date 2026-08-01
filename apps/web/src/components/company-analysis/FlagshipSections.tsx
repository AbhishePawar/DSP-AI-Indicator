"use client";

/**
 * P9.4 / EPIC-005 — Dedicated flagship workspace modules.
 * Display-only over ResearchView / explainability maps. No client scoring.
 */

import Link from "next/link";

import { Accordion, Button } from "@/components/ds";
import { ExplainableRatingItem } from "./ExplainableRatingItem";
import { formatPct } from "@/lib/intelligence/mapResponse";
import type { ResearchView } from "@/lib/research/mapResearchView";
import {
  FieldRow,
  SectionCard,
  StageSectionCard,
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

function metricValue(
  section: ResearchView["moat"],
  label: string,
): string {
  const hit = section.metrics.find(
    (m) => m.label.toLowerCase() === label.toLowerCase(),
  );
  return hit?.value ?? "Unavailable";
}

export function ManagementSection({ view }: { view: ResearchView }) {
  const m = view.management;
  return (
    <div className="space-y-4">
      <SectionCard
        title="Management"
        description="Mapped from management_quality stage — no client scoring"
      >
        <dl>
          <FieldRow label="Management quality" value={m.label} />
          <FieldRow label="Governance" value={m.decision} />
          <FieldRow label="Integrity" value={metricValue(m, "Integrity")} />
          <FieldRow
            label="Capital allocation discipline"
            value={metricValue(m, "Capital Allocation") || m.score}
          />
          <FieldRow
            label="Shareholder orientation"
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

export function MoatSection({ view }: { view: ResearchView }) {
  const moat = view.moat;
  return (
    <div className="space-y-4">
      <SectionCard
        title="Economic Moat"
        description="Mapped from economic_moat stage outputs"
      >
        <dl>
          <FieldRow label="Moat label" value={moat.label} />
          <FieldRow label="Brand" value={metricValue(moat, "Brand")} />
          <FieldRow
            label="Switching Costs"
            value={metricValue(moat, "Switching Costs")}
          />
          <FieldRow
            label="Network Effects"
            value={metricValue(moat, "Network Effects")}
          />
          <FieldRow
            label="Distribution"
            value={metricValue(moat, "Distribution")}
          />
          <FieldRow
            label="Cost Advantage"
            value={metricValue(moat, "Cost Advantage")}
          />
          <FieldRow
            label="Moat durability"
            value={moat.decision || metricValue(moat, "Durability")}
          />
          <FieldRow label="Score" value={moat.score} />
          <FieldRow label="Confidence" value={moat.confidence} />
        </dl>
      </SectionCard>
      <StageSectionCard title="Moat stage detail" section={moat} />
    </div>
  );
}

export function RiskSection({ view }: { view: ResearchView }) {
  const fs = view.financialStrength;
  return (
    <div className="space-y-4">
      <SectionCard
        title="Risk"
        description="Risk notes and financial_strength stage — honest empty when fields absent"
      >
        <dl>
          <FieldRow label="Business Risk" value={fs.label} />
          <FieldRow label="Financial Risk" value={fs.decision} />
          <FieldRow
            label="Operational Risk"
            value={metricValue(fs, "Operational Risk")}
          />
          <FieldRow
            label="Regulatory Risk"
            value={metricValue(fs, "Regulatory Risk")}
          />
          <FieldRow
            label="Permanent Capital Loss"
            value={metricValue(fs, "Permanent Capital Loss")}
          />
          <FieldRow
            label="Margin of Safety"
            value={view.valuation.marginOfSafety}
          />
          <FieldRow label="Strength score" value={fs.score} />
          <FieldRow label="Confidence" value={fs.confidence} />
        </dl>
      </SectionCard>
      <ListBlock
        title="Key risks"
        description="From pipeline stage warnings / mapped IntelligenceView.risks"
        items={view.risks}
      />
      <ListBlock title="Weaknesses" items={view.weaknesses} />
      <StageSectionCard title="Financial strength stage" section={fs} />
    </div>
  );
}

export function FinancialSection({ view }: { view: ResearchView }) {
  const fin = view.financial;
  const growth = view.growth;
  const earnings = view.earnings;
  return (
    <div className="space-y-4">
      <SectionCard
        title="Financial Performance"
        description="Stage summaries only — line-item history requires filings APIs not wired here"
      >
        <dl>
          <FieldRow label="Revenue" value={metricValue(fin, "Revenue")} />
          <FieldRow label="Profit" value={metricValue(fin, "Profit")} />
          <FieldRow label="Cash Flow" value={metricValue(fin, "Cash Flow")} />
          <FieldRow label="ROE" value={metricValue(fin, "ROE")} />
          <FieldRow label="ROCE" value={metricValue(fin, "ROCE")} />
          <FieldRow label="Debt" value={metricValue(fin, "Debt")} />
          <FieldRow label="Margins" value={metricValue(fin, "Margins")} />
          <FieldRow label="Financial label" value={fin.label} />
          <FieldRow label="Financial score" value={fin.score} />
          <FieldRow label="Confidence" value={fin.confidence} />
        </dl>
      </SectionCard>
      <div className="grid gap-4 lg:grid-cols-2">
        <StageSectionCard title="Financial stage" section={fin} />
        <StageSectionCard title="Growth stage" section={growth} />
        <StageSectionCard title="Earnings quality" section={earnings} />
      </div>
      <SectionCard title="Historical trends">
        <WorkspaceEmpty description="Data unavailable. No multi-period financial series is exposed on AnalyseResponse for charting in this workspace." />
      </SectionCard>
    </div>
  );
}

export function ExplainabilitySection({ view }: { view: ResearchView }) {
  const modules = view.explainability.modules;
  const first = modules[0];
  return (
    <div className="space-y-4">
      <SectionCard
        title="Why recommendation?"
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
        title="Evidence chain & reasoning path"
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
        title="Sources"
        description="Stage strengths used as citation proxies"
        items={view.strengths}
      />
    </div>
  );
}

export function EvidenceSection({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Supporting Evidence"
        description="Evidence cards from mapped analyse outputs — no fabricated filings"
      >
        <dl>
          <FieldRow label="Correlation ID" value={view.correlationId} />
          <FieldRow label="Pipeline version" value={view.pipelineVersion} />
          <FieldRow label="Platform version" value={view.platformVersion} />
          <FieldRow
            label="Recommendation stage"
            value={view.recommendationStage.status}
          />
        </dl>
      </SectionCard>
      <ListBlock title="Evidence cards (stage strengths)" items={view.strengths} />
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
              Institutional dashboard
            </Button>
          </Link>
        }
      >
        <p className="text-sm text-[var(--muted)]">
          Open the institutional research surface for RS layout. This panel stays
          honest about missing document payloads.
        </p>
      </SectionCard>
    </div>
  );
}
