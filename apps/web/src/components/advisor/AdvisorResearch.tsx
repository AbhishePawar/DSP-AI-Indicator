"use client";

import { memo, useCallback, useMemo, useState, type ReactNode } from "react";

import { ResearchCollectionSidebar } from "@/components/advisor/ResearchCollectionSidebar";
import { AdvisorShell } from "@/components/advisor/AdvisorWorkspace";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { WindowedList } from "@/lib/perf/WindowedList";
import {
  ADVISOR_RESEARCH_TRUST,
  buildCompareRows,
  buildQuickReview,
  buildResearchLibrary,
  listAdvisorBookmarks,
  listAdvisorResearchNotes,
  listAdvisorResearchTimeline,
  listResearchEnvelopes,
  seedCollections,
  unifiedSearch,
} from "@/lib/advisor/advisorResearchViewModel";
import type {
  AdvisorResearchCollection,
  DemoResearchEnvelope,
  ResearchCollectionTheme,
} from "@/lib/advisor/advisorResearchTypes";

function ResearchShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <AdvisorShell title={title} description={description}>
      <p role="note" className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm">
        {ADVISOR_RESEARCH_TRUST}
      </p>
      <div className="flex flex-col gap-4 lg:flex-row">
        <ResearchCollectionSidebar />
        <div className="min-w-0 flex-1 space-y-4">{children}</div>
      </div>
    </AdvisorShell>
  );
}

export function FavoriteBadge() {
  return <Badge tone="accent">Favorite</Badge>;
}

export function ResearchTag({ label }: { label: string }) {
  return <Badge tone="neutral">{label}</Badge>;
}

export function ResearchSearch({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const hits = useMemo(() => unifiedSearch(value), [value]);
  return (
    <div className="space-y-2">
      <label className="block text-sm">
        <span className="font-medium">Unified search</span>
        <input
          type="search"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Companies, collections, reports, bookmarks, notes…"
          className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          aria-label="Unified research search"
        />
      </label>
      {value.trim() ? (
        <ul className="space-y-1 text-sm" aria-live="polite">
          {hits.length === 0 ? (
            <li className="text-[var(--muted)]">No matches</li>
          ) : (
            hits.map((h) => (
              <li
                key={`${h.kind}-${h.id}`}
                className="rounded-md border border-[var(--border)] px-3 py-2"
              >
                <span className="mr-2">
                  <Badge tone="neutral">{h.kind}</Badge>
                </span>
                <span className="font-medium">{h.label}</span>
                <p className="text-xs text-[var(--muted)]">{h.detail}</p>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}

export const QuickReviewCard = memo(function QuickReviewCard({
  envelope,
}: {
  envelope: DemoResearchEnvelope;
}) {
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={envelope.companyLabel}
        description="Quick review — reused demo DSP envelope"
        action={<Badge tone="accent">Demo</Badge>}
      />
      <CardBody className="space-y-2 text-sm">
        <p>
          <span className="font-medium">Investment thesis — </span>
          {envelope.thesis}
        </p>
        <div>
          <p className="font-medium">Top risks</p>
          <ul className="list-disc pl-5 text-[var(--muted)]">
            {envelope.topRisks.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-medium">Key opportunities</p>
          <ul className="list-disc pl-5 text-[var(--muted)]">
            {envelope.keyOpportunities.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ul>
        </div>
        <p>
          <span className="font-medium">Valuation summary — </span>
          {envelope.valuationSummary}
        </p>
        <p>
          <span className="font-medium">Confidence — </span>
          {envelope.confidence}
        </p>
        <p>
          <span className="font-medium">Methodology — </span>
          {envelope.methodology}
        </p>
        <div>
          <p className="font-medium">Evidence</p>
          <ul className="list-disc pl-5 text-[var(--muted)]">
            {envelope.evidence.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-medium">Limitations</p>
          <ul className="list-disc pl-5 text-[var(--muted)]">
            {envelope.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </div>
      </CardBody>
    </Card>
  );
});

export const ResearchBookmarkCard = memo(function ResearchBookmarkCard({
  label,
  kind,
  tags,
}: {
  label: string;
  kind: string;
  tags: string[];
}) {
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={label}
        action={kind === "favorite" ? <FavoriteBadge /> : <Badge tone="neutral">{kind}</Badge>}
      />
      <CardBody className="flex flex-wrap gap-1">
        {tags.map((t) => (
          <ResearchTag key={t} label={t} />
        ))}
      </CardBody>
    </Card>
  );
});

export function ResearchTimelineCard() {
  const events = useMemo(() => listAdvisorResearchTimeline(), []);
  return (
    <Card>
      <CardHeader title="Research timeline" description="Demo activity — not engine events" />
      <CardBody>
        <ol className="space-y-3 border-l-2 border-[var(--border)] pl-4">
          {events.map((e) => (
            <li key={e.id} className="relative text-sm">
              <span
                className="absolute -left-[1.35rem] top-1.5 h-2.5 w-2.5 rounded-full bg-[var(--accent)]"
                aria-hidden
              />
              <p className="font-medium">{e.label}</p>
              <p className="text-xs text-[var(--muted)]">
                {e.kind.replace(/_/g, " ")} · {new Date(e.occurredAt).toLocaleString()}
              </p>
            </li>
          ))}
        </ol>
      </CardBody>
    </Card>
  );
}

export const ResearchLibraryWorkspace = memo(function ResearchLibraryWorkspace() {
  const [query, setQuery] = useState("");
  const library = useMemo(() => buildResearchLibrary(), []);
  const featured = library.recentlyViewed[0];

  return (
    <ResearchShell
      title="Research Library"
      description="Organize existing DSP research for client servicing — presentation only."
    >
      <ResearchSearch value={query} onChange={setQuery} />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Card>
          <CardHeader title="Favorite companies" />
          <CardBody>
            <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
              {library.favoriteCompanies.map((c) => (
                <li key={c}>
                  {c} <FavoriteBadge />
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Saved research" />
          <CardBody>
            <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
              {library.savedResearch.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Recent reports" />
          <CardBody>
            <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
              {library.recentReports.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Pinned research" />
          <CardBody>
            <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
              {library.pinnedResearch.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <Card className="sm:col-span-2">
          <CardHeader title="Collections" />
          <CardBody className="flex flex-wrap gap-2">
            {library.collections.map((c) => (
              <Badge key={c.id} tone="neutral">
                {c.name}
              </Badge>
            ))}
          </CardBody>
        </Card>
      </div>
      <section aria-labelledby="recently-viewed">
        <h2 id="recently-viewed" className="mb-3 font-[family-name:var(--font-display)] text-xl">
          Recently viewed
        </h2>
        <WindowedList
          items={library.recentlyViewed}
          initial={4}
          empty={<EmptyState title="No recent research" />}
          renderItem={(e) => <QuickReviewCard key={e.id} envelope={e} />}
        />
      </section>
      {featured ? (
        <section aria-labelledby="featured-quick">
          <h2 id="featured-quick" className="mb-3 font-[family-name:var(--font-display)] text-xl">
            Featured quick review
          </h2>
          <QuickReviewCard envelope={featured} />
        </section>
      ) : null}
    </ResearchShell>
  );
});

export const ResearchCollectionWorkspace = memo(function ResearchCollectionWorkspace() {
  const [collections, setCollections] = useState<AdvisorResearchCollection[]>(() =>
    seedCollections(),
  );
  const [newName, setNewName] = useState("");
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const active = useMemo(
    () => collections.filter((c) => c.lifecycle === "active"),
    [collections],
  );
  const archived = useMemo(
    () => collections.filter((c) => c.lifecycle === "archived"),
    [collections],
  );

  const createCollection = useCallback(() => {
    const name = newName.trim() || "Custom";
    const id = `acol-custom-${Date.now().toString(36)}`;
    setCollections((prev) => [
      {
        id,
        name,
        theme: "custom" as ResearchCollectionTheme,
        itemIds: [],
        lifecycle: "active",
        updatedAt: new Date().toISOString(),
      },
      ...prev,
    ]);
    setNewName("");
  }, [newName]);

  const renameCollection = useCallback(() => {
    if (!renameId || !renameValue.trim()) return;
    setCollections((prev) =>
      prev.map((c) =>
        c.id === renameId
          ? { ...c, name: renameValue.trim(), updatedAt: new Date().toISOString() }
          : c,
      ),
    );
    setRenameId(null);
    setRenameValue("");
  }, [renameId, renameValue]);

  const archiveCollection = useCallback((id: string) => {
    setCollections((prev) =>
      prev.map((c) =>
        c.id === id
          ? { ...c, lifecycle: "archived", updatedAt: new Date().toISOString() }
          : c,
      ),
    );
  }, []);

  return (
    <ResearchShell
      title="Research Collections"
      description="Growth · Value · Dividend · Small Cap · Large Cap · High Quality · Custom — session demo only."
    >
      <Card>
        <CardHeader title="Create collection (demo)" description="In-session only — not persisted" />
        <CardBody className="flex flex-wrap gap-2">
          <input
            className="min-h-11 min-w-[12rem] flex-1 rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Collection name"
            aria-label="New collection name"
          />
          <Button type="button" onClick={createCollection}>
            Create
          </Button>
        </CardBody>
      </Card>
      <div className="grid gap-3 md:grid-cols-2">
        {active.map((c) => (
          <Card key={c.id} className="dsp-interactive">
            <CardHeader
              title={c.name}
              description={`${c.theme.replace(/_/g, " ")} · ${c.itemIds.length} envelopes`}
              action={<Badge tone="success">Active</Badge>}
            />
            <CardBody className="space-y-2 text-sm">
              <ul className="list-disc pl-5 text-[var(--muted)]">
                {c.itemIds.length === 0 ? (
                  <li>Empty</li>
                ) : (
                  c.itemIds.map((id) => {
                    const env = buildQuickReview(id);
                    return <li key={id}>{env?.companyLabel ?? id}</li>;
                  })
                )}
              </ul>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setRenameId(c.id);
                    setRenameValue(c.name);
                  }}
                >
                  Rename
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => archiveCollection(c.id)}
                >
                  Archive
                </Button>
              </div>
            </CardBody>
          </Card>
        ))}
      </div>
      {renameId ? (
        <Card>
          <CardHeader title="Rename collection" />
          <CardBody className="flex flex-wrap gap-2">
            <input
              className="min-h-11 flex-1 rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              aria-label="Rename collection"
            />
            <Button type="button" onClick={renameCollection}>
              Save name
            </Button>
            <Button type="button" variant="ghost" onClick={() => setRenameId(null)}>
              Cancel
            </Button>
          </CardBody>
        </Card>
      ) : null}
      {archived.length > 0 ? (
        <section aria-labelledby="archived-cols">
          <h2 id="archived-cols" className="mb-2 font-[family-name:var(--font-display)] text-lg">
            Archived
          </h2>
          <ul className="list-disc pl-5 text-sm text-[var(--muted)]">
            {archived.map((c) => (
              <li key={c.id}>{c.name}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </ResearchShell>
  );
});

export const CompareWorkspace = memo(function CompareWorkspace() {
  const envelopes = useMemo(() => listResearchEnvelopes(), []);
  const [selected, setSelected] = useState<string[]>(() =>
    envelopes.slice(0, 3).map((e) => e.id),
  );

  const toggle = useCallback((id: string) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 5) return prev;
      return [...prev, id];
    });
  }, []);

  const rows = useMemo(() => buildCompareRows(selected), [selected]);

  return (
    <ResearchShell
      title="Company Compare"
      description="Select 2–5 demo envelopes. Reuses existing research fields — no new conclusions."
    >
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Companies ({selected.length}/5)</legend>
        <div className="flex flex-wrap gap-2">
          {envelopes.map((e) => {
            const on = selected.includes(e.id);
            return (
              <button
                key={e.id}
                type="button"
                aria-pressed={on}
                onClick={() => toggle(e.id)}
                className={`min-h-11 rounded-md border px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
                  on
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)]"
                }`}
              >
                {e.companyLabel}
              </button>
            );
          })}
        </div>
      </fieldset>
      {selected.length < 2 ? (
        <EmptyState
          title="Select at least 2 companies"
          description="Comparison uses demo DSP envelope fields only."
        />
      ) : (
        <div className="overflow-x-auto" role="region" aria-label="Comparison table">
          <table className="w-full min-w-[40rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left">
                <th className="p-2 font-medium">Dimension</th>
                {rows[0]?.values.map((v) => (
                  <th key={v.companyLabel} className="p-2 font-medium">
                    {v.companyLabel}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.dimension} className="border-b border-[var(--border)]">
                  <th scope="row" className="p-2 text-left font-medium">
                    {row.label}
                  </th>
                  {row.values.map((v) => (
                    <td key={v.companyLabel} className="p-2 text-[var(--muted)]">
                      {v.value}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-[var(--muted)]">
        Evidence · Confidence · Methodology · Limitations remain on each envelope&apos;s Quick
        Review — compare does not generate recommendations.
      </p>
    </ResearchShell>
  );
});

export const AdvisorResearchNotesWorkspace = memo(function AdvisorResearchNotesWorkspace() {
  const notes = useMemo(() => listAdvisorResearchNotes(), []);
  return (
    <ResearchShell title="Research Notes" description="Pinned · Private · Client · Meeting · Findings — demo only.">
      <div className="space-y-3">
        {notes.map((n) => (
          <Card key={n.id} className="dsp-interactive">
            <CardHeader
              title={n.title}
              action={
                <div className="flex gap-1">
                  {n.pinned ? <Badge tone="accent">Pinned</Badge> : null}
                  <Badge tone="neutral">{n.kind}</Badge>
                </div>
              }
            />
            <CardBody className="text-sm text-[var(--muted)] whitespace-pre-wrap">{n.body}</CardBody>
          </Card>
        ))}
      </div>
    </ResearchShell>
  );
});

export const AdvisorResearchTimelineWorkspace = memo(function AdvisorResearchTimelineWorkspace() {
  return (
    <ResearchShell title="Research Timeline" description="Analysis · updates · reports · collections · favorites.">
      <ResearchTimelineCard />
    </ResearchShell>
  );
});

export const AdvisorResearchBookmarksWorkspace = memo(
  function AdvisorResearchBookmarksWorkspace() {
    const bookmarks = useMemo(() => listAdvisorBookmarks(), []);
    return (
      <ResearchShell
        title="Research Bookmarks"
        description="Favorites · Recent · Pinned · Collections · Tags"
      >
        <WindowedList
          items={bookmarks}
          initial={8}
          empty={<EmptyState title="No bookmarks" />}
          className="grid gap-3 sm:grid-cols-2"
          renderItem={(b) => (
            <ResearchBookmarkCard key={b.id} label={b.label} kind={b.kind} tags={b.tags} />
          )}
        />
      </ResearchShell>
    );
  },
);

/** Default /advisor/research entry = library */
export const AdvisorResearchWorkspace = ResearchLibraryWorkspace;
