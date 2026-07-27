/**
 * In-memory Shared Research session (no persistence).
 * Organizes existing demo envelopes — never mutates research truth fields.
 */

import { getEnvelope, listResearchEnvelopes } from "./advisorResearchViewModel";
import { buildCompareRows } from "./advisorResearchViewModel";
import {
  DEFAULT_SHARED_RESEARCH_FILTERS,
  type SharedCollection,
  type SharedResearchActivityItem,
  type SharedResearchFilterState,
} from "./sharedResearchTypes";
import {
  metaForEnvelope,
  seedSharedActivity,
  seedSharedCollections,
} from "./sharedResearchModels";
import type { DemoResearchEnvelope } from "./advisorResearchTypes";

export type SharedResearchSnapshot = {
  collections: SharedCollection[];
  bookmarkedIds: string[];
  pinnedIds: string[];
  favoriteIds: string[];
  recentlyViewed: string[];
  recentlyCompared: string[][];
  compareSelection: string[];
  filters: SharedResearchFilterState;
  activity: SharedResearchActivityItem[];
  comparisonSessionCount: number;
};

let collections: SharedCollection[] = seedSharedCollections();
let bookmarkedIds: string[] = ["re-aurora", "re-beacon"];
let pinnedIds: string[] = ["re-aurora", "re-delta"];
let favoriteIds: string[] = ["re-aurora", "re-delta", "re-beacon"];
let recentlyViewed: string[] = ["re-aurora", "re-beacon", "re-cedar"];
let recentlyCompared: string[][] = [["re-aurora", "re-beacon", "re-delta"]];
let compareSelection: string[] = ["re-aurora", "re-beacon"];
let filters: SharedResearchFilterState = { ...DEFAULT_SHARED_RESEARCH_FILTERS };
let activity: SharedResearchActivityItem[] = seedSharedActivity();
let comparisonSessionCount = 1;

const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

function pushActivity(
  kind: SharedResearchActivityItem["kind"],
  label: string,
  envelopeId?: string,
) {
  activity = [
    {
      id: `act-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      kind,
      label,
      at: new Date().toISOString(),
      envelopeId,
    },
    ...activity,
  ].slice(0, 40);
}

export function subscribeSharedResearch(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSharedResearchSnapshot(): SharedResearchSnapshot {
  return {
    collections,
    bookmarkedIds,
    pinnedIds,
    favoriteIds,
    recentlyViewed,
    recentlyCompared,
    compareSelection,
    filters,
    activity,
    comparisonSessionCount,
  };
}

export function setSharedFilters(patch: Partial<SharedResearchFilterState>) {
  filters = { ...filters, ...patch };
  emit();
}

export function resetSharedFilters() {
  filters = { ...DEFAULT_SHARED_RESEARCH_FILTERS };
  emit();
}

export function recordOpened(envelopeId: string) {
  const env = getEnvelope(envelopeId);
  if (!env) return;
  recentlyViewed = [envelopeId, ...recentlyViewed.filter((id) => id !== envelopeId)].slice(
    0,
    12,
  );
  pushActivity("opened", `Opened — ${env.companyLabel}`, envelopeId);
  emit();
}

export function toggleBookmark(envelopeId: string) {
  const env = getEnvelope(envelopeId);
  if (!env) return;
  const has = bookmarkedIds.includes(envelopeId);
  bookmarkedIds = has
    ? bookmarkedIds.filter((id) => id !== envelopeId)
    : [...bookmarkedIds, envelopeId];
  if (!has) pushActivity("bookmarked", `Bookmarked — ${env.companyLabel}`, envelopeId);
  emit();
}

export function togglePin(envelopeId: string) {
  const env = getEnvelope(envelopeId);
  if (!env) return;
  const has = pinnedIds.includes(envelopeId);
  pinnedIds = has
    ? pinnedIds.filter((id) => id !== envelopeId)
    : [...pinnedIds, envelopeId];
  if (!has) pushActivity("pinned", `Pinned — ${env.companyLabel}`, envelopeId);
  emit();
}

export function toggleFavorite(envelopeId: string) {
  const env = getEnvelope(envelopeId);
  if (!env) return;
  const has = favoriteIds.includes(envelopeId);
  favoriteIds = has
    ? favoriteIds.filter((id) => id !== envelopeId)
    : [...favoriteIds, envelopeId];
  if (!has) pushActivity("favorited", `Favorited — ${env.companyLabel}`, envelopeId);
  emit();
}

export function toggleCompareSelection(envelopeId: string) {
  if (compareSelection.includes(envelopeId)) {
    compareSelection = compareSelection.filter((id) => id !== envelopeId);
  } else if (compareSelection.length < 5) {
    compareSelection = [...compareSelection, envelopeId];
  }
  emit();
}

export function setCompareSelection(ids: string[]) {
  compareSelection = [...new Set(ids)].slice(0, 5);
  emit();
}

export function commitComparisonSession() {
  if (compareSelection.length < 2) return;
  recentlyCompared = [compareSelection, ...recentlyCompared].slice(0, 8);
  comparisonSessionCount += 1;
  const labels = compareSelection
    .map((id) => getEnvelope(id)?.companyLabel ?? id)
    .join(" · ");
  pushActivity("compared", `Compared — ${labels}`);
  emit();
}

export function createSharedCollection(name: string) {
  const trimmed = name.trim() || "Untitled collection";
  const next: SharedCollection = {
    id: `scol-${Date.now()}`,
    name: trimmed,
    theme: "custom",
    itemIds: [],
    lifecycle: "active",
    favorite: false,
    updatedAt: new Date().toISOString(),
  };
  collections = [next, ...collections];
  emit();
  return next;
}

export function renameSharedCollection(id: string, name: string) {
  const trimmed = name.trim();
  if (!trimmed) return;
  collections = collections.map((c) =>
    c.id === id
      ? { ...c, name: trimmed, updatedAt: new Date().toISOString() }
      : c,
  );
  emit();
}

export function deleteSharedCollection(id: string) {
  collections = collections.map((c) =>
    c.id === id
      ? { ...c, lifecycle: "archived", updatedAt: new Date().toISOString() }
      : c,
  );
  emit();
}

export function toggleCollectionFavorite(id: string) {
  collections = collections.map((c) =>
    c.id === id ? { ...c, favorite: !c.favorite, updatedAt: new Date().toISOString() } : c,
  );
  emit();
}

export function moveResearchToCollection(collectionId: string, envelopeId: string) {
  const env = getEnvelope(envelopeId);
  if (!env) return;
  collections = collections.map((c) => {
    if (c.id !== collectionId) return c;
    if (c.itemIds.includes(envelopeId)) return c;
    return {
      ...c,
      itemIds: [...c.itemIds, envelopeId],
      updatedAt: new Date().toISOString(),
    };
  });
  const col = collections.find((c) => c.id === collectionId);
  pushActivity(
    "collection_add",
    `Added ${env.companyLabel} to ${col?.name ?? "collection"}`,
    envelopeId,
  );
  emit();
}

export function removeResearchFromCollection(collectionId: string, envelopeId: string) {
  collections = collections.map((c) =>
    c.id === collectionId
      ? {
          ...c,
          itemIds: c.itemIds.filter((id) => id !== envelopeId),
          updatedAt: new Date().toISOString(),
        }
      : c,
  );
  emit();
}

export function filterEnvelopes(
  snap: SharedResearchSnapshot = getSharedResearchSnapshot(),
): DemoResearchEnvelope[] {
  const f = snap.filters;
  const q = f.query.trim().toLowerCase();

  return listResearchEnvelopes().filter((e) => {
    const meta = metaForEnvelope(e.id);
    if (q && !e.companyLabel.toLowerCase().includes(q) && !e.thesis.toLowerCase().includes(q)) {
      return false;
    }
    if (f.sector && meta?.sector !== f.sector) return false;
    if (f.industry && meta?.industry !== f.industry) return false;
    if (f.marketCap && meta?.marketCap !== f.marketCap) return false;
    if (f.rating && meta?.rating !== f.rating) return false;
    if (f.risk && !e.risk.toLowerCase().includes(f.risk.toLowerCase())) return false;
    if (f.valuation && !e.valuation.toLowerCase().includes(f.valuation.toLowerCase())) {
      return false;
    }
    if (f.watchlistOnly && !meta?.watchlist) return false;
    if (f.bookmarkedOnly && !snap.bookmarkedIds.includes(e.id)) return false;
    if (f.pinnedOnly && !snap.pinnedIds.includes(e.id)) return false;
    if (f.favoritesOnly && !snap.favoriteIds.includes(e.id)) return false;
    return true;
  });
}

export function buildSharedOverview(snap: SharedResearchSnapshot = getSharedResearchSnapshot()) {
  const envelopes = listResearchEnvelopes();
  const activeCollections = snap.collections.filter((c) => c.lifecycle === "active");
  const newest = [...envelopes].sort((a, b) => b.viewedAt.localeCompare(a.viewedAt))[0];
  const oldest = [...envelopes].sort((a, b) => a.viewedAt.localeCompare(b.viewedAt))[0];

  return {
    researchCount: envelopes.length,
    collectionsCount: activeCollections.length,
    bookmarksCount: snap.bookmarkedIds.length,
    comparisonSessions: snap.comparisonSessionCount,
    coverage: `${envelopes.length} demo companies · ${activeCollections.length} collections`,
    recentlyActive: snap.recentlyViewed
      .map((id) => getEnvelope(id)?.companyLabel)
      .filter(Boolean)
      .slice(0, 5) as string[],
    freshness: newest && oldest
      ? `Newest view ${newest.viewedAt.slice(0, 10)} · Oldest ${oldest.viewedAt.slice(0, 10)} (demo)`
      : "n/a",
  };
}

export { buildCompareRows, getEnvelope, listResearchEnvelopes };
