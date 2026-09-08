"use client";

/**
 * AIResearchSection — compact research-terminal block for the Analysis Page.
 *
 * Shows AI-generated research fields using ONLY existing real data:
 *   • Research Conclusion  — view.conclusion.conclusion
 *   • Confidence           — view.conclusion.researchConfidence / view.dashboard.researchConfidence
 *   • Key Opportunity      — view.conclusion.primaryOpportunity / view.dashboard.topOpportunity
 *   • Key Risk             — view.conclusion.primaryRisk / view.dashboard.biggestRisk
 *   • Supporting Insight   — view.conclusion.evidence.supportingEvidence[0]
 *
 * Unavailable fields are shown clearly as "—" (never invented).
 */

import type { AnalysisWorkspaceView, DisplayField } from "@/lib/analysis/types";

/* ─── Helpers ────────────────────────────────────────────────────── */

function val(field: DisplayField<string | number>): string {
  if (field.presence === "unavailable" || field.value == null) return "—";
  return String(field.value);
}

function avail(field: DisplayField<unknown>): boolean {
  return field.presence === "available" && field.value != null;
}

/* ─── Conclusion colour map ──────────────────────────────────────── */

const CONCLUSION_COLOURS: Record<string, string> = {
  BUY: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10",
  STRONG_BUY: "text-emerald-300 border-emerald-500/50 bg-emerald-500/15",
  HOLD: "text-amber-400 border-amber-500/40 bg-amber-500/10",
  WATCH: "text-amber-400 border-amber-500/40 bg-amber-500/10",
  AVOID: "text-red-400 border-red-500/40 bg-red-500/10",
  SELL: "text-red-300 border-red-500/50 bg-red-500/15",
};

function conclusionColour(label: string): string {
  const key = label.toUpperCase().replace(/\s+/g, "_");
  return CONCLUSION_COLOURS[key] ?? "text-[var(--fg)] border-[var(--border)] bg-[var(--surface-2)]";
}

const CONFIDENCE_COLOURS: Record<string, string> = {
  HIGH: "text-emerald-400",
  MEDIUM: "text-amber-400",
  LOW: "text-red-400",
};

function confidenceColour(level: string): string {
  return CONFIDENCE_COLOURS[level.toUpperCase()] ?? "text-[var(--muted)]";
}

/* ─── Terminal row ───────────────────────────────────────────────── */

function TerminalRow({
  label,
  value,
  isAvail,
  valueClass,
}: {
  label: string;
  value: string;
  isAvail: boolean;
  valueClass?: string;
}) {
  return (
    <div className="grid grid-cols-[auto_1fr] items-start gap-x-4 border-b border-[var(--border)] py-2.5 last:border-0">
      <span className="whitespace-nowrap text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">
        {label}
      </span>
      <span
        className={[
          "text-right font-mono text-sm leading-snug",
          isAvail ? (valueClass ?? "text-[var(--fg)]") : "text-[var(--muted)]",
        ].join(" ")}
      >
        {value}
      </span>
    </div>
  );
}

/* ─── Signal block ───────────────────────────────────────────────── */

function SignalBlock({
  kind,
  value,
  isAvail,
}: {
  kind: "opportunity" | "risk";
  value: string;
  isAvail: boolean;
}) {
  const isOpp = kind === "opportunity";
  const icon = isOpp ? "▲" : "▼";
  const label = isOpp ? "KEY OPPORTUNITY" : "KEY RISK";
  const activeClass = isOpp
    ? "border-emerald-500/30 bg-emerald-500/5" :"border-red-500/30 bg-red-500/5";
  const iconClass = isOpp ? "text-emerald-400" : "text-red-400";

  return (
    <div
      className={[
        "flex flex-col gap-1.5 rounded border p-3",
        isAvail ? activeClass : "border-[var(--border)] bg-[var(--surface-2)]",
      ].join(" ")}
    >
      <div className="flex items-center gap-1.5">
        <span className={["text-[10px] font-bold", isAvail ? iconClass : "text-[var(--muted)]"].join(" ")}>
          {icon}
        </span>
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">
          {label}
        </span>
      </div>
      <p
        className={[
          "text-sm leading-snug",
          isAvail ? "text-[var(--fg)]" : "font-mono text-[var(--muted)]",
        ].join(" ")}
      >
        {value}
      </p>
    </div>
  );
}

/* ─── Main component ─────────────────────────────────────────────── */

export function AIResearchSection({ view }: { view: AnalysisWorkspaceView }) {
  const { conclusion, dashboard } = view;

  /* Conclusion label */
  const conclusionLabel = avail(dashboard.researchConclusion)
    ? val(dashboard.researchConclusion)
    : val(conclusion.conclusion);
  const conclusionIsAvail = conclusionLabel !== "—";

  /* Confidence */
  const confidenceRaw = avail(dashboard.researchConfidence)
    ? val(dashboard.researchConfidence)
    : conclusion.researchConfidence.value != null
      ? String(conclusion.researchConfidence.value)
      : "—";
  const confidenceIsAvail =
    avail(dashboard.researchConfidence) ||
    (conclusion.researchConfidence.presence === "available" &&
      conclusion.researchConfidence.value != null);

  /* Key opportunity */
  const opportunityValue = avail(conclusion.primaryOpportunity)
    ? val(conclusion.primaryOpportunity)
    : avail(dashboard.topOpportunity)
      ? val(dashboard.topOpportunity)
      : "—";
  const opportunityIsAvail =
    avail(conclusion.primaryOpportunity) || avail(dashboard.topOpportunity);

  /* Key risk */
  const riskValue = avail(conclusion.primaryRisk)
    ? val(conclusion.primaryRisk)
    : avail(dashboard.biggestRisk)
      ? val(dashboard.biggestRisk)
      : "—";
  const riskIsAvail =
    avail(conclusion.primaryRisk) || avail(dashboard.biggestRisk);

  /* Supporting insight — first item from evidence.supportingEvidence */
  const supportingInsights = conclusion.evidence?.supportingEvidence ?? [];
  const insightValue = supportingInsights.length > 0 ? supportingInsights[0] : "—";
  const insightIsAvail = supportingInsights.length > 0;

  return (
    <div className="space-y-3">
      {/* ── Terminal header ─────────────────────────────────────── */}
      <div className="flex items-center justify-between rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">
          AI Research Terminal
        </span>
        <span className="text-[10px] font-mono text-[var(--muted)]">
          DSP Research Engine · Deterministic
        </span>
      </div>

      {/* ── Verdict + confidence row ─────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3 rounded border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
        {/* Conclusion badge */}
        <div
          className={[
            "inline-flex items-center rounded border px-3 py-1",
            conclusionIsAvail
              ? conclusionColour(conclusionLabel)
              : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)]",
          ].join(" ")}
        >
          <span className="font-mono text-base font-bold tracking-wide">
            {conclusionLabel}
          </span>
        </div>

        {/* Confidence pill */}
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-medium uppercase tracking-widest text-[var(--muted)]">
            Confidence
          </span>
          <span
            className={[
              "font-mono text-sm font-bold",
              confidenceIsAvail ? confidenceColour(confidenceRaw) : "text-[var(--muted)]",
            ].join(" ")}
          >
            {confidenceRaw}
          </span>
        </div>
      </div>

      {/* ── Opportunity / Risk blocks ────────────────────────────── */}
      <div className="grid gap-3 sm:grid-cols-2">
        <SignalBlock kind="opportunity" value={opportunityValue} isAvail={opportunityIsAvail} />
        <SignalBlock kind="risk" value={riskValue} isAvail={riskIsAvail} />
      </div>

      {/* ── Supporting insight ───────────────────────────────────── */}
      <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
        <TerminalRow
          label="Supporting Insight"
          value={insightValue}
          isAvail={insightIsAvail}
        />
      </div>
    </div>
  );
}
