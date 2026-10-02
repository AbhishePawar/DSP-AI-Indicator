"use client";

/**
 * Research Intelligence — Figma Make `ResearchIntelligence.tsx` (signal feed ·
 * type filter chips · 240px sidebar with sector filter + Today's Summary).
 * Signals come from /api/v1 coverageSignals; the measurement block uses the
 * research-intelligence performance API. Missing values render
 * "Data unavailable." — the Figma demo signals are never copied (CV-001).
 */

import { useMemo, useState } from "react";
import Link from "next/link";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { ErrorState } from "@/components/ds";
import { FigmaPage } from "@/components/pages/PagePrimitives";
import { api } from "@/lib/api/client";
import { readStoredSession } from "@/lib/auth/sessionStore";
import { ApiClientError } from "@/lib/api/types";
import type { CoverageSignal } from "@/lib/api/workspaceTypes";
import { displayMetric } from "@/lib/research-intelligence";
import { analysisPath } from "@/lib/securities/identity";

type SignalType = CoverageSignal["type"];

const TYPE_META: Record<SignalType, { label: string; color: string }> = {
  upgrade: { label: "Rating Change", color: "var(--c-profit)" },
  downgrade: { label: "Rating Change", color: "var(--c-risk)" },
  risk: { label: "Risk Alert", color: "var(--c-risk)" },
  valuation: { label: "Valuation Signal", color: "var(--c-valuation)" },
};

const TYPE_FILTERS: Array<{ id: string; label: string; types: SignalType[] | null }> = [
  { id: "all", label: "All Types", types: null },
  { id: "rating", label: "Rating Change", types: ["upgrade", "downgrade"] },
  { id: "risk", label: "Risk Alert", types: ["risk"] },
  { id: "valuation", label: "Valuation Signal", types: ["valuation"] },
];

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "";
  const minutes = Math.round((Date.now() - then) / 60_000);
  if (minutes < 60) return `${Math.max(minutes, 0)} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? "Yesterday" : `${days} days ago`;
}

export function FigmaSignalFeed() {
  const [sector, setSector] = useState("All Sectors");
  const [typeFilter, setTypeFilter] = useState("all");

  const query = useQuery({
    queryKey: ["coverage-signals", sector],
    queryFn: () =>
      api.coverageSignals({
        token: readStoredSession()?.accessToken ?? null,
        limit: 50,
        sector: sector === "All Sectors" ? null : sector,
      }),
    placeholderData: keepPreviousData,
  });

  const performance = useQuery({
    queryKey: ["ri-performance", 12],
    queryFn: async () => {
      const res = await api.researchIntelligencePerformance(
        { window_months: 12 },
        { token: readStoredSession()?.accessToken ?? null },
      );
      return res.dashboard ?? null;
    },
    retry: 1,
  });

  const sectors = useMemo(() => {
    const fromApi = query.data?.sectors?.filter(Boolean) ?? [];
    if (fromApi.length > 0) return ["All Sectors", ...fromApi];
    const found = new Set<string>();
    for (const signal of query.data?.signals ?? []) {
      if (signal.sector) found.add(signal.sector);
    }
    return ["All Sectors", ...found];
  }, [query.data?.sectors, query.data?.signals]);

  const activeTypes = TYPE_FILTERS.find((f) => f.id === typeFilter)?.types ?? null;
  const signals = (query.data?.signals ?? []).filter((signal) => {
    if (activeTypes && !activeTypes.includes(signal.type)) return false;
    if (sector !== "All Sectors" && signal.sector !== sector) return false;
    return true;
  });
  const today = query.data?.today;
  const dashboard = performance.data as Record<string, unknown> | null | undefined;

  return (
    <FigmaPage
      title="Research Intelligence"
      subtitle="DSP signals · Market insights · Rating changes"
    >
      <div className="grid grid-cols-1 overflow-hidden rounded-[var(--card-radius)] border border-[var(--border)] bg-[var(--bg)] lg:grid-cols-[minmax(0,1fr)_240px]">
        <div className="px-5 py-6 sm:px-7">
          <div className="mb-5 flex flex-wrap gap-2" role="group" aria-label="Filter by signal type">
            {TYPE_FILTERS.map((filter) => {
              const active = filter.id === typeFilter;
              return (
                <button
                  key={filter.id}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setTypeFilter(filter.id)}
                  className={`min-h-11 rounded-[20px] border px-3 font-mono text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                    active
                      ? "border-[var(--border)] bg-[var(--surface-2)] text-[var(--fg)]"
                      : "border-[var(--border)] text-[var(--muted)]"
                  }`}
                >
                  {filter.label}
                </button>
              );
            })}
          </div>

          {query.isLoading ? (
            <p className="text-sm text-[var(--muted)]" role="status">
              Loading signals…
            </p>
          ) : null}
          {query.isError ? (
            <ErrorState
              title="Signals unavailable"
              description={
                query.error instanceof ApiClientError
                  ? query.error.message
                  : "The coverage service did not respond."
              }
            />
          ) : null}
          {!query.isLoading && !query.isError && signals.length === 0 ? (
            <p className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--muted)]">
              Data unavailable.
            </p>
          ) : null}

          <ul className="flex flex-col gap-3">
            {signals.map((signal) => {
              const meta = TYPE_META[signal.type] ?? {
                label: signal.label,
                color: "var(--muted)",
              };
              const href = signal.symbol ? analysisPath({ ticker: signal.symbol }) : null;
              return (
                <li
                  key={signal.signal_id}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-5 py-4"
                  style={{ borderLeft: `3px solid ${meta.color}` }}
                >
                  <div className="mb-2.5 flex items-start justify-between gap-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className="rounded-md px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.07em]"
                        style={{
                          color: meta.color,
                          background: `color-mix(in srgb, ${meta.color} 10%, transparent)`,
                        }}
                      >
                        {meta.label}
                      </span>
                      <span className="font-mono text-sm font-semibold text-[var(--fg)]">
                        {signal.symbol}
                      </span>
                      {signal.company_name ? (
                        <span className="text-xs text-[var(--muted)]">{signal.company_name}</span>
                      ) : null}
                    </div>
                    <time
                      dateTime={signal.timestamp}
                      className="shrink-0 font-mono text-[11px] text-[var(--muted)]"
                    >
                      {relativeTime(signal.timestamp)}
                    </time>
                  </div>
                  <p className="text-[13px] leading-[1.65] text-[var(--muted)]">{signal.text}</p>
                  {signal.from_rating || signal.label ? (
                    <p className="mt-1 font-mono text-[11px] text-[var(--muted)]">{signal.label}</p>
                  ) : null}
                  {href ? (
                    <div className="mt-3">
                      <Link
                        href={href}
                        className="inline-flex min-h-11 items-center rounded-md border border-[color-mix(in_srgb,var(--c-dsp)_20%,transparent)] bg-[color-mix(in_srgb,var(--c-dsp)_10%,transparent)] px-3 text-[11px] text-[var(--c-dsp)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                      >
                        Research {signal.symbol} →
                      </Link>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>

        <aside
          aria-label="Signal filters and summary"
          className="border-t border-[var(--border)] bg-[var(--surface)] px-4 py-5 lg:border-l lg:border-t-0"
        >
          <p className="mb-3.5 font-mono text-[11px] uppercase tracking-[0.07em] text-[var(--muted)]">
            Filter by Sector
          </p>
          <div role="group" aria-label="Filter by sector" className="flex flex-col">
            {sectors.map((item) => {
              const active = sector === item;
              return (
                <button
                  key={item}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setSector(item)}
                  className={`mb-0.5 min-h-11 rounded-lg px-2.5 text-left text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                    active ? "bg-[var(--surface-2)] text-[var(--fg)]" : "text-[var(--muted)]"
                  }`}
                >
                  {item}
                </button>
              );
            })}
          </div>

          <div className="mt-6 border-t border-[var(--border)] pt-5">
            <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.07em] text-[var(--muted)]">
              Today&apos;s Summary
            </p>
            <SummaryRow label="New signals" value={today?.new_signals} loading={query.isLoading} />
            <SummaryRow label="Upgrades" value={today?.upgrades} loading={query.isLoading} />
            <SummaryRow label="Downgrades" value={today?.downgrades} loading={query.isLoading} />
            <SummaryRow label="Risk flags" value={today?.risk_flags} loading={query.isLoading} />
            {today?.as_of ? (
              <p className="mt-2 font-mono text-[10px] text-[var(--muted)]">
                As of {new Date(today.as_of).toLocaleString()}
              </p>
            ) : null}
          </div>

          <div className="mt-6 border-t border-[var(--border)] pt-5">
            <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.07em] text-[var(--muted)]">
              Measurement · 12m
            </p>
            <SummaryRow
              label="Overall accuracy"
              value={dashboard?.overall_accuracy}
              loading={performance.isLoading}
              format
            />
            <SummaryRow
              label="Recommendation accuracy"
              value={dashboard?.recommendation_accuracy}
              loading={performance.isLoading}
              format
            />
            <SummaryRow
              label="IV error"
              value={dashboard?.iv_error}
              loading={performance.isLoading}
              format
            />
            <SummaryRow
              label="Avg MoS"
              value={dashboard?.avg_mos}
              loading={performance.isLoading}
              format
            />
          </div>
        </aside>
      </div>
    </FigmaPage>
  );
}

function SummaryRow({
  label,
  value,
  loading,
  format = false,
}: {
  label: string;
  value: unknown;
  loading: boolean;
  format?: boolean;
}) {
  const text = loading
    ? "…"
    : format
      ? displayMetric(value)
      : value == null
        ? "Data unavailable."
        : String(value);
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] py-1.5">
      <span className="text-xs text-[var(--muted)]">{label}</span>
      <span className="text-right font-mono text-xs font-semibold text-[var(--fg)]">{text}</span>
    </div>
  );
}
