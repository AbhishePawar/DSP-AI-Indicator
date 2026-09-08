"use client";

/**
 * AIInvestmentViewSection — institutional research-report layout for the Analysis Page.
 *
 * Data sources (existing, no mock data):
 *   - view.conclusion  → conclusion, intrinsicValueRange, marginOfSafety,
 *                        researchConfidence, primaryOpportunity, primaryRisk
 *   - view.dashboard   → researchConclusion, researchConfidence,
 *                        topOpportunity, biggestRisk
 *
 * Rendering rules:
 *   - Available field  → accent colour, full value
 *   - Unavailable field → "—" in muted colour (never invented)
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

/* ─── Conclusion colour ──────────────────────────────────────────── */

const CONCLUSION_COLOURS: Record<string, string> = {
  BUY: "border-emerald-500/40 text-emerald-700",
  STRONG_BUY: "border-emerald-500/50 text-emerald-700",
  HOLD: "border-amber-500/40 text-amber-700",
  WATCH: "border-amber-500/40 text-amber-700",
  AVOID: "border-red-500/40 text-red-700",
  SELL: "border-red-500/50 text-red-700",
};

function conclusionColour(label: string): string {
  const key = label.toUpperCase().replace(/\s+/g, "_");
  return (
    CONCLUSION_COLOURS[key] ??
    "border-[var(--border)] text-[var(--fg)]"
  );
}

/* ─── Confidence colour ──────────────────────────────────────────── */

const CONFIDENCE_COLOURS: Record<string, string> = {
  HIGH: "text-emerald-700",
  MEDIUM: "text-amber-700",
  LOW: "text-red-700",
};

function confidenceColour(level: string): string {
  return CONFIDENCE_COLOURS[level.toUpperCase()] ?? "text-[var(--muted)]";
}

/* ─── Metric row ─────────────────────────────────────────────────── */

function MetricRow({
  label,
  value,
  available: isAvail,
  valueClassName,
}: {
  label: string;
  value: string;
  available: boolean;
  valueClassName?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-2.5 border-b border-[var(--border)] last:border-0">
      <span className="text-xs text-[var(--muted)] shrink-0">{label}</span>
      <span
        className={[
          "min-w-0 text-right font-mono text-sm font-semibold leading-snug break-words",
          isAvail
            ? (valueClassName ?? "text-[var(--accent)]")
            : "text-[var(--muted)]",
        ].join(" ")}
      >
        {value}
      </span>
    </div>
  );
}

/* ─── Signal block (opportunity / risk) ─────────────────────────── */

function SignalBlock({
  kind,
  value,
  available: isAvail,
}: {
  kind: "opportunity" | "risk";
  value: string;
  available: boolean;
}) {
  const isOpportunity = kind === "opportunity";
  const labelText = isOpportunity ? "Key Opportunity" : "Key Risk";
  const borderClass = isOpportunity
    ? "border-l-2 border-emerald-500/40" :"border-l-2 border-red-500/40";
  const labelClass = isOpportunity ? "text-emerald-700" : "text-red-700";

  return (
    <div className={["pl-3 py-1", isAvail ? borderClass : "border-l-2 border-[var(--border)]"].join(" ")}>
      <p
        className={[
          "text-[10px] font-semibold uppercase tracking-widest mb-1",
          isAvail ? labelClass : "text-[var(--muted)]",
        ].join(" ")}
      >
        {labelText}
      </p>
      <p
        className={[
          "text-sm leading-relaxed",
          isAvail ? "text-[var(--fg)]" : "text-[var(--muted)]",
        ].join(" ")}
      >
        {value}
      </p>
    </div>
  );
}

/* ─── Main component ─────────────────────────────────────────────── */

export function AIInvestmentViewSection({
  view,
}: {
  view: AnalysisWorkspaceView;
}) {
  const { conclusion, dashboard } = view;

  /* Prefer dashboard.researchConclusion; fall back to conclusion.conclusion */
  const conclusionLabel =
    avail(dashboard.researchConclusion)
      ? val(dashboard.researchConclusion)
      : val(conclusion.conclusion);

  /* Confidence */
  const confidenceRaw =
    avail(dashboard.researchConfidence)
      ? val(dashboard.researchConfidence)
      : conclusion.researchConfidence.value != null
        ? String(conclusion.researchConfidence.value)
        : "—";

  const confidenceAvail =
    avail(dashboard.researchConfidence) ||
    (conclusion.researchConfidence.presence === "available" &&
      conclusion.researchConfidence.value != null);

  /* Intrinsic value & margin of safety */
  const intrinsicValue = val(conclusion.intrinsicValueRange);
  const intrinsicAvail = avail(conclusion.intrinsicValueRange);

  const marginOfSafety = val(conclusion.marginOfSafety);
  const mosAvail = avail(conclusion.marginOfSafety);

  /* Key opportunity */
  const opportunityValue =
    avail(conclusion.primaryOpportunity)
      ? val(conclusion.primaryOpportunity)
      : avail(dashboard.topOpportunity)
        ? val(dashboard.topOpportunity)
        : "—";
  const opportunityAvail =
    avail(conclusion.primaryOpportunity) || avail(dashboard.topOpportunity);

  /* Key risk */
  const riskValue =
    avail(conclusion.primaryRisk)
      ? val(conclusion.primaryRisk)
      : avail(dashboard.biggestRisk)
        ? val(dashboard.biggestRisk)
        : "—";
  const riskAvail =
    avail(conclusion.primaryRisk) || avail(dashboard.biggestRisk);

  const conclusionIsAvail = conclusionLabel !== "—";

  return (
    <div className="space-y-6">
      {/* ── Verdict + confidence ─────────────────────────────────── */}
      <div className="flex flex-wrap items-start gap-6">
        {/* Conclusion */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mb-2">
            Investment Verdict
          </p>
          <div
            className={[
              "inline-flex items-center rounded border px-4 py-2",
              conclusionIsAvail
                ? conclusionColour(conclusionLabel)
                : "border-[var(--border)] text-[var(--muted)]",
            ].join(" ")}
          >
            <span className="font-[family-name:var(--font-display)] text-xl font-semibold tracking-wide">
              {conclusionLabel}
            </span>
          </div>
        </div>

        {/* Confidence */}
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mb-2">
            Research Confidence
          </p>
          <span
            className={[
              "font-mono text-base font-bold",
              confidenceAvail
                ? confidenceColour(confidenceRaw)
                : "text-[var(--muted)]",
            ].join(" ")}
          >
            {confidenceRaw}
          </span>
        </div>
      </div>

      {/* ── Valuation metrics ────────────────────────────────────── */}
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mb-1">
          Valuation Metrics
        </p>
        <div className="border-t border-[var(--border)]">
          <MetricRow
            label="Intrinsic Value"
            value={intrinsicValue}
            available={intrinsicAvail}
          />
          <MetricRow
            label="Margin of Safety"
            value={marginOfSafety}
            available={mosAvail}
            valueClassName={
              mosAvail
                ? marginOfSafety.startsWith("-")
                  ? "text-red-700" :"text-emerald-700"
                : undefined
            }
          />
        </div>
      </div>

      {/* ── Signal blocks ────────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2">
        <SignalBlock
          kind="opportunity"
          value={opportunityValue}
          available={opportunityAvail}
        />
        <SignalBlock
          kind="risk"
          value={riskValue}
          available={riskAvail}
        />
      </div>

      {/* ── Disclaimer ───────────────────────────────────────────── */}
      <p className="text-[10px] leading-relaxed text-[var(--muted)] border-t border-[var(--border)] pt-3">
        Generated by the DSP deterministic research engine. Not financial advice.
        All values are derived from the analysis pipeline — unavailable fields show &ldquo;—&rdquo;.
      </p>
    </div>
  );
}
