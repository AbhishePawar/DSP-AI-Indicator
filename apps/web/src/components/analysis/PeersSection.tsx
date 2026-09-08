"use client";

/**
 * PeersSection — compact Indian equity-research peer-comparison block.
 *
 * Data sources (all existing, no mock data):
 *   - view.snapshot        → primary CMP, marketCap, 52W range (fallback labels)
 *   - view.dashboard       → primary businessScore, financialScore, valuationScore,
 *                            growthScore, riskScore
 *   - view.valuation       → primary intrinsicValueRange, marginOfSafety
 *   - useMarketQuotes(tickers) → live price, marketCap, dailyChange for all peers
 *                                via /api/v1/market/quote (existing endpoint)
 *   - api.compare()        → POST /compare qualitative comparison engine
 *
 * Rendering rules:
 *   - Available fields: show value with colour-coded accent
 *   - Unavailable fields: show "—" in muted colour (never invent values)
 *   - Terminal aesthetic: monospace values, compact rows, dense grid
 *   - Primary ticker row is always shown first, highlighted
 */

import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { useMarketQuotes } from "@/providers/MarketDataProvider";
import { formatMarketPrice, formatMarketCap } from "@/lib/market";
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

function changeColour(change: number | null): string {
  if (change == null) return "text-[var(--muted)]";
  if (change > 0) return "text-emerald-400";
  if (change < 0) return "text-red-400";
  return "text-[var(--muted)]";
}

function describeError(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status === 401) return "Sign in required for peer comparison.";
    return error.message || `API error (${error.status})`;
  }
  if (error instanceof Error) return error.message;
  return "Data unavailable.";
}

function defaultRange() {
  const end = new Date();
  const start = new Date();
  start.setFullYear(end.getFullYear() - 1);
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { start: iso(start), end: iso(end) };
}

const MAX_PEERS = 5;

/* ─── Score pill ─────────────────────────────────────────────────── */

function ScorePill({ label, score }: { label: string; score: string }) {
  return (
    <span className="inline-flex flex-col items-center gap-0.5">
      <span className={["font-mono text-xs font-bold leading-none", scoreColour(score)].join(" ")}>
        {score}
      </span>
      <span className="text-[8px] uppercase tracking-widest text-[var(--muted)]">{label}</span>
    </span>
  );
}

/* ─── Comparison result types ────────────────────────────────────── */

type ComparisonResultPayload = {
  status: string;
  refused: boolean;
  report: {
    explanation: { summary: string; detail: string | null };
    included_symbols: string[];
    excluded_symbols: string[];
    dimension_results: { dimension: string; observations: { code: string; text: string }[] }[];
    limitations: { code: string; message: string }[];
  };
};

/* ─── Main component ─────────────────────────────────────────────── */

export function PeersSection({
  view,
  ticker,
}: {
  view: AnalysisWorkspaceView;
  ticker: string;
}) {
  const { session } = useAuth();
  const token = session?.accessToken ?? null;
  const [draft, setDraft] = useState("");

  /* Parse peer tickers from input */
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

  /* All tickers including primary */
  const allTickers = useMemo(
    () => [ticker.toUpperCase(), ...peerTickers],
    [ticker, peerTickers],
  );

  /* Live market quotes for all tickers */
  const { quotes, status: quotesStatus, refresh: refreshQuotes, isRefreshing } = useMarketQuotes(
    peerTickers.length > 0 ? allTickers : [],
  );

  /* Primary scores from view.dashboard */
  const dash = view.dashboard;
  const primaryScores = {
    business: dv(dash.businessScore),
    financial: dv(dash.financialScore),
    valuation: dv(dash.valuationScore),
    growth: dv(dash.growthScore),
    risk: dv(dash.riskScore),
  };

  /* Primary price/cap from snapshot (fallback when no live quote) */
  const snap = view.snapshot;
  const primaryQuote = quotes[ticker.toUpperCase()] ?? null;
  const primaryPrice = primaryQuote
    ? formatMarketPrice(primaryQuote.currentPrice)
    : dv(snap.currentMarketPrice);
  const primaryCap = primaryQuote?.marketCap != null
    ? formatMarketCap(primaryQuote.marketCap)
    : dv(snap.marketCap);
  const primaryChange = primaryQuote
    ? primaryQuote.dailyChangePercent
    : null;

  /* Valuation from view */
  const intrinsic = dv(view.valuation.intrinsicValueRange);
  const mos = dv(view.valuation.marginOfSafety);

  /* Qualitative comparison mutation */
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
      if (reportIds.length < 2) throw new Error("Need at least 2 successful analyses for comparison.");
      const compared = await api.compare({ report_ids: reportIds }, { token });
      return (compared.result as ComparisonResultPayload | undefined) ?? null;
    },
  });

  const report = compareMutation.data?.report ?? null;

  return (
    <div className="space-y-4">

      {/* ── Primary stock snapshot row ──────────────────────────── */}
      <div className="rounded-lg border border-[var(--accent)]/30 bg-[var(--accent)]/5 px-4 py-3">
        <div className="mb-2 flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-[var(--accent)]">{ticker.toUpperCase()}</span>
          <span className="rounded bg-[var(--accent)]/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-widest text-[var(--accent)]">
            Primary
          </span>
          {quotesStatus === "loading" || isRefreshing ? (
            <span className="text-[9px] text-[var(--muted)]">Refreshing…</span>
          ) : null}
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-4 lg:grid-cols-7">
          <div className="flex flex-col gap-0.5">
            <span className="text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">CMP</span>
            <span className="font-mono text-sm font-bold text-[var(--fg)]">{primaryPrice}</span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">Day Chg</span>
            <span className={["font-mono text-sm font-semibold", changeColour(primaryChange)].join(" ")}>
              {primaryChange != null ? `${primaryChange >= 0 ? "+" : ""}${primaryChange.toFixed(2)}%` : "—"}
            </span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">Mkt Cap</span>
            <span className="font-mono text-sm font-semibold text-[var(--fg)]">{primaryCap}</span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">Intrinsic</span>
            <span className="font-mono text-sm font-semibold text-[var(--accent)]">{intrinsic}</span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">MoS</span>
            <span className="font-mono text-sm font-semibold text-[var(--accent)]">{mos}</span>
          </div>
          <div className="col-span-2 flex flex-wrap items-center gap-3 sm:col-span-2">
            <ScorePill label="Biz" score={primaryScores.business} />
            <ScorePill label="Fin" score={primaryScores.financial} />
            <ScorePill label="Val" score={primaryScores.valuation} />
            <ScorePill label="Gro" score={primaryScores.growth} />
            <ScorePill label="Risk" score={primaryScores.risk} />
          </div>
        </div>
      </div>

      {/* ── Peer input ──────────────────────────────────────────── */}
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
          Add Peers (up to {MAX_PEERS})
        </p>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={`e.g. INFY, WIPRO, HCLTECH`}
            aria-label="Peer tickers comma-separated"
            className="flex-1 min-h-[40px] rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-2 font-mono text-xs text-[var(--fg)] placeholder:text-[var(--muted)] focus:border-[var(--accent)] focus:outline-none"
          />
          <div className="flex gap-2">
            {peerTickers.length > 0 ? (
              <button
                type="button"
                onClick={() => refreshQuotes()}
                disabled={isRefreshing}
                className="min-h-[40px] rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs text-[var(--muted)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:opacity-50"
              >
                {isRefreshing ? "…" : "↻ Refresh"}
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => compareMutation.mutate()}
              disabled={compareMutation.isPending || peerTickers.length === 0}
              className="min-h-[40px] rounded border border-[var(--accent)]/50 bg-[var(--accent)]/10 px-3 py-2 text-xs font-semibold text-[var(--accent)] transition-colors hover:bg-[var(--accent)]/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {compareMutation.isPending ? "Comparing…" : "Run Comparison"}
            </button>
          </div>
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

      {/* ── Peer market data table ───────────────────────────────── */}
      {peerTickers.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-[var(--border)] -mx-0">
          <table className="w-full min-w-[520px] text-xs">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--surface-2)]">
                <th className="px-3 py-2 text-left font-semibold uppercase tracking-widest text-[var(--muted)]">
                  Ticker
                </th>
                <th className="px-3 py-2 text-right font-semibold uppercase tracking-widest text-[var(--muted)]">
                  CMP
                </th>
                <th className="px-3 py-2 text-right font-semibold uppercase tracking-widest text-[var(--muted)]">
                  Day Chg
                </th>
                <th className="px-3 py-2 text-right font-semibold uppercase tracking-widest text-[var(--muted)]">
                  Mkt Cap
                </th>
                <th className="px-3 py-2 text-right font-semibold uppercase tracking-widest text-[var(--muted)]">
                  52W High
                </th>
                <th className="px-3 py-2 text-right font-semibold uppercase tracking-widest text-[var(--muted)]">
                  52W Low
                </th>
                <th className="px-3 py-2 text-center font-semibold uppercase tracking-widest text-[var(--muted)]">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {peerTickers.map((t) => {
                const q = quotes[t] ?? null;
                const isLoading = quotesStatus === "loading" || isRefreshing;
                return (
                  <tr key={t} className="bg-[var(--surface)] transition-colors hover:bg-[var(--surface-2)]">
                    <td className="px-3 py-2.5">
                      <span className="font-mono font-semibold text-[var(--fg)]">{t}</span>
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono font-semibold text-[var(--fg)]">
                      {isLoading ? (
                        <span className="text-[var(--muted)]">…</span>
                      ) : q ? (
                        formatMarketPrice(q.currentPrice)
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono">
                      {isLoading ? (
                        <span className="text-[var(--muted)]">…</span>
                      ) : q ? (
                        <span className={changeColour(q.dailyChangePercent)}>
                          {q.dailyChangePercent >= 0 ? "+" : ""}
                          {q.dailyChangePercent.toFixed(2)}%
                        </span>
                      ) : (
                        <span className="text-[var(--muted)]">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[var(--fg)]">
                      {isLoading ? (
                        <span className="text-[var(--muted)]">…</span>
                      ) : q?.marketCap != null ? (
                        formatMarketCap(q.marketCap)
                      ) : (
                        <span className="text-[var(--muted)]">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[var(--muted)]">
                      {isLoading ? (
                        "…"
                      ) : q?.week52High != null ? (
                        formatMarketPrice(q.week52High)
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-[var(--muted)]">
                      {isLoading ? (
                        "…"
                      ) : q?.week52Low != null ? (
                        formatMarketPrice(q.week52Low)
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {isLoading ? (
                        <span className="text-[9px] text-[var(--muted)]">Loading</span>
                      ) : q ? (
                        <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-emerald-400">
                          Live
                        </span>
                      ) : (
                        <span className="rounded bg-[var(--surface-2)] px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                          N/A
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-6 text-center text-xs text-[var(--muted)]">
          Enter peer tickers above to load live market data and run qualitative comparison.
        </p>
      )}

      {/* ── Qualitative comparison result ───────────────────────── */}
      {compareMutation.isError ? (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3">
          <p className="text-xs text-red-400">{describeError(compareMutation.error)}</p>
        </div>
      ) : null}

      {compareMutation.isPending ? (
        <div className="space-y-2 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-4">
          <div className="h-3 w-3/4 animate-pulse rounded bg-[var(--border)]" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-[var(--border)]" />
          <div className="h-3 w-2/3 animate-pulse rounded bg-[var(--border)]" />
        </div>
      ) : null}

      {report ? (
        <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-4">
          {/* Summary */}
          <div>
            <p className="mb-1 text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">
              Qualitative Comparison · /api/v1/compare
            </p>
            <p className="text-xs text-[var(--fg)]">{report.explanation.summary}</p>
          </div>

          {/* Included / excluded */}
          {(report.included_symbols.length > 0 || report.excluded_symbols.length > 0) ? (
            <div className="flex flex-wrap gap-4 text-[10px]">
              {report.included_symbols.length > 0 ? (
                <span className="text-[var(--muted)]">
                  Included:{" "}
                  <span className="font-mono font-semibold text-emerald-400">
                    {report.included_symbols.join(", ")}
                  </span>
                </span>
              ) : null}
              {report.excluded_symbols.length > 0 ? (
                <span className="text-[var(--muted)]">
                  Excluded:{" "}
                  <span className="font-mono font-semibold text-amber-400">
                    {report.excluded_symbols.join(", ")}
                  </span>
                </span>
              ) : null}
            </div>
          ) : null}

          {/* Dimension results */}
          {report.dimension_results.length > 0 ? (
            <div className="space-y-2">
              {report.dimension_results.map((dim) => (
                <div
                  key={dim.dimension}
                  className="rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-2"
                >
                  <p className="mb-1.5 text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                    {dim.dimension.replace(/_/g, " ")}
                  </p>
                  <ul className="space-y-0.5">
                    {dim.observations.map((obs, i) => (
                      <li key={i} className="text-[11px] text-[var(--fg)]">
                        {obs.text}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          ) : null}

          {/* Limitations */}
          {report.limitations.length > 0 ? (
            <div className="rounded border border-amber-500/20 bg-amber-500/5 px-3 py-2">
              <p className="mb-1 text-[9px] font-semibold uppercase tracking-widest text-amber-400">
                Limitations
              </p>
              <ul className="space-y-0.5">
                {report.limitations.map((lim, i) => (
                  <li key={i} className="text-[10px] text-[var(--muted)]">
                    {lim.message}
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
