"use client";

/**
 * ExportShareSection — compact research-terminal Export/Share block.
 *
 * Reuses:
 *   - view.snapshot, view.conclusion, view.dashboard, view.valuation,
 *     view.freshness, view.reportId  (AnalysisWorkspaceView)
 *   - downloadText() from @/lib/company-analysis/exportView
 *   - onShare (clipboard URL) already wired in AnalysisClient
 *
 * No new backend endpoints. No invented data.
 * Unavailable actions are shown disabled with a reason label.
 */

import { useState } from "react";
import { downloadText } from "@/lib/company-analysis/exportView";
import type { AnalysisWorkspaceView } from "@/lib/analysis/types";

/* ── helpers ──────────────────────────────────────────────────────── */

function fv(field: { value: string | null; presence: string } | undefined): string {
  if (!field || field.presence !== "available" || !field.value) return "—";
  return field.value;
}

function buildJsonExport(view: AnalysisWorkspaceView, ticker: string): string {
  return JSON.stringify(
    {
      exportedAt: new Date().toISOString(),
      source: "dsp_platform /api/v1/analyse — display snapshot only",
      note: "No client-side scoring. Values are as returned by the API.",
      ticker,
      reportId: view.reportId ?? "—",
      company: fv(view.snapshot.companyName),
      exchange: fv(view.snapshot.exchange),
      researchDate: view.freshness.researchDate ?? "—",
      analysisVersion: view.freshness.analysisVersion,
      conclusion: fv(view.conclusion.conclusion),
      researchConfidence: fv(view.conclusion.researchConfidence as { value: string | null; presence: string }),
      intrinsicValueRange: fv(view.conclusion.intrinsicValueRange),
      marginOfSafety: fv(view.conclusion.marginOfSafety),
      primaryOpportunity: fv(view.conclusion.primaryOpportunity),
      primaryRisk: fv(view.conclusion.primaryRisk),
      scores: {
        business: fv(view.dashboard.businessScore),
        financial: fv(view.dashboard.financialScore),
        valuation: fv(view.dashboard.valuationScore),
        growth: fv(view.dashboard.growthScore),
        risk: fv(view.dashboard.riskScore),
        management: fv(view.dashboard.managementScore),
      },
      valuation: {
        currentPrice: fv(view.valuation.currentPrice),
        intrinsicValueRange: fv(view.valuation.intrinsicValueRange),
        marginOfSafety: fv(view.valuation.marginOfSafety),
        summary: fv(view.valuation.summary),
      },
    },
    null,
    2,
  );
}

function buildCsvExport(view: AnalysisWorkspaceView, ticker: string): string {
  const esc = (v: string) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
  const rows: [string, string][] = [
    ["field", "value"],
    ["ticker", ticker],
    ["reportId", view.reportId ?? "—"],
    ["company", fv(view.snapshot.companyName)],
    ["exchange", fv(view.snapshot.exchange)],
    ["researchDate", view.freshness.researchDate ?? "—"],
    ["analysisVersion", view.freshness.analysisVersion],
    ["conclusion", fv(view.conclusion.conclusion)],
    ["researchConfidence", fv(view.conclusion.researchConfidence as { value: string | null; presence: string })],
    ["intrinsicValueRange", fv(view.conclusion.intrinsicValueRange)],
    ["marginOfSafety", fv(view.conclusion.marginOfSafety)],
    ["primaryOpportunity", fv(view.conclusion.primaryOpportunity)],
    ["primaryRisk", fv(view.conclusion.primaryRisk)],
    ["score_business", fv(view.dashboard.businessScore)],
    ["score_financial", fv(view.dashboard.financialScore)],
    ["score_valuation", fv(view.dashboard.valuationScore)],
    ["score_growth", fv(view.dashboard.growthScore)],
    ["score_risk", fv(view.dashboard.riskScore)],
    ["score_management", fv(view.dashboard.managementScore)],
    ["valuation_currentPrice", fv(view.valuation.currentPrice)],
    ["valuation_intrinsicValueRange", fv(view.valuation.intrinsicValueRange)],
    ["valuation_marginOfSafety", fv(view.valuation.marginOfSafety)],
  ];
  return rows.map(([k, v]) => `${esc(k)},${esc(v)}`).join("\n");
}

function buildTextSummary(view: AnalysisWorkspaceView, ticker: string): string {
  const lines = [
    `DSP Research Terminal — ${ticker}`,
    `Company : ${fv(view.snapshot.companyName)}`,
    `Exchange : ${fv(view.snapshot.exchange)}`,
    `Report ID : ${view.reportId ?? "—"}`,
    `Research Date : ${view.freshness.researchDate ?? "—"}`,
    ``,
    `Conclusion : ${fv(view.conclusion.conclusion)}`,
    `Confidence : ${fv(view.conclusion.researchConfidence as { value: string | null; presence: string })}`,
    `Intrinsic Value : ${fv(view.conclusion.intrinsicValueRange)}`,
    `Margin of Safety : ${fv(view.conclusion.marginOfSafety)}`,
    ``,
    `Scores`,
    `  Business   : ${fv(view.dashboard.businessScore)}`,
    `  Financial  : ${fv(view.dashboard.financialScore)}`,
    `  Valuation  : ${fv(view.dashboard.valuationScore)}`,
    `  Growth     : ${fv(view.dashboard.growthScore)}`,
    `  Risk       : ${fv(view.dashboard.riskScore)}`,
    `  Management : ${fv(view.dashboard.managementScore)}`,
    ``,
    `Key Opportunity : ${fv(view.conclusion.primaryOpportunity)}`,
    `Key Risk        : ${fv(view.conclusion.primaryRisk)}`,
    ``,
    `Exported : ${new Date().toISOString()}`,
    `Source   : DSP AI Indicator — display snapshot only, no client scoring.`,
  ];
  return lines.join("\n");
}

/* ── sub-components ───────────────────────────────────────────────── */

type ActionStatus = "idle" | "done" | "error";

function ActionButton({
  label,
  sublabel,
  available,
  unavailableReason,
  onAction,
}: {
  label: string;
  sublabel: string;
  available: boolean;
  unavailableReason?: string;
  onAction: () => void;
}) {
  const [status, setStatus] = useState<ActionStatus>("idle");

  function handleClick() {
    if (!available) return;
    try {
      onAction();
      setStatus("done");
      setTimeout(() => setStatus("idle"), 2000);
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 2000);
    }
  }

  if (!available) {
    return (
      <div className="flex flex-col gap-0.5 rounded border border-dashed border-[var(--border)] bg-[var(--surface)] px-3 py-3 opacity-50">
        <span className="text-xs font-medium text-[var(--muted)]">{label}</span>
        <span className="text-[10px] text-[var(--muted)]">{unavailableReason ?? "Unavailable"}</span>
      </div>
    );
  }

  const stateLabel =
    status === "done" ? "✓ Done" : status === "error" ? "✗ Error" : sublabel;

  return (
    <button
      type="button"
      onClick={handleClick}
      className="flex min-h-[52px] flex-col gap-0.5 rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-3 text-left transition-colors hover:border-[var(--accent)] hover:bg-[var(--surface-2)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)] active:bg-[var(--surface-2)]"
    >
      <span className="text-xs font-medium text-[var(--fg)]">{label}</span>
      <span
        className={`text-[10px] ${
          status === "done"
            ? "text-emerald-500"
            : status === "error" ?"text-red-500" :"text-[var(--muted)]"
        }`}
      >
        {stateLabel}
      </span>
    </button>
  );
}

/* ── main component ───────────────────────────────────────────────── */

export function ExportShareSection({
  view,
  ticker,
}: {
  view: AnalysisWorkspaceView;
  ticker: string;
}) {
  const hasData = view.apiOk && view.snapshot.ticker.presence === "available";
  const slug = ticker || "research";
  const dateSlug = view.freshness.researchDate
    ? view.freshness.researchDate.slice(0, 10).replace(/-/g, "")
    : "export";

  /* ── action definitions ─────────────────────────────────────────── */
  const actions = [
    {
      label: "Copy URL",
      sublabel: "Copy analysis link",
      available: true,
      onAction: () => {
        const url = `${window.location.origin}/analysis?symbol=${encodeURIComponent(slug)}`;
        void navigator.clipboard?.writeText(url);
      },
    },
    {
      label: "Copy Summary",
      sublabel: "Plain-text snapshot",
      available: hasData,
      unavailableReason: "Run analysis first",
      onAction: () => {
        void navigator.clipboard?.writeText(buildTextSummary(view, slug));
      },
    },
    {
      label: "Download JSON",
      sublabel: "Structured data snapshot",
      available: hasData,
      unavailableReason: "Run analysis first",
      onAction: () => {
        downloadText(
          `${slug}_${dateSlug}.json`,
          buildJsonExport(view, slug),
          "application/json",
        );
      },
    },
    {
      label: "Download CSV",
      sublabel: "Key metrics spreadsheet",
      available: hasData,
      unavailableReason: "Run analysis first",
      onAction: () => {
        downloadText(
          `${slug}_${dateSlug}.csv`,
          buildCsvExport(view, slug),
          "text/csv",
        );
      },
    },
    {
      label: "Download PDF",
      sublabel: "Not supported",
      available: false,
      unavailableReason: "No PDF endpoint available",
      onAction: () => {},
    },
    {
      label: "Email Report",
      sublabel: "Not supported",
      available: false,
      unavailableReason: "No email endpoint available",
      onAction: () => {},
    },
  ];

  return (
    <div className="space-y-4">
      {/* Status row */}
      <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
        <span className="font-mono font-semibold text-[var(--accent)]">{slug}</span>
        {view.reportId ? (
          <span className="rounded bg-[var(--surface-2)] px-1.5 py-0.5 font-mono text-[10px]">
            ID: {view.reportId.slice(0, 12)}…
          </span>
        ) : null}
        {view.freshness.researchDate ? (
          <span className="text-[10px]">
            Analysed: {view.freshness.researchDate.slice(0, 10)}
          </span>
        ) : null}
        {!hasData ? (
          <span className="rounded border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-400">
            No analysis loaded — run analysis to enable data exports
          </span>
        ) : (
          <span className="rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-400">
            Analysis loaded
          </span>
        )}
      </div>

      {/* Action grid — 2-col on mobile, 3-col on sm, 6-col on md+ */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-6">
        {actions.map((a) => (
          <ActionButton key={a.label} {...a} />
        ))}
      </div>

      {/* Disclaimer */}
      <p className="text-[10px] leading-relaxed text-[var(--muted)]">
        Exports are display snapshots only — no client-side scoring or recalculation.
        PDF and email export require backend endpoints not currently available.
        Data sourced from{" "}
        <span className="font-mono">GET /api/v1/analyse</span>.
      </p>
    </div>
  );
}
