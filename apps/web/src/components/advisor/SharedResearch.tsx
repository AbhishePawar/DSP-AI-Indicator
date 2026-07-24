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
import { COMPARE_DIMENSIONS } from "@/lib/advisor/advisorResearchTypes";
import type { DemoResearchEnvelope } from "@/lib/advisor/advisorResearchTypes";
import {
  FILTER_INDUSTRIES,
  FILTER_RATINGS,
  FILTER_SECTORS,
  SHARED_RESEARCH_TRUST,
  metaForEnvelope,
} from "@/lib/advisor/sharedResearchModels";
import {
  buildCompareRows,
  buildSharedOverview,
  commitComparisonSession,
  createSharedCollection,
  deleteSharedCollection,
  filterEnvelopes,
  getEnvelope,
  getSharedResearchSnapshot,
  listResearchEnvelopes,
  moveResearchToCollection,
  recordOpened,
  renameSharedCollection,
  resetSharedFilters,
  setCompareSelection,
  setSharedFilters,
  subscribeSharedResearch,
  toggleBookmark,
  toggleCollectionFavorite,
  toggleCompareSelection,
  toggleFavorite,
  togglePin,
} from "@/lib/advisor/sharedResearchSession";
import {
  SHARED_RESEARCH_NAV,
  type SharedCollection,
  type SharedResearchActivityItem,
} from "@/lib/advisor/sharedResearchTypes";

function useSharedResearch() {
  return useSyncExternalStore(
    subscribeSharedResearch,
    getSharedResearchSnapshot,
    getSharedResearchSnapshot,
  );
}

/* ── Shell / sidebar / quick actions ────────────────────────────── */

export function ResearchSidebar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Shared research sections"
      className="sticky top-24 flex max-h-[calc(100vh-7rem)] w-full shrink-0 flex-col gap-1 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--surface)] p-2 lg:w-44"
    >
      {SHARED_RESEARCH_NAV.map((link) => {
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

export const ResearchQuickActions = memo(function ResearchQuickActions() {
  const actions = [
    { href: "/advisor/team/shared-research/library", label: "Library" },
    { href: "/advisor/team/shared-research/collections", label: "Collections" },
    { href: "/advisor/team/shared-research/compare", label: "Compare 2–5" },
    { href: "/advisor/team/shared-research/bookmarks", label: "Bookmarks" },
    { href: "/advisor/team/shared-research/activity", label: "Activity" },
    { href: "/advisor/research", label: "Advisor Research" },
  ] as const;
  return (
    <Card>
      <CardHeader title="Research quick actions" description="Session navigation" />
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

function SharedResearchShell({
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
        {SHARED_RESEARCH_TRUST}
      </p>
      <div className="flex flex-col gap-4 lg:flex-row">
        <ResearchSidebar />
        <div className="min-w-0 flex-1 space-y-4">{children}</div>
      </div>
    </CollaborationLayout>
  );
}

/* ── Cards ──────────────────────────────────────────────────────── */

export const ResearchCollectionCard = memo(function ResearchCollectionCard({
  collection,
  onRename,
  onDelete,
  onFavorite,
  onAdd,
}: {
  collection: SharedCollection;
  onRename?: (id: string) => void;
  onDelete?: (id: string) => void;
  onFavorite?: (id: string) => void;
  onAdd?: (id: string) => void;
}) {
  const items = useMemo(
    () =>
      collection.itemIds
        .map((id) => getEnvelope(id))
        .filter((e): e is DemoResearchEnvelope => Boolean(e)),
    [collection.itemIds],
  );

  return (
    <Card>
      <CardHeader
        title={collection.name}
        description={`${collection.theme} · ${items.length} items · session`}
      />
      <CardBody className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {collection.favorite ? <Badge>Favorite</Badge> : null}
          <Badge>{collection.lifecycle}</Badge>
        </div>
        <ul className="space-y-1 text-sm" aria-label={`${collection.name} research items`}>
          {items.length === 0 ? (
            <li className="text-[var(--muted)]">Empty collection</li>
          ) : (
            items.map((e) => (
              <li key={e.id} className="rounded-md border border-[var(--border)] px-2 py-1">
                {e.companyLabel}
              </li>
            ))
          )}
        </ul>
        <div className="flex flex-wrap gap-2">
          {onFavorite ? (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              aria-pressed={collection.favorite}
              onClick={() => onFavorite(collection.id)}
            >
              {collection.favorite ? "Unfavorite" : "Favorite"}
            </Button>
          ) : null}
          {onRename ? (
            <Button type="button" size="sm" variant="secondary" onClick={() => onRename(collection.id)}>
              Rename
            </Button>
          ) : null}
          {onAdd ? (
            <Button type="button" size="sm" variant="secondary" onClick={() => onAdd(collection.id)}>
              Add research
            </Button>
          ) : null}
          {onDelete ? (
            <Button type="button" size="sm" variant="danger" onClick={() => onDelete(collection.id)}>
              Delete
            </Button>
          ) : null}
        </div>
      </CardBody>
    </Card>
  );
});

export const ResearchBookmarkCard = memo(function ResearchBookmarkCard({
  envelope,
}: {
  envelope: DemoResearchEnvelope;
}) {
  const snap = useSharedResearch();
  return (
    <Card>
      <CardHeader title={envelope.companyLabel} description="Bookmark / pin / favorite — session" />
      <CardBody className="space-y-2 text-sm">
        <p className="text-[var(--muted)]">{envelope.thesis.slice(0, 120)}…</p>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Bookmark actions">
          <Button
            type="button"
            size="sm"
            variant={snap.bookmarkedIds.includes(envelope.id) ? "primary" : "secondary"}
            aria-pressed={snap.bookmarkedIds.includes(envelope.id)}
            onClick={() => toggleBookmark(envelope.id)}
          >
            Bookmark
          </Button>
          <Button
            type="button"
            size="sm"
            variant={snap.pinnedIds.includes(envelope.id) ? "primary" : "secondary"}
            aria-pressed={snap.pinnedIds.includes(envelope.id)}
            onClick={() => togglePin(envelope.id)}
          >
            Pin
          </Button>
          <Button
            type="button"
            size="sm"
            variant={snap.favoriteIds.includes(envelope.id) ? "primary" : "secondary"}
            aria-pressed={snap.favoriteIds.includes(envelope.id)}
            onClick={() => toggleFavorite(envelope.id)}
          >
            Favorite
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => recordOpened(envelope.id)}
          >
            Mark viewed
          </Button>
        </div>
        <p className="text-xs text-[var(--muted)]">
          Confidence: {envelope.confidence} · Risk: {envelope.risk}
        </p>
      </CardBody>
    </Card>
  );
});

export const ResearchActivityFeed = memo(function ResearchActivityFeed({
  items,
}: {
  items: SharedResearchActivityItem[];
}) {
  return (
    <Card>
      <CardHeader title="Research Activity" description="Session feed — not live multi-user" />
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

export const ResearchFilterPanel = memo(function ResearchFilterPanel() {
  const snap = useSharedResearch();
  const f = snap.filters;
  const selectClass =
    "mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]";

  return (
    <Card>
      <CardHeader title="Research Filters" description="Presentation filters over demo envelopes" />
      <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <label className="block text-xs text-[var(--muted)] sm:col-span-2 lg:col-span-3">
          Search
          <input
            type="search"
            value={f.query}
            onChange={(e) => setSharedFilters({ query: e.target.value })}
            className={selectClass}
            aria-label="Search shared research"
            placeholder="Company or thesis…"
          />
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Sector
          <select
            value={f.sector}
            onChange={(e) => setSharedFilters({ sector: e.target.value })}
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
          Industry
          <select
            value={f.industry}
            onChange={(e) => setSharedFilters({ industry: e.target.value })}
            className={selectClass}
            aria-label="Filter by industry"
          >
            <option value="">All</option>
            {FILTER_INDUSTRIES.map((s) => (
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
              setSharedFilters({
                marketCap: e.target.value as typeof f.marketCap,
              })
            }
            className={selectClass}
            aria-label="Filter by market cap"
          >
            <option value="">All</option>
            <option value="mega">Mega</option>
            <option value="large">Large</option>
            <option value="mid">Mid</option>
            <option value="small">Small</option>
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Rating
          <select
            value={f.rating}
            onChange={(e) => setSharedFilters({ rating: e.target.value })}
            className={selectClass}
            aria-label="Filter by rating"
          >
            <option value="">All</option>
            {FILTER_RATINGS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Risk contains
          <input
            value={f.risk}
            onChange={(e) => setSharedFilters({ risk: e.target.value })}
            className={selectClass}
            aria-label="Filter by risk text"
            placeholder="e.g. Moderate"
          />
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Valuation contains
          <input
            value={f.valuation}
            onChange={(e) => setSharedFilters({ valuation: e.target.value })}
            className={selectClass}
            aria-label="Filter by valuation text"
            placeholder="e.g. Fair"
          />
        </label>
        <fieldset className="sm:col-span-2 lg:col-span-3">
          <legend className="text-xs text-[var(--muted)]">Flags</legend>
          <div className="mt-2 flex flex-wrap gap-3">
            {(
              [
                ["watchlistOnly", "Watchlist", f.watchlistOnly],
                ["bookmarkedOnly", "Bookmarked", f.bookmarkedOnly],
                ["pinnedOnly", "Pinned", f.pinnedOnly],
                ["favoritesOnly", "Favorites", f.favoritesOnly],
              ] as const
            ).map(([key, label, checked]) => (
              <label key={key} className="flex min-h-11 items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => setSharedFilters({ [key]: e.target.checked })}
                />
                {label}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="sm:col-span-2 lg:col-span-3">
          <Button type="button" variant="ghost" size="sm" onClick={() => resetSharedFilters()}>
            Reset filters
          </Button>
        </div>
      </CardBody>
    </Card>
  );
});

export const ResearchOverviewDashboard = memo(function ResearchOverviewDashboard() {
  const snap = useSharedResearch();
  const overview = useMemo(() => buildSharedOverview(snap), [snap]);
  const cells = [
    ["Research count", String(overview.researchCount)],
    ["Collections", String(overview.collectionsCount)],
    ["Bookmarks", String(overview.bookmarksCount)],
    ["Comparison sessions", String(overview.comparisonSessions)],
    ["Coverage", overview.coverage],
    ["Freshness", overview.freshness],
  ] as const;

  return (
    <Card>
      <CardHeader
        title="Research Overview Dashboard"
        description="Presentation metrics from existing DSP demos"
      />
      <CardBody className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {cells.map(([label, value]) => (
            <div
              key={label}
              className="rounded-md border border-[var(--border)] bg-[var(--surface-2)]/40 p-3"
            >
              <p className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</p>
              <p className="mt-1 text-sm font-medium">{value}</p>
            </div>
          ))}
        </div>
        <div>
          <p className="mb-1 text-xs uppercase tracking-wide text-[var(--muted)]">
            Recently active companies
          </p>
          <ul className="flex flex-wrap gap-2" aria-label="Recently active companies">
            {overview.recentlyActive.map((name) => (
              <li key={name}>
                <Badge>{name}</Badge>
              </li>
            ))}
          </ul>
        </div>
      </CardBody>
    </Card>
  );
});

export const ResearchLibraryPanel = memo(function ResearchLibraryPanel() {
  const snap = useSharedResearch();
  const filtered = useMemo(() => filterEnvelopes(snap), [snap]);
  const recent = useMemo(
    () =>
      snap.recentlyViewed
        .map((id) => getEnvelope(id))
        .filter((e): e is DemoResearchEnvelope => Boolean(e)),
    [snap.recentlyViewed],
  );
  const saved = useMemo(
    () =>
      snap.bookmarkedIds
        .map((id) => getEnvelope(id))
        .filter((e): e is DemoResearchEnvelope => Boolean(e)),
    [snap.bookmarkedIds],
  );
  const pinned = useMemo(
    () =>
      snap.pinnedIds
        .map((id) => getEnvelope(id))
        .filter((e): e is DemoResearchEnvelope => Boolean(e)),
    [snap.pinnedIds],
  );
  const favorited = useMemo(
    () =>
      snap.favoriteIds
        .map((id) => getEnvelope(id))
        .filter((e): e is DemoResearchEnvelope => Boolean(e)),
    [snap.favoriteIds],
  );
  const activeCollections = useMemo(
    () => snap.collections.filter((c) => c.lifecycle === "active"),
    [snap.collections],
  );

  return (
    <div className="space-y-4">
      <ResearchFilterPanel />
      <Card>
        <CardHeader
          title="Shared Research Library"
          description={`${filtered.length} envelopes after filters — truth fields unchanged`}
        />
        <CardBody>
          <WindowedList
            items={filtered}
            initial={6}
            step={4}
            empty={<EmptyState title="No research matches filters" />}
            renderItem={(e) => {
              const meta = metaForEnvelope(e.id);
              return (
                <article
                  key={e.id}
                  className="rounded-md border border-[var(--border)] p-3 text-sm"
                  aria-label={e.companyLabel}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <h3 className="font-medium">{e.companyLabel}</h3>
                      <p className="mt-1 text-[var(--muted)]">{e.thesis.slice(0, 110)}…</p>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {snap.bookmarkedIds.includes(e.id) ? <Badge>Bookmarked</Badge> : null}
                      {snap.pinnedIds.includes(e.id) ? <Badge>Pinned</Badge> : null}
                      {snap.favoriteIds.includes(e.id) ? <Badge>Favorite</Badge> : null}
                    </div>
                  </div>
                  <p className="mt-2 text-xs text-[var(--muted)]">
                    {meta?.sector} · {meta?.industry} · {meta?.marketCap} · {meta?.rating}
                  </p>
                  <p className="mt-1 text-xs text-[var(--muted)]">
                    Confidence: {e.confidence} · Valuation: {e.valuation} · Risk: {e.risk}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() => recordOpened(e.id)}
                    >
                      Open
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      aria-pressed={snap.compareSelection.includes(e.id)}
                      onClick={() => toggleCompareSelection(e.id)}
                    >
                      {snap.compareSelection.includes(e.id) ? "In compare" : "Add to compare"}
                    </Button>
                    <Button type="button" size="sm" variant="ghost" onClick={() => toggleBookmark(e.id)}>
                      Bookmark
                    </Button>
                    <Button type="button" size="sm" variant="ghost" onClick={() => togglePin(e.id)}>
                      Pin
                    </Button>
                    <Button type="button" size="sm" variant="ghost" onClick={() => toggleFavorite(e.id)}>
                      Favorite
                    </Button>
                  </div>
                </article>
              );
            }}
          />
        </CardBody>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Recent Research" />
          <CardBody>
            <ul className="space-y-1 text-sm" aria-label="Recent research">
              {recent.map((e) => (
                <li key={e.id}>{e.companyLabel}</li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Saved / Bookmarked" />
          <CardBody>
            <ul className="space-y-1 text-sm" aria-label="Saved research">
              {saved.map((e) => (
                <li key={e.id}>{e.companyLabel}</li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Pinned Research" />
          <CardBody>
            <ul className="space-y-1 text-sm" aria-label="Pinned research">
              {pinned.map((e) => (
                <li key={e.id}>{e.companyLabel}</li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Bookmarked / Favorites" />
          <CardBody>
            <ul className="space-y-1 text-sm" aria-label="Favorite research">
              {favorited.map((e) => (
                <li key={e.id}>{e.companyLabel}</li>
              ))}
            </ul>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader title="Shared Collections" description="Active session collections" />
        <CardBody className="grid gap-3 md:grid-cols-2">
          {activeCollections.map((c) => (
            <ResearchCollectionCard key={c.id} collection={c} />
          ))}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Research Timeline" description="Session activity derived from workspace actions" />
        <CardBody>
          <ul className="space-y-2 text-sm" aria-label="Research timeline">
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

export const ResearchComparisonWorkspace = memo(function ResearchComparisonWorkspace() {
  const snap = useSharedResearch();
  const envelopes = useMemo(() => listResearchEnvelopes(), []);
  const rows = useMemo(
    () => buildCompareRows(snap.compareSelection),
    [snap.compareSelection],
  );
  const selectedEnvs = useMemo(
    () =>
      snap.compareSelection
        .map((id) => getEnvelope(id))
        .filter((e): e is DemoResearchEnvelope => Boolean(e)),
    [snap.compareSelection],
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader
          title="Select companies (2–5)"
          description="Reuses existing Business / Financial / Valuation / Risk / Summary fields — never regenerated"
        />
        <CardBody>
          <ul
            className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3"
            aria-label="Compare selection"
          >
            {envelopes.map((e) => {
              const checked = snap.compareSelection.includes(e.id);
              const disabled = !checked && snap.compareSelection.length >= 5;
              return (
                <li key={e.id}>
                  <label
                    className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-[var(--border)] px-3 text-sm ${
                      disabled ? "opacity-50" : ""
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={() => toggleCompareSelection(e.id)}
                    />
                    {e.companyLabel}
                  </label>
                </li>
              );
            })}
          </ul>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              type="button"
              disabled={snap.compareSelection.length < 2}
              onClick={() => commitComparisonSession()}
            >
              Record comparison session
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setCompareSelection([])}
            >
              Clear
            </Button>
          </div>
        </CardBody>
      </Card>

      {selectedEnvs.length >= 2 ? (
        <>
          <Card>
            <CardHeader title="Comparison table" description="Accessible reuse of envelope fields" />
            <CardBody className="overflow-x-auto">
              <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
                <caption className="sr-only">
                  Side-by-side comparison of selected research envelopes
                </caption>
                <thead>
                  <tr>
                    <th scope="col" className="border-b border-[var(--border)] px-2 py-2">
                      Dimension
                    </th>
                    {selectedEnvs.map((e) => (
                      <th
                        key={e.id}
                        scope="col"
                        className="border-b border-[var(--border)] px-2 py-2"
                      >
                        {e.companyLabel}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.dimension}>
                      <th
                        scope="row"
                        className="border-b border-[var(--border)] px-2 py-2 font-medium"
                      >
                        {row.label}
                      </th>
                      {row.values.map((v) => (
                        <td
                          key={`${row.dimension}-${v.companyLabel}`}
                          className="border-b border-[var(--border)] px-2 py-2 text-[var(--muted)]"
                        >
                          {v.value}
                        </td>
                      ))}
                    </tr>
                  ))}
                  <tr>
                    <th scope="row" className="border-b border-[var(--border)] px-2 py-2">
                      Research Summary
                    </th>
                    {selectedEnvs.map((e) => (
                      <td key={`sum-${e.id}`} className="border-b border-[var(--border)] px-2 py-2 text-[var(--muted)]">
                        {e.thesis.slice(0, 80)}…
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <th scope="row" className="border-b border-[var(--border)] px-2 py-2">
                      Evidence
                    </th>
                    {selectedEnvs.map((e) => (
                      <td key={`ev-${e.id}`} className="border-b border-[var(--border)] px-2 py-2 text-[var(--muted)]">
                        {e.evidence.join("; ")}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <th scope="row" className="border-b border-[var(--border)] px-2 py-2">
                      Methodology
                    </th>
                    {selectedEnvs.map((e) => (
                      <td key={`m-${e.id}`} className="border-b border-[var(--border)] px-2 py-2 text-[var(--muted)]">
                        {e.methodology}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <th scope="row" className="px-2 py-2">
                      Limitations
                    </th>
                    {selectedEnvs.map((e) => (
                      <td key={`l-${e.id}`} className="px-2 py-2 text-[var(--muted)]">
                        {e.limitations.join("; ")}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </CardBody>
          </Card>
          <p className="text-xs text-[var(--muted)]">
            Dimensions included: {COMPARE_DIMENSIONS.map((d) => d.label).join(" · ")}. Compare does
            not generate recommendations.
          </p>
        </>
      ) : (
        <EmptyState title="Select at least 2 companies to compare" />
      )}

      {snap.recentlyCompared.length > 0 ? (
        <Card>
          <CardHeader title="Recently Compared" />
          <CardBody>
            <ul className="space-y-2 text-sm" aria-label="Recently compared sets">
              {snap.recentlyCompared.map((set, i) => (
                <li key={i}>
                  <button
                    type="button"
                    className="min-h-11 text-left text-[var(--accent)] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                    onClick={() => setCompareSelection(set)}
                  >
                    {set.map((id) => getEnvelope(id)?.companyLabel ?? id).join(" · ")}
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

/* ── Page workspaces ────────────────────────────────────────────── */

export const SharedResearchWorkspace = memo(function SharedResearchWorkspace() {
  const snap = useSharedResearch();
  return (
    <SharedResearchShell
      title="Shared Research Workspace"
      description="Organize, compare, bookmark, and review existing DSP research — session only"
    >
      <ResearchQuickActions />
      <ResearchOverviewDashboard />
      <div className="grid gap-4 lg:grid-cols-2">
        <ResearchActivityFeed items={snap.activity.slice(0, 6)} />
        <Card>
          <CardHeader title="Trust reminder" />
          <CardBody className="text-sm text-[var(--muted)]">
            Research remains the single source of truth. This workspace never regenerates Business
            Analysis, Financial Analysis, Valuation, Risk, Evidence, Confidence, Methodology, or
            Limitations.
          </CardBody>
        </Card>
      </div>
    </SharedResearchShell>
  );
});

export const SharedResearchLibraryPage = memo(function SharedResearchLibraryPage() {
  return (
    <SharedResearchShell
      title="Shared Research Library"
      description="Recent · Saved · Pinned · Bookmarked · Collections · Timeline"
    >
      <ResearchLibraryPanel />
    </SharedResearchShell>
  );
});

export const SharedResearchCollectionsPage = memo(function SharedResearchCollectionsPage() {
  const snap = useSharedResearch();
  const [name, setName] = useState("");
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [addId, setAddId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [favoritesOnly, setFavoritesOnly] = useState(false);

  const active = useMemo(() => {
    let list = snap.collections.filter((c) => c.lifecycle === "active");
    if (favoritesOnly) list = list.filter((c) => c.favorite);
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      list = list.filter(
        (c) => c.name.toLowerCase().includes(q) || c.theme.toLowerCase().includes(q),
      );
    }
    return list;
  }, [snap.collections, query, favoritesOnly]);

  return (
    <SharedResearchShell
      title="Research Collections"
      description="Create · rename · delete · move · favorite — session presentation only"
    >
      <Card>
        <CardHeader title="Create / search collections" />
        <CardBody className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
          <label className="block flex-1 text-xs text-[var(--muted)]">
            New collection
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              aria-label="New collection name"
              placeholder="Collection name"
            />
          </label>
          <Button
            type="button"
            onClick={() => {
              createSharedCollection(name);
              setName("");
            }}
          >
            Create
          </Button>
          <label className="block flex-1 text-xs text-[var(--muted)]">
            Search collections
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              aria-label="Search collections"
            />
          </label>
          <label className="flex min-h-11 items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={favoritesOnly}
              onChange={(e) => setFavoritesOnly(e.target.checked)}
            />
            Favorites only
          </label>
        </CardBody>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {active.map((c) => (
          <ResearchCollectionCard
            key={c.id}
            collection={c}
            onFavorite={(id) => toggleCollectionFavorite(id)}
            onDelete={(id) => deleteSharedCollection(id)}
            onRename={(id) => {
              setRenameId(id);
              setRenameValue(c.name);
            }}
            onAdd={(id) => setAddId(id)}
          />
        ))}
      </div>

      {renameId ? (
        <Card>
          <CardHeader title="Rename collection" />
          <CardBody className="flex flex-wrap gap-2">
            <input
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              className="min-h-11 flex-1 rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              aria-label="Rename collection"
            />
            <Button
              type="button"
              onClick={() => {
                renameSharedCollection(renameId, renameValue);
                setRenameId(null);
              }}
            >
              Save
            </Button>
            <Button type="button" variant="ghost" onClick={() => setRenameId(null)}>
              Cancel
            </Button>
          </CardBody>
        </Card>
      ) : null}

      {addId ? (
        <Card>
          <CardHeader title="Move research into collection" />
          <CardBody className="flex flex-wrap gap-2">
            {listResearchEnvelopes().map((e) => (
              <Button
                key={e.id}
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => {
                  moveResearchToCollection(addId, e.id);
                  setAddId(null);
                }}
              >
                {e.companyLabel}
              </Button>
            ))}
            <Button type="button" variant="ghost" size="sm" onClick={() => setAddId(null)}>
              Cancel
            </Button>
          </CardBody>
        </Card>
      ) : null}
    </SharedResearchShell>
  );
});

export const SharedResearchComparePage = memo(function SharedResearchComparePage() {
  return (
    <SharedResearchShell
      title="Research Comparison"
      description="Compare 2–5 companies using existing DSP envelope fields only"
    >
      <ResearchComparisonWorkspace />
    </SharedResearchShell>
  );
});

export const SharedResearchBookmarksPage = memo(function SharedResearchBookmarksPage() {
  const snap = useSharedResearch();
  const envelopes = useMemo(() => listResearchEnvelopes(), []);
  const recentlyViewed = useMemo(
    () =>
      snap.recentlyViewed
        .map((id) => getEnvelope(id))
        .filter((e): e is DemoResearchEnvelope => Boolean(e)),
    [snap.recentlyViewed],
  );

  return (
    <SharedResearchShell
      title="Bookmarks & Favorites"
      description="Bookmark · Pin · Favorite · Recently viewed — session only"
    >
      <div className="grid gap-4 md:grid-cols-2">
        {envelopes.map((e) => (
          <ResearchBookmarkCard key={e.id} envelope={e} />
        ))}
      </div>
      <Card>
        <CardHeader title="Recently Viewed" />
        <CardBody>
          <ul className="space-y-1 text-sm" aria-label="Recently viewed research">
            {recentlyViewed.map((e) => (
              <li key={e.id}>{e.companyLabel}</li>
            ))}
          </ul>
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Recently Compared" />
        <CardBody>
          <ul className="space-y-2 text-sm" aria-label="Recently compared">
            {snap.recentlyCompared.map((set, i) => (
              <li key={i}>
                {set.map((id) => getEnvelope(id)?.companyLabel ?? id).join(" · ")}
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>
    </SharedResearchShell>
  );
});

export const SharedResearchActivityPage = memo(function SharedResearchActivityPage() {
  const snap = useSharedResearch();
  const buckets = useMemo(() => {
    const by = (kind: SharedResearchActivityItem["kind"]) =>
      snap.activity.filter((a) => a.kind === kind);
    return {
      opened: by("opened"),
      compared: by("compared"),
      presented: by("presented"),
      bookmarked: by("bookmarked"),
      collection_add: by("collection_add"),
    };
  }, [snap.activity]);

  return (
    <SharedResearchShell
      title="Research Activity"
      description="Opened · Compared · Presented · Bookmarked · Added to collections"
    >
      <ResearchActivityFeed items={snap.activity} />
      <div className="grid gap-4 md:grid-cols-2">
        {(
          [
            ["Recently Opened", buckets.opened],
            ["Recently Compared", buckets.compared],
            ["Recently Presented", buckets.presented],
            ["Recently Bookmarked", buckets.bookmarked],
            ["Recently Added to Collections", buckets.collection_add],
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
    </SharedResearchShell>
  );
});
