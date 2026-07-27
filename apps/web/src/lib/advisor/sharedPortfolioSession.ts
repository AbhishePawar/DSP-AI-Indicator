/**
 * In-memory Shared Portfolio session (no persistence).
 * Organizes existing model portfolio demos — never recalculates engine outputs.
 */

import {
  buildPortfolioReview,
  computeAllocationTotals,
  sectorMix,
  seedModelPortfolioLibrary,
} from "./modelPortfolioManager";
import type { ModelPortfolioDraft } from "./modelPortfolioTypes";
import { seedPresentations } from "./presentationModels";
import {
  getPortfolioById,
  portfolioWatchlistIds,
  seedSharedPortfolioActivity,
  seedSharedPortfolioCollections,
} from "./sharedPortfolioModels";
import {
  DEFAULT_SHARED_PORTFOLIO_FILTERS,
  type PortfolioDiscussionDraft,
  type SharedPortfolioActivityItem,
  type SharedPortfolioCollection,
  type SharedPortfolioFilterState,
} from "./sharedPortfolioTypes";

export type SharedPortfolioSnapshot = {
  collections: SharedPortfolioCollection[];
  pinnedIds: string[];
  favoriteIds: string[];
  recentlyViewed: string[];
  recentlyCompared: string[][];
  compareSelection: string[];
  filters: SharedPortfolioFilterState;
  activity: SharedPortfolioActivityItem[];
  discussions: Record<string, PortfolioDiscussionDraft>;
  comparisonSessionCount: number;
  activeDiscussionId: string;
  activeScenarioPortfolioId: string;
};

function seedDiscussions(): Record<string, PortfolioDiscussionDraft> {
  const out: Record<string, PortfolioDiscussionDraft> = {};
  for (const p of seedModelPortfolioLibrary.slice(0, 3)) {
    out[p.id] = {
      portfolioId: p.id,
      portfolioNotes: p.notes.map((n) => n.body).join(" ") || "No seeded notes.",
      reviewNotes: buildPortfolioReview(p).diversification,
      investmentThesis: p.objective,
      concerns: buildPortfolioReview(p).potentialRisks.join(" · "),
      followUps: "Confirm suitability framing before client meeting (demo).",
      updatedAt: "2026-07-20T12:00:00.000Z",
    };
  }
  return out;
}

let collections = seedSharedPortfolioCollections();
let pinnedIds = ["mp-lib-growth", "mp-lib-balanced"];
let favoriteIds = ["mp-lib-growth", "mp-lib-quality", "mp-lib-income"];
let recentlyViewed = ["mp-lib-growth", "mp-lib-balanced", "mp-lib-income"];
let recentlyCompared: string[][] = [["mp-lib-growth", "mp-lib-income", "mp-lib-balanced"]];
let compareSelection = ["mp-lib-growth", "mp-lib-income"];
let filters: SharedPortfolioFilterState = { ...DEFAULT_SHARED_PORTFOLIO_FILTERS };
let activity = seedSharedPortfolioActivity();
let discussions = seedDiscussions();
let comparisonSessionCount = 1;
let activeDiscussionId = "mp-lib-balanced";
let activeScenarioPortfolioId = "mp-lib-growth";

const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

function pushActivity(
  kind: SharedPortfolioActivityItem["kind"],
  label: string,
  portfolioId?: string,
) {
  activity = [
    {
      id: `pact-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      kind,
      label,
      at: new Date().toISOString(),
      portfolioId,
    },
    ...activity,
  ].slice(0, 40);
}

export function subscribeSharedPortfolio(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSharedPortfolioSnapshot(): SharedPortfolioSnapshot {
  return {
    collections,
    pinnedIds,
    favoriteIds,
    recentlyViewed,
    recentlyCompared,
    compareSelection,
    filters,
    activity,
    discussions,
    comparisonSessionCount,
    activeDiscussionId,
    activeScenarioPortfolioId,
  };
}

export function setSharedPortfolioFilters(patch: Partial<SharedPortfolioFilterState>) {
  filters = { ...filters, ...patch };
  emit();
}

export function resetSharedPortfolioFilters() {
  filters = { ...DEFAULT_SHARED_PORTFOLIO_FILTERS };
  emit();
}

export function recordPortfolioViewed(portfolioId: string) {
  const p = getPortfolioById(portfolioId);
  if (!p) return;
  recentlyViewed = [
    portfolioId,
    ...recentlyViewed.filter((id) => id !== portfolioId),
  ].slice(0, 12);
  pushActivity("viewed", `Viewed — ${p.name}`, portfolioId);
  emit();
}

export function togglePortfolioPin(portfolioId: string) {
  const p = getPortfolioById(portfolioId);
  if (!p) return;
  const has = pinnedIds.includes(portfolioId);
  pinnedIds = has
    ? pinnedIds.filter((id) => id !== portfolioId)
    : [...pinnedIds, portfolioId];
  if (!has) pushActivity("pinned", `Pinned — ${p.name}`, portfolioId);
  emit();
}

export function togglePortfolioFavorite(portfolioId: string) {
  const p = getPortfolioById(portfolioId);
  if (!p) return;
  const has = favoriteIds.includes(portfolioId);
  favoriteIds = has
    ? favoriteIds.filter((id) => id !== portfolioId)
    : [...favoriteIds, portfolioId];
  if (!has) pushActivity("favorited", `Favorited — ${p.name}`, portfolioId);
  emit();
}

export function togglePortfolioCompare(portfolioId: string) {
  if (compareSelection.includes(portfolioId)) {
    compareSelection = compareSelection.filter((id) => id !== portfolioId);
  } else if (compareSelection.length < 5) {
    compareSelection = [...compareSelection, portfolioId];
  }
  emit();
}

export function setPortfolioCompareSelection(ids: string[]) {
  compareSelection = [...new Set(ids)].slice(0, 5);
  emit();
}

export function commitPortfolioComparison() {
  if (compareSelection.length < 2) return;
  recentlyCompared = [compareSelection, ...recentlyCompared].slice(0, 8);
  comparisonSessionCount += 1;
  const labels = compareSelection
    .map((id) => getPortfolioById(id)?.name ?? id)
    .join(" · ");
  pushActivity("compared", `Compared — ${labels}`);
  emit();
}

export function setActiveDiscussionId(id: string) {
  activeDiscussionId = id;
  emit();
}

export function setActiveScenarioPortfolioId(id: string) {
  activeScenarioPortfolioId = id;
  emit();
}

export function updateDiscussion(
  portfolioId: string,
  patch: Partial<Omit<PortfolioDiscussionDraft, "portfolioId">>,
) {
  const p = getPortfolioById(portfolioId);
  if (!p) return;
  const prev = discussions[portfolioId] ?? {
    portfolioId,
    portfolioNotes: "",
    reviewNotes: "",
    investmentThesis: p.objective,
    concerns: "",
    followUps: "",
    updatedAt: new Date().toISOString(),
  };
  discussions = {
    ...discussions,
    [portfolioId]: {
      ...prev,
      ...patch,
      portfolioId,
      updatedAt: new Date().toISOString(),
    },
  };
  pushActivity("discussion", `Discussion updated — ${p.name}`, portfolioId);
  pushActivity("updated", `Recently updated — ${p.name}`, portfolioId);
  emit();
}

export function markPortfolioReviewed(portfolioId: string) {
  const p = getPortfolioById(portfolioId);
  if (!p) return;
  pushActivity("reviewed", `Reviewed — ${p.name}`, portfolioId);
  emit();
}

export function filterPortfolios(
  snap: SharedPortfolioSnapshot = getSharedPortfolioSnapshot(),
): ModelPortfolioDraft[] {
  const f = snap.filters;
  const q = f.query.trim().toLowerCase();

  return seedModelPortfolioLibrary.filter((p) => {
    if (q && !p.name.toLowerCase().includes(q) && !p.objective.toLowerCase().includes(q)) {
      return false;
    }
    if (f.riskLevel && p.riskLevel !== f.riskLevel) return false;
    if (f.strategy && p.category !== f.strategy) return false;
    if (f.sector && !p.holdings.some((h) => h.sector === f.sector)) return false;
    if (f.marketCap && !p.holdings.some((h) => h.marketCapBand === f.marketCap)) {
      return false;
    }
    if (f.allocationBand) {
      const totals = computeAllocationTotals(p.holdings, p.cashAllocationPct);
      if (f.allocationBand === "cash_heavy" && p.cashAllocationPct < 15) return false;
      if (f.allocationBand === "equity_heavy" && totals.holdingsPct < 85) return false;
      if (
        f.allocationBand === "balanced" &&
        (p.cashAllocationPct < 8 || p.cashAllocationPct > 15)
      ) {
        return false;
      }
    }
    if (f.watchlistOnly && !portfolioWatchlistIds.has(p.id)) return false;
    if (f.pinnedOnly && !snap.pinnedIds.includes(p.id)) return false;
    if (f.favoritesOnly && !snap.favoriteIds.includes(p.id)) return false;
    if (f.recentlyViewedOnly && !snap.recentlyViewed.includes(p.id)) return false;
    return true;
  });
}

export function buildSharedPortfolioOverview(
  snap: SharedPortfolioSnapshot = getSharedPortfolioSnapshot(),
) {
  const all = seedModelPortfolioLibrary;
  const riskDist = all.reduce<Record<string, number>>((acc, p) => {
    acc[p.riskLevel] = (acc[p.riskLevel] ?? 0) + 1;
    return acc;
  }, {});
  const sectorWeights = new Map<string, number>();
  for (const p of all) {
    for (const s of sectorMix(p.holdings)) {
      sectorWeights.set(s.label, (sectorWeights.get(s.label) ?? 0) + s.pct);
    }
  }
  const topSectors = Array.from(sectorWeights.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([label, pct]) => `${label} (~${Math.round(pct)} demo pts)`);

  const avgCash =
    Math.round(
      (all.reduce((s, p) => s + p.cashAllocationPct, 0) / Math.max(all.length, 1)) * 10,
    ) / 10;

  return {
    portfolioCount: all.length,
    comparisonSessions: snap.comparisonSessionCount,
    scenarioCoverage: "5 scenario frames × selected model (presentation)",
    allocationSummary: `${all.length} models · avg cash ${avgCash}% (demo)`,
    riskDistribution: Object.entries(riskDist)
      .map(([k, v]) => `${k}: ${v}`)
      .join(" · "),
    sectorExposure: topSectors.join(" · "),
    presentationReadiness: `${seedPresentations.filter((p) => p.modelPortfolioId).length} presentation packs reference models`,
  };
}

export function comparePortfolioFields(ids: string[]) {
  const selected = ids
    .map((id) => getPortfolioById(id))
    .filter((p): p is ModelPortfolioDraft => Boolean(p))
    .slice(0, 5);
  if (selected.length < 2) return null;

  const holdingIds = new Set(selected.flatMap((p) => p.holdings.map((h) => h.envelopeId)));

  return {
    portfolios: selected,
    rows: [
      {
        label: "Portfolio Summary",
        values: selected.map((p) => p.objective),
      },
      {
        label: "Risk Profile",
        values: selected.map((p) => p.riskLevel),
      },
      {
        label: "Expected Return (demo tag)",
        values: selected.map(
          (p) =>
            `Illustrative · ${p.category} · horizon ${p.targetHorizon} (not computed)`,
        ),
      },
      {
        label: "Cash Allocation",
        values: selected.map((p) => `${p.cashAllocationPct}%`),
      },
      {
        label: "Holdings Allocation",
        values: selected.map((p) => {
          const t = computeAllocationTotals(p.holdings, p.cashAllocationPct);
          return `${t.holdingsPct}%`;
        }),
      },
      {
        label: "Sector Allocation",
        values: selected.map((p) =>
          sectorMix(p.holdings)
            .slice(0, 3)
            .map((s) => `${s.label}: ${s.pct}%`)
            .join("; "),
        ),
      },
      {
        label: "Asset Allocation (demo)",
        values: selected.map((p) => {
          const t = computeAllocationTotals(p.holdings, p.cashAllocationPct);
          return `Equity sleeves ${t.holdingsPct}% · Cash ${t.cashPct}%`;
        }),
      },
      {
        label: "Portfolio Notes",
        values: selected.map((p) =>
          p.notes.length ? p.notes.map((n) => n.title).join(", ") : "—",
        ),
      },
    ],
    holdingMatrix: Array.from(holdingIds).map((eid) => ({
      envelopeId: eid,
      companyLabel:
        selected.flatMap((p) => p.holdings).find((h) => h.envelopeId === eid)
          ?.companyLabel ?? eid,
      values: selected.map(
        (p) => p.holdings.find((h) => h.envelopeId === eid)?.allocationPct ?? 0,
      ),
    })),
  };
}

export { getPortfolioById, seedModelPortfolioLibrary };
