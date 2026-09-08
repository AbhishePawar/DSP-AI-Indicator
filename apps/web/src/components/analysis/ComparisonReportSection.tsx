"use client";

/**
 * ComparisonReportSection — compact research-terminal comparison report.
 *
 * Data sources (all existing, no mock data):
 *   - view.dashboard       → primary scores (business, financial, valuation, growth, risk)
 *   - view.snapshot        → primary CMP, marketCap
 *   - view.valuation       → intrinsicValueRange, marginOfSafety
 *   - view.conclusion      → researchConfidence, conclusion
 *   - api.compare()        → POST /compare — qualitative comparison engine
 *                            (same endpoint used by PeersSection)
 *   - api.analyzeCompany() → pre-compute Decision Pack per symbol
 *
 * Rendering rules:
 *   - Available fields: show value with colour-coded accent
 *   - Unavailable fields: show "—" in muted colour (never invent values)
 *   - Terminal aesthetic: monospace values, compact rows, dense grid
 *   - Comparison conclusion / ranking shown when real data exists
 */

import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiClientError } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthProvider";
import type { AnalysisWorkspaceView, DisplayField } from "@/lib/analysis/types";

/* ─── Helpers ────────────────────────────────────────────────────── */

function dv(field: DisplayField<string | number | string[]> | undefined): string {
  if (!field || field.presence === "unavailable" || field.value == null) return "—";
  if (Array.isArray(field.value)) return field.value.join(" · ");
  return String(field.value);
}

function scoreColour(scoreStr: string): string {
  if (scoreStr === "—") return "text-[var(--muted)]";
  const n = parseFloat(scoreStr);
  if (isNaN(n)) return "text-[var(--accent)]";
  if (n >= 7) return "text-emerald-400";
  if (n >= 5) return "text-amber-400";
  return "text-red-400";
}

function describeError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) return "Sign in required to run comparison report.";
    return error.message || `API error (${error.status})`;
  }
  if (error instanceof Error) return error.message;
  return "Comparison data unavailable.";
}

function defaultRange() {
  const end = new Date();
  const start = new Date();
  start.setFullYear(end.getFullYear() - 1);
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { start: iso(start), end: iso(end) };
}

const MAX_PEERS = 5;

/* ─── Types ──────────────────────────────────────────────────────── */

type DimensionResult = {
  dimension: string;
  observations: { code: string; text: string }[];
};

type ComparisonReport = {
  explanation: { summary: string; detail: string | null };
  included_symbols: string[];
  excluded_symbols: string[];
  dimension_results: DimensionResult[];
  limitations: { code: string; message: string }[];
};

type ComparisonResultPayload = {
  status: string;
  refused: boolean;
  report: ComparisonReport;
};

/* ─── Score badge ────────────────────────────────────────────────── */

function ScoreBadge({ label, score }: { label: string; score: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5">
      <span className={["font-mono text-sm font-bold leading-none", scoreColour(score)].join(" ")}>
        {score}
      </span>
      <span className="text-[8px] font-semibold uppercase tracking-widest text-[var(--muted)]">
        {label}
      </span>
    </div>
  );
}

/* ─── Dimension card ─────────────────────────────────────────────── */

function DimensionCard({ dim }: { dim: DimensionResult }) {
  const label = dim.dimension.replace(/_/g, " ");
  const iconMap: Record<string, string> = {
    valuation: "◈",
    quality: "◆",
    growth: "▲",
    risk: "⚠",
    financial: "◆",
    business: "◉",
    management: "◎",
  };
  const key = Object.keys(iconMap).find((k) => label.toLowerCase().includes(k));
  const icon = key ? iconMap[key] : "·";

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2.5">
      <div className="mb-2 flex items-center gap-1.5">
        <span className="text-[10px] text-[var(--accent)]">{icon}</span>
        <span className="text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">
          {label}
        </span>
      </div>
      <ul className="space-y-1">
        {dim.observations.map((obs, i) => (
          <li key={i} className="flex items-start gap-1.5 text-[11px] text-[var(--fg)]">
            <span className="mt-0.5 shrink-0 text-[var(--accent)]">›</span>
            <span>{obs.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ─── Main component ─────────────────────────────────────────────── */

export function ComparisonReportSection({
  view,
  ticker,
}: {
  view: AnalysisWorkspaceView;
  ticker: string;
}) {
  const { session } = useAuth();
  const token = session?.accessToken ?? null;
  const [draft, setDraft] = useState("");

  /* Parse peer tickers */
  const peerTickers = useMemo(() => {
    return Array.from(
      new Set(
        draft
          .split(/[,\s+]+/)
          .map((s) => s.trim().toUpperCase())
          .filter((s) => s && s !== ticker.toUpperCase()),
      ),
    ).slice(0, MAX_PEERS);
  }, [draft, ticker]);

  /* Primary scores from view.dashboard */
  const dash = view.dashboard;
  const scores = {
    business: dv(dash.businessScore),
    financial: dv(dash.financialScore),
    valuation: dv(dash.valuationScore),
    growth: dv(dash.growthScore),
    risk: dv(dash.riskScore),
  };

  /* Conclusion / confidence from view */
  const conclusion = dv(view.conclusion.conclusion ?? view.dashboard.researchConclusion);
  const confidence = dv(
    (view.conclusion.researchConfidence as DisplayField<string> | undefined) ??
      view.dashboard.researchConfidence,
  );
  const intrinsic = dv(view.valuation.intrinsicValueRange);
  const mos = dv(view.valuation.marginOfSafety);

  /* Comparison mutation */
  const compareMutation = useMutation({
    mutationFn: async () => {
      if (peerTickers.length < 1) throw new Error("Add at least one peer ticker.");
      const { start, end } = defaultRange();
      const symbols = [ticker.toUpperCase(), ...peerTickers];
      const analyzed = await Promise.all(
        symbols.map(async (sym) => {
          try {
            const res = await api.analyzeCompany(
              { symbol: sym, start, end, as_decision_pack: true },
              { token },
            );
            return { symbol: sym, reportId: res.payload?.report_id ?? null };
          } catch {
            return { symbol: sym, reportId: null };
          }
        }),
      );
      const reportIds = analyzed
        .map((a) => a.reportId)
        .filter((id): id is string => Boolean(id));
      if (reportIds.length < 2)
        throw new Error("Need at least 2 successful analyses for comparison report.");
      const compared = await api.compare({ report_ids: reportIds }, { token });
      return (compared.result as ComparisonResultPayload | undefined) ?? null;
    },
  });

  const report = compareMutation.data?.report ?? null;

  return (
    <div className="space-y-4">

      {/* ── Primary company scorecard ────────────────────────────── */}
      <div className="rounded-lg border border-[var(--accent)]/30 bg-[var(--accent)]/5 px-4 py-3">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs font-bold text-[var(--accent)]">
            {ticker.toUpperCase()}
          </span>
          <span className="rounded bg-[var(--accent)]/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-widest text-[var(--accent)]">
            Subject
          </span>
          {conclusion !== "—" ? (
            <span className="rounded border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-[10px] text-[var(--fg)]">
              {conclusion}
            </span>
          ) : null}
          {confidence !== "—" ? (
            <span className="rounded border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-[10px] text-[var(--muted)]">
              Confidence: {confidence}
            </span>
          ) : null}
        </div>

        {/* Score row */}
        <div className="mb-3 flex flex-wrap gap-2">
          <ScoreBadge label="Business" score={scores.business} />
          <ScoreBadge label="Financial" score={scores.financial} />
          <ScoreBadge label="Valuation" score={scores.valuation} />
          <ScoreBadge label="Growth" score={scores.growth} />
          <ScoreBadge label="Risk" score={scores.risk} />
        </div>

        {/* Valuation row */}
        {(intrinsic !== "—" || mos !== "—") ? (
          <div className="flex flex-wrap gap-6 border-t border-[var(--border)] pt-2.5">
            {intrinsic !== "—" ? (
              <div className="flex flex-col gap-0.5">
                <span className="text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                  Intrinsic Value
                </span>
                <span className="font-mono text-xs font-semibold text-[var(--accent)]">
                  {intrinsic}
                </span>
              </div>
            ) : null}
            {mos !== "—" ? (
              <div className="flex flex-col gap-0.5">
                <span className="text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                  Margin of Safety
                </span>
                <span className="font-mono text-xs font-semibold text-[var(--accent)]">
                  {mos}
                </span>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {/* ── Peer input + run ─────────────────────────────────────── */}
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
          Comparison Report — Add Peers (up to {MAX_PEERS})
        </p>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="e.g. INFY, WIPRO, HCLTECH"
            aria-label="Peer tickers for comparison report"
            className="flex-1 rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 font-mono text-xs text-[var(--fg)] placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:outline-none"
          />
          <button
            type="button"
            onClick={() => compareMutation.mutate()}
            disabled={compareMutation.isPending || peerTickers.length === 0}
            className="rounded border border-[var(--accent)]/50 bg-[var(--accent)]/10 px-3 py-1.5 text-xs font-semibold text-[var(--accent)] transition-colors hover:bg-[var(--accent)]/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {compareMutation.isPending ? "Generating Report…" : "Generate Report"}
          </button>
        </div>
        {peerTickers.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1">
            {peerTickers.map((t) => (
              <span
                key={t}
                className="rounded border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 font-mono text-[10px] text-[var(--fg)]"
              >
                {t}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      {/* ── Idle state ───────────────────────────────────────────── */}
      {!compareMutation.isPending && !compareMutation.isError && !report ? (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-6 text-center">
          <p className="text-xs text-[var(--muted)]">
            Enter peer tickers above and click{" "}
            <span className="font-semibold text-[var(--accent)]">Generate Report</span> to produce a
            structured valuation · quality · growth · risk comparison.
          </p>
        </div>
      ) : null}

      {/* ── Error ────────────────────────────────────────────────── */}
      {compareMutation.isError ? (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3">
          <p className="text-xs text-red-400">{describeError(compareMutation.error)}</p>
        </div>
      ) : null}

      {/* ── Loading skeleton ─────────────────────────────────────── */}
      {compareMutation.isPending ? (
        <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-4">
          <div className="h-3 w-2/3 animate-pulse rounded bg-[var(--border)]" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-[var(--border)]" />
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="h-20 animate-pulse rounded bg-[var(--border)]" />
            <div className="h-20 animate-pulse rounded bg-[var(--border)]" />
            <div className="h-20 animate-pulse rounded bg-[var(--border)]" />
            <div className="h-20 animate-pulse rounded bg-[var(--border)]" />
          </div>
        </div>
      ) : null}

      {/* ── Comparison report ────────────────────────────────────── */}
      {report ? (
        <div className="space-y-4">

          {/* Report header */}
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                Comparison Report · /api/v1/compare
              </span>
              {report.included_symbols.length > 0 ? (
                <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-emerald-400">
                  {report.included_symbols.length} symbols
                </span>
              ) : null}
            </div>
            <p className="text-xs leading-relaxed text-[var(--fg)]">
              {report.explanation.summary}
            </p>
            {report.explanation.detail ? (
              <p className="mt-1.5 text-[11px] leading-relaxed text-[var(--muted)]">
                {report.explanation.detail}
              </p>
            ) : null}

            {/* Included / excluded symbols */}
            {(report.included_symbols.length > 0 || report.excluded_symbols.length > 0) ? (
              <div className="mt-3 flex flex-wrap gap-4 border-t border-[var(--border)] pt-2.5 text-[10px]">
                {report.included_symbols.length > 0 ? (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[var(--muted)]">Compared:</span>
                    <div className="flex flex-wrap gap-1">
                      {report.included_symbols.map((sym) => (
                        <span
                          key={sym}
                          className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 font-mono font-semibold text-emerald-400"
                        >
                          {sym}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
                {report.excluded_symbols.length > 0 ? (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[var(--muted)]">Excluded:</span>
                    <div className="flex flex-wrap gap-1">
                      {report.excluded_symbols.map((sym) => (
                        <span
                          key={sym}
                          className="rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 font-mono font-semibold text-amber-400"
                        >
                          {sym}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          {/* Dimension breakdown grid */}
          {report.dimension_results.length > 0 ? (
            <div>
              <p className="mb-2 text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                Dimension Analysis
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                {report.dimension_results.map((dim) => (
                  <DimensionCard key={dim.dimension} dim={dim} />
                ))}
              </div>
            </div>
          ) : null}

          {/* Limitations */}
          {report.limitations.length > 0 ? (
            <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3">
              <p className="mb-1.5 text-[9px] font-semibold uppercase tracking-widest text-amber-400">
                Report Limitations
              </p>
              <ul className="space-y-1">
                {report.limitations.map((lim, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-[10px] text-[var(--muted)]">
                    <span className="mt-0.5 shrink-0 text-amber-400">·</span>
                    <span>{lim.message}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
