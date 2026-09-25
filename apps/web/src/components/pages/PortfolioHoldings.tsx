"use client";

/**
 * Figma `Portfolio.tsx` — 4 summary cards · Holdings table (1fr) with sort
 * pills · Sector Allocation donut (260px).
 *
 * Data: `GET /api/v1/workspace/portfolio` — per-user holdings joined
 * server-side with authenticated CMP, DSP rating and sector; invested /
 * current value / P&L / return / weight / sector allocation are computed
 * by the backend. Holdings mutations exist on the API but are not exposed
 * here — Figma has no portfolio-management UI.
 */

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  buildPortfolioSummaryCards,
  buildSectorSlices,
  donutSegments,
  mapHoldingRow,
  PORTFOLIO_SORT_KEYS,
  sortHoldings,
  type PortfolioSortKey,
} from "@/lib/figma-pages/portfolioView";
import { analysisHref } from "@/lib/figma-pages/researchHubView";
import {
  ChangeText,
  DataCell,
  FigmaPage,
  Panel,
  PanelEmpty,
  PillButton,
  RatingPill,
  StatCard,
  TH_CLASS,
  TD_CLASS,
} from "./PagePrimitives";

const HEADERS = ["Symbol", "Qty", "Avg Cost", "CMP", "P&L", "Return", "DSP", ""];
const QUERY_KEY = ["workspace", "portfolio"] as const;

export function PortfolioHoldings() {
  const { session } = useAuth();
  const token = session?.accessToken;
  const [sortBy, setSortBy] = useState<PortfolioSortKey>("value");

  const portfolioQuery = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => api.workspacePortfolio({ token }),
    enabled: Boolean(token),
    retry: false,
    staleTime: 30_000,
  });
  const data = portfolioQuery.data;

  const holdings = useMemo(() => data?.holdings ?? [], [data]);
  const sorted = useMemo(() => sortHoldings(holdings, sortBy), [holdings, sortBy]);
  const rows = sorted.map(mapHoldingRow);
  const cards = buildPortfolioSummaryCards(data);
  const slices = buildSectorSlices(data?.sector_allocation);
  const segments = donutSegments(slices);
  const isEmpty = holdings.length === 0;
  const loading = Boolean(token) && portfolioQuery.isPending;

  return (
    <FigmaPage title="Portfolio" subtitle="Holdings · P&L Analysis">
      <section aria-label="Portfolio summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((c) => (
          <StatCard key={c.label} label={c.label} value={c.value} tone={c.tone} note={c.note} />
        ))}
      </section>

      <div className="grid gap-5 lg:grid-cols-[1fr_260px]">
        <Panel
          title={`Holdings (${holdings.length})`}
          action={
            <div className="flex gap-1.5" role="group" aria-label="Sort holdings">
              {PORTFOLIO_SORT_KEYS.map((key) => (
                <PillButton
                  key={key}
                  active={sortBy === key}
                  onClick={() => setSortBy(key)}
                  ariaLabel={`Sort by ${key}`}
                >
                  {key}
                </PillButton>
              ))}
            </div>
          }
        >
          {!token ? (
            <PanelEmpty
              title="Sign in to see your holdings."
              description="Holdings, cost basis and P&L are stored per account on the server."
            />
          ) : loading ? (
            <PanelEmpty title="Loading holdings…" description="GET /api/v1/workspace/portfolio" />
          ) : portfolioQuery.isError ? (
            <PanelEmpty
              title="Data unavailable."
              description="The portfolio service did not respond. Nothing is estimated in the browser."
            />
          ) : isEmpty ? (
            <PanelEmpty
              title="No holdings yet."
              description="Holdings appear here once they are recorded for your account. Demo holdings are never seeded."
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
                    {HEADERS.map((h, i) => (
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
                        <div className="text-[11px] text-[var(--muted)]">{row.sector}</div>
                      </td>
                      <DataCell className="text-xs text-[var(--muted)]">{row.quantity}</DataCell>
                      <DataCell className="text-xs text-[var(--muted)]">{row.averageCost}</DataCell>
                      <DataCell>
                        {row.priced ? (
                          <ChangeText text={row.cmp} direction={null} />
                        ) : (
                          <span className="text-xs text-[var(--muted)]">{row.cmp}</span>
                        )}
                      </DataCell>
                      <DataCell>
                        {row.priced ? (
                          <ChangeText text={row.pnl} direction={row.pnlDirection} />
                        ) : (
                          <span className="text-xs text-[var(--muted)]">{row.pnl}</span>
                        )}
                      </DataCell>
                      <DataCell>
                        {row.priced ? (
                          <ChangeText text={row.returnPct} direction={row.pnlDirection} />
                        ) : (
                          <span className="text-xs text-[var(--muted)]">{row.returnPct}</span>
                        )}
                      </DataCell>
                      <td className={TD_CLASS}>
                        <RatingPill value={row.rating} />
                      </td>
                      <td className={TD_CLASS}>
                        <Link
                          href={analysisHref(row.symbol)}
                          aria-label={`Open analysis for ${row.symbol}`}
                          className="inline-flex min-h-8 items-center rounded-md border border-[var(--border)] px-2 text-[11px] text-[var(--muted)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                        >
                          →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="border-t border-[var(--border)] px-5 py-2 font-[family-name:var(--font-mono)] text-[10px] text-[var(--muted)]">
            Qty and Avg Cost are your recorded inputs. CMP is provider-reported. P&amp;L, Return and
            totals are computed by the server (quantity × price); holdings without an authenticated
            price stay unavailable and are excluded from totals.
          </p>
        </Panel>

        <Panel title="Sector Allocation" padded>
          {slices.length === 0 ? (
            <PanelEmpty
              description={
                isEmpty
                  ? "Holdings appear here once they are recorded for your account."
                  : "Data unavailable. Allocation needs an authenticated price for at least one holding."
              }
            />
          ) : (
            <>
              <svg
                viewBox="-90 -90 180 180"
                className="mx-auto block h-[180px] w-[180px]"
                role="img"
                aria-label={`Sector allocation: ${slices
                  .map((s) => `${s.name} ${s.percent.toFixed(1)}%`)
                  .join(", ")}`}
              >
                {segments.map(({ slice, path }) => (
                  <path key={slice.name} d={path} fill={slice.colorVar} opacity={0.85} />
                ))}
              </svg>
              <ul className="m-0 mt-2 flex list-none flex-col gap-2 p-0">
                {slices.map((s) => (
                  <li key={s.name} className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-xs text-[var(--muted)]">
                      <span
                        className="inline-block h-2 w-2 rounded-full"
                        style={{ background: s.colorVar }}
                        aria-hidden="true"
                      />
                      {s.name}
                    </span>
                    <span className="font-[family-name:var(--font-mono)] text-xs text-[var(--fg)]">
                      {s.percent.toLocaleString(undefined, { maximumFractionDigits: 1 })}%
                    </span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-[10px] text-[var(--muted)]">
                Weights are current market value by sector, computed by the server.
              </p>
            </>
          )}
        </Panel>
      </div>
    </FigmaPage>
  );
}
