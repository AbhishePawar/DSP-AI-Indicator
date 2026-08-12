"use client";

/**
 * P9.6 / EPIC-007 — Report cover, summary, explainability, evidence, timeline, downloads, audit.
 */

import Link from "next/link";

import { Accordion, Badge, Button } from "@/components/ds";
import { ExplainableRatingItem } from "@/components/company-analysis/ExplainableRatingItem";
import { ReportInformationCard } from "@/components/company-analysis/ReportInformationCard";
import {
  downloadText,
  researchViewToCsv,
  researchViewToHtml,
  researchViewToJson,
} from "@/lib/company-analysis";
import { featureFlags } from "@/lib/featureFlags";
import { formatPct } from "@/lib/intelligence/mapResponse";
import { useInstitutionalReportsPrefsStore } from "@/lib/institutional-reports";
import { loadRecentAnalyses } from "@/lib/analysis/recentAnalyses";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { mapReportTransparency } from "@/lib/report-transparency";
import {
  FieldRow,
  ListBlock,
  SectionCard,
  WorkspaceEmpty,
} from "./Primitives";

export function CoverSection({
  view,
  preparedBy,
  marketStatus,
}: {
  view: ResearchView;
  preparedBy: string;
  marketStatus: string;
}) {
  const transparency = mapReportTransparency(view, { marketStatus });
  const coverage =
    view.ok && view.stages.length > 0
      ? `${view.stages.filter((s) => s.status === "succeeded").length}/${view.stages.length} stages succeeded`
      : view.ok
        ? "Analyse succeeded — stage detail Data unavailable."
        : "Incomplete / failed";

  return (
    <div className="space-y-4 report-module" data-report-module="cover">
      <SectionCard
        title="Institutional Research Report"
        description="Official publishing cover — mapped AnalyseResponse metadata only"
        action={
          <Badge variant={featureFlags.researchMode ? "accent" : "outline"}>
            Research Mode
          </Badge>
        }
      >
        <dl>
          <FieldRow label="Company" value={view.company} />
          <FieldRow label="Ticker" value={view.ticker} />
          <FieldRow label="Exchange" value={view.exchange} />
          <FieldRow label="Research Date" value={view.analysedAt} />
          <FieldRow label="Version" value={transparency.reportId} />
          <FieldRow label="Pipeline version" value={view.pipelineVersion} />
          <FieldRow label="Platform version" value={view.platformVersion} />
          <FieldRow label="Coverage" value={coverage} />
          <FieldRow
            label="Confidence"
            value={
              formatPct(view.recommendationConfidence) ||
              transparency.confidence
            }
          />
          <FieldRow label="Prepared By" value={preparedBy} />
          <FieldRow
            label="Status"
            value={view.ok ? "Published (analyse OK)" : "Incomplete"}
          />
          <FieldRow
            label="Recommendation state"
            value={view.recommendation}
          />
        </dl>
      </SectionCard>
      <ReportInformationCard transparency={transparency} />
    </div>
  );
}

export function ExecutiveSummarySection({
  view,
  marketStatus,
}: {
  view: ResearchView;
  marketStatus: string;
}) {
  return (
    <div className="space-y-4 report-module" data-report-module="summary">
      <SectionCard
        title="Executive Summary"
        description="Institutional summary from /api/v1/analyse — Research Mode · research before recommendation"
      >
        <dl>
          <FieldRow
            label="Conclusion"
            value={view.committeeDecision || view.recommendation}
          />
          <FieldRow
            label="Recommendation state"
            value={view.recommendation}
          />
          <FieldRow
            label="Confidence"
            value={formatPct(view.recommendationConfidence)}
          />
          <FieldRow
            label="Business quality"
            value={view.businessQualityLabel}
          />
          <FieldRow
            label="Margin of safety"
            value={formatPct(view.marginOfSafety)}
          />
          <FieldRow label="Research timestamp" value={view.analysedAt} />
          <FieldRow label="Market status" value={marketStatus} />
        </dl>
      </SectionCard>
      <TrustLadderCard view={view} />
      <ListBlock title="Key positives" items={view.strengths} />
      <ListBlock title="Key negatives" items={view.weaknesses} />
      <ListBlock title="Key risks" items={view.risks} />
    </div>
  );
}

function TrustLadderCard({ view }: { view: ResearchView }) {
  return (
    <SectionCard
      title="Trust Ladder"
      description="User Trust Standard — Observed Facts → Analysis → Inference → Recommendation"
    >
      <div
        className="mb-3 flex flex-wrap gap-2"
        aria-label="Epistemic categories"
      >
        <Badge variant="outline">Verified / Observed</Badge>
        <Badge variant="outline">Calculated</Badge>
        <Badge variant="outline">AI / Committee</Badge>
        <Badge variant="accent">Research Mode</Badge>
      </div>
      <ol className="space-y-3 text-sm">
        <li className="rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2 print:break-inside-avoid">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            1 · Facts · Verified / market signals
          </p>
          <p className="mt-1">
            Price {view.valuation.currentPrice} · Coverage{" "}
            {view.ok ? "analyse succeeded" : "incomplete / failed"} · Stages{" "}
            {view.stages.length || "Data unavailable."}
          </p>
        </li>
        <li className="rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2 print:break-inside-avoid">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            2 · Analysis · Calculated stage outputs
          </p>
          <p className="mt-1">
            Quality {view.businessQualityLabel} · Moat {view.moat.label} · MoS{" "}
            {view.valuation.marginOfSafety}
          </p>
        </li>
        <li className="rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2 print:break-inside-avoid">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            3 · Inference · AI Committee
          </p>
          <p className="mt-1">
            Committee {view.committeeDecision} · Confidence{" "}
            {formatPct(view.committeeConfidence)}
          </p>
        </li>
        <li className="rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2 print:break-inside-avoid">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            4 · Recommendation · Research Mode
          </p>
          <p className="mt-1">
            {view.recommendation} · Confidence{" "}
            {formatPct(view.recommendationConfidence)}
          </p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Educational investigation — not personalised investment advice.
            Confidence always shown; missing fields remain Data unavailable.
          </p>
        </li>
      </ol>
    </SectionCard>
  );
}

export function ExplainabilityModule({ view }: { view: ResearchView }) {
  const modules = view.explainability.modules;
  const first = modules[0];
  const contradictory = [
    ...view.committee.opposingReasons,
    ...view.weaknesses,
    ...view.risks,
  ];
  return (
    <div
      className="space-y-4 report-module"
      data-report-module="explainability"
    >
      <TrustLadderCard view={view} />
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
        title="Primary sources"
        description="Stage strengths used as citation proxies — never fabricated"
        items={view.strengths}
      />
      <ListBlock
        title="Contradictory evidence"
        description="Opposing committee notes, weaknesses, and risks"
        items={contradictory}
      />
    </div>
  );
}

export function EvidenceModule({ view }: { view: ResearchView }) {
  return (
    <div className="space-y-4 report-module" data-report-module="evidence">
      <SectionCard
        title="Research objects"
        description="Mapped analyse metadata — no fabricated filings or documents"
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
      <ListBlock title="Evidence cards" items={view.strengths} />
      <ListBlock title="Research object warnings" items={view.warnings} />
      <SectionCard title="Documents">
        <WorkspaceEmpty description="Data unavailable. Document attachments are not exposed on the frozen analyse contract." />
      </SectionCard>
      <SectionCard title="Statements">
        <WorkspaceEmpty description="Data unavailable. Statement line items require filings endpoints not used in this publishing layer." />
      </SectionCard>
      <SectionCard title="Datasets">
        <WorkspaceEmpty description="Data unavailable. Dataset catalogue is not wired in the thin client." />
      </SectionCard>
      <SectionCard
        title="Related surfaces"
        action={
          <Link href={`/analysis?symbol=${encodeURIComponent(view.ticker)}`}>
            <Button size="sm" variant="secondary">
              Company analysis
            </Button>
          </Link>
        }
      >
        <p className="text-sm text-[var(--muted)]">
          Open Company Analysis for the flagship investigation workspace. This
          report surface stays honest about missing document payloads.
        </p>
      </SectionCard>
    </div>
  );
}

export function TimelineModule({ view }: { view: ResearchView }) {
  const recent = loadRecentAnalyses().filter(
    (r) => r.ticker.toUpperCase() === view.ticker.toUpperCase(),
  );

  return (
    <div className="space-y-4 report-module" data-report-module="timeline">
      <SectionCard
        title="Pipeline timeline"
        description="Stage summaries from this AnalyseResponse"
      >
        {view.stages.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <ol className="space-y-2" aria-label="Stage timeline">
            {view.stages.map((stage, index) => (
              <li
                key={`${stage.stage}-${index}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2 text-sm print:break-inside-avoid"
              >
                <span>
                  <span className="font-medium">{stage.stage}</span>
                  {stage.label ? (
                    <span className="ml-2 text-[var(--muted)]">
                      {stage.label}
                    </span>
                  ) : null}
                </span>
                <Badge
                  variant={
                    stage.status === "succeeded" ? "accent" : "outline"
                  }
                >
                  {stage.status}
                </Badge>
              </li>
            ))}
          </ol>
        )}
      </SectionCard>
      <SectionCard title="Historical reports (local session)">
        {recent.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No prior local analyses for this ticker in the current session." />
        ) : (
          <ul className="space-y-2 text-sm">
            {recent.map((entry) => (
              <li
                key={`${entry.ticker}-${entry.analysedAt}`}
                className="rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2"
              >
                <p className="font-medium">{entry.analysedAt}</p>
                <p className="text-[var(--muted)]">
                  {entry.recommendation} · {entry.company}
                </p>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Previous recommendations">
        <dl>
          <FieldRow
            label="Current recommendation"
            value={view.recommendation}
          />
          <FieldRow
            label="Committee decision"
            value={view.committeeDecision}
          />
          <FieldRow label="Analysed at" value={view.analysedAt} />
        </dl>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Multi-run server history is Data unavailable. Local recent analyses
          appear above when present.
        </p>
      </SectionCard>
      <SectionCard title="Material events">
        <WorkspaceEmpty description="Data unavailable. No material-events feed on the frozen analyse contract." />
      </SectionCard>
      <SectionCard title="Audit timeline">
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

export function DownloadsModule({ view }: { view: ResearchView }) {
  const setReportMode = useInstitutionalReportsPrefsStore(
    (s) => s.setReportMode,
  );
  const base = `${view.ticker.toLowerCase()}-institutional-report`;
  const sharePath = `/research/institutional?symbol=${encodeURIComponent(view.ticker)}`;
  const shareUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}${sharePath}`
      : sharePath;

  return (
    <div className="space-y-4 report-module" data-report-module="export">
      <SectionCard
        title="Downloads"
        description="Print, PDF layout, share, and research export — mapped fields only · no recalculation"
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
          <Button
            variant="secondary"
            onClick={() => {
              setReportMode("print");
              window.setTimeout(() => window.print(), 50);
            }}
          >
            Print
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setReportMode("pdf");
              window.setTimeout(() => window.print(), 50);
            }}
          >
            PDF layout
          </Button>
        </div>
        <p className="mt-3 break-all font-mono text-xs text-[var(--muted)]">
          {shareUrl}
        </p>
      </SectionCard>
      <SectionCard
        title="Research export"
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
                `${base}.html`,
                researchViewToHtml(view),
                "text/html",
              );
            }}
          >
            Export HTML
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              downloadText(
                `${base}.html`,
                researchViewToHtml(view),
                "text/html",
              );
              setReportMode("pdf");
              window.setTimeout(() => window.print(), 50);
            }}
          >
            PDF (browser print)
          </Button>
        </div>
        <p className="mt-3 text-xs text-[var(--muted)]">
          PDF uses browser print CSS. Native XLSX/PDF engines are not shipped in
          this epic — no fabricated PDF service.
        </p>
      </SectionCard>
    </div>
  );
}

export function AuditModule({
  view,
  marketStatus,
}: {
  view: ResearchView;
  marketStatus: string;
}) {
  const transparency = mapReportTransparency(view, { marketStatus });
  return (
    <div className="space-y-4 report-module" data-report-module="audit">
      <SectionCard
        title="Audit Metadata"
        description="Report version, timestamps, engine versions, data freshness — presentation only"
      >
        <dl>
          <FieldRow label="Report version / ID" value={transparency.reportId} />
          <FieldRow label="Research timestamp" value={view.analysedAt} />
          <FieldRow
            label="Analysis date"
            value={transparency.analysisDate}
          />
          <FieldRow
            label="Frontend version"
            value={transparency.analysisVersions.frontend}
          />
          <FieldRow
            label="Backend / platform"
            value={transparency.analysisVersions.backend}
          />
          <FieldRow label="Pipeline version" value={view.pipelineVersion} />
          <FieldRow label="Platform version" value={view.platformVersion} />
          <FieldRow
            label="Buffett framework"
            value={transparency.analysisVersions.buffettFramework}
          />
          <FieldRow
            label="Institutional rating framework"
            value={
              transparency.analysisVersions.institutionalRatingFramework
            }
          />
          <FieldRow
            label="Explainability framework"
            value={view.explainability.version}
          />
          <FieldRow label="Correlation ID" value={view.correlationId} />
          <FieldRow
            label="Data freshness"
            value={transparency.dataInformation.dataFreshness}
          />
          <FieldRow
            label="Primary data source"
            value={transparency.dataInformation.primaryDataSource}
          />
          <FieldRow
            label="Financial period used"
            value={transparency.dataInformation.financialPeriodUsed}
          />
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
      <ListBlock title="Limitations" items={view.limitations} />
      <ListBlock title="Errors" items={view.errors} />
      <ListBlock title="Warnings" items={view.warnings} />
      <ReportInformationCard transparency={transparency} />
    </div>
  );
}
