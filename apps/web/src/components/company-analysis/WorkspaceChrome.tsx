"use client";

import Link from "next/link";

import { Badge, Button } from "@/components/ds";
import { env } from "@/lib/env";
import type { CompanyEntry } from "@/lib/companies/catalogue";
import { useDashboardPrefsStore } from "@/lib/dashboard";
import { formatPct } from "@/lib/intelligence/mapResponse";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { FieldRow, SectionCard } from "./WorkspacePrimitives";

export function CompanyHeaderBar({
  view,
  catalogue,
  marketStatus,
  lastUpdated,
}: {
  view: ResearchView | null;
  catalogue: CompanyEntry | undefined;
  marketStatus: string;
  lastUpdated: string | null;
}) {
  const company = view?.company || catalogue?.name || "Data unavailable.";
  const symbol = view?.ticker || catalogue?.ticker || "—";
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
          ? `Partial · failed ${view.failedStage}`
          : "Incomplete";
  const researchConfidence =
    view?.recommendationConfidence != null
      ? formatPct(view.recommendationConfidence)
      : view?.committeeConfidence != null
        ? formatPct(view.committeeConfidence)
        : null;
  const sharePath = `/analysis?symbol=${encodeURIComponent(symbol)}`;

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
            href={`/compare?symbol=${encodeURIComponent(symbol)}`}
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
        <FieldRow label="Market Cap" value={catalogue?.marketCap} />
        <FieldRow label="Coverage" value={coverage} />
        <FieldRow label="Research timestamp" value={lastUpdated} />
        <FieldRow label="Confidence" value={researchConfidence} />
        <FieldRow label="Market status" value={marketStatus} />
      </dl>
    </SectionCard>
  );
}

export function WorkspaceToolbar({
  onAnalyze,
  analyzing,
  onToggleLeft,
  onToggleRight,
  leftOpen,
  rightOpen,
}: {
  onAnalyze: () => void;
  analyzing: boolean;
  onToggleLeft: () => void;
  onToggleRight: () => void;
  leftOpen: boolean;
  rightOpen: boolean;
}) {
  return (
    <div className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] bg-[var(--surface)]/95 px-3 py-2 backdrop-blur motion-reduce:backdrop-blur-none">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="ghost"
          onClick={onToggleLeft}
          aria-pressed={leftOpen}
          aria-label={leftOpen ? "Hide navigation panel" : "Show navigation panel"}
        >
          {leftOpen ? "Hide nav" : "Show nav"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="lg:inline-flex"
          onClick={onToggleRight}
          aria-pressed={rightOpen}
          aria-label={rightOpen ? "Hide context panel" : "Show context panel"}
        >
          {rightOpen ? "Hide context" : "Show context"}
        </Button>
        <span className="hidden text-xs text-[var(--muted)] md:inline">
          Shortcuts: Ctrl+Enter analyze · 1–9 / E T R V O B C · [ / ] panels
        </span>
      </div>
      <Button size="sm" onClick={onAnalyze} disabled={analyzing}>
        {analyzing ? "Analyzing…" : "Run analysis"}
      </Button>
    </div>
  );
}
