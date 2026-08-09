"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { Badge, Button } from "@/components/ds";
import {
  downloadBase64,
  downloadText,
  researchViewToCsv,
  researchViewToHtml,
  researchViewToJson,
  useWorkspacePrefsStore,
} from "@/lib/company-analysis";
import { api } from "@/lib/api/client";
import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import { featureFlags } from "@/lib/featureFlags";
import { formatPct } from "@/lib/intelligence/mapResponse";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { mapReportTransparency } from "@/lib/report-transparency";
import type { CompanyEntry } from "@/lib/companies/catalogue";
import {
  FieldRow,
  firstStageMetric,
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
  marketQuote,
  financialStatements,
}: {
  view: ResearchView;
  catalogue: CompanyEntry | undefined;
  marketStatus: string;
  marketQuote?: import("@/lib/institutional-dashboard/mapInstitutionalDashboard").MarketQuotePayload | null;
  financialStatements?: import("@/lib/institutional-dashboard/mapInstitutionalDashboard").FinancialStatementsPayload | null;
}) {
  return (
    <div className="space-y-4">
      <CompanyHeaderBar
        view={view}
        catalogue={catalogue}
        marketStatus={marketStatus}
        lastUpdated={view.analysedAt}
        marketQuote={marketQuote}
        financialStatements={financialStatements}
      />
      <SectionCard
        title="Executive Summary"
        description="Institutional summary from /api/v1/analyse — Research Mode · research before recommendation"
      >
        <dl>
          <FieldRow
            label="Institutional summary"
            value={view.committeeDecision || view.recommendation}
          />
          <FieldRow label="Recommendation" value={view.recommendation} />
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
      <TrustLadderCard view={view} />
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

function TrustLadderCard({ view }: { view: ResearchView }) {
  return (
    <SectionCard
      title="Research ladder"
      description="DSP Trust Standard — Observed Facts → Analysis → Inference → Recommendation. Epistemic categories shown per layer."
    >
      <div className="mb-3 flex flex-wrap gap-2" aria-label="Epistemic categories">
        <Badge variant="outline">Verified / Observed</Badge>
        <Badge variant="outline">Calculated</Badge>
        <Badge variant="outline">AI / Committee</Badge>
        <Badge variant="accent">Research Mode</Badge>
      </div>
      <ol className="space-y-3 text-sm">
        <li className="rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            1 · Observed facts · Verified / market signals
          </p>
          <p className="mt-1">
            Price {view.valuation.currentPrice} · Coverage{" "}
            {view.ok ? "analyse succeeded" : "incomplete / failed"} · Stages{" "}
            {view.stages.length || "Data unavailable."}
          </p>
        </li>
        <li className="rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            2 · Analysis · Calculated stage outputs
          </p>
          <p className="mt-1">
            Quality {view.businessQualityLabel} · Moat {view.moat.label} · MoS{" "}
            {view.valuation.marginOfSafety}
          </p>
        </li>
        <li className="rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            3 · Inference · AI Committee
          </p>
          <p className="mt-1">
            Committee {view.committeeDecision} · Confidence{" "}
            {formatPct(view.committeeConfidence)}
          </p>
        </li>
        <li className="rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2">
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

function AnalystNotesCard({ symbol }: { symbol: string }) {
  const allNotes = useWorkspacePrefsStore((s) => s.notes);
  const addNote = useWorkspacePrefsStore((s) => s.addNote);
  const removeNote = useWorkspacePrefsStore((s) => s.removeNote);
  const [draft, setDraft] = useState("");
  const sym = symbol.toUpperCase();
  const notes = allNotes.filter((n) => n.symbol === sym);

  return (
    <SectionCard
      title="Research notes"
      description="Local workspace notes — User category · not sent to the analyse API"
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

function provenanceText(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Data unavailable.";
  }
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number" || typeof value === "string") return String(value);
  return "Data unavailable.";
}

export function ResearchSection({ view }: { view: ResearchView }) {
  const { session } = useAuth();
  const token = session?.accessToken ?? null;
  const analysisId = view.analysisId?.trim() || "";
  const provenanceQuery = useQuery({
    queryKey: ["analyse-provenance", analysisId, Boolean(token)],
    enabled: Boolean(analysisId && token),
    queryFn: async () => {
      const res = await api.analyseProvenance(analysisId, { token });
      if (!res.ok || !res.provenance) {
        throw new Error(res.message ?? res.error ?? "Data unavailable.");
      }
      return res.provenance;
    },
    retry: false,
  });
  const provenance = provenanceQuery.data;
  const sourceEvidence =
    provenance && typeof provenance.source_evidence === "object"
      ? (provenance.source_evidence as Record<string, unknown>)
      : null;
  const release =
    provenance && typeof provenance.release === "object"
      ? (provenance.release as Record<string, unknown>)
      : null;

  return (
    <div className="space-y-4">
      <SectionCard
        title="Research Object Viewer"
        description="Composition analyse payload metadata — display only"
      >
        <dl>
          <FieldRow label="OK" value={String(view.ok)} />
          <FieldRow label="Analysis ID" value={view.analysisId} />
          <FieldRow label="Audit reference" value={view.auditReference} />
          <FieldRow
            label="Provenance persisted"
            value={
              view.provenancePersisted === null
                ? "Data unavailable."
                : view.provenancePersisted
                  ? "Yes"
                  : "No"
            }
          />
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
      <SectionCard
        title="Investment Provenance"
        description="Server-owned lineage for the displayed analysis_id — read-only"
      >
        {!analysisId ? (
          <WorkspaceEmpty description="Data unavailable. Run an analysis to load provenance." />
        ) : !token ? (
          <WorkspaceEmpty description="Sign in to load server provenance for this analysis." />
        ) : provenanceQuery.isLoading ? (
          <p className="text-sm text-[var(--muted)]" role="status">
            Loading provenance…
          </p>
        ) : provenanceQuery.isError ? (
          <p className="text-sm text-[var(--danger-fg)]" role="alert">
            {provenanceQuery.error instanceof Error
              ? provenanceQuery.error.message
              : "Data unavailable."}
          </p>
        ) : provenance ? (
          <dl>
            <FieldRow
              label="Analysis ID"
              value={provenanceText(provenance.analysis_id)}
            />
            <FieldRow
              label="Source / provider"
              value={provenanceText(
                sourceEvidence?.statement_provider ??
                  sourceEvidence?.quote_provider ??
                  sourceEvidence?.status,
              )}
            />
            <FieldRow
              label="Evidence class"
              value={provenanceText(
                sourceEvidence?.statement_source_type ??
                  sourceEvidence?.quote_source_type ??
                  (sourceEvidence?.authenticated ? "authenticated" : "unavailable"),
              )}
            />
            <FieldRow
              label="Retrieval timestamp"
              value={provenanceText(
                sourceEvidence?.statement_retrieved_at ??
                  sourceEvidence?.quote_retrieved_at ??
                  provenance.calculated_at ??
                  provenance.created_at,
              )}
            />
            <FieldRow
              label="Statement basis"
              value={provenanceText(sourceEvidence?.statement_basis)}
            />
            <FieldRow
              label="Persistence state"
              value={
                view.provenancePersisted === true
                  ? "Persisted"
                  : view.provenancePersisted === false
                    ? "Not persisted"
                    : "Data unavailable."
              }
            />
            <FieldRow
              label="Release identity"
              value={provenanceText(release?.label ?? release?.product_version)}
            />
            <FieldRow
              label="Input fingerprint"
              value={provenanceText(provenance.input_fingerprint)}
            />
            <FieldRow
              label="Result fingerprint"
              value={provenanceText(provenance.result_fingerprint)}
            />
            <FieldRow
              label="Authority"
              value={provenanceText(provenance.authority ?? "server")}
            />
          </dl>
        ) : (
          <WorkspaceEmpty description="Data unavailable." />
        )}
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

function valuationMethodValue(
  methods: ResearchView["valuationTransparency"]["methods"],
  names: string[],
): string {
  for (const name of names) {
    const exact = methods.find(
      (m) => m.methodName.toLowerCase() === name.toLowerCase(),
    );
    if (exact) {
      if (
        exact.intrinsicValue &&
        exact.intrinsicValue !== "Unavailable" &&
        exact.intrinsicValue !== "—"
      ) {
        return exact.intrinsicValue;
      }
      return "Data unavailable.";
    }
  }
  for (const name of names) {
    const fuzzy = methods.find((m) =>
      m.methodName.toLowerCase().includes(name.toLowerCase()),
    );
    if (fuzzy) {
      if (
        fuzzy.intrinsicValue &&
        fuzzy.intrinsicValue !== "Unavailable" &&
        fuzzy.intrinsicValue !== "—"
      ) {
        return fuzzy.intrinsicValue;
      }
      return "Data unavailable.";
    }
  }
  return "Data unavailable.";
}

export function ValuationSection({ view }: { view: ResearchView }) {
  const valuationStage = view.stages.find((s) => s.stage === "valuation");
  const vt = view.valuationTransparency;
  const dcf = valuationMethodValue(vt.methods, ["DCF"]);
  const relative = valuationMethodValue(vt.methods, ["Relative Valuation", "Relative"]);
  const residual = valuationMethodValue(vt.methods, [
    "Residual Income",
    "Residual",
  ]);
  const epv = valuationMethodValue(vt.methods, ["EPV"]);
  return (
    <div className="space-y-4">
      <SectionCard
        title="Valuation"
        description="Mapped engine outputs only — no client recalculation. Missing methods show Data unavailable."
      >
        <dl>
          <FieldRow label="Intrinsic Value" value={view.valuation.intrinsicValue} />
          <FieldRow label="Current Price" value={view.valuation.currentPrice} />
          <FieldRow
            label="Margin of Safety"
            value={view.valuation.marginOfSafety}
          />
          <FieldRow label="DCF" value={dcf} />
          <FieldRow label="Relative Valuation" value={relative} />
          <FieldRow label="Residual Income" value={residual} />
          <FieldRow label="EPV" value={epv} />
          <FieldRow
            label="Overall Valuation"
            value={vt.executive.valuationVerdict}
          />
          <FieldRow
            label="Valuation method (stage)"
            value={view.valuation.method}
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
        description="REP-002 Book 04 — values from business_quality_aggregator only. Missing sub-dimensions show Data unavailable. Never alias Management, Growth, Moat, Risk, or Financial."
      >
        <dl>
          <FieldRow label="Overall score" value={bq.score} />
          <FieldRow label="Label" value={bq.label} />
          <FieldRow
            label="Capital Allocation Quality"
            value={firstStageMetric(bq, [
              "Capital Allocation Quality",
              "Capital Allocation",
            ])}
          />
          <FieldRow
            label="Industry Structure"
            value={firstStageMetric(bq, ["Industry Structure"])}
          />
          <FieldRow
            label="Operating Discipline"
            value={firstStageMetric(bq, ["Operating Discipline"])}
          />
          <FieldRow
            label="Franchise Durability"
            value={firstStageMetric(bq, ["Franchise Durability"])}
          />
          <FieldRow
            label="Reinvestment Opportunity"
            value={firstStageMetric(bq, ["Reinvestment Opportunity"])}
          />
          <FieldRow label="Confidence" value={bq.confidence} />
          <FieldRow label="Stage status" value={bq.status} />
        </dl>
      </SectionCard>
      <StageSectionCard title="Business Quality Aggregator" section={bq} />
      <p className="text-xs text-[var(--muted)]">
        Earnings Quality, Growth Quality, and Financial Strength are separate
        stages — open their dedicated sections. They are not Business Quality
        substitutes.
      </p>
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

function describeExportError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) {
      return "Permission denied — sign in required for institutional export.";
    }
    return error.message || `API error (${error.status})`;
  }
  if (error instanceof Error) return error.message;
  return "Data unavailable.";
}

export function ExportSection({
  view,
  analyseRequest,
  analyseResponse,
}: {
  view: ResearchView;
  analyseRequest?: AnalyseRequest | null;
  analyseResponse?: AnalyseResponse | null;
}) {
  const { session } = useAuth();
  const token = session?.accessToken ?? null;
  const base = `${view.ticker.toLowerCase()}-research`;
  const sharePath = `/analysis?symbol=${encodeURIComponent(view.ticker)}`;
  const shareUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}${sharePath}`
      : sharePath;

  const institutionalExportMutation = useMutation({
    mutationFn: async (format: "docx" | "pptx") => {
      if (!analyseResponse) {
        throw new Error(
          "Run an analysis first — institutional export uses the loaded research, it does not fetch its own data.",
        );
      }
      const analysisId =
        view.analysisId?.trim() ||
        (typeof analyseResponse.analysis_id === "string"
          ? analyseResponse.analysis_id.trim()
          : "") ||
        (typeof (analyseResponse.payload as { analysis_id?: unknown } | undefined)
          ?.analysis_id === "string"
          ? String(
              (analyseResponse.payload as { analysis_id?: string }).analysis_id,
            ).trim()
          : "");
      if (!analysisId) {
        throw new Error(
          "Server analysis_id is required for institutional export — run analysis again.",
        );
      }
      if (!token) {
        throw new Error(
          "Sign in required for institutional export — server ownership is enforced.",
        );
      }
      const objectRes = await api.researchObject(
        {
          symbol: view.ticker,
          company: view.company,
          exchange: view.exchange,
          analysis_id: analysisId,
          analysis_payload:
            (analyseResponse.payload as Record<string, unknown> | undefined) ??
            null,
          fetch_data_bundle: false,
        },
        { token },
      );
      if (!objectRes.ok || !objectRes.research_object) {
        throw new Error(objectRes.message ?? objectRes.error ?? "Data unavailable.");
      }
      if (
        objectRes.analysis_id &&
        String(objectRes.analysis_id).trim() !== analysisId
      ) {
        throw new Error("Export analysis_id mismatch — refusing stale client state.");
      }
      const reportRes = await api.researchReport(
        {
          research_object: objectRes.research_object,
          analysis_id: analysisId,
        },
        { token },
      );
      if (!reportRes.ok || !reportRes.report) {
        throw new Error(reportRes.message ?? reportRes.error ?? "Data unavailable.");
      }
      const exportRes = await api.researchExport(
        {
          report: reportRes.report,
          analysis_id: analysisId,
          format,
        },
        { token },
      );
      if (!exportRes.ok || !exportRes.export) {
        throw new Error(exportRes.message ?? exportRes.error ?? "Data unavailable.");
      }
      downloadBase64(
        exportRes.export.metadata.filename,
        exportRes.export.content_base64,
        exportRes.export.metadata.content_type,
      );
      return format;
    },
  });

  return (
    <div className="space-y-4">
      <SectionCard
        title="Downloads"
        description="PDF, research report, share link, and print — mapped fields only · no recalculation"
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
      <SectionCard
        title="Institutional Report Export"
        description="Word and PowerPoint generated server-side from dsp_platform.institutional_export — same frozen report as PDF/CSV/XLSX, no recalculation."
      >
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            disabled={institutionalExportMutation.isPending || !analyseResponse}
            onClick={() => institutionalExportMutation.mutate("docx")}
          >
            {institutionalExportMutation.isPending &&
            institutionalExportMutation.variables === "docx"
              ? "Exporting…"
              : "Export Word (.docx)"}
          </Button>
          <Button
            variant="secondary"
            disabled={institutionalExportMutation.isPending || !analyseResponse}
            onClick={() => institutionalExportMutation.mutate("pptx")}
          >
            {institutionalExportMutation.isPending &&
            institutionalExportMutation.variables === "pptx"
              ? "Exporting…"
              : "Export PowerPoint (.pptx)"}
          </Button>
        </div>
        {!analyseResponse ? (
          <p className="mt-3 text-xs text-[var(--muted)]">
            Run an analysis first to enable Word/PowerPoint export.
          </p>
        ) : null}
        {institutionalExportMutation.isError ? (
          <p className="mt-3 text-sm text-[var(--danger-fg)]" role="alert">
            {describeExportError(institutionalExportMutation.error)}
          </p>
        ) : null}
        {institutionalExportMutation.isSuccess ? (
          <p className="mt-3 text-sm text-[var(--muted)]" role="status">
            {institutionalExportMutation.data === "docx" ? "Word" : "PowerPoint"}{" "}
            export downloaded.
          </p>
        ) : null}
      </SectionCard>
    </div>
  );
}
