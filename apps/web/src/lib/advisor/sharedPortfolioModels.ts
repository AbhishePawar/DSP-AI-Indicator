/**
 * Shared Portfolio fixtures — presentation metadata & scenario framings only.
 * Never recalculates Portfolio Engine outputs.
 */

import {
  computeAllocationTotals,
  sectorMix,
  seedModelPortfolioLibrary,
} from "./modelPortfolioManager";
import type { ModelPortfolioDraft } from "./modelPortfolioTypes";
import { seedPresentations } from "./presentationModels";
import type {
  PortfolioScenarioView,
  SharedPortfolioActivityItem,
  SharedPortfolioCollection,
} from "./sharedPortfolioTypes";

export const SHARED_PORTFOLIO_TRUST =
  "Shared Portfolio Workspace reviews existing DSP model portfolio demos only — never recalculates allocations, scenarios, or risk. Portfolio Engine / demo library remains the single source of truth. No trading.";

/** Presentation watchlist flags (does not alter portfolio math). */
export const portfolioWatchlistIds = new Set([
  "mp-lib-growth",
  "mp-lib-balanced",
  "mp-lib-income",
  "mp-lib-quality",
]);

export function seedSharedPortfolioCollections(): SharedPortfolioCollection[] {
  return [
    {
      id: "spcol-core",
      name: "Core Models",
      portfolioIds: ["mp-lib-growth", "mp-lib-balanced", "mp-lib-quality"],
      updatedAt: "2026-07-21T10:00:00.000Z",
    },
    {
      id: "spcol-income",
      name: "Income Sleeve",
      portfolioIds: ["mp-lib-income"],
      updatedAt: "2026-07-20T10:00:00.000Z",
    },
    {
      id: "spcol-satellite",
      name: "Satellite / Value",
      portfolioIds: ["mp-lib-value", "mp-lib-small", "mp-lib-custom"],
      updatedAt: "2026-07-19T10:00:00.000Z",
    },
  ];
}

/**
 * Scenario cards frame existing demo fields under labeled scenarios.
 * No new Portfolio Engine calculations.
 */
export function buildScenarioViews(draft: ModelPortfolioDraft): PortfolioScenarioView[] {
  const totals = computeAllocationTotals(draft.holdings, draft.cashAllocationPct);
  const sectors = sectorMix(draft.holdings);
  const topSector = sectors[0]?.label ?? "n/a";
  const baseAlloc = `Holdings ${totals.holdingsPct}% · Cash ${totals.cashPct}% · Total ${totals.totalPct}%`;

  return [
    {
      id: "conservative",
      label: "Conservative Scenario",
      framing: `Emphasize cash sleeve (${draft.cashAllocationPct}%) and lower-volatility holdings already in the model.`,
      riskCue: `Catalog risk level: ${draft.riskLevel}`,
      allocationCue: baseAlloc,
      note: "Presentation framing of existing allocation — not a recalculated stress engine.",
    },
    {
      id: "base",
      label: "Base Scenario",
      framing: `As-modeled objective: ${draft.objective}`,
      riskCue: `Horizon ${draft.targetHorizon} · category ${draft.category}`,
      allocationCue: baseAlloc,
      note: "Base case restates the demo model as stored — no engine recompute.",
    },
    {
      id: "bull",
      label: "Bull Scenario",
      framing: `Narrative tilt toward growth sleeves already present (primary sector: ${topSector}).`,
      riskCue: `Existing risk tag remains ${draft.riskLevel}`,
      allocationCue: baseAlloc,
      note: "Bull label is discussion-only; weights are unchanged demo values.",
    },
    {
      id: "bear",
      label: "Bear Scenario",
      framing: "Discussion focus on concentration and sector concentration already reported by portfolio review helpers.",
      riskCue: `Existing risk tag remains ${draft.riskLevel}`,
      allocationCue: baseAlloc,
      note: "Bear label reuses existing holdings — no downside engine run.",
    },
    {
      id: "stress",
      label: "Stress Scenario",
      framing: `Review cash buffer (${draft.cashAllocationPct}%) and largest sleeves under adverse narrative.`,
      riskCue: `Existing risk tag remains ${draft.riskLevel}`,
      allocationCue: baseAlloc,
      note: "Stress framing is presentation-only; Portfolio Engine untouched.",
    },
  ];
}

export function seedSharedPortfolioActivity(): SharedPortfolioActivityItem[] {
  const presented = seedPresentations
    .filter((p) => p.modelPortfolioId)
    .map((p) => {
      const name =
        seedModelPortfolioLibrary.find((m) => m.id === p.modelPortfolioId)?.name ??
        p.modelPortfolioId;
      return {
        id: `pact-pres-${p.id}`,
        kind: "presented" as const,
        label: `Presented — ${name} in “${p.title}”`,
        at: p.updatedAt,
        portfolioId: p.modelPortfolioId ?? undefined,
      };
    });

  return [
    {
      id: "pact-view-1",
      kind: "viewed",
      label: "Viewed — Growth Core",
      at: "2026-07-21T11:00:00.000Z",
      portfolioId: "mp-lib-growth",
    },
    {
      id: "pact-cmp-1",
      kind: "compared",
      label: "Compared — Growth Core · Income Focus · Balanced Blend",
      at: "2026-07-21T09:30:00.000Z",
    },
    {
      id: "pact-rev-1",
      kind: "reviewed",
      label: "Reviewed — Quality Compounders",
      at: "2026-07-20T14:00:00.000Z",
      portfolioId: "mp-lib-quality",
    },
    {
      id: "pact-upd-1",
      kind: "updated",
      label: "Discussion notes updated — Balanced Blend",
      at: "2026-07-20T12:00:00.000Z",
      portfolioId: "mp-lib-balanced",
    },
    ...presented,
  ].sort((a, b) => b.at.localeCompare(a.at));
}

export function getPortfolioById(id: string): ModelPortfolioDraft | undefined {
  return seedModelPortfolioLibrary.find((p) => p.id === id);
}

export const FILTER_STRATEGIES = [
  ...new Set(seedModelPortfolioLibrary.map((p) => p.category)),
].sort();

export const FILTER_SECTORS = [
  ...new Set(
    seedModelPortfolioLibrary.flatMap((p) => p.holdings.map((h) => h.sector)),
  ),
].sort();
