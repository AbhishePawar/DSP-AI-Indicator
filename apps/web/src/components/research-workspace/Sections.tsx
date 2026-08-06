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
  downloadText,
  libraryFromArchive,
  libraryFromRecent,
  libraryFromReports,
  mergeLibraryItems,
  researchViewToCsv,
  researchViewToHtml,
  researchViewToJson,
  useResearchWorkspacePrefsStore,
  type ResearchLibraryItem,
} from "@/lib/research-workspace";
import { loadRecentAnalyses } from "@/lib/analysis/recentAnalyses";
import { listArchivedSessions } from "@/lib/copilot/sessionArchive";
import { featureFlags } from "@/lib/featureFlags";
import { formatPct } from "@/lib/intelligence/mapResponse";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { listRecentReports } from "@/lib/recentReports";
import { FieldRow, SectionCard, WorkspaceEmpty } from "./Primitives";
import { ReportInformationCard } from "@/components/company-analysis/ReportInformationCard";

type SortKey = "ticker" | "company" | "source" | "analysedAt";

export function LibrarySection({
  onOpenTicker,
}: {
  onOpenTicker: (ticker: string) => void;
}) {
  const [items, setItems] = useState<ResearchLibraryItem[]>([]);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [sortKey, setSortKey] = useState<SortKey>("analysedAt");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const toggleFavourite = useResearchWorkspacePrefsStore(
    (s) => s.toggleFavourite,
  );
  const togglePinned = useResearchWorkspacePrefsStore((s) => s.togglePinned);
  const isFavourite = useResearchWorkspacePrefsStore((s) => s.isFavourite);
  const isPinned = useResearchWorkspacePrefsStore((s) => s.isPinned);

  useEffect(() => {
    setItems(
      mergeLibraryItems([
        ...libraryFromRecent(loadRecentAnalyses()),
        ...libraryFromArchive(listArchivedSessions()),
        ...libraryFromReports(listRecentReports()),
      ]),
    );
  }, []);

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    let next = items.filter((item) => {
      if (sourceFilter !== "all" && item.source !== sourceFilter) return false;
      if (!q) return true;
      return (
        item.ticker.toLowerCase().includes(q) ||
        item.company.toLowerCase().includes(q)
      );
    });
    next = [...next].sort((a, b) => {
      const av = String(a[sortKey] ?? "");
      const bv = String(b[sortKey] ?? "");
      const cmp = av.localeCompare(bv);
      return sortDir === "asc" ? cmp : -cmp;
    });
    return next;
  }, [items, search, sourceFilter, sortKey, sortDir]);

  return (
    <SectionCard
      title="Research Library"
      description="Local session history, archive, and report ids — not a server research catalogue"
    >
      <div className="mb-3 flex flex-wrap gap-2">
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search research"
          aria-label="Search research library"
          className="max-w-xs"
        />
        <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
          Source
          <select
            className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-[var(--fg)]"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            aria-label="Filter research by source"
          >
            <option value="all">All</option>
            <option value="recent">Recent</option>
            <option value="archive">Archive</option>
            <option value="report">Report</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
          Sort
          <select
            className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-[var(--fg)]"
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            aria-label="Sort research library"
          >
            <option value="analysedAt">Date</option>
            <option value="ticker">Ticker</option>
            <option value="company">Company</option>
            <option value="source">Source</option>
          </select>
        </label>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}
        >
          {sortDir === "asc" ? "Asc" : "Desc"}
        </Button>
      </div>

      {rows.length === 0 ? (
        <WorkspaceEmpty
          description="Data unavailable. Run Company Analysis to populate recent research, or open a ticker below."
          action={
            <Link href="/analysis">
              <Button size="sm" variant="secondary">
                Analyze company
              </Button>
            </Link>
          }
        />
      ) : (
        <Table aria-label="Research library">
          <TableHeader>
            <TableRow>
              <TableHead>Ticker</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Analysed</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-mono text-xs">{item.ticker}</TableCell>
                <TableCell>{item.company}</TableCell>
                <TableCell>
                  <Badge variant="outline">{item.source}</Badge>
                </TableCell>
                <TableCell className="text-xs text-[var(--muted)]">
                  {item.analysedAt
                    ? new Date(item.analysedAt).toLocaleString()
                    : "Data unavailable."}
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => onOpenTicker(item.ticker)}
                    >
                      Open
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        toggleFavourite(item.ticker, item.company)
                      }
                    >
                      {isFavourite(item.ticker) ? "Unfavourite" : "Favourite"}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => togglePinned(item.ticker)}
                    >
                      {isPinned(item.ticker) ? "Unpin" : "Pin"}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </SectionCard>
  );
}

export function ViewerSection({
  view,
  loading,
  error,
  onRetry,
}: {
  view: ResearchView | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  if (loading) {
    return (
      <SectionCard title="Research Object Viewer">
        <p className="text-sm text-[var(--muted)]" aria-live="polite">
          Loading research…
        </p>
      </SectionCard>
    );
  }

  if (error) {
    return (
      <SectionCard title="Research Object Viewer">
        <WorkspaceEmpty
          title="Research failed"
          description={error}
          action={
            <Button size="sm" variant="secondary" onClick={onRetry}>
              Retry
            </Button>
          }
        />
      </SectionCard>
    );
  }

  if (!view) {
    return (
      <SectionCard title="Research Object Viewer">
        <WorkspaceEmpty description="Data unavailable. Select a ticker from the library or search to load /api/v1/analyse outputs." />
      </SectionCard>
    );
  }

  return (
    <div className="space-y-4">
      <SectionCard
        title="Research Object Viewer"
        description="Mapped AnalyseResponse — display only"
        action={
          <Link href={`/research/${encodeURIComponent(view.ticker)}`}>
            <Button size="sm" variant="secondary">
              Full company research page
            </Button>
          </Link>
        }
      >
        <dl>
          <FieldRow label="Company" value={view.company} />
          <FieldRow label="Ticker" value={view.ticker} />
          <FieldRow label="Exchange" value={view.exchange} />
          <FieldRow label="Analysed at" value={view.analysedAt} />
          <FieldRow label="Recommendation" value={view.recommendation} />
          <FieldRow label="Correlation ID" value={view.correlationId} />
        </dl>
      </SectionCard>

      <ReportInformationCard transparency={view.transparency} />

      <SectionCard title="Institutional Report Viewer">
        <p className="text-sm text-[var(--muted)]">
          RS-001…RS-010 layout lives on the institutional dashboard.
        </p>
        <Link href="/research/institutional" className="mt-3 inline-block">
          <Button size="sm" variant="secondary">
            Open institutional dashboard
          </Button>
        </Link>
      </SectionCard>

      <SectionCard title="Metadata Panel">
        <dl>
          <FieldRow label="Platform version" value={view.platformVersion} />
          <FieldRow label="Pipeline version" value={view.pipelineVersion} />
          <FieldRow label="OK" value={String(view.ok)} />
          <FieldRow label="Failed stage" value={view.failedStage} />
        </dl>
      </SectionCard>

      <SectionCard title="Version Information">
        <dl>
          <FieldRow label="API / pipeline" value={view.pipelineVersion} />
          <FieldRow label="Platform" value={view.platformVersion} />
        </dl>
        {Object.keys(view.packageVersions).length === 0 ? (
          <p className="mt-2 text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="mt-2 space-y-1 text-xs text-[var(--muted)]">
            {Object.entries(view.packageVersions).map(([k, v]) => (
              <li key={k}>
                {k}: {v}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <SectionCard title="Provenance">
        <FieldRow label="Correlation ID" value={view.correlationId} />
        <FieldRow
          label="Elapsed ms"
          value={
            view.totalElapsedMs === null
              ? "Data unavailable."
              : String(view.totalElapsedMs)
          }
        />
      </SectionCard>

      <SectionCard title="Citations / Evidence strengths">
        {view.strengths.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="list-disc space-y-1 pl-4 text-sm">
            {view.strengths.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}

export function ArchiveSection() {
  const [sessions, setSessions] = useState(listArchivedSessions());

  useEffect(() => {
    setSessions(listArchivedSessions());
  }, []);

  return (
    <div className="space-y-4">
      <SectionCard
        title="Archive Browser"
        description="Local session archive (dsp.researchArchive.v1) — not a server archive API"
      >
        {sessions.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. Analyze companies to populate the local research archive." />
        ) : (
          <ul className="space-y-2 text-sm">
            {sessions.map((s) => (
              <li
                key={`${s.ticker}-${s.analysedAt}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2"
              >
                <span>
                  <span className="font-medium">{s.ticker}</span>
                  <span className="ml-2 text-[var(--muted)]">
                    {s.company || "Data unavailable."}
                  </span>
                </span>
                <span className="text-xs text-[var(--muted)]">
                  {new Date(s.analysedAt).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Snapshot Viewer">
        <WorkspaceEmpty description="Data unavailable. No server snapshot viewer API. Open a ticker in Viewer to inspect mapped analyse output." />
      </SectionCard>
      <SectionCard title="Snapshot Metadata">
        <WorkspaceEmpty description="Data unavailable. No archive metadata endpoint in frozen /api/v1." />
      </SectionCard>
      <SectionCard title="Archive Timeline">
        {sessions.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <ol className="space-y-2 text-sm">
            {sessions.map((s) => (
              <li key={`tl-${s.ticker}-${s.analysedAt}`}>
                {new Date(s.analysedAt).toLocaleString()} — {s.ticker}
              </li>
            ))}
          </ol>
        )}
      </SectionCard>
    </div>
  );
}

export function DiffSection() {
  return (
    <div className="space-y-4">
      <SectionCard title="Research Diff Viewer">
        <WorkspaceEmpty description="Data unavailable. No research-diff API in the thin client." />
      </SectionCard>
      <SectionCard title="Section Comparison">
        <WorkspaceEmpty description="Data unavailable. Section diffs require a certified compare endpoint." />
      </SectionCard>
      <SectionCard title="Change Summary">
        <dl>
          <FieldRow label="Added" value="Data unavailable." />
          <FieldRow label="Removed" value="Data unavailable." />
          <FieldRow label="Modified" value="Data unavailable." />
        </dl>
      </SectionCard>
    </div>
  );
}

export function AiSection({ view }: { view: ResearchView | null }) {
  if (!view) {
    return (
      <SectionCard title="AI & Committee">
        <WorkspaceEmpty description="Data unavailable. Load research in the Viewer first." />
      </SectionCard>
    );
  }

  return (
    <div className="space-y-4">
      <SectionCard
        title="Copilot Results"
        description="Full chat lives on /copilot — context from mapped research"
        action={
          <Link href="/copilot">
            <Button size="sm" variant="secondary">
              Open Copilot
            </Button>
          </Link>
        }
      >
        <p className="text-sm text-[var(--muted)]">
          This workspace does not run local AI inference.
        </p>
      </SectionCard>
      <SectionCard title="Committee Summary">
        <dl>
          <FieldRow label="Decision" value={view.committeeDecision} />
          <FieldRow
            label="Confidence"
            value={formatPct(view.committeeConfidence)}
          />
          <FieldRow label="Consensus" value={view.committeeConsensus} />
          <FieldRow
            label="Final recommendation"
            value={view.committee.finalRecommendation}
          />
        </dl>
      </SectionCard>
      <SectionCard title="Committee Opinions / Evidence">
        {view.committee.supportingReasons.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="list-disc space-y-1 pl-4 text-sm">
            {view.committee.supportingReasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Minority Opinions">
        {view.minorityNotes.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="list-disc space-y-1 pl-4 text-sm">
            {view.minorityNotes.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Confidence Summary">
        {Object.keys(view.confidenceSummary).length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <dl>
            {Object.entries(view.confidenceSummary).map(([k, v]) => (
              <FieldRow key={k} label={k} value={formatPct(v)} />
            ))}
          </dl>
        )}
      </SectionCard>
    </div>
  );
}

export function ComplianceSection({ view }: { view: ResearchView | null }) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Compliance Summary"
        description="Feature-flag presentation + analyse limitations — not a compliance engine"
      >
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
          <li className="flex justify-between gap-2">
            <span className="text-[var(--muted)]">SEBI Mode</span>
            <Badge variant="outline">
              {featureFlags.sebiMode ? "On" : "Off"}
            </Badge>
          </li>
        </ul>
      </SectionCard>
      <SectionCard title="Workflow Status">
        <WorkspaceEmpty description="Data unavailable. No research workflow status field on AnalyseResponse." />
      </SectionCard>
      <SectionCard title="Policy Results">
        <FieldRow
          label="Analyse OK"
          value={view ? (view.ok ? "Succeeded" : "Failed / incomplete") : null}
        />
      </SectionCard>
      <SectionCard title="Audit References">
        <FieldRow label="Correlation ID" value={view?.correlationId} />
        {view?.limitations.length ? (
          <ul className="mt-2 list-disc space-y-1 pl-4 text-sm">
            {view.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-[var(--muted)]">Data unavailable.</p>
        )}
      </SectionCard>
    </div>
  );
}

export function ExportSection({ view }: { view: ResearchView | null }) {
  if (!view) {
    return (
      <SectionCard title="Export">
        <WorkspaceEmpty description="Data unavailable. Load research before exporting." />
      </SectionCard>
    );
  }

  const base = `${view.ticker.toLowerCase()}-research`;

  return (
    <SectionCard
      title="Export"
      description="Exports mapped display fields only — no client research generation"
    >
      <div className="grid gap-2 sm:grid-cols-2">
        <Button
          variant="secondary"
          onClick={() =>
            downloadText(
              `${base}.json`,
              researchViewToJson(view),
              "application/json",
            )
          }
        >
          Export JSON
        </Button>
        <Button
          variant="secondary"
          onClick={() =>
            downloadText(`${base}.csv`, researchViewToCsv(view), "text/csv")
          }
        >
          Export CSV
        </Button>
        <Button
          variant="secondary"
          onClick={() =>
            downloadText(
              `${base}-excel.csv`,
              researchViewToCsv(view),
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
              `${base}.html`,
              researchViewToHtml(view),
              "text/html",
            );
            window.print();
          }}
        >
          Export PDF (print)
        </Button>
      </div>
    </SectionCard>
  );
}
