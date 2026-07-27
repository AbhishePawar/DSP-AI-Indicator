/**
 * Shared Research fixtures — parallel filter metadata only.
 * Never mutates demo envelope conclusions / evidence / confidence / methodology / limitations.
 */

import { demoResearchEnvelopes } from "./advisorResearchModels";
import { seedAdvisorCollections } from "./advisorResearchModels";
import { seedPresentations } from "./presentationModels";
import type {
  EnvelopeFilterMeta,
  SharedCollection,
  SharedResearchActivityItem,
} from "./sharedResearchTypes";

export const SHARED_RESEARCH_TRUST =
  "Shared Research Workspace organizes existing DSP demo research envelopes only — conclusions, Evidence, Confidence, Methodology, and Limitations are never modified or regenerated.";

/** Presentation-only taxonomy for filters (does not alter envelope truth fields). */
export const envelopeFilterCatalog: EnvelopeFilterMeta[] = [
  {
    envelopeId: "re-aurora",
    sector: "Technology",
    industry: "Software",
    marketCap: "large",
    rating: "Buy (demo)",
    watchlist: true,
  },
  {
    envelopeId: "re-beacon",
    sector: "Financials",
    industry: "Banks",
    marketCap: "mid",
    rating: "Hold (demo)",
    watchlist: true,
  },
  {
    envelopeId: "re-cedar",
    sector: "Industrials",
    industry: "Machinery",
    marketCap: "mid",
    rating: "Buy (demo)",
    watchlist: false,
  },
  {
    envelopeId: "re-delta",
    sector: "Healthcare",
    industry: "Pharma",
    marketCap: "mega",
    rating: "Buy (demo)",
    watchlist: true,
  },
  {
    envelopeId: "re-ember",
    sector: "Technology",
    industry: "Semiconductors",
    marketCap: "small",
    rating: "Speculative (demo)",
    watchlist: false,
  },
];

export function metaForEnvelope(id: string): EnvelopeFilterMeta | undefined {
  return envelopeFilterCatalog.find((m) => m.envelopeId === id);
}

export function seedSharedCollections(): SharedCollection[] {
  return seedAdvisorCollections.map((c) => ({
    id: c.id,
    name: c.name,
    theme: c.theme,
    itemIds: [...c.itemIds],
    lifecycle: c.lifecycle,
    favorite: c.theme === "high_quality" || c.theme === "growth",
    updatedAt: c.updatedAt,
  }));
}

export function seedSharedActivity(): SharedResearchActivityItem[] {
  const presented = seedPresentations
    .flatMap((p) =>
      p.envelopeIds.map((eid) => {
        const label =
          demoResearchEnvelopes.find((e) => e.id === eid)?.companyLabel ?? eid;
        return {
          id: `act-pres-${p.id}-${eid}`,
          kind: "presented" as const,
          label: `Presented — ${label} in “${p.title}”`,
          at: p.updatedAt,
          envelopeId: eid,
        };
      }),
    )
    .slice(0, 4);

  return [
    {
      id: "act-open-1",
      kind: "opened",
      label: "Opened — Demo Co. Aurora",
      at: "2026-07-21T10:00:00.000Z",
      envelopeId: "re-aurora",
    },
    {
      id: "act-cmp-1",
      kind: "compared",
      label: "Compared — Aurora · Beacon · Delta",
      at: "2026-07-21T09:00:00.000Z",
    },
    {
      id: "act-bm-1",
      kind: "bookmarked",
      label: "Bookmarked — Demo Co. Beacon",
      at: "2026-07-20T15:00:00.000Z",
      envelopeId: "re-beacon",
    },
    {
      id: "act-col-1",
      kind: "collection_add",
      label: "Added Aurora to High Quality",
      at: "2026-07-16T08:30:00.000Z",
      envelopeId: "re-aurora",
    },
    ...presented,
  ].sort((a, b) => b.at.localeCompare(a.at));
}

export const FILTER_SECTORS = [
  ...new Set(envelopeFilterCatalog.map((m) => m.sector)),
].sort();

export const FILTER_INDUSTRIES = [
  ...new Set(envelopeFilterCatalog.map((m) => m.industry)),
].sort();

export const FILTER_RATINGS = [
  ...new Set(envelopeFilterCatalog.map((m) => m.rating)),
].sort();
