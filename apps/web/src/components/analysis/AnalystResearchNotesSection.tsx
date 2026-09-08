"use client";

/**
 * AnalystResearchNotesSection — compact research-terminal Analyst/Research Notes block.
 *
 * Presents only analyst/research observations already available in the existing analysis view.
 * Uses ONLY existing real data — never invents, mocks, synthesises, or paraphrases unsupported data.
 *
 * Data sources (all existing, no new endpoints):
 *   • view.conclusion  — conclusion, primaryOpportunity, primaryRisk, researchConfidence,
 *                        evidence.limitations, evidence.supportingEvidence, evidence.primaryEvidence
 *   • view.dashboard   — researchConclusion, topOpportunity, biggestRisk, researchConfidence
 *   • view.thesis      — longTermThesis, keyStrengths, keyConcerns
 *   • view.risks[]     — first HIGH-severity risk as risk signal
 *   • view.freshness   — researchDate, analysisVersion, researchMode (provenance)
 *   • view.reportId    — report provenance ID
 *
 * Rules:
 *   - Every unavailable/null field displays "—" or "Unavailable".
 *   - Does NOT duplicate AI Research, Risks & Opportunities, or Data Freshness sections.
 *   - No new backend endpoints, no auth or routing changes.
 */

import type {
  AnalysisWorkspaceView,
  DisplayField,
  RiskInsightView,
} from "@/lib/analysis/types";

/* ─── Helpers ────────────────────────────────────────────────────── */

function fv(field: DisplayField<string | number> | undefined): string {
  if (!field || field.presence !== "available" || field.value == null) return "—";
  return String(field.value);
}

function arrVal(field: DisplayField<string[]> | undefined): string[] {
  if (!field || field.presence !== "available" || !Array.isArray(field.value)) return [];
  return field.value;
}

function str(v: string | null | undefined): string {
  if (!v || String(v).trim() === "") return "—";
  return String(v);
}

/* ─── Confidence pill ────────────────────────────────────────────── */

const CONFIDENCE_STYLE: Record<string, string> = {
  HIGH: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  MEDIUM: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  LOW: "bg-red-500/15 text-red-400 border-red-500/30",
};

function ConfidencePill({ level }: { level: string }) {
  if (!level || level === "—") {
    return (
      <span className="rounded border border-dashed border-[var(--border)] px-2 py-0.5 text-[10px] font-mono italic text-[var(--muted)]">
        Unavailable
      </span>
    );
  }
  const key = level.toUpperCase();
  const style =
    CONFIDENCE_STYLE[key] ??
    "bg-[var(--surface-2)] text-[var(--fg)] border-[var(--border)]";
  return (
    <span
      className={`rounded border px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider ${style}`}
    >
      {level}
    </span>
  );
}

/* ─── Signal pill ────────────────────────────────────────────────── */

function SignalPill({
  type,
}: {
  type: "opportunity" | "risk";
}) {
  return type === "opportunity" ? (
    <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-mono font-bold uppercase text-emerald-400">
      OPP
    </span>
  ) : (
    <span className="rounded border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[10px] font-mono font-bold uppercase text-red-400">
      RISK
    </span>
  );
}

/* ─── Block header ───────────────────────────────────────────────── */

function BlockHeader({ title }: { title: string }) {
  return (
    <div className="mb-2 flex items-center gap-2">
      <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--accent)]">
        {title}
      </span>
      <div className="h-px flex-1 bg-[var(--border)]" />
    </div>
  );
}

/* ─── Terminal row ───────────────────────────────────────────────── */

function TermRow({
  label,
  value,
  mono = false,
  valueClass,
}: {
  label: string;
  value: string;
  mono?: boolean;
  valueClass?: string;
}) {
  const isUnavail = value === "—" || value === "Unavailable";
  return (
    <div className="grid grid-cols-[auto_1fr] items-start gap-x-4 border-b border-[var(--border)] py-2 last:border-0">
      <span className="whitespace-nowrap text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">
        {label}
      </span>
      <span
        className={[
          "text-right text-xs leading-snug",
          mono ? "font-mono" : "font-normal",
          isUnavail
            ? "italic text-[var(--muted)]"
            : (valueClass ?? "text-[var(--fg)]"),
        ].join(" ")}
      >
        {value}
      </span>
    </div>
  );
}

/* ─── Evidence bullet list ───────────────────────────────────────── */

function EvidenceList({
  items,
  emptyLabel = "No evidence available",
}: {
  items: string[];
  emptyLabel?: string;
}) {
  if (items.length === 0) {
    return (
      <p className="text-xs italic text-[var(--muted)]">{emptyLabel}</p>
    );
  }
  return (
    <ul className="space-y-1">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-xs text-[var(--fg)]">
          <span className="mt-0.5 shrink-0 text-[var(--accent)]">›</span>
          <span className="leading-snug">{item}</span>
        </li>
      ))}
    </ul>
  );
}

/* ─── Risk signal row ────────────────────────────────────────────── */

const SEVERITY_COLOURS: Record<string, string> = {
  HIGH: "text-red-400 border-red-500/40 bg-red-500/10",
  MEDIUM: "text-amber-400 border-amber-500/40 bg-amber-500/10",
  LOW: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
};

function RiskSignalRow({ risk }: { risk: RiskInsightView }) {
  const cls =
    SEVERITY_COLOURS[risk.severity?.toUpperCase()] ??
    "text-[var(--muted)] border-[var(--border)] bg-[var(--surface-2)]";
  return (
    <div className="flex flex-wrap items-start gap-2 py-2">
      <span
        className={`inline-flex shrink-0 items-center rounded border px-2 py-0.5 font-mono text-[10px] font-bold uppercase ${cls}`}
      >
        {risk.severity || "—"}
      </span>
      <span className="flex-1 text-xs font-medium leading-snug text-[var(--fg)]">
        {risk.title || "—"}
      </span>
      {risk.reason && risk.reason !== "—" && (
        <p className="w-full pl-0 text-xs leading-snug text-[var(--muted)]">
          {risk.reason}
        </p>
      )}
    </div>
  );
}

/* ─── Main component ─────────────────────────────────────────────── */

export function AnalystResearchNotesSection({
  view,
}: {
  view: AnalysisWorkspaceView;
}) {
  const { conclusion, dashboard, thesis, risks, freshness, reportId } = view;

  /* ── Key research conclusion ──────────────────────────────────── */
  // Prefer conclusion.conclusion; fall back to dashboard.researchConclusion
  const conclusionText =
    fv(conclusion.conclusion) !== "—"
      ? fv(conclusion.conclusion)
      : fv(dashboard.researchConclusion);

  /* ── Research confidence ──────────────────────────────────────── */
  const confidence =
    fv(conclusion.researchConfidence as DisplayField<string>) !== "—"
      ? fv(conclusion.researchConfidence as DisplayField<string>)
      : fv(dashboard.researchConfidence as DisplayField<string>);

  /* ── Supporting evidence ──────────────────────────────────────── */
  // Primary evidence from conclusion.evidence, then keyStrengths as fallback
  const primaryEvidence: string[] = conclusion.evidence?.primaryEvidence?.length
    ? conclusion.evidence.primaryEvidence
    : [];
  const supportingEvidence: string[] = conclusion.evidence?.supportingEvidence?.length
    ? conclusion.evidence.supportingEvidence
    : [];
  const combinedEvidence = [...primaryEvidence, ...supportingEvidence].slice(0, 5);

  /* ── Opportunity signal ───────────────────────────────────────── */
  // Use conclusion.primaryOpportunity; fall back to dashboard.topOpportunity
  const opportunitySignal =
    fv(conclusion.primaryOpportunity) !== "—"
      ? fv(conclusion.primaryOpportunity)
      : fv(dashboard.topOpportunity);

  /* ── Risk signal ──────────────────────────────────────────────── */
  // Use conclusion.primaryRisk; fall back to dashboard.biggestRisk; then first HIGH risk
  const primaryRiskText =
    fv(conclusion.primaryRisk) !== "—"
      ? fv(conclusion.primaryRisk)
      : fv(dashboard.biggestRisk);

  // First HIGH-severity risk from risks[] for the risk signal row
  const highRisk: RiskInsightView | undefined = risks.find(
    (r) => r.available && r.severity?.toUpperCase() === "HIGH"
  );
  const firstRisk: RiskInsightView | undefined =
    highRisk ?? risks.find((r) => r.available);

  /* ── Limitations / caveats ────────────────────────────────────── */
  const limitations: string[] = conclusion.evidence?.limitations?.length
    ? conclusion.evidence.limitations
    : [];

  /* ── Long-term thesis (supporting context) ────────────────────── */
  const longTermThesis = fv(thesis.longTermThesis);

  /* ── Provenance ───────────────────────────────────────────────── */
  const researchDate = str(freshness.researchDate);
  const analysisVersion = str(freshness.analysisVersion);
  const researchMode = str(freshness.researchMode);
  const reportIdStr = str(reportId);

  return (
    <div className="space-y-5 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 font-mono text-sm">
      {/* ── Header bar ──────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-3">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--accent)]">
          Analyst / Research Notes
        </span>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--muted)]">Research Confidence</span>
          <ConfidencePill level={confidence} />
        </div>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        {/* ── Block 1: Key Research Conclusion ──────────────────── */}
        <div className="sm:col-span-2">
          <BlockHeader title="Key Research Conclusion" />
          {conclusionText !== "—" ? (
            <p className="text-sm leading-relaxed text-[var(--fg)]">
              {conclusionText}
            </p>
          ) : (
            <p className="text-xs italic text-[var(--muted)]">—</p>
          )}
          {longTermThesis !== "—" && (
            <p className="mt-2 text-xs leading-snug text-[var(--muted)]">
              <span className="font-bold uppercase tracking-wider">Long-Term Thesis: </span>
              {longTermThesis}
            </p>
          )}
        </div>

        {/* ── Block 2: Supporting Evidence ──────────────────────── */}
        <div>
          <BlockHeader title="Supporting Evidence" />
          <EvidenceList
            items={combinedEvidence}
            emptyLabel="No supporting evidence available"
          />
        </div>

        {/* ── Block 3: Opportunity & Risk Signals ───────────────── */}
        <div className="space-y-4">
          {/* Opportunity signal */}
          <div>
            <div className="mb-1.5 flex items-center gap-2">
              <SignalPill type="opportunity" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">
                Key Opportunity Signal
              </span>
            </div>
            {opportunitySignal !== "—" ? (
              <p className="text-xs leading-snug text-[var(--fg)]">
                {opportunitySignal}
              </p>
            ) : (
              <p className="text-xs italic text-[var(--muted)]">—</p>
            )}
          </div>

          {/* Risk signal */}
          <div>
            <div className="mb-1.5 flex items-center gap-2">
              <SignalPill type="risk" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">
                Key Risk Signal
              </span>
            </div>
            {firstRisk ? (
              <RiskSignalRow risk={firstRisk} />
            ) : primaryRiskText !== "—" ? (
              <p className="text-xs leading-snug text-[var(--fg)]">{primaryRiskText}</p>
            ) : (
              <p className="text-xs italic text-[var(--muted)]">—</p>
            )}
          </div>
        </div>

        {/* ── Block 4: Limitations / Caveats ────────────────────── */}
        <div>
          <BlockHeader title="Limitations / Caveats" />
          <EvidenceList
            items={limitations}
            emptyLabel="No limitations recorded"
          />
        </div>

        {/* ── Block 5: Provenance / Source ──────────────────────── */}
        <div>
          <BlockHeader title="Provenance / Source" />
          <div className="space-y-0">
            <TermRow label="Research Date" value={researchDate} mono />
            <TermRow label="Analysis Version" value={analysisVersion} mono />
            <TermRow label="Research Mode" value={researchMode} mono={false} />
            <TermRow label="Report ID" value={reportIdStr} mono />
          </div>
        </div>
      </div>

      {/* ── Footer disclaimer ────────────────────────────────────── */}
      <p className="border-t border-[var(--border)] pt-3 text-[10px] leading-snug text-[var(--muted)]">
        All observations sourced from existing analysis fields (
        <span className="font-mono">conclusion</span>,{" "}
        <span className="font-mono">dashboard</span>,{" "}
        <span className="font-mono">thesis</span>,{" "}
        <span className="font-mono">risks</span>,{" "}
        <span className="font-mono">freshness</span>). No data has been invented,
        synthesised, or paraphrased beyond what the analysis engine produced.
      </p>
    </div>
  );
}
