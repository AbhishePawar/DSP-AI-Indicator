"use client";

import Link from "next/link";

import { Badge, Button } from "@/components/ds";
import { env } from "@/lib/env";
import type { CompanyEntry } from "@/lib/companies/catalogue";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import { formatPct } from "@/lib/intelligence/mapResponse";
import type {
  FinancialStatementsPayload,
  MarketQuotePayload,
} from "@/lib/institutional-dashboard/mapInstitutionalDashboard";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { FieldRow, SectionCard } from "./WorkspacePrimitives";

function money(value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value)) return null;
  return value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
}

function compact(value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value)) return null;
  return Intl.NumberFormat(undefined, {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

function pct(value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value)) return null;
  return `${(value * 100).toFixed(2)}%`;
}

/** Daily change is a display-only derivation from two already-fetched raw
 * quote fields â€” not a valuation calculation. */
function dailyChange(
  current: number | null | undefined,
  previousClose: number | null | undefined,
): string | null {
  if (current == null || previousClose == null || previousClose === 0) {
    return null;
  }
  const delta = current - previousClose;
  const changePct = (delta / previousClose) * 100;
  const sign = delta >= 0 ? "+" : "";
  return `${sign}${delta.toFixed(2)} (${sign}${changePct.toFixed(2)}%)`;
}

export function CompanyHeaderBar({
  view,
  catalogue,
  marketStatus,
  lastUpdated,
  marketQuote,
  financialStatements,
}: {
  view: ResearchView | null;
  catalogue: CompanyEntry | undefined;
  marketStatus: string;
  lastUpdated: string | null;
  /** EPIC-D001 authenticated market quote â€” never invents missing fields. */
  marketQuote?: MarketQuotePayload | null;
  /** EPIC-D002 authenticated financial statements â€” latest period ratios only. */
  financialStatements?: FinancialStatementsPayload | null;
}) {
  const company = view?.company || catalogue?.name || "Data unavailable.";
  const symbol = view?.ticker || catalogue?.ticker || "â€”";
  const exchange = view?.exchange || catalogue?.exchange || "Data unavailable.";
  const pinCompany = useDashboardPrefsStore((s) => s.pinCompany);
  const unpinCompany = useDashboardPrefsStore((s) => s.unpinCompany);
  const pinnedCompanies = useDashboardPrefsStore((s) => s.pinnedCompanies);
  const isPinned = pinnedCompanies.some(
    (p) => p.symbol.toUpperCase() === symbol.toUpperCase(),
  );
  const coverage =
    view == null
      ? "Not loaded"
      : view.ok
        ? "Covered"
        : view.failedStage
          ? `Partial Â· failed ${view.failedStage}`
          : "Incomplete";
  const researchConfidence =
    view?.recommendationConfidence != null
      ? formatPct(view.recommendationConfidence)
      : view?.committeeConfidence != null
        ? formatPct(view.committeeConfidence)
        : null;
  const sharePath = `/analysis?symbol=${encodeURIComponent(symbol)}`;

  const quoteFields =
    marketQuote?.available && marketQuote.authenticated
      ? marketQuote.fields
      : null;
  const latestRatios =
    financialStatements?.available &&
    financialStatements.authenticated &&
    financialStatements.periods?.length
      ? financialStatements.periods[0]?.ratios
      : null;

  return (
    <SectionCard
      title={company}
      description="Company identity from analyse request + local catalogue metadata"
      action={
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="accent">{symbol}</Badge>
          <Badge variant="outline" className="font-mono text-[10px]">
            v{env.foundationVersion}
          </Badge>
          <Button
            size="sm"
            variant="secondary"
            aria-pressed={isPinned}
            onClick={() =>
              isPinned ? unpinCompany(symbol) : pinCompany(symbol, company)
            }
          >
            {isPinned ? "Watchlisted" : "Watchlist"}
          </Button>
          <Link
            href={`/analysis/compare?symbols=${encodeURIComponent(symbol)}`}
            className="inline-flex"
          >
            <Button size="sm" variant="ghost">
              Compare
            </Button>
          </Link>
          <Button
            size="sm"
            variant="ghost"
            aria-label="Copy share link for this analysis"
            onClick={async () => {
              const url =
                typeof window !== "undefined"
                  ? `${window.location.origin}${sharePath}`
                  : sharePath;
              try {
                await navigator.clipboard.writeText(url);
              } catch {
                /* clipboard may be denied */
              }
            }}
          >
            Share
          </Button>
        </div>
      }
    >
      <dl className="grid gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
        <FieldRow label="Company" value={company} />
        <FieldRow label="Ticker" value={symbol} />
        <FieldRow label="Exchange" value={exchange} />
        <FieldRow label="Sector" value={catalogue?.sector} />
        <FieldRow label="Industry" value={catalogue?.industry} />
        <FieldRow label="Coverage" value={coverage} />
        <FieldRow label="Research timestamp" value={lastUpdated} />
        <FieldRow label="Confidence" value={researchConfidence} />
        <FieldRow label="Market status" value={marketStatus} />
      </dl>
      <p className="mb-2 mt-4 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        Live market snapshot â€” EPIC-D001/D002 authenticated feeds only
      </p>
      <dl className="grid gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
        <FieldRow label="Current Price" value={money(quoteFields?.current_price)} />
        <FieldRow
          label="Daily Change"
          value={dailyChange(
            quoteFields?.current_price,
            quoteFields?.previous_close,
          )}
        />
        <FieldRow
          label="Market Cap"
          value={compact(quoteFields?.market_cap) ?? catalogue?.marketCap}
        />
        <FieldRow label="52 Week High" value={money(quoteFields?.week_52_high)} />
        <FieldRow label="52 Week Low" value={money(quoteFields?.week_52_low)} />
        <FieldRow
          label="Dividend Yield"
          value={pct(quoteFields?.dividend_yield)}
        />
        <FieldRow label="P/E" value={null} />
        <FieldRow label="P/B" value={null} />
        <FieldRow label="ROE" value={pct(latestRatios?.roe)} />
      </dl>
    </SectionCard>
  );
}
