"use client";

/**
 * Figma `InstitutionalResearch.tsx` — 4 summary stats · Quality Screener
 * (1fr) with rating filters · Coverage Growth + Rating Distribution (280px).
 *
 * Data: `GET /api/v1/coverage/institutional` — server-authored coverage
 * registry aggregates (counts, latest-per-symbol screener rows with server
 * P/E · ROE · revenue growth, monthly coverage growth, rating distribution).
 * Nothing is screened, ranked or computed in the browser.
 */

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { analysisHref } from "@/lib/figma-pages/researchHubView";
import {
  DataCell,
  FigmaPage,
  MiniBarChart,
  MiniLineChart,
  Panel,
  PanelEmpty,
  PillButton,
  RatingPill,
  StatCard,
  TH_CLASS,
  TD_CLASS,
} from "./PagePrimitives";

const FILTERS = ["All", "A+", "A", "B+", "B"] as const;
const HEADERS = ["Symbol", "DSP Rating", "Sector", "P/E", "ROE", "Rev Growth"];
const UNAVAILABLE = "Data unavailable.";

function fmtMultiple(v: number | null): string {
  return typeof v === "number" && Number.isFinite(v) ? `${v.toLocaleString(undefined, { maximumFractionDigits: 1 })}×` : UNAVAILABLE;
}
function fmtPct(v: number | null, signed = false): string {
  if (typeof v !== "number" || !Number.isFinite(v)) return UNAVAILABLE;
  const pct = v * 100;
  return `${signed && pct > 0 ? "+" : ""}${pct.toLocaleString(undefined, { maximumFractionDigits: 1 })}%`;
}
function fmtCount(v: number | undefined): string {
  return typeof v === "number" ? v.toLocaleString() : UNAVAILABLE;
}
function fmtLastUpdated(iso: string | null | undefined): string {
  if (!iso) return UNAVAILABLE;
  const d = new Date(iso);
  if (!Number.isFinite(d.getTime())) return UNAVAILABLE;
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function InstitutionalResearch() {
  const { session } = useAuth();
  const token = session?.accessToken;
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("All");

  const query = useQuery({
    queryKey: ["coverage", "institutional", filter],
    queryFn: () => api.coverageInstitutional({ token, rating: filter === "All" ? null : filter, months: 6 }),
    enabled: Boolean(token),
    retry: false,
    staleTime: 60_000,
  });
  const data = query.data;
  const loading = Boolean(token) && query.isPending;
  const stats = data?.stats;
  const rows = data?.screener ?? [];

  const statCards = [
    { label: "Securities Covered", value: fmtCount(stats?.securities_covered), note: "Distinct companies with a server analysis" },
    { label: "DSP Rated", value: fmtCount(stats?.dsp_rated), note: "Latest analysis produced a business-quality grade" },
    { label: "A / A+ Rated", value: fmtCount(stats?.a_rated), note: stats ? `${stats.a_plus_rated.toLocaleString()} rated A+` : undefined },
    { label: "Last Updated", value: fmtLastUpdated(stats?.last_updated), note: "Most recent recorded analysis" },
  ];

  const growth = data?.coverage_growth ?? [];
  const distribution = (data?.rating_distribution ?? []).filter((d) => d.rating !== "F" || d.count > 0);

  return (
    <FigmaPage title="Institutional Research" subtitle="Screener · Coverage · Bulk analysis">
      <section aria-label="Coverage summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {statCards.map((s) => (
          <StatCard key={s.label} label={s.label} value={loading ? "Loading…" : s.value} note={s.note} />
        ))}
      </section>

      <div className="grid gap-5 lg:grid-cols-[1fr_280px]">
        <Panel
          title="Quality Screener"
          action={
            <div className="flex gap-1.5" role="group" aria-label="Filter by DSP rating">
              {FILTERS.map((f) => (
                <PillButton key={f} active={filter === f} onClick={() => setFilter(f)}>
                  {f}
                </PillButton>
              ))}
            </div>
          }
        >
          {!token ? (
            <PanelEmpty title="Sign in to use the screener." description="Coverage is served per account from /api/v1/coverage/institutional." />
          ) : loading ? (
            <PanelEmpty title="Loading coverage…" description="GET /api/v1/coverage/institutional" />
          ) : query.isError ? (
            <PanelEmpty title={UNAVAILABLE} description="The coverage service did not respond. Nothing is estimated in the browser." />
          ) : rows.length === 0 ? (
            <PanelEmpty
              title={filter === "All" ? UNAVAILABLE : "No companies match this rating."}
              description={
                filter === "All"
                  ? "No securities have been analysed yet. Every /api/v1/analyse run is recorded into coverage with its server P/E, ROE and revenue growth."
                  : undefined
              }
              action={
                filter === "All" ? (
                  <Link href="/companies" className="text-xs text-[var(--c-dsp)] hover:underline">
                    Browse companies →
                  </Link>
                ) : null
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    {HEADERS.map((h) => (
                      <th key={h} scope="col" className={TH_CLASS}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={r.symbol} className={i < rows.length - 1 ? "border-b border-[var(--border)]" : undefined}>
                      <td className={TD_CLASS}>
                        <Link
                          href={analysisHref(r.symbol)}
                          className="font-[family-name:var(--font-mono)] text-[13px] font-semibold hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                        >
                          {r.symbol}
                        </Link>
                        {r.company_name ? (
                          <div className="text-[11px] text-[var(--muted)]">{r.company_name}</div>
                        ) : null}
                      </td>
                      <td className={TD_CLASS}>
                        <RatingPill value={r.rating ?? "—"} />
                      </td>
                      <td className={`${TD_CLASS} text-xs text-[var(--muted)]`}>{r.sector ?? UNAVAILABLE}</td>
                      <DataCell className={typeof r.pe === "number" ? undefined : "text-xs text-[var(--muted)]"}>
                        {fmtMultiple(r.pe)}
                      </DataCell>
                      <DataCell className={typeof r.roe === "number" ? "text-[var(--c-profit)]" : "text-xs text-[var(--muted)]"}>
                        {fmtPct(r.roe)}
                      </DataCell>
                      <DataCell className={typeof r.revenue_growth === "number" ? "text-[var(--c-revenue)]" : "text-xs text-[var(--muted)]"}>
                        {fmtPct(r.revenue_growth, true)}
                      </DataCell>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="border-t border-[var(--border)] px-5 py-2 font-[family-name:var(--font-mono)] text-[10px] text-[var(--muted)]">
            Rows are the latest server analysis per company. Rating is the business-quality grade;
            P/E (price ÷ diluted EPS), ROE and revenue growth are server-calculated from authenticated
            statements and quotes. Nothing is screened or ranked client-side.
          </p>
        </Panel>

        <div className="flex flex-col gap-4">
          <Panel title="Coverage Growth" padded>
            <MiniLineChart
              height={160}
              label={
                growth.length
                  ? `Coverage growth: ${growth.map((g) => `${g.month} covered ${g.covered}, rated ${g.rated}`).join("; ")}`
                  : "Coverage growth"
              }
              categories={growth.map((g) => g.month)}
              series={[
                { name: "Covered", values: growth.map((g) => g.covered), stroke: "var(--c-revenue)" },
                { name: "Rated", values: growth.map((g) => g.rated), stroke: "var(--c-dsp)" },
              ]}
            />
            <p className="mt-2 flex gap-3 text-[10px] text-[var(--muted)]">
              <span className="flex items-center gap-1">
                <span className="inline-block h-1.5 w-3 rounded" style={{ background: "var(--c-revenue)" }} aria-hidden="true" />
                Covered
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block h-1.5 w-3 rounded" style={{ background: "var(--c-dsp)" }} aria-hidden="true" />
                Rated
              </span>
              <span className="ml-auto">Cumulative distinct companies by month end.</span>
            </p>
          </Panel>
          <Panel title="Rating Distribution" padded>
            <MiniBarChart
              height={130}
              label={
                distribution.length
                  ? `Rating distribution: ${distribution.map((d) => `${d.rating} ${d.count}`).join(", ")}`
                  : "Rating distribution"
              }
              data={distribution.map((d) => ({ label: d.rating, value: d.count }))}
            />
            <p className="mt-2 text-[10px] text-[var(--muted)]">
              Latest grade per covered company (A+ ≥ 90 · A ≥ 80 · B+ ≥ 70 · B ≥ 60 · C ≥ 50 · D ≥ 40).
            </p>
          </Panel>
        </div>
      </div>
    </FigmaPage>
  );
}
