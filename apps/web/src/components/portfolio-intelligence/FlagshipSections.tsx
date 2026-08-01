"use client";

/**
 * P9.5 / EPIC-006 — Flagship portfolio modules.
 * Session facts + optional /portfolio/intelligence pass-through. No client scoring.
 */

import Link from "next/link";

import { Badge, Button } from "@/components/ds";
import type { PortfolioIntelligenceView } from "@/lib/portfolio-intelligence";
import {
  attentionItems,
  researchCoverageFacts,
  sectorHoldingCounts,
  sessionAllocationBySector,
  usePortfolioIntelPrefsStore,
} from "@/lib/portfolio-intelligence";
import type { PortfolioActivity, PortfolioHolding } from "@/lib/portfolio/model";
import {
  FieldRow,
  SectionCard,
  WorkspaceEmpty,
} from "./Primitives";
import { ResearchSection } from "./Sections";

function CountBars({
  title,
  description,
  segments,
}: {
  title: string;
  description: string;
  segments: { name: string; count: number; shareOfHoldings: string }[];
}) {
  const max = Math.max(...segments.map((s) => s.count), 1);
  return (
    <SectionCard title={title} description={description}>
      {segments.length === 0 ? (
        <WorkspaceEmpty description="Data unavailable." />
      ) : (
        <ul className="space-y-2" aria-label={title}>
          {segments.map((s) => (
            <li key={s.name}>
              <div className="mb-1 flex justify-between gap-2 text-sm">
                <span>{s.name}</span>
                <span className="text-[var(--muted)]">
                  {s.count} · {s.shareOfHoldings}
                </span>
              </div>
              <div
                className="h-2 overflow-hidden rounded-full bg-[var(--surface-2)]"
                role="presentation"
              >
                <div
                  className="h-full bg-[var(--accent)] transition-[width] duration-300 motion-reduce:transition-none"
                  style={{ width: `${(s.count / max) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

export function PortfolioHeaderCard({
  portfolioName,
  owner,
  lastUpdated,
  holdingsCount,
  researchCoverage,
  onExport,
  onShare,
}: {
  portfolioName: string;
  owner: string;
  lastUpdated: string | null;
  holdingsCount: number;
  /** Session research-available coverage facts — not a confidence score. */
  researchCoverage: string;
  onExport: () => void;
  onShare: () => void;
}) {
  return (
    <SectionCard
      title={portfolioName}
      description="Portfolio identity from session prefs — values that require market feeds stay Data unavailable."
      action={
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={onShare}>
            Share
          </Button>
          <Button size="sm" variant="ghost" onClick={onExport}>
            Export
          </Button>
        </div>
      }
    >
      <dl className="grid gap-x-6 sm:grid-cols-2 lg:grid-cols-3">
        <FieldRow label="Portfolio Name" value={portfolioName} />
        <FieldRow label="Owner" value={owner} />
        <FieldRow
          label="Total Value"
          value="Data unavailable. No certified portfolio valuation feed in the thin client."
        />
        <FieldRow
          label="Cash Position"
          value="Data unavailable. Cash balances are not on the session holdings model."
        />
        <FieldRow label="Holdings count" value={holdingsCount} />
        <FieldRow label="Last Updated" value={lastUpdated} />
        <FieldRow label="Research coverage" value={researchCoverage} />
        <FieldRow
          label="Benchmark"
          value="Data unavailable. No benchmark API wired for this workspace."
        />
        <FieldRow
          label="Performance Period"
          value="Data unavailable. Returns require a performance feed."
        />
      </dl>
    </SectionCard>
  );
}

export function ExecutivePortfolioSummary({
  holdings,
  intel,
  intelStatus,
}: {
  holdings: PortfolioHolding[];
  intel: PortfolioIntelligenceView | null;
  intelStatus: string;
}) {
  const coverage = researchCoverageFacts(holdings);
  const attention = attentionItems(holdings);
  const strengths: string[] = [];
  const risks: string[] = [];
  if (coverage.covered > 0) {
    strengths.push(`${coverage.covered} holding(s) flagged research-available in session.`);
  }
  if (intel?.linkedResearchCount && intel.linkedResearchCount !== "Data unavailable.") {
    strengths.push(`Intelligence API linked research count: ${intel.linkedResearchCount}.`);
  }
  if (coverage.pending > 0) {
    risks.push(`${coverage.pending} holding(s) without research coverage flag.`);
  }
  if (intel?.missingResearchCount && intel.missingResearchCount !== "0") {
    risks.push(`Missing linked research (API): ${intel.missingResearchCount}.`);
  }

  return (
    <div className="space-y-4">
      <SectionCard
        title="Executive Portfolio Summary"
        description="Research Mode — session coverage counts and API pass-through only"
      >
        <dl>
          <FieldRow
            label="Research coverage status"
            value={
              holdings.length === 0
                ? "Empty session portfolio — no holdings to cover"
                : coverage.pending === 0
                  ? "All holdings flagged research-available (session)"
                  : "Partial research coverage (session)"
            }
          />
          <FieldRow
            label="Overall Recommendation"
            value="Data unavailable. Portfolio-level recommendation requires linked research + committee feed."
          />
          <FieldRow label="Intelligence API status" value={intelStatus} />
          <FieldRow
            label="Portfolio Score"
            value="Data unavailable. No client-side portfolio score; engine scores are not fabricated."
          />
          <FieldRow
            label="Linked research (API)"
            value={intel?.linkedResearchCount ?? "Data unavailable."}
          />
        </dl>
      </SectionCard>
      <SectionCard title="Key Strengths">
        {strengths.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="list-disc space-y-1 pl-4 text-sm">
            {strengths.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Key Risks">
        {risks.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
        ) : (
          <ul className="list-disc space-y-1 pl-4 text-sm">
            {risks.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Today's Attention Items">
        {attention.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">
            No attention items from session holdings.
          </p>
        ) : (
          <ul className="list-disc space-y-1 pl-4 text-sm">
            {attention.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}

export function AllocationSection({
  holdings,
}: {
  holdings: PortfolioHolding[];
}) {
  const bySector = sectorHoldingCounts(holdings);
  const sessionAlloc = sessionAllocationBySector(holdings);
  return (
    <div className="space-y-4">
      <CountBars
        title="Allocation by Sector"
        description="Holding counts by sector label on session holdings — not market-value weights"
        segments={bySector}
      />
      <SectionCard
        title="Session allocation % by sector"
        description={sessionAlloc.note}
      >
        {sessionAlloc.segments.length === 0 ? (
          <WorkspaceEmpty description={sessionAlloc.note} />
        ) : (
          <dl>
            {sessionAlloc.segments.map((s) => (
              <FieldRow key={s.name} label={s.name} value={s.percentLabel} />
            ))}
          </dl>
        )}
      </SectionCard>
      <SectionCard title="Industry">
        <WorkspaceEmpty description="Data unavailable. Industry is not on the session PortfolioHolding model." />
      </SectionCard>
      <SectionCard title="Market Cap">
        <WorkspaceEmpty description="Data unavailable. Market-cap buckets require catalogue/API fields not used as portfolio weights here." />
      </SectionCard>
      <SectionCard title="Asset Type">
        <WorkspaceEmpty description="Data unavailable. Asset type is not on the session holdings model." />
      </SectionCard>
      <SectionCard title="Cash">
        <WorkspaceEmpty description="Data unavailable. Cash position is not persisted on the session portfolio." />
      </SectionCard>
      <SectionCard title="Charts">
        <p className="text-sm text-[var(--muted)]">
          Sector count bars above are the only charted series — derived from observed
          holding labels. No fabricated performance charts.
        </p>
      </SectionCard>
    </div>
  );
}

export function PerformanceSection() {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Performance"
        description="Returns and alpha require a certified performance feed — never inferred from prices in the browser"
      >
        <dl>
          <FieldRow label="Portfolio Return" value="Data unavailable." />
          <FieldRow label="Benchmark Return" value="Data unavailable." />
          <FieldRow label="Alpha" value="Data unavailable." />
          <FieldRow label="Drawdown" value="Data unavailable." />
          <FieldRow label="Rolling Returns" value="Data unavailable." />
          <FieldRow label="Historical Performance" value="Data unavailable." />
        </dl>
      </SectionCard>
      <WorkspaceEmpty description="Data unavailable. No portfolio performance / benchmark API is wired in the frozen thin client." />
    </div>
  );
}

export function QualitySection({
  holdings,
  intel,
}: {
  holdings: PortfolioHolding[];
  intel: PortfolioIntelligenceView | null;
}) {
  const covered = holdings.filter((h) => h.researchAvailable);
  const pending = holdings.filter((h) => !h.researchAvailable);
  return (
    <div className="space-y-4">
      <SectionCard
        title="Portfolio Quality"
        description="Pass-through from /portfolio/intelligence when linked research exists — no average scores invented in the client"
      >
        <dl>
          <FieldRow
            label="Average Business Quality"
            value="Data unavailable. API does not emit portfolio-average BQ; see position pass-through."
          />
          <FieldRow
            label="Average Management Quality"
            value="Data unavailable."
          />
          <FieldRow
            label="Average Economic Moat"
            value="Data unavailable."
          />
          <FieldRow
            label="Average Financial Strength"
            value="Data unavailable."
          />
          <FieldRow
            label="Quality positions available (API)"
            value={intel?.qualityAvailableCount ?? "Data unavailable."}
          />
          <FieldRow
            label="Quality positions unavailable (API)"
            value={intel?.qualityUnavailableCount ?? "Data unavailable."}
          />
        </dl>
        {intel?.qualityNote ? (
          <p className="mt-2 text-xs text-[var(--muted)]">{intel.qualityNote}</p>
        ) : null}
      </SectionCard>
      <SectionCard title="Distribution">
        {intel?.qualityPositions.length ? (
          <ul className="space-y-1 text-sm">
            {intel.qualityPositions.map((p) => (
              <li key={p.symbol} className="flex justify-between gap-2">
                <span className="font-mono text-xs">{p.symbol}</span>
                <span>{p.detail}</span>
              </li>
            ))}
          </ul>
        ) : (
          <WorkspaceEmpty description="Data unavailable. Link research objects server-side for quality pass-through." />
        )}
      </SectionCard>
      <SectionCard title="Top Quality Holdings">
        {covered.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No session holdings flagged research-available." />
        ) : (
          <ul className="space-y-1 text-sm">
            {covered.slice(0, 8).map((h) => (
              <li key={h.ticker}>
                <Link
                  href={`/analysis?symbol=${encodeURIComponent(h.ticker)}`}
                  className="text-[var(--accent)] hover:underline"
                >
                  {h.ticker} · {h.company}
                </Link>
                <span className="ml-2 text-xs text-[var(--muted)]">
                  research-available (session)
                </span>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Weakest Holdings">
        {pending.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">
            No coverage-pending holdings in session.
          </p>
        ) : (
          <ul className="space-y-1 text-sm">
            {pending.slice(0, 8).map((h) => (
              <li key={h.ticker}>
                <Link
                  href={`/analysis?symbol=${encodeURIComponent(h.ticker)}`}
                  className="text-[var(--accent)] hover:underline"
                >
                  {h.ticker} · {h.company}
                </Link>
                <Badge variant="outline" className="ml-2 text-[10px]">
                  Coverage pending
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}

export function ValuationSection({
  intel,
}: {
  intel: PortfolioIntelligenceView | null;
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Portfolio Valuation"
        description="No portfolio-weighted MoS is computed in the browser or invented from incomplete links"
      >
        <dl>
          <FieldRow label="Intrinsic Value" value="Data unavailable." />
          <FieldRow
            label="Weighted Margin of Safety"
            value="Data unavailable. Intelligence API explicitly does not compute portfolio-weighted MoS."
          />
          <FieldRow label="Portfolio Fair Value" value="Data unavailable." />
          <FieldRow
            label="MoS positions available (API)"
            value={intel?.mosAvailableCount ?? "Data unavailable."}
          />
          <FieldRow
            label="MoS positions unavailable (API)"
            value={intel?.mosUnavailableCount ?? "Data unavailable."}
          />
        </dl>
        {intel?.mosNote ? (
          <p className="mt-2 text-xs text-[var(--muted)]">{intel.mosNote}</p>
        ) : null}
      </SectionCard>
      <SectionCard title="Valuation Distribution">
        {intel?.mosPositions.length ? (
          <ul className="space-y-1 text-sm">
            {intel.mosPositions.map((p) => (
              <li key={p.symbol} className="flex justify-between gap-2">
                <span className="font-mono text-xs">{p.symbol}</span>
                <span>{p.marginOfSafety}</span>
              </li>
            ))}
          </ul>
        ) : (
          <WorkspaceEmpty description="Data unavailable. Pass research_objects with MoS fields via server linkage." />
        )}
      </SectionCard>
      <SectionCard title="Undervalued / Overvalued Holdings">
        <WorkspaceEmpty description="Data unavailable. Classification requires certified MoS thresholds from linked research — not inferred client-side." />
      </SectionCard>
    </div>
  );
}

export function RiskSection({
  intel,
}: {
  intel: PortfolioIntelligenceView | null;
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Portfolio Risk"
        description="REP-002 Book 07 concepts — pass-through only when present"
      >
        <dl>
          <FieldRow
            label="Concentration Risk"
            value={
              intel?.topHoldings.length
                ? `${intel.topHoldings.length} top holding(s) by session/API weight`
                : "Data unavailable."
            }
          />
          <FieldRow
            label="Sector Risk"
            value={
              intel?.uniqueSectorCount !== undefined
                ? `Unique sectors (API/session): ${intel.uniqueSectorCount}`
                : "Data unavailable."
            }
          />
          <FieldRow label="Business Risk" value="Data unavailable." />
          <FieldRow label="Financial Risk" value="Data unavailable." />
          <FieldRow label="Governance Risk" value="Data unavailable." />
          <FieldRow
            label="Permanent Capital Loss Exposure"
            value="Data unavailable. No portfolio PCL aggregate on the intelligence contract."
          />
          <FieldRow
            label="Risk positions available (API)"
            value={intel?.riskAvailableCount ?? "Data unavailable."}
          />
        </dl>
        {intel?.riskNote ? (
          <p className="mt-2 text-xs text-[var(--muted)]">{intel.riskNote}</p>
        ) : null}
      </SectionCard>
      <SectionCard title="Concentration (top holdings)">
        {intel?.topHoldings.length ? (
          <ul className="space-y-1 text-sm">
            {intel.topHoldings.map((h) => (
              <li key={h.symbol} className="flex justify-between gap-2">
                <span className="font-mono text-xs">{h.symbol}</span>
                <span>{h.detail}</span>
              </li>
            ))}
          </ul>
        ) : (
          <WorkspaceEmpty description={intel?.concentrationNote || "Data unavailable."} />
        )}
      </SectionCard>
      <SectionCard title="Risk Heatmap">
        {intel?.riskPositions.length ? (
          <ul className="space-y-1 text-sm">
            {intel.riskPositions.map((p) => (
              <li key={p.symbol} className="flex justify-between gap-2 border-b border-[var(--border)] py-1">
                <span className="font-mono text-xs">{p.symbol}</span>
                <span>{p.detail}</span>
              </li>
            ))}
          </ul>
        ) : (
          <WorkspaceEmpty description="Data unavailable. Heatmap cells require linked risk sections per holding." />
        )}
      </SectionCard>
    </div>
  );
}

export function WatchlistSection() {
  const watchlist = usePortfolioIntelPrefsStore((s) => s.watchlist);
  const removeWatchlistSymbol = usePortfolioIntelPrefsStore(
    (s) => s.removeWatchlistSymbol,
  );

  return (
    <div className="space-y-4">
      <SectionCard
        title="Watchlist Integration"
        description="Local workspace watchlist — not a server portfolio"
      >
        {watchlist.length === 0 ? (
          <WorkspaceEmpty description="Watchlist empty. Add symbols from the left navigation." />
        ) : (
          <ul className="space-y-2 text-sm">
            {watchlist.map((w) => (
              <li
                key={w.symbol}
                className="flex items-center justify-between gap-2 rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2"
              >
                <div>
                  <Link
                    href={`/analysis?symbol=${encodeURIComponent(w.symbol)}`}
                    className="font-mono text-[var(--accent)] hover:underline"
                  >
                    {w.symbol}
                  </Link>
                  <p className="text-xs text-[var(--muted)]">
                    Added {new Date(w.addedAt).toLocaleString()}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => removeWatchlistSymbol(w.symbol)}
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Candidates">
        <p className="text-sm text-[var(--muted)]">
          Use Company Analysis to research a ticker, then pin it to this
          watchlist. No demo symbols are pre-loaded.
        </p>
      </SectionCard>
      <SectionCard title="Recently Added">
        {watchlist.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <ul className="space-y-1 text-sm">
            {[...watchlist]
              .sort((a, b) => b.addedAt.localeCompare(a.addedAt))
              .slice(0, 5)
              .map((w) => (
                <li key={w.symbol}>{w.symbol}</li>
              ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="Coverage Pending">
        <WorkspaceEmpty description="Data unavailable at watchlist level until research objects are linked server-side." />
      </SectionCard>
    </div>
  );
}

export function OpportunitiesSection({
  holdings,
  intel,
}: {
  holdings: PortfolioHolding[];
  intel: PortfolioIntelligenceView | null;
}) {
  const pending = holdings.filter((h) => !h.researchAvailable);
  const covered = holdings.filter((h) => h.researchAvailable);
  return (
    <div className="space-y-4">
      <SectionCard
        title="Opportunities"
        description="Investigation candidates from session + API — not trade recommendations"
      >
        <p className="text-sm text-[var(--muted)]">
          Research Mode: next investigation steps only. No BUY/SELL chrome.
        </p>
      </SectionCard>
      <SectionCard title="Highest Margin of Safety">
        {intel?.mosPositions.length ? (
          <ul className="space-y-1 text-sm">
            {intel.mosPositions.slice(0, 8).map((p) => (
              <li key={p.symbol} className="flex justify-between gap-2">
                <Link
                  href={`/analysis?symbol=${encodeURIComponent(p.symbol)}`}
                  className="font-mono text-[var(--accent)] hover:underline"
                >
                  {p.symbol}
                </Link>
                <span>{p.marginOfSafety}</span>
              </li>
            ))}
          </ul>
        ) : (
          <WorkspaceEmpty description="Data unavailable. MoS pass-through requires linked research." />
        )}
      </SectionCard>
      <SectionCard title="Highest Conviction">
        <WorkspaceEmpty description="Data unavailable. Portfolio conviction ranking is not on the intelligence contract." />
      </SectionCard>
      <SectionCard title="Research-available holdings">
        {covered.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable. No session holdings flagged research-available." />
        ) : (
          <ul className="space-y-1 text-sm">
            {covered.slice(0, 8).map((h) => (
              <li key={h.ticker}>
                <Link
                  href={`/analysis?symbol=${encodeURIComponent(h.ticker)}`}
                  className="text-[var(--accent)] hover:underline"
                >
                  {h.ticker}
                </Link>
                <span className="ml-2 text-xs text-[var(--muted)]">
                  Session flag: research-available — open Company Analysis
                </span>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
      <SectionCard title="New Research Coverage">
        <WorkspaceEmpty description="Data unavailable. No coverage-delta feed in the thin client." />
      </SectionCard>
      <SectionCard title="Upgrade Candidates">
        {pending.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">
            No coverage-pending holdings.
          </p>
        ) : (
          <ul className="space-y-1 text-sm">
            {pending.map((h) => (
              <li key={h.ticker}>
                <Link
                  href={`/analysis?symbol=${encodeURIComponent(h.ticker)}`}
                  className="text-[var(--accent)] hover:underline"
                >
                  Run analysis for {h.ticker}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}

export function RebalancingSection({
  holdings,
  intel,
}: {
  holdings: PortfolioHolding[];
  intel: PortfolioIntelligenceView | null;
}) {
  const pending = holdings.filter((h) => !h.researchAvailable);
  return (
    <div className="space-y-4">
      <SectionCard
        title="Rebalancing"
        description="Review queue only — no trade execution or optimisation"
      >
        <dl>
          <FieldRow
            label="Suggested Reviews"
            value={
              pending.length
                ? `${pending.length} coverage-pending holding(s)`
                : "None from session coverage flags"
            }
          />
          <FieldRow
            label="Concentration Alerts"
            value={
              intel?.topHoldings.length
                ? "Inspect top holdings list in Risk"
                : "Data unavailable."
            }
          />
          <FieldRow label="Risk Alerts" value="Data unavailable. No alerts API." />
          <FieldRow
            label="Quality Deterioration"
            value="Data unavailable. No quality-delta feed."
          />
          <FieldRow
            label="Moat Erosion"
            value="Data unavailable. No moat-delta feed."
          />
        </dl>
      </SectionCard>
      <SectionCard title="Review Queue">
        {pending.length === 0 && !intel?.missingResearch.length ? (
          <WorkspaceEmpty description="Review queue empty for session coverage flags." />
        ) : (
          <ul className="space-y-2 text-sm">
            {pending.map((h) => (
              <li key={h.ticker}>
                <Badge variant="outline" className="mr-2">
                  Coverage
                </Badge>
                <Link
                  href={`/analysis?symbol=${encodeURIComponent(h.ticker)}`}
                  className="text-[var(--accent)] hover:underline"
                >
                  {h.ticker}
                </Link>
              </li>
            ))}
            {intel?.missingResearch.map((m) => (
              <li key={`miss-${m.symbol}`}>
                <Badge variant="outline" className="mr-2">
                  Missing research
                </Badge>
                {m.symbol}: {m.message}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}

export function ExplainabilitySection({
  intel,
  holdings,
}: {
  intel: PortfolioIntelligenceView | null;
  holdings: PortfolioHolding[];
}) {
  const coverage = researchCoverageFacts(holdings);
  return (
    <div className="space-y-4">
      <SectionCard
        title="Why portfolio score?"
        description="No client portfolio score exists. Explainability describes available evidence only."
      >
        <dl>
          <FieldRow
            label="Portfolio Score"
            value="Data unavailable — not computed in the thin client."
          />
          <FieldRow label="Intelligence result id" value={intel?.resultId ?? "Data unavailable."} />
          <FieldRow label="Schema version" value={intel?.schemaVersion ?? "Data unavailable."} />
          <FieldRow
            label="Session holdings"
            value={`${coverage.total} · research-available ${coverage.covered}`}
          />
        </dl>
      </SectionCard>
      <SectionCard title="Evidence chain">
        {intel?.rawNotes.length ? (
          <ul className="list-disc space-y-1 pl-4 text-sm">
            {intel.rawNotes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        ) : (
          <WorkspaceEmpty description="Data unavailable until /portfolio/intelligence returns notes." />
        )}
      </SectionCard>
      <SectionCard title="Research contributors">
        <FieldRow
          label="Linked research count"
          value={intel?.linkedResearchCount ?? "Data unavailable."}
        />
        <FieldRow
          label="Missing research count"
          value={intel?.missingResearchCount ?? "Data unavailable."}
        />
      </SectionCard>
      <SectionCard title="Coverage contributors">
        <WorkspaceEmpty description="Data unavailable. Portfolio coverage contributors are not on the intelligence summary contract." />
      </SectionCard>
      <SectionCard title="Contradictory evidence">
        {intel?.missingResearch.length ? (
          <ul className="list-disc space-y-1 pl-4 text-sm">
            {intel.missingResearch.map((m) => (
              <li key={m.symbol}>
                {m.symbol}: {m.message}
              </li>
            ))}
          </ul>
        ) : (
          <WorkspaceEmpty description="No contradictory / missing-research rows from the API." />
        )}
      </SectionCard>
    </div>
  );
}

export function ResearchActivitySection({
  holdings,
  activities,
}: {
  holdings: PortfolioHolding[];
  activities: PortfolioActivity[];
}) {
  return (
    <div className="space-y-4">
      <ResearchSection holdings={holdings} />
      <SectionCard title="Coverage Changes">
        <WorkspaceEmpty description="Data unavailable. No coverage-change timeline API." />
      </SectionCard>
      <SectionCard title="Recent AI Committee Decisions">
        <WorkspaceEmpty description="Data unavailable at portfolio level. Open Company Analysis AI Committee per holding." />
      </SectionCard>
      <SectionCard title="Material Events">
        <WorkspaceEmpty description="Data unavailable. Corporate-actions feeds are per-symbol, not portfolio-aggregated here." />
      </SectionCard>
      <SectionCard title="Session activity">
        {activities.length === 0 ? (
          <WorkspaceEmpty description="Data unavailable." />
        ) : (
          <ul className="space-y-2 text-sm">
            {activities.slice(0, 12).map((a) => (
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
    </div>
  );
}
