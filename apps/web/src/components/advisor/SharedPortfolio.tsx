"use client";

import {
  memo,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { CollaborationLayout } from "@/components/advisor/TeamCollaboration";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { WindowedList } from "@/lib/perf/WindowedList";
import type { ModelPortfolioDraft } from "@/lib/advisor/modelPortfolioTypes";
import {
  FILTER_SECTORS,
  FILTER_STRATEGIES,
  SHARED_PORTFOLIO_TRUST,
  buildScenarioViews,
  getPortfolioById,
} from "@/lib/advisor/sharedPortfolioModels";
import {
  buildSharedPortfolioOverview,
  commitPortfolioComparison,
  comparePortfolioFields,
  filterPortfolios,
  getSharedPortfolioSnapshot,
  markPortfolioReviewed,
  recordPortfolioViewed,
  resetSharedPortfolioFilters,
  seedModelPortfolioLibrary,
  setActiveDiscussionId,
  setActiveScenarioPortfolioId,
  setPortfolioCompareSelection,
  setSharedPortfolioFilters,
  subscribeSharedPortfolio,
  togglePortfolioCompare,
  togglePortfolioFavorite,
  togglePortfolioPin,
  updateDiscussion,
} from "@/lib/advisor/sharedPortfolioSession";
import {
  SHARED_PORTFOLIO_NAV,
  type SharedPortfolioActivityItem,
} from "@/lib/advisor/sharedPortfolioTypes";

function useSharedPortfolio() {
  return useSyncExternalStore(
    subscribeSharedPortfolio,
    getSharedPortfolioSnapshot,
    getSharedPortfolioSnapshot,
  );
}

/* ── Shell ──────────────────────────────────────────────────────── */

export function PortfolioSidebar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Shared portfolio sections"
      className="sticky top-24 flex max-h-[calc(100vh-7rem)] w-full shrink-0 flex-col gap-1 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--surface)] p-2 lg:w-44"
    >
      {SHARED_PORTFOLIO_NAV.map((link) => {
        const active = link.exact
          ? pathname === link.href
          : pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            className={`min-h-11 rounded-md px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
              active
                ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

export const PortfolioQuickActions = memo(function PortfolioQuickActions() {
  const actions = [
    { href: "/advisor/team/shared-portfolios/library", label: "Library" },
    { href: "/advisor/team/shared-portfolios/compare", label: "Compare 2–5" },
    { href: "/advisor/team/shared-portfolios/scenarios", label: "Scenarios" },
    { href: "/advisor/team/shared-portfolios/discussion", label: "Discussion" },
    { href: "/advisor/team/shared-portfolios/activity", label: "Activity" },
    { href: "/advisor/portfolios", label: "Model Portfolio Manager" },
  ] as const;
  return (
    <Card>
      <CardHeader title="Portfolio quick actions" description="Session navigation" />
      <CardBody className="flex flex-wrap gap-2">
        {actions.map((a) => (
          <Link key={a.href} href={a.href}>
            <Button variant="secondary" size="md">
              {a.label}
            </Button>
          </Link>
        ))}
      </CardBody>
    </Card>
  );
});

function SharedPortfolioShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <CollaborationLayout title={title} description={description}>
      <p
        role="note"
        className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm"
      >
        {SHARED_PORTFOLIO_TRUST}
      </p>
      <div className="flex flex-col gap-4 lg:flex-row">
        <PortfolioSidebar />
        <div className="min-w-0 flex-1 space-y-4">{children}</div>
      </div>
    </CollaborationLayout>
  );
}

/* ── Panels / cards ─────────────────────────────────────────────── */

export const PortfolioFilterPanel = memo(function PortfolioFilterPanel() {
  const snap = useSharedPortfolio();
  const f = snap.filters;
  const selectClass =
    "mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]";

  return (
    <Card>
      <CardHeader title="Portfolio Filters" description="Presentation filters over demo models" />
      <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <label className="block text-xs text-[var(--muted)] sm:col-span-2 lg:col-span-3">
          Search
          <input
            type="search"
            value={f.query}
            onChange={(e) => setSharedPortfolioFilters({ query: e.target.value })}
            className={selectClass}
            aria-label="Search shared portfolios"
            placeholder="Name or objective…"
          />
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Risk level
          <select
            value={f.riskLevel}
            onChange={(e) =>
              setSharedPortfolioFilters({
                riskLevel: e.target.value as typeof f.riskLevel,
              })
            }
            className={selectClass}
            aria-label="Filter by risk level"
          >
            <option value="">All</option>
            <option value="conservative">Conservative</option>
            <option value="moderate">Moderate</option>
            <option value="growth">Growth</option>
            <option value="aggressive">Aggressive</option>
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Strategy
          <select
            value={f.strategy}
            onChange={(e) => setSharedPortfolioFilters({ strategy: e.target.value })}
            className={selectClass}
            aria-label="Filter by strategy"
          >
            <option value="">All</option>
            {FILTER_STRATEGIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Sector
          <select
            value={f.sector}
            onChange={(e) => setSharedPortfolioFilters({ sector: e.target.value })}
            className={selectClass}
            aria-label="Filter by sector"
          >
            <option value="">All</option>
            {FILTER_SECTORS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Market Cap
          <select
            value={f.marketCap}
            onChange={(e) =>
              setSharedPortfolioFilters({
                marketCap: e.target.value as typeof f.marketCap,
              })
            }
            className={selectClass}
            aria-label="Filter by market cap band"
          >
            <option value="">All</option>
            <option value="large">Large</option>
            <option value="mid">Mid</option>
            <option value="small">Small</option>
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Allocation
          <select
            value={f.allocationBand}
            onChange={(e) =>
              setSharedPortfolioFilters({
                allocationBand: e.target.value as typeof f.allocationBand,
              })
            }
            className={selectClass}
            aria-label="Filter by allocation band"
          >
            <option value="">All</option>
            <option value="equity_heavy">Equity heavy</option>
            <option value="balanced">Balanced cash</option>
            <option value="cash_heavy">Cash heavy</option>
          </select>
        </label>
        <fieldset className="sm:col-span-2 lg:col-span-3">
          <legend className="text-xs text-[var(--muted)]">Flags</legend>
          <div className="mt-2 flex flex-wrap gap-3">
            {(
              [
                ["watchlistOnly", "Watchlist", f.watchlistOnly],
                ["pinnedOnly", "Pinned", f.pinnedOnly],
                ["favoritesOnly", "Favorites", f.favoritesOnly],
                ["recentlyViewedOnly", "Recently viewed", f.recentlyViewedOnly],
              ] as const
            ).map(([key, label, checked]) => (
              <label key={key} className="flex min-h-11 items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) =>
                    setSharedPortfolioFilters({ [key]: e.target.checked })
                  }
                />
                {label}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="sm:col-span-2 lg:col-span-3">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => resetSharedPortfolioFilters()}
          >
            Reset filters
          </Button>
        </div>
      </CardBody>
    </Card>
  );
});

export const PortfolioOverviewDashboard = memo(function PortfolioOverviewDashboard() {
  const snap = useSharedPortfolio();
  const overview = useMemo(() => buildSharedPortfolioOverview(snap), [snap]);
  const cells = [
    ["Portfolio count", String(overview.portfolioCount)],
    ["Comparison sessions", String(overview.comparisonSessions)],
    ["Scenario coverage", overview.scenarioCoverage],
    ["Allocation summary", overview.allocationSummary],
    ["Risk distribution", overview.riskDistribution],
    ["Sector exposure", overview.sectorExposure],
    ["Presentation readiness", overview.presentationReadiness],
  ] as const;

  return (
    <Card>
      <CardHeader
        title="Portfolio Overview Dashboard"
        description="Presentation metrics from existing model library"
      />
      <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cells.map(([label, value]) => (
          <div
            key={label}
            className="rounded-md border border-[var(--border)] bg-[var(--surface-2)]/40 p-3"
          >
            <p className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</p>
            <p className="mt-1 text-sm font-medium">{value}</p>
          </div>
        ))}
      </CardBody>
    </Card>
  );
});

export const PortfolioActivityFeed = memo(function PortfolioActivityFeed({
  items,
}: {
  items: SharedPortfolioActivityItem[];
}) {
  return (
    <Card>
      <CardHeader title="Portfolio Activity" description="Session feed — not live multi-user" />
      <CardBody>
        <WindowedList
          items={items}
          initial={8}
          step={8}
          className="grid gap-2"
          empty={<EmptyState title="No activity yet" />}
          renderItem={(item) => (
            <div
              key={item.id}
              className="flex min-h-11 flex-col gap-1 rounded-md border border-[var(--border)] px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between"
            >
              <span>{item.label}</span>
              <span className="flex items-center gap-2 text-xs text-[var(--muted)]">
                <Badge>{item.kind}</Badge>
                <time dateTime={item.at}>{item.at.slice(0, 16).replace("T", " ")}</time>
              </span>
            </div>
          )}
        />
      </CardBody>
    </Card>
  );
});

export const PortfolioScenarioCard = memo(function PortfolioScenarioCard({
  portfolio,
}: {
  portfolio: ModelPortfolioDraft;
}) {
  const scenarios = useMemo(() => buildScenarioViews(portfolio), [portfolio]);
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {scenarios.map((s) => (
        <Card key={s.id}>
          <CardHeader title={s.label} description={portfolio.name} />
          <CardBody className="space-y-2 text-sm">
            <p>{s.framing}</p>
            <p className="text-[var(--muted)]">{s.riskCue}</p>
            <p className="text-[var(--muted)]">{s.allocationCue}</p>
            <p className="text-xs text-[var(--muted)]" role="note">
              {s.note}
            </p>
          </CardBody>
        </Card>
      ))}
    </div>
  );
});

export const PortfolioDiscussionPanel = memo(function PortfolioDiscussionPanel() {
  const snap = useSharedPortfolio();
  const draft =
    snap.discussions[snap.activeDiscussionId] ??
    ({
      portfolioId: snap.activeDiscussionId,
      portfolioNotes: "",
      reviewNotes: "",
      investmentThesis: getPortfolioById(snap.activeDiscussionId)?.objective ?? "",
      concerns: "",
      followUps: "",
      updatedAt: "",
    } as const);

  const fieldClass =
    "mt-1 min-h-[5.5rem] w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]";

  return (
    <Card>
      <CardHeader
        title="Portfolio Discussion"
        description="Session notes only — not chat or real-time collaboration"
      />
      <CardBody className="space-y-4">
        <label className="block text-xs text-[var(--muted)]">
          Portfolio
          <select
            value={snap.activeDiscussionId}
            onChange={(e) => setActiveDiscussionId(e.target.value)}
            className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            aria-label="Select portfolio for discussion"
          >
            {seedModelPortfolioLibrary.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        {(
          [
            ["portfolioNotes", "Portfolio Notes", draft.portfolioNotes],
            ["reviewNotes", "Review Notes", draft.reviewNotes],
            ["investmentThesis", "Investment Thesis", draft.investmentThesis],
            ["concerns", "Concerns", draft.concerns],
            ["followUps", "Follow-up Items", draft.followUps],
          ] as const
        ).map(([key, label, value]) => (
          <label key={key} className="block text-xs text-[var(--muted)]">
            {label}
            <textarea
              value={value}
              onChange={(e) =>
                updateDiscussion(snap.activeDiscussionId, { [key]: e.target.value })
              }
              className={fieldClass}
              aria-label={label}
            />
          </label>
        ))}
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={() => markPortfolioReviewed(snap.activeDiscussionId)}
          >
            Mark reviewed
          </Button>
          {draft.updatedAt ? (
            <span className="self-center text-xs text-[var(--muted)]">
              Updated {draft.updatedAt.slice(0, 19).replace("T", " ")}
            </span>
          ) : null}
        </div>
      </CardBody>
    </Card>
  );
});

export const PortfolioLibraryPanel = memo(function PortfolioLibraryPanel() {
  const snap = useSharedPortfolio();
  const filtered = useMemo(() => filterPortfolios(snap), [snap]);
  const resolve = (ids: string[]) =>
    ids
      .map((id) => getPortfolioById(id))
      .filter((p): p is ModelPortfolioDraft => Boolean(p));

  const recent = useMemo(() => resolve(snap.recentlyViewed), [snap.recentlyViewed]);
  const pinned = useMemo(() => resolve(snap.pinnedIds), [snap.pinnedIds]);
  const favorites = useMemo(() => resolve(snap.favoriteIds), [snap.favoriteIds]);

  return (
    <div className="space-y-4">
      <PortfolioFilterPanel />
      <Card>
        <CardHeader
          title="Model Portfolios"
          description={`${filtered.length} models after filters — allocations unchanged`}
        />
        <CardBody>
          <WindowedList
            items={filtered}
            initial={6}
            step={4}
            empty={<EmptyState title="No portfolios match filters" />}
            renderItem={(p) => (
              <article
                key={p.id}
                className="rounded-md border border-[var(--border)] p-3 text-sm"
                aria-label={p.name}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="font-medium">{p.name}</h3>
                    <p className="mt-1 text-[var(--muted)]">{p.objective}</p>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    <Badge>{p.riskLevel}</Badge>
                    <Badge>{p.category}</Badge>
                    {snap.pinnedIds.includes(p.id) ? <Badge>Pinned</Badge> : null}
                    {snap.favoriteIds.includes(p.id) ? <Badge>Favorite</Badge> : null}
                  </div>
                </div>
                <p className="mt-2 text-xs text-[var(--muted)]">
                  Cash {p.cashAllocationPct}% · {p.holdings.length} holdings ·{" "}
                  {p.targetHorizon}
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => recordPortfolioViewed(p.id)}
                  >
                    View
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    aria-pressed={snap.compareSelection.includes(p.id)}
                    onClick={() => togglePortfolioCompare(p.id)}
                  >
                    {snap.compareSelection.includes(p.id) ? "In compare" : "Add to compare"}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => togglePortfolioPin(p.id)}
                  >
                    Pin
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => togglePortfolioFavorite(p.id)}
                  >
                    Favorite
                  </Button>
                </div>
              </article>
            )}
          />
        </CardBody>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Recent Portfolios" />
          <CardBody>
            <ul className="space-y-1 text-sm" aria-label="Recent portfolios">
              {recent.map((p) => (
                <li key={p.id}>{p.name}</li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Pinned Portfolios" />
          <CardBody>
            <ul className="space-y-1 text-sm" aria-label="Pinned portfolios">
              {pinned.map((p) => (
                <li key={p.id}>{p.name}</li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Favorite Portfolios" />
          <CardBody>
            <ul className="space-y-1 text-sm" aria-label="Favorite portfolios">
              {favorites.map((p) => (
                <li key={p.id}>{p.name}</li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Portfolio Collections" />
          <CardBody>
            <ul className="space-y-2 text-sm" aria-label="Portfolio collections">
              {snap.collections.map((c) => (
                <li key={c.id} className="rounded-md border border-[var(--border)] px-3 py-2">
                  <p className="font-medium">{c.name}</p>
                  <p className="text-xs text-[var(--muted)]">
                    {c.portfolioIds
                      .map((id) => getPortfolioById(id)?.name ?? id)
                      .join(" · ")}
                  </p>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader title="Portfolio Timeline" description="Session activity" />
        <CardBody>
          <ul className="space-y-2 text-sm" aria-label="Portfolio timeline">
            {snap.activity.slice(0, 8).map((a) => (
              <li
                key={a.id}
                className="flex min-h-11 flex-col gap-1 rounded-md border border-[var(--border)] px-3 py-2 sm:flex-row sm:items-center sm:justify-between"
              >
                <span>{a.label}</span>
                <Badge>{a.kind}</Badge>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
});

export const PortfolioComparisonWorkspace = memo(function PortfolioComparisonWorkspace() {
  const snap = useSharedPortfolio();
  const cmp = useMemo(
    () => comparePortfolioFields(snap.compareSelection),
    [snap.compareSelection],
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title="Select model portfolios (2–5)"
          description="Reuses existing summary · allocation · sector · risk · notes — never recalculated"
        />
        <CardBody>
          <ul
            className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3"
            aria-label="Portfolio compare selection"
          >
            {seedModelPortfolioLibrary.map((p) => {
              const checked = snap.compareSelection.includes(p.id);
              const disabled = !checked && snap.compareSelection.length >= 5;
              return (
                <li key={p.id}>
                  <label
                    className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-[var(--border)] px-3 text-sm ${
                      disabled ? "opacity-50" : ""
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={() => togglePortfolioCompare(p.id)}
                    />
                    {p.name}
                  </label>
                </li>
              );
            })}
          </ul>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              type="button"
              disabled={snap.compareSelection.length < 2}
              onClick={() => commitPortfolioComparison()}
            >
              Record comparison session
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setPortfolioCompareSelection([])}
            >
              Clear
            </Button>
          </div>
        </CardBody>
      </Card>

      {cmp ? (
        <>
          <Card>
            <CardHeader title="Comparison table" />
            <CardBody className="overflow-x-auto">
              <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
                <caption className="sr-only">
                  Side-by-side comparison of selected model portfolios
                </caption>
                <thead>
                  <tr>
                    <th scope="col" className="border-b border-[var(--border)] px-2 py-2">
                      Field
                    </th>
                    {cmp.portfolios.map((p) => (
                      <th
                        key={p.id}
                        scope="col"
                        className="border-b border-[var(--border)] px-2 py-2"
                      >
                        {p.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {cmp.rows.map((row) => (
                    <tr key={row.label}>
                      <th
                        scope="row"
                        className="border-b border-[var(--border)] px-2 py-2 font-medium"
                      >
                        {row.label}
                      </th>
                      {row.values.map((v, i) => (
                        <td
                          key={`${row.label}-${i}`}
                          className="border-b border-[var(--border)] px-2 py-2 text-[var(--muted)]"
                        >
                          {v}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Holding allocation matrix" description="Existing sleeve weights only" />
            <CardBody className="overflow-x-auto">
              <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
                <caption className="sr-only">Holding allocation percentages by portfolio</caption>
                <thead>
                  <tr>
                    <th scope="col" className="border-b border-[var(--border)] px-2 py-2">
                      Holding
                    </th>
                    {cmp.portfolios.map((p) => (
                      <th
                        key={p.id}
                        scope="col"
                        className="border-b border-[var(--border)] px-2 py-2"
                      >
                        {p.name} %
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {cmp.holdingMatrix.map((row) => (
                    <tr key={row.envelopeId}>
                      <th
                        scope="row"
                        className="border-b border-[var(--border)] px-2 py-2 font-medium"
                      >
                        {row.companyLabel}
                      </th>
                      {row.values.map((v, i) => (
                        <td
                          key={`${row.envelopeId}-${i}`}
                          className="border-b border-[var(--border)] px-2 py-2 tabular-nums text-[var(--muted)]"
                        >
                          {v}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Scenario Analysis (existing framing)" />
            <CardBody className="text-sm text-[var(--muted)]">
              Open{" "}
              <Link
                href="/advisor/team/shared-portfolios/scenarios"
                className="text-[var(--accent)] underline"
              >
                Scenarios
              </Link>{" "}
              to review Conservative · Base · Bull · Bear · Stress cards built from the same demo
              allocations (not recalculated).
            </CardBody>
          </Card>
        </>
      ) : (
        <EmptyState title="Select at least 2 portfolios to compare" />
      )}

      {snap.recentlyCompared.length > 0 ? (
        <Card>
          <CardHeader title="Recently Compared" />
          <CardBody>
            <ul className="space-y-2 text-sm" aria-label="Recently compared portfolios">
              {snap.recentlyCompared.map((set, i) => (
                <li key={i}>
                  <button
                    type="button"
                    className="min-h-11 text-left text-[var(--accent)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                    onClick={() => setPortfolioCompareSelection(set)}
                  >
                    {set.map((id) => getPortfolioById(id)?.name ?? id).join(" · ")}
                  </button>
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      ) : null}
    </div>
  );
});

/* ── Pages ──────────────────────────────────────────────────────── */

export const SharedPortfolioWorkspace = memo(function SharedPortfolioWorkspace() {
  const snap = useSharedPortfolio();
  return (
    <SharedPortfolioShell
      title="Shared Portfolio Workspace"
      description="Review, compare, discuss, and present existing model portfolios — session only"
    >
      <PortfolioQuickActions />
      <PortfolioOverviewDashboard />
      <div className="grid gap-4 lg:grid-cols-2">
        <PortfolioActivityFeed items={snap.activity.slice(0, 6)} />
        <Card>
          <CardHeader title="Trust reminder" />
          <CardBody className="text-sm text-[var(--muted)]">
            Portfolio Engine / demo library remains the single source of truth. This workspace never
            recalculates allocations, scenarios, or risk — and never modifies Evidence, Confidence,
            Methodology, or Limitations on linked research.
          </CardBody>
        </Card>
      </div>
    </SharedPortfolioShell>
  );
});

export const SharedPortfolioLibraryPage = memo(function SharedPortfolioLibraryPage() {
  return (
    <SharedPortfolioShell
      title="Shared Portfolio Library"
      description="Models · pinned · recent · favorites · collections · timeline"
    >
      <PortfolioLibraryPanel />
    </SharedPortfolioShell>
  );
});

export const SharedPortfolioComparePage = memo(function SharedPortfolioComparePage() {
  return (
    <SharedPortfolioShell
      title="Portfolio Comparison"
      description="Compare 2–5 model portfolios using existing DSP fields only"
    >
      <PortfolioComparisonWorkspace />
    </SharedPortfolioShell>
  );
});

export const SharedPortfolioScenariosPage = memo(function SharedPortfolioScenariosPage() {
  const snap = useSharedPortfolio();
  const portfolio =
    getPortfolioById(snap.activeScenarioPortfolioId) ?? seedModelPortfolioLibrary[0];

  return (
    <SharedPortfolioShell
      title="Scenario Review"
      description="Conservative · Base · Bull · Bear · Stress — presentation framings of existing models"
    >
      <Card>
        <CardHeader title="Select model" />
        <CardBody>
          <label className="block text-xs text-[var(--muted)]">
            Portfolio
            <select
              value={snap.activeScenarioPortfolioId}
              onChange={(e) => setActiveScenarioPortfolioId(e.target.value)}
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              aria-label="Select portfolio for scenario review"
            >
              {seedModelPortfolioLibrary.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
        </CardBody>
      </Card>
      {portfolio ? <PortfolioScenarioCard portfolio={portfolio} /> : null}
    </SharedPortfolioShell>
  );
});

export const SharedPortfolioDiscussionPage = memo(function SharedPortfolioDiscussionPage() {
  return (
    <SharedPortfolioShell
      title="Portfolio Discussion"
      description="Notes · thesis · concerns · follow-ups — session only"
    >
      <PortfolioDiscussionPanel />
    </SharedPortfolioShell>
  );
});

export const SharedPortfolioActivityPage = memo(function SharedPortfolioActivityPage() {
  const snap = useSharedPortfolio();
  const buckets = useMemo(() => {
    const by = (kind: SharedPortfolioActivityItem["kind"]) =>
      snap.activity.filter((a) => a.kind === kind);
    return {
      viewed: by("viewed"),
      compared: by("compared"),
      presented: by("presented"),
      reviewed: by("reviewed"),
      updated: by("updated"),
    };
  }, [snap.activity]);

  return (
    <SharedPortfolioShell
      title="Portfolio Activity"
      description="Viewed · Compared · Presented · Reviewed · Updated"
    >
      <PortfolioActivityFeed items={snap.activity} />
      <div className="grid gap-4 md:grid-cols-2">
        {(
          [
            ["Recently Viewed", buckets.viewed],
            ["Recently Compared", buckets.compared],
            ["Recently Presented", buckets.presented],
            ["Recently Reviewed", buckets.reviewed],
            ["Recently Updated", buckets.updated],
          ] as const
        ).map(([title, items]) => (
          <Card key={title}>
            <CardHeader title={title} />
            <CardBody>
              <ul className="space-y-1 text-sm" aria-label={title}>
                {items.length === 0 ? (
                  <li className="text-[var(--muted)]">None yet</li>
                ) : (
                  items.slice(0, 6).map((a) => <li key={a.id}>{a.label}</li>)
                )}
              </ul>
            </CardBody>
          </Card>
        ))}
      </div>
    </SharedPortfolioShell>
  );
});
