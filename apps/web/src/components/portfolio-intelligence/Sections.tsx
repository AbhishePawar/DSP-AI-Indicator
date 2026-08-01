"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  Badge,
  Button,
  Input,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ds";
import {
  buildPortfolioExportSnapshot,
  downloadText,
  portfolioSnapshotToCsv,
  portfolioSnapshotToHtml,
  portfolioSnapshotToJson,
  usePortfolioIntelPrefsStore,
} from "@/lib/portfolio-intelligence";
import { featureFlags } from "@/lib/featureFlags";
import {
  listRecentReports,
  type RecentReportEntry,
} from "@/lib/recentReports";
import type { PortfolioActivity, PortfolioHolding } from "@/lib/portfolio/model";
import { RemoveHoldingButton } from "@/components/portfolio/RemoveHoldingButton";
import {
  FieldRow,
  SectionCard,
  StatusBadge,
  WorkspaceEmpty,
} from "./Primitives";

type SortKey = "ticker" | "company" | "sector" | "recommendation";

export function SummarySection({
  holdings,
  watchlistCount,
  lastUpdated,
}: {
  holdings: PortfolioHolding[];
  watchlistCount: number;
  lastUpdated: string | null;
}) {
  const researchCount = holdings.filter((h) => h.researchAvailable).length;
  return (
    <div className="space-y-4">
      <SectionCard
        title="Portfolio Overview"
        description="Session holdings counts only — no portfolio value or return analytics (no portfolio API)"
      >
        <dl>
          <FieldRow label="Holdings count" value={holdings.length} />
          <FieldRow label="Watchlist count" value={watchlistCount} />
          <FieldRow label="Latest research count" value={researchCount} />
          <FieldRow label="Last updated" value={lastUpdated} />
        </dl>
      </SectionCard>
      <SectionCard title="Certified analytics">
        <WorkspaceEmpty description="Data unavailable. Portfolio totals, weights, risk, and P&L require a backend portfolio API — not computed in the browser." />
      </SectionCard>
    </div>
  );
}

export function HoldingsSection({
  holdings,
}: {
  holdings: PortfolioHolding[];
}) {
  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("ticker");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const sectors = useMemo(
    () =>
      Array.from(new Set(holdings.map((h) => h.sector).filter(Boolean))).sort(),
    [holdings],
  );

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    let next = holdings.filter((h) => {
      if (sectorFilter !== "all" && h.sector !== sectorFilter) return false;
      if (!q) return true;
      return (
        h.ticker.toLowerCase().includes(q) ||
        h.company.toLowerCase().includes(q) ||
        h.sector.toLowerCase().includes(q)
      );
    });
    next = [...next].sort((a, b) => {
      const av = String(a[sortKey] ?? "");
      const bv = String(b[sortKey] ?? "");
      const cmp = av.localeCompare(bv);
      return sortDir === "asc" ? cmp : -cmp;
    });
    return next;
  }, [holdings, search, sectorFilter, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  return (
    <SectionCard
      title="Holdings"
      description="Session holdings list — search/filter/sort are presentation only"
    >
      <div className="mb-3 flex flex-wrap gap-2">
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search holdings"
          aria-label="Search holdings"
          className="max-w-xs"
        />
        <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
          Sector
          <select
            className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-[var(--fg)]"
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            aria-label="Filter holdings by sector"
          >
            <option value="all">All</option>
            {sectors.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      {holdings.length === 0 ? (
        <WorkspaceEmpty
          description="Data unavailable. Add holdings from Company Analysis or load session portfolio actions."
          action={
            <Link href="/analysis">
              <Button size="sm" variant="secondary">
                Analyze company
              </Button>
            </Link>
          }
        />
      ) : rows.length === 0 ? (
        <WorkspaceEmpty description="No holdings match the current search/filter." />
      ) : (
        <div className="max-h-[28rem] overflow-auto rounded-[var(--radius-md)] border border-[var(--border)]">
          <Table aria-label="Portfolio holdings">
            <TableHeader className="sticky top-0 z-10 bg-[var(--surface)]">
              <TableRow>
                {(
                  [
                    ["company", "Company"],
                    ["ticker", "Ticker"],
                    ["sector", "Sector"],
                    ["recommendation", "Status"],
                  ] as const
                ).map(([key, label]) => (
                  <TableHead key={key}>
                    <button
                      type="button"
                      className="hover:text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                      onClick={() => toggleSort(key)}
                    >
                      {label}
                      {sortKey === key ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
                    </button>
                  </TableHead>
                ))}
                <TableHead>Research</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((h) => (
                <TableRow key={h.ticker}>
                  <TableCell>{h.company}</TableCell>
                  <TableCell className="font-mono text-xs">{h.ticker}</TableCell>
                  <TableCell>{h.sector || "Data unavailable."}</TableCell>
                  <TableCell>
                    <StatusBadge
                      ok={Boolean(h.recommendation)}
                      label={h.recommendation || "Data unavailable."}
                    />
                  </TableCell>
                  <TableCell>
                    <Badge variant={h.researchAvailable ? "accent" : "outline"}>
                      {h.researchAvailable
                        ? "Session flag: linked"
                        : "Not linked"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-2">
                      <Link
                        href={`/analysis?symbol=${encodeURIComponent(h.ticker)}`}
                      >
                        <Button size="sm" variant="secondary">
                          Quick analysis
                        </Button>
                      </Link>
                      <RemoveHoldingButton ticker={h.ticker} />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </SectionCard>
  );
}

export function ResearchSection({
  holdings,
}: {
  holdings: PortfolioHolding[];
}) {
  const covered = holdings.filter((h) => h.researchAvailable);
  const [reports, setReports] = useState<RecentReportEntry[]>([]);

  useEffect(() => {
    setReports(listRecentReports());
  }, []);

  return (
    <div className="space-y-4">
      <SectionCard
        title="Research Coverage"
        description="Count of holdings flagged researchAvailable in session data"
      >
        <FieldRow label="Covered holdings" value={covered.length} />
        <FieldRow label="Total holdings" value={holdings.length} />
        {covered.length === 0 ? (
          <p className="mt-3 text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="mt-3 space-y-1 text-sm">
            {covered.map((h) => (
              <li key={h.ticker}>
                <Link
                  href={`/research/${encodeURIComponent(h.ticker)}`}
                  className="text-[var(--accent)] hover:underline"
                >
                  {h.ticker} · {h.company}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Recent Reports">
        {reports.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. Analyze a company to store report ids locally." />
        ) : (
          <ul className="space-y-1 text-sm">
            {reports.slice(0, 5).map((r) => (
              <li key={r.reportId}>
                <Link
                  href={`/reports/${encodeURIComponent(r.reportId)}`}
                  className="text-[var(--accent)] hover:underline"
                >
                  {r.reportId}
                  {r.symbol ? ` · ${r.symbol}` : ""}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Archive Status">
        <WorkspaceEmpty description="Data unavailable. No portfolio archive API in the frozen client." />
      </SectionCard>
      <SectionCard title="Research Timeline">
        <WorkspaceEmpty description="Data unavailable. Open Company Analysis timeline per ticker." />
      </SectionCard>
      <SectionCard title="Research Links">
        <div className="flex flex-wrap gap-2">
          <Link href="/research">
            <Button size="sm" variant="secondary">
              Research workspace
            </Button>
          </Link>
          <Link href="/research/institutional">
            <Button size="sm" variant="secondary">
              Institutional dashboard
            </Button>
          </Link>
        </div>
      </SectionCard>
    </div>
  );
}

export function AiSection() {
  return (
    <div className="space-y-4">
      <SectionCard title="Portfolio Intelligence">
        <WorkspaceEmpty description="Use Refresh intelligence on the toolbar. POST /api/v1/portfolio/intelligence requires sign-in and does not invent research objects client-side." />
      </SectionCard>
      <SectionCard title="Monitoring Summary">
        <WorkspaceEmpty description="Data unavailable. No portfolio monitoring API in the client." />
      </SectionCard>
      <SectionCard title="Committee Activity">
        <WorkspaceEmpty
          description="Data unavailable at portfolio level. Open Company Analysis AI section per holding."
          action={
            <Link href="/analysis">
              <Button size="sm" variant="secondary">
                Company Analysis
              </Button>
            </Link>
          }
        />
      </SectionCard>
      <SectionCard title="Compliance Summary">
        <ul className="space-y-2 text-sm">
          <li className="flex justify-between gap-2">
            <span className="text-[var(--muted)]">Research Mode</span>
            <Badge variant={featureFlags.researchMode ? "accent" : "outline"}>
              {featureFlags.researchMode ? "On" : "Off"}
            </Badge>
          </li>
          <li className="flex justify-between gap-2">
            <span className="text-[var(--muted)]">Recommendation Mode</span>
            <Badge variant="outline">
              {featureFlags.recommendationMode ? "On" : "Off"}
            </Badge>
          </li>
        </ul>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Flags are presentation only — not portfolio compliance outcomes.
        </p>
      </SectionCard>
      <SectionCard title="Workflow Summary">
        <WorkspaceEmpty description="Data unavailable. No portfolio workflow list API in the client." />
      </SectionCard>
    </div>
  );
}

export function MonitoringSection({
  activities,
  watchlist,
}: {
  activities: PortfolioActivity[];
  watchlist: { symbol: string; addedAt: string }[];
}) {
  return (
    <div className="space-y-4">
      <SectionCard title="Alerts">
        <WorkspaceEmpty description="Data unavailable. No portfolio alerts API in the frozen client." />
      </SectionCard>
      <SectionCard title="Recent Changes">
        {activities.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <ul className="space-y-2 text-sm">
            {activities.slice(0, 10).map((a) => (
              <li key={a.id} className="flex justify-between gap-3">
                <span>{a.label}</span>
                <span className="text-xs text-[var(--muted)]">
                  {new Date(a.timestamp).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Watchlist Activity">
        {watchlist.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <ul className="space-y-1 text-sm">
            {watchlist.map((w) => (
              <li key={w.symbol}>
                {w.symbol}
                <span className="ml-2 text-xs text-[var(--muted)]">
                  added {new Date(w.addedAt).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Research Monitoring">
        <WorkspaceEmpty
          description={
            featureFlags.showResearchAlerts
              ? "Data unavailable. Alert feed API not wired."
              : "Data unavailable. Research alerts remain gated by feature flags."
          }
        />
      </SectionCard>
    </div>
  );
}

export function ComplianceSection() {
  return (
    <div className="space-y-4">
      <SectionCard title="Policy Status">
        <FieldRow
          label="Research Mode"
          value={featureFlags.researchMode ? "On" : "Off"}
        />
        <FieldRow
          label="SEBI Mode"
          value={featureFlags.sebiMode ? "On" : "Off"}
        />
      </SectionCard>
      <SectionCard title="Portfolio Warnings">
        <WorkspaceEmpty description="Data unavailable. No portfolio compliance warnings API." />
      </SectionCard>
      <SectionCard title="Violations">
        <WorkspaceEmpty description="Data unavailable." />
      </SectionCard>
      <SectionCard title="Workflow Status">
        <WorkspaceEmpty description="Data unavailable. No portfolio workflow status field." />
      </SectionCard>
    </div>
  );
}

export function ExportSection({
  holdings,
  activities,
}: {
  holdings: PortfolioHolding[];
  activities: PortfolioActivity[];
}) {
  const portfolioId = usePortfolioIntelPrefsStore((s) => s.activePortfolioId);
  const portfolios = usePortfolioIntelPrefsStore((s) => s.portfolios);
  const watchlist = usePortfolioIntelPrefsStore((s) => s.watchlist);
  const name =
    portfolios.find((p) => p.id === portfolioId)?.name ??
    "Primary session portfolio";

  const snapshot = buildPortfolioExportSnapshot({
    portfolioId,
    portfolioName: name,
    holdings,
    watchlist: watchlist.map((w) => w.symbol),
    activities,
  });

  const sharePath = `/portfolio?section=export`;

  return (
    <div className="space-y-4">
      <SectionCard
        title="Downloads"
        description="Portfolio PDF/print, research links, and share — session snapshot only"
      >
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={async () => {
              const url =
                typeof window !== "undefined"
                  ? `${window.location.origin}${sharePath}`
                  : sharePath;
              try {
                await navigator.clipboard.writeText(url);
              } catch {
                /* ignore */
              }
            }}
          >
            Share
          </Button>
          <Button variant="secondary" onClick={() => window.print()}>
            Print
          </Button>
          <Link href="/research/institutional">
            <Button variant="ghost">Research Report</Button>
          </Link>
        </div>
      </SectionCard>
      <SectionCard
        title="Export files"
        description="Exports session holdings fields only — no value/return/risk rollups"
      >
        <div className="grid gap-2 sm:grid-cols-2">
          <Button
            variant="secondary"
            onClick={() =>
              downloadText(
                "portfolio.json",
                portfolioSnapshotToJson(snapshot),
                "application/json",
              )
            }
          >
            Export JSON
          </Button>
          <Button
            variant="secondary"
            onClick={() =>
              downloadText(
                "portfolio.csv",
                portfolioSnapshotToCsv(snapshot),
                "text/csv",
              )
            }
          >
            Export CSV
          </Button>
          <Button
            variant="secondary"
            onClick={() =>
              downloadText(
                "portfolio-excel.csv",
                portfolioSnapshotToCsv(snapshot),
                "text/csv",
              )
            }
          >
            Export Excel (CSV)
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              downloadText(
                "portfolio.html",
                portfolioSnapshotToHtml(snapshot),
                "text/html",
              );
              window.print();
            }}
          >
            Portfolio PDF (print)
          </Button>
        </div>
      </SectionCard>
    </div>
  );
}
