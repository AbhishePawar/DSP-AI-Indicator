"use client";

/**
 * Figma `Dashboard.tsx` — market bar · Watchlist (1fr) · Recent Research +
 * DSP Signals (300px).
 *
 * Data (all server-authored, thin client):
 * - GET /api/v1/market/indices          → market bar (value · change · sparkline)
 * - GET /api/v1/workspace/dashboard     → watchlist (quote + DSP rating joined
 *                                          server-side) · recent research · signals
 * - GET /api/v1/market/quote            → quotes for session-derived symbols
 *                                          (analysed / held) not yet on the watchlist
 */

import Link from "next/link";
import { useQueries, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api/client";
import { loadRecentAnalyses } from "@/lib/analysis/recentAnalyses";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  listArchivedSessions,
  type ArchivedResearchSession,
} from "@/lib/copilot/sessionArchive";
import {
  buildWatchlistSymbols,
  MARKET_BAR_PLACEHOLDERS,
  mapMarketIndices,
  mapRecentResearch,
  mapServerRecentResearch,
  mapServerWatchlistRow,
  mapSignals,
  mapWatchlistRow,
  relativeTime,
  type RecentResearchRow,
  type WatchlistRow,
} from "@/lib/figma-pages/dashboardView";
import { analysisHref } from "@/lib/figma-pages/researchHubView";
import { usePortfolio } from "@/lib/portfolio/PortfolioProvider";
import {
  ChangeText,
  DataCell,
  FigmaPage,
  Panel,
  PanelEmpty,
  RatingPill,
  Sparkline,
  TH_CLASS,
  TD_CLASS,
} from "./PagePrimitives";

function monthLabel(date: Date): string {
  return date.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

export function DashboardOverview() {
  const { session, status } = useAuth();
  const token = session?.accessToken;
  const { holdings } = usePortfolio();

  // Session stores are browser-only; read after mount to keep SSR honest.
  const [sessions, setSessions] = useState<ArchivedResearchSession[]>([]);
  const [localRecent, setLocalRecent] = useState<RecentResearchRow[]>([]);
  useEffect(() => {
    setSessions(listArchivedSessions());
    setLocalRecent(mapRecentResearch(loadRecentAnalyses()));
  }, []);

  // Market bar — public provider-reported index snapshots.
  const indicesQuery = useQuery({
    queryKey: ["dashboard", "market-indices"],
    queryFn: () => api.marketIndices({ token }),
    retry: false,
    staleTime: 60_000,
  });
  const marketCards = indicesQuery.data
    ? mapMarketIndices(indicesQuery.data)
    : MARKET_BAR_PLACEHOLDERS;

  // Server-owned watchlist · recent research · DSP signals (per user).
  const overviewQuery = useQuery({
    queryKey: ["dashboard", "workspace-overview"],
    queryFn: () => api.workspaceDashboard({ token }),
    enabled: Boolean(token),
    retry: false,
    staleTime: 30_000,
  });
  const overview = overviewQuery.data;

  const serverRows: WatchlistRow[] = useMemo(
    () => (overview?.watchlist ?? []).map(mapServerWatchlistRow),
    [overview],
  );

  // Session-derived symbols (analysed / held) that are not on the server watchlist.
  const derivedSymbols = useMemo(() => {
    const onServer = new Set(serverRows.map((r) => r.symbol));
    return buildWatchlistSymbols(sessions, holdings).filter((s) => !onServer.has(s.symbol));
  }, [sessions, holdings, serverRows]);

  const quoteQueries = useQueries({
    queries: derivedSymbols.map((s) => ({
      queryKey: ["dashboard", "quote", s.symbol, s.exchange ?? ""],
      queryFn: () => api.marketQuote(s.symbol, { token, exchange: s.exchange }),
      enabled: Boolean(token),
      retry: false,
      staleTime: 60_000,
    })),
  });

  const derivedRows: WatchlistRow[] = derivedSymbols.map((s, i) => {
    const q = quoteQueries[i];
    const quoteStatus: WatchlistRow["quoteStatus"] = !token
      ? "unauthenticated"
      : q?.isPending
        ? "loading"
        : q?.isError || !q?.data
          ? "unavailable"
          : "available";
    return mapWatchlistRow(s, q?.data ?? null, quoteStatus, sessions);
  });

  const rows: WatchlistRow[] = [...serverRows, ...derivedRows];

  const recent: RecentResearchRow[] =
    overview && overview.recent_research.length > 0
      ? mapServerRecentResearch(overview.recent_research)
      : localRecent;
  const signals = mapSignals(overview?.signals);

  const subtitle = `Overview · ${monthLabel(new Date())}`;

  return (
    <FigmaPage title="Dashboard" subtitle={subtitle}>
      {/* Market bar */}
      <section aria-label="Market overview" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {marketCards.map((m) => (
          <div
            key={m.label}
            className="rounded-[10px] border border-[var(--border)] bg-[var(--card)] px-4 py-3.5"
          >
            <p className="mb-1.5 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.06em] text-[var(--muted)]">
              {m.label}
            </p>
            {m.available ? (
              <>
                <p className="font-[family-name:var(--font-mono)] text-lg font-semibold text-[var(--fg)]">
                  {m.value}
                </p>
                <p
                  className="mt-0.5 font-[family-name:var(--font-mono)] text-xs"
                  style={{
                    color:
                      m.direction === "down"
                        ? "var(--c-risk)"
                        : m.direction === "up"
                          ? "var(--c-profit)"
                          : "var(--muted)",
                  }}
                >
                  {m.change ?? "—"}
                </p>
              </>
            ) : (
              <>
                <p className="text-sm text-[var(--muted)]">
                  {indicesQuery.isPending ? "Loading…" : m.value}
                </p>
                <p className="mt-0.5 font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]">
                  {indicesQuery.isPending ? "GET /api/v1/market/indices" : m.note}
                </p>
              </>
            )}
            <div className="mt-2 h-9">
              <Sparkline
                values={m.sparkline}
                stroke={m.direction === "down" ? "var(--c-risk)" : "var(--c-profit)"}
                label={m.available ? `${m.label} recent closes` : undefined}
              />
            </div>
          </div>
        ))}
      </section>

      {/* Main grid */}
      <div className="grid gap-5 lg:grid-cols-[1fr_300px]">
        <Panel
          title="Watchlist"
          action={
            <Link
              href="/companies"
              className="text-xs text-[var(--c-dsp)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              + Add
            </Link>
          }
        >
          {rows.length === 0 ? (
            <PanelEmpty
              title={overviewQuery.isPending && token ? "Loading watchlist…" : "No companies on your watchlist yet."}
              description="Companies you add, analyse or hold appear here with authenticated quotes and their DSP rating. Nothing is pre-seeded."
              action={
                <Link href="/companies" className="text-xs text-[var(--c-dsp)] hover:underline">
                  Browse companies →
                </Link>
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    {["Symbol", "Price", "Change", "DSP Rating", ""].map((h, i) => (
                      <th key={`${h}-${i}`} scope="col" className={TH_CLASS}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr
                      key={row.symbol}
                      className={i < rows.length - 1 ? "border-b border-[var(--border)]" : undefined}
                    >
                      <td className={TD_CLASS}>
                        <div className="font-[family-name:var(--font-mono)] text-[13px] font-semibold">
                          {row.symbol}
                        </div>
                        <div className="text-[11px] text-[var(--muted)]">
                          {row.name ??
                            (row.origin === "portfolio"
                              ? "Portfolio holding"
                              : row.origin === "research"
                                ? "Analysed"
                                : "Watchlist")}
                        </div>
                      </td>
                      <DataCell>
                        {row.quoteStatus === "loading" ? (
                          <span className="text-[var(--muted)]">Loading…</span>
                        ) : row.quoteStatus === "unauthenticated" ? (
                          <span className="text-xs text-[var(--muted)]">Sign in for quotes</span>
                        ) : (
                          <span className={row.price === "Data unavailable." ? "text-xs text-[var(--muted)]" : undefined}>
                            {row.price}
                          </span>
                        )}
                      </DataCell>
                      <td className={TD_CLASS}>
                        {row.quoteStatus === "available" ? (
                          <ChangeText text={row.change} direction={row.direction} />
                        ) : (
                          <span className="text-xs text-[var(--muted)]">—</span>
                        )}
                      </td>
                      <td className={TD_CLASS}>
                        <RatingPill value={row.rating} />
                      </td>
                      <td className={TD_CLASS}>
                        <Link
                          href={analysisHref(row.symbol, row.exchange)}
                          className="inline-flex min-h-8 items-center rounded-md border border-[color-mix(in_srgb,var(--c-dsp)_30%,transparent)] px-2.5 text-[11px] text-[var(--c-dsp)] hover:bg-[color-mix(in_srgb,var(--c-dsp)_8%,transparent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                        >
                          Research →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="border-t border-[var(--border)] px-5 py-2 font-[family-name:var(--font-mono)] text-[10px] text-[var(--muted)]">
            Price and change are provider-reported. DSP Rating is the server-recorded business
            quality grade from the latest /api/v1/analyse for that company.
          </p>
        </Panel>

        <div className="flex flex-col gap-4">
          <Panel title="Recent Research">
            {recent.length === 0 ? (
              <PanelEmpty
                title="No research yet."
                description={
                  status === "authenticated"
                    ? "Run a company analysis to see it here."
                    : "Sign in and run a company analysis to see it here."
                }
              />
            ) : (
              <ul className="m-0 list-none p-0">
                {recent.map((r, i) => (
                  <li
                    key={`${r.symbol}-${r.analysedAt}`}
                    className={i < recent.length - 1 ? "border-b border-[var(--border)]" : undefined}
                  >
                    <Link
                      href={analysisHref(r.symbol)}
                      className="block px-4 py-3 hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)]"
                    >
                      <div className="mb-1 flex justify-between font-[family-name:var(--font-mono)]">
                        <span className="text-[11px] text-[var(--c-dsp)]">{r.symbol}</span>
                        <span className="text-[10px] text-[var(--muted)]">
                          {relativeTime(r.analysedAt)}
                        </span>
                      </div>
                      <div className="text-xs leading-snug text-[var(--fg)]">
                        {r.company} · {r.recommendation}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="DSP Signals">
            {signals.length === 0 ? (
              <PanelEmpty
                description={
                  !token
                    ? "Sign in to see rating changes and risk flags across covered companies."
                    : overviewQuery.isPending
                      ? "Loading signals…"
                      : "No signals yet. Signals appear when a company's DSP rating, risk score or margin of safety changes between analyses."
                }
              />
            ) : (
              <ul className="m-0 list-none p-0">
                {signals.map((s, i) => (
                  <li
                    key={s.id}
                    className={`flex items-center gap-3 px-4 py-3 ${i < signals.length - 1 ? "border-b border-[var(--border)]" : ""}`}
                  >
                    <span
                      className="h-1.5 w-1.5 shrink-0 rounded-full"
                      style={{ background: s.color }}
                      aria-hidden="true"
                    />
                    <div>
                      <div className="mb-0.5 text-xs text-[var(--fg)]">
                        <Link href={analysisHref(s.symbol)} className="hover:underline">
                          {s.symbol}
                        </Link>{" "}
                        — {s.label}
                      </div>
                      {s.from && s.to ? (
                        <div className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)]">
                          {s.from} → {s.to}
                        </div>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>
    </FigmaPage>
  );
}
