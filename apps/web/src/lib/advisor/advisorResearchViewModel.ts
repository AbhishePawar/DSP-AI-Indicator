/**
 * Advisor research view-models — pure transforms; session collection edits are UI-local.
 */

import {
  ADVISOR_RESEARCH_TRUST,
  demoAdvisorBookmarks,
  demoAdvisorResearchNotes,
  demoAdvisorResearchTimeline,
  demoFavoriteCompanies,
  demoPinnedResearch,
  demoRecentReports,
  demoResearchEnvelopes,
  demoSavedResearch,
  seedAdvisorCollections,
} from "./advisorResearchModels";
import type {
  AdvisorResearchCollection,
  AdvisorResearchNote,
  CompareDimension,
  DemoResearchEnvelope,
} from "./advisorResearchTypes";
import { COMPARE_DIMENSIONS } from "./advisorResearchTypes";

export type ResearchLibraryView = {
  trust: string;
  recentlyViewed: DemoResearchEnvelope[];
  savedResearch: string[];
  favoriteCompanies: string[];
  recentReports: string[];
  collections: AdvisorResearchCollection[];
  pinnedResearch: string[];
};

export type QuickReviewView = DemoResearchEnvelope;

export type CompareRow = {
  dimension: CompareDimension;
  label: string;
  values: { companyLabel: string; value: string }[];
};

export type UnifiedSearchHit = {
  id: string;
  kind: "company" | "collection" | "report" | "bookmark" | "note";
  label: string;
  detail: string;
};

export function buildResearchLibrary(
  collections: AdvisorResearchCollection[] = seedAdvisorCollections,
): ResearchLibraryView {
  const recentlyViewed = [...demoResearchEnvelopes].sort((a, b) =>
    b.viewedAt.localeCompare(a.viewedAt),
  );
  return {
    trust: ADVISOR_RESEARCH_TRUST,
    recentlyViewed,
    savedResearch: demoSavedResearch,
    favoriteCompanies: demoFavoriteCompanies,
    recentReports: demoRecentReports,
    collections: collections.filter((c) => c.lifecycle === "active"),
    pinnedResearch: demoPinnedResearch,
  };
}

export function listResearchEnvelopes(): DemoResearchEnvelope[] {
  return demoResearchEnvelopes;
}

export function getEnvelope(id: string): DemoResearchEnvelope | undefined {
  return demoResearchEnvelopes.find((e) => e.id === id);
}

export function buildQuickReview(id: string): QuickReviewView | null {
  return getEnvelope(id) ?? null;
}

export function buildCompareRows(envelopeIds: string[]): CompareRow[] {
  const selected = envelopeIds
    .map((id) => getEnvelope(id))
    .filter((e): e is DemoResearchEnvelope => Boolean(e))
    .slice(0, 5);
  if (selected.length < 2) return [];

  return COMPARE_DIMENSIONS.map((dim) => ({
    dimension: dim.id,
    label: dim.label,
    values: selected.map((e) => ({
      companyLabel: e.companyLabel,
      value: String(e[dim.id]),
    })),
  }));
}

export function listAdvisorResearchNotes(): AdvisorResearchNote[] {
  return [...demoAdvisorResearchNotes].sort(
    (a, b) => Number(b.pinned) - Number(a.pinned) || b.updatedAt.localeCompare(a.updatedAt),
  );
}

export function listAdvisorResearchTimeline() {
  return [...demoAdvisorResearchTimeline].sort((a, b) =>
    b.occurredAt.localeCompare(a.occurredAt),
  );
}

export function listAdvisorBookmarks() {
  return demoAdvisorBookmarks;
}

export function seedCollections(): AdvisorResearchCollection[] {
  return seedAdvisorCollections.map((c) => ({ ...c, itemIds: [...c.itemIds] }));
}

export function unifiedSearch(query: string): UnifiedSearchHit[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const hits: UnifiedSearchHit[] = [];

  for (const e of demoResearchEnvelopes) {
    if (e.companyLabel.toLowerCase().includes(q) || e.thesis.toLowerCase().includes(q)) {
      hits.push({
        id: e.id,
        kind: "company",
        label: e.companyLabel,
        detail: e.thesis.slice(0, 120),
      });
    }
  }
  for (const c of seedAdvisorCollections) {
    if (c.name.toLowerCase().includes(q)) {
      hits.push({
        id: c.id,
        kind: "collection",
        label: c.name,
        detail: `${c.theme} · ${c.itemIds.length} items`,
      });
    }
  }
  for (const r of demoRecentReports) {
    if (r.toLowerCase().includes(q)) {
      hits.push({ id: r, kind: "report", label: r, detail: "Recent report (demo)" });
    }
  }
  for (const b of demoAdvisorBookmarks) {
    if (
      b.label.toLowerCase().includes(q) ||
      b.tags.some((t) => t.toLowerCase().includes(q))
    ) {
      hits.push({
        id: b.id,
        kind: "bookmark",
        label: b.label,
        detail: `${b.kind} · ${b.tags.join(", ")}`,
      });
    }
  }
  for (const n of demoAdvisorResearchNotes) {
    if (n.title.toLowerCase().includes(q) || n.body.toLowerCase().includes(q)) {
      hits.push({ id: n.id, kind: "note", label: n.title, detail: n.kind });
    }
  }
  return hits.slice(0, 40);
}

export { ADVISOR_RESEARCH_TRUST, COMPARE_DIMENSIONS };
