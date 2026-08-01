"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, Button } from "@/components/ds";
import {
  downloadText,
  researchViewToCsv,
  researchViewToHtml,
  researchViewToJson,
  useWorkspacePrefsStore,
} from "@/lib/company-analysis";
import { featureFlags } from "@/lib/featureFlags";
import { formatPct } from "@/lib/intelligence/mapResponse";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { mapReportTransparency } from "@/lib/report-transparency";
import type { CompanyEntry } from "@/lib/companies/catalogue";
import {
  FieldRow,
  SectionCard,
  StageSectionCard,
  WorkspaceEmpty,
} from "./WorkspacePrimitives";
import { CompanyHeaderBar } from "./WorkspaceChrome";
import { ReportInformationCard } from "./ReportInformationCard";

function ListBlock({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  return (
    <SectionCard title={title}>
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

export function SummarySection({
  view,
  catalogue,
  marketStatus,
}: {
  view: ResearchView;
  catalogue: CompanyEntry | undefined;
  marketStatus: string;
}) {
  return (
    <div className="space-y-4">
      <CompanyHeaderBar
        view={view}
        catalogue={catalogue}
        marketStatus={marketStatus}
        lastUpdated={view.analysedAt}
      />
      <SectionCard
        title="Executive Summary"
        description="Institutional summary from /api/v1/analyse — Research Mode display"
      >
        <dl>
          <FieldRow
            label="Overall conclusion"
            value={view.committeeDecision || view.recommendation}
          />
          <FieldRow label="Recommendation state" value={view.recommendation} />
          <FieldRow
            label="Confidence"
            value={formatPct(view.recommendationConfidence)}
          />
          <FieldRow label="Research timestamp" value={view.analysedAt} />
          <FieldRow
            label="Business quality"
            value={view.businessQualityLabel}
          />
          <FieldRow
            label="Margin of safety"
            value={formatPct(view.marginOfSafety)}
          />
        </dl>
      </SectionCard>
      <ListBlock title="Key positives" items={view.strengths} />
      <ListBlock title="Key risks" items={view.risks} />
      <AnalystNotesCard symbol={view.ticker} />
      <ReportInformationCard
        transparency={mapReportTransparency(view, { marketStatus })}
      />
      <SectionCard title="Market Information">
        <dl>
          <FieldRow label="Market status" value={marketStatus} />
          <FieldRow
            label="Current price (request/signals)"
            value={view.valuation.currentPrice}
          />
          <FieldRow label="Platform" value={view.platformVersion} />
          <FieldRow label="Pipeline" value={view.pipelineVersion} />
        </dl>
      </SectionCard>
    </div>
  );
}

function AnalystNotesCard({ symbol }: { symbol: string }) {
  const allNotes = useWorkspacePrefsStore((s) => s.notes);
  const addNote = useWorkspacePrefsStore((s) => s.addNote);
  const removeNote = useWorkspacePrefsStore((s) => s.removeNote);
  const [draft, setDraft] = useState("");
  const sym = symbol.toUpperCase();
  const notes = allNotes.filter((n) => n.symbol === sym);

  return (
    <SectionCard
      title="Analyst notes"
      description="Local workspace notes — not sent to the analyse API"
    >
      <form
        className="flex flex-col gap-2 sm:flex-row"
        onSubmit={(e) => {
          e.preventDefault();
          addNote(symbol, draft);
          setDraft("");
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="min-w-0 flex-1 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm"
          placeholder="Add a note for this symbol"
          aria-label="Analyst note"
        />
        <Button type="submit" size="sm" variant="secondary">
          Add note
        </Button>
      </form>
      {notes.length === 0 ? (
        <p className="mt-3 text-sm text-[var(--muted)]">No notes yet.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className="flex items-start justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2 text-sm"
            >
              <div>
                <p>{note.text}</p>
                <p className="text-xs text-[var(--muted)]">{note.at}</p>
              </div>
              <Button
                size="sm"
                variant="ghost"
                aria-label="Remove note"
                onClick={() => removeNote(note.id)}
              >
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

export function ResearchSection({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Research Object Viewer"
        description="Composition analyse payload metadata — display only"
      >
        <dl>
          <FieldRow label="OK" value={String(view.ok)} />
          <FieldRow label="Correlation ID" value={view.correlationId} />
          <FieldRow label="Pipeline version" value={view.pipelineVersion} />
          <FieldRow label="Platform version" value={view.platformVersion} />
          <FieldRow label="Failed stage" value={view.failedStage} />
          <FieldRow
            label="Elapsed ms"
            value={
              view.totalElapsedMs === null
                ? "Data unavailable."
                : String(view.totalElapsedMs)
            }
          />
        </dl>
      </SectionCard>
      <SectionCard title="Institutional Report Viewer">
        <p className="text-sm text-[var(--muted)]">
          Open the institutional research dashboard for RS-001…RS-010 layout.
        </p>
        <Link href="/research/institutional" className="mt-3 inline-block">
          <Button size="sm" variant="secondary">
            Open institutional dashboard
          </Button>
        </Link>
      </SectionCard>
      <SectionCard title="Report Metadata">
        <dl>
          <FieldRow label="Ticker" value={view.ticker} />
          <FieldRow label="Analysed at" value={view.analysedAt} />
          <FieldRow label="Recommendation stage" value={view.recommendationStage.status} />
        </dl>
      </SectionCard>
      <SectionCard title="Archive Status">
        <WorkspaceEmpty description="Data unavailable. No archive status endpoint is wired in the frozen client." />
      </SectionCard>
      <SectionCard title="Research History">
        <p className="text-sm text-[var(--muted)]">
          Local recent analyses appear in the left panel. Server-side history is
          Data unavailable.
        </p>
      </SectionCard>
      <SectionCard title="Research Diff Viewer">
        <WorkspaceEmpty description="Data unavailable. No research-diff API in the thin client." />
      </SectionCard>
    </div>
  );
}

export function ValuationSection({ view }: { view: ResearchView }) {
  const valuationStage = view.stages.find((s) => s.stage === "valuation");
  const vt = view.valuationTransparency;
  const dcf = vt.methods.find((m) =>
    m.methodName.toLowerCase().includes("dcf"),
  );
  const relative = vt.methods.find((m) =>
    m.methodName.toLowerCase().includes("relative"),
  );
  return (
    <div className="space-y-4">
      <SectionCard
        title="Valuation"
        description="Values from analyse signals and valuation transparency — no client math"
      >
        <dl>
          <FieldRow label="Intrinsic Value" value={view.valuation.intrinsicValue} />
          <FieldRow label="Current Price" value={view.valuation.currentPrice} />
          <FieldRow
            label="Margin of Safety"
            value={view.valuation.marginOfSafety}
          />
          <FieldRow
            label="DCF"
            value={dcf?.intrinsicValue ?? dcf?.status ?? "Unavailable"}
          />
          <FieldRow
            label="Relative Valuation"
            value={
              relative?.intrinsicValue ?? relative?.status ?? "Unavailable"
            }
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
      <SectionCard title="Individual Model Results">
        {valuationStage ? (
          <dl>
            <FieldRow label="Stage status" value={valuationStage.status} />
            <FieldRow label="Label" value={valuationStage.label} />
            <FieldRow label="Decision" value={valuationStage.decision} />
            <FieldRow
              label="Score"
              value={
                valuationStage.score === null || valuationStage.score === undefined
                  ? "Data unavailable."
                  : String(valuationStage.score)
              }
            />
            <FieldRow
              label="Confidence"
              value={formatPct(valuationStage.confidence ?? null)}
            />
          </dl>
        ) : (
          <WorkspaceEmpty description="Data unavailable. Valuation stage summary not present in response." />
        )}
      </SectionCard>
      <SectionCard title="Consensus Result">
        <dl>
          <FieldRow label="Recommendation" value={view.recommendation} />
          <FieldRow
            label="Committee consensus"
            value={view.committeeConsensus}
          />
          <FieldRow
            label="Transparency consensus"
            value={vt.consensus.consensusValue}
          />
        </dl>
      </SectionCard>
    </div>
  );
}

export function QualitySection({ view }: { view: ResearchView }) {
  const bq = view.businessQuality;
  return (
    <div className="space-y-4">
      <SectionCard
        title="Business Quality"
        description="Aggregator and related stage outputs — dedicated Moat/Management/Risk sections for detail"
      >
        <dl>
          <FieldRow label="Business Quality score" value={bq.score} />
          <FieldRow label="Label" value={bq.label} />
          <FieldRow
            label="Capital allocation"
            value={view.management.label}
          />
          <FieldRow
            label="Reinvestment"
            value={
              view.growth.label !== "Unavailable"
                ? view.growth.label
                : view.growth.decision
            }
          />
          <FieldRow
            label="Operating discipline"
            value={view.earnings.label}
          />
          <FieldRow
            label="Industry structure"
            value={view.moat.decision}
          />
          <FieldRow label="Franchise durability" value={view.moat.label} />
          <FieldRow label="Confidence" value={bq.confidence} />
        </dl>
      </SectionCard>
      <div className="grid gap-4 lg:grid-cols-2">
        <StageSectionCard
          title="Business Quality Aggregator"
          section={bq}
        />
        <StageSectionCard title="Earnings Quality" section={view.earnings} />
        <StageSectionCard title="Growth Quality" section={view.growth} />
        <StageSectionCard
          title="Financial Strength"
          section={view.financialStrength}
        />
      </div>
    </div>
  );
}

export function AiSection({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="AI Committee"
        description="Committee decision from investment_committee stage — no local AI inference"
      >
        <dl>
          <FieldRow label="Committee decision" value={view.committeeDecision} />
          <FieldRow
            label="Supporting rationale"
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
        title="Supporting rationale detail"
        items={view.committee.supportingReasons}
      />
      <ListBlock
        title="Contradictory evidence"
        items={view.committee.opposingReasons}
      />
      <ListBlock title="Minority opinions" items={view.minorityNotes} />
      <SectionCard title="Review history">
        {view.executionOrder.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No separate committee review history field on AnalyseResponse." />
        ) : (
          <ol className="list-decimal space-y-1 pl-5 text-sm">
            {view.executionOrder.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        )}
      </SectionCard>
      <SectionCard
        title="Copilot"
        description="Full Copilot chat lives on /copilot"
        action={
          <Link href="/copilot">
            <Button size="sm" variant="secondary">
              Open Copilot
            </Button>
          </Link>
        }
      >
        <p className="text-sm text-[var(--muted)]">
          Use Copilot with mapped company context. This workspace does not run
          local AI inference.
        </p>
      </SectionCard>
      <SectionCard title="Confidence Summary">
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

export function ComplianceSection({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Policy Summary"
        description="Feature-flag presentation only — enforcement remains on the backend"
      >
        <ul className="space-y-2 text-sm">
          <li className="flex justify-between gap-2">
            <span className="text-[var(--muted)]">Research Mode</span>
            <Badge variant={featureFlags.researchMode ? "accent" : "outline"}>
              {featureFlags.researchMode ? "On" : "Off"}
            </Badge>
          </li>
          <li className="flex justify-between gap-2">
            <span className="text-[var(--muted)]">Recommendation Mode</span>
            <Badge variant="outline">
              {featureFlags.recommendationMode ? "On" : "Off"}
            </Badge>
          </li>
          <li className="flex justify-between gap-2">
            <span className="text-[var(--muted)]">SEBI Mode</span>
            <Badge variant="outline">
              {featureFlags.sebiMode ? "On" : "Off"}
            </Badge>
          </li>
        </ul>
      </SectionCard>
      <SectionCard title="Compliance Status">
        <FieldRow
          label="Analyse OK"
          value={view.ok ? "Succeeded" : "Failed / incomplete"}
        />
        <FieldRow label="Platform version" value={view.platformVersion} />
      </SectionCard>
      <ListBlock title="Violations / Errors" items={view.errors} />
      <ListBlock title="Warnings" items={view.warnings} />
      <ListBlock title="Limitations" items={view.limitations} />
      <SectionCard title="Workflow Status">
        <WorkspaceEmpty description="Data unavailable. No workflow status field on AnalyseResponse." />
      </SectionCard>
    </div>
  );
}

export function TimelineSection({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Research Timeline"
        description="Historical analyses from this response’s pipeline stage_summaries"
      >
        {view.stages.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <ol className="space-y-2">
            {view.stages.map((stage, index) => (
              <li
                key={`${stage.stage}-${index}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2 text-sm"
              >
                <span>
                  <span className="font-medium">{stage.stage}</span>
                  {stage.label ? (
                    <span className="ml-2 text-[var(--muted)]">{stage.label}</span>
                  ) : null}
                </span>
                <Badge
                  variant={stage.status === "succeeded" ? "accent" : "outline"}
                >
                  {stage.status}
                </Badge>
              </li>
            ))}
          </ol>
        )}
      </SectionCard>
      <SectionCard title="Recommendation history">
        <dl>
          <FieldRow label="Current recommendation" value={view.recommendation} />
          <FieldRow label="Committee decision" value={view.committeeDecision} />
          <FieldRow label="Analysed at" value={view.analysedAt} />
        </dl>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Multi-run server history is Data unavailable. Local recent analyses
          appear in the left navigation.
        </p>
      </SectionCard>
      <SectionCard title="Material events">
        <WorkspaceEmpty description="Data unavailable. No material-events feed on the frozen analyse contract." />
      </SectionCard>
      <SectionCard title="Audit Timeline">
        {view.executionOrder.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <ol className="list-decimal space-y-1 pl-5 text-sm">
            {view.executionOrder.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        )}
      </SectionCard>
    </div>
  );
}

export function ExportSection({ view }: { view: ResearchView }) {
  const base = `${view.ticker.toLowerCase()}-research`;
  const sharePath = `/analysis?symbol=${encodeURIComponent(view.ticker)}`;
  const shareUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}${sharePath}`
      : sharePath;

  return (
    <div className="space-y-4">
      <SectionCard
        title="Downloads"
        description="PDF, research report, share link, and print — mapped fields only"
      >
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(shareUrl);
              } catch {
                /* ignore clipboard denial */
              }
            }}
          >
            Share link
          </Button>
          <Button variant="secondary" onClick={() => window.print()}>
            Print
          </Button>
          <Link href="/research/institutional">
            <Button variant="ghost">Research report</Button>
          </Link>
        </div>
        <p className="mt-3 break-all font-mono text-xs text-[var(--muted)]">
          {shareUrl}
        </p>
      </SectionCard>
      <SectionCard
        title="Export files"
        description="Exports mapped display fields only — no recalculation"
      >
        <div className="grid gap-2 sm:grid-cols-2">
          <Button
            variant="secondary"
            onClick={() => {
              downloadText(
                `${base}.json`,
                researchViewToJson(view),
                "application/json",
              );
            }}
          >
            Export JSON
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              downloadText(`${base}.csv`, researchViewToCsv(view), "text/csv");
            }}
          >
            Export CSV
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              downloadText(
                `${base}-excel.csv`,
                researchViewToCsv(view),
                "text/csv",
              );
            }}
          >
            Export Excel (CSV)
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              const html = researchViewToHtml(view);
              downloadText(`${base}.html`, html, "text/html");
              window.print();
            }}
          >
            PDF (print)
          </Button>
        </div>
        <p className="mt-3 text-xs text-[var(--muted)]">
          PDF uses browser print. Excel downloads CSV that Excel can open. Native
          XLSX/PDF engines are not shipped in this epic.
        </p>
      </SectionCard>
    </div>
  );
}
