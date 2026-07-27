/**
 * Model Portfolio Manager — demo fixtures + pure allocation helpers.
 * Reuses advisor research envelopes; does not call Portfolio Engine.
 */

import { demoResearchEnvelopes } from "./advisorResearchModels";
import type {
  AllocationTotals,
  ModelPortfolioDraft,
  MpCategory,
  MpHolding,
  MpNote,
  MpTemplateId,
  PortfolioReviewView,
} from "./modelPortfolioTypes";

export const MP_TRUST =
  "Model Portfolio Manager is presentation-only — reuses demo DSP research summaries; never alters Evidence, Confidence, Methodology, Limitations, or Investment Thesis. No trading or broker sync.";

const SECTOR_BY_ENVELOPE: Record<string, { sector: string; marketCapBand: MpHolding["marketCapBand"] }> = {
  "re-aurora": { sector: "Information Technology (demo)", marketCapBand: "large" },
  "re-beacon": { sector: "Utilities / Income (demo)", marketCapBand: "mid" },
  "re-cedar": { sector: "Industrials (demo)", marketCapBand: "mid" },
  "re-delta": { sector: "Consumer Staples (demo)", marketCapBand: "large" },
  "re-ember": { sector: "Communication Services (demo)", marketCapBand: "small" },
};

export function holdingMeta(envelopeId: string): Pick<MpHolding, "sector" | "marketCapBand" | "companyLabel"> {
  const env = demoResearchEnvelopes.find((e) => e.id === envelopeId);
  const meta = SECTOR_BY_ENVELOPE[envelopeId] ?? {
    sector: "Unclassified (demo)",
    marketCapBand: "mid" as const,
  };
  return {
    companyLabel: env?.companyLabel ?? envelopeId,
    sector: meta.sector,
    marketCapBand: meta.marketCapBand,
  };
}

export function computeAllocationTotals(
  holdings: MpHolding[],
  cashAllocationPct: number,
): AllocationTotals {
  const holdingsPct = Math.round(holdings.reduce((s, h) => s + h.allocationPct, 0) * 10) / 10;
  const cashPct = cashAllocationPct;
  const totalPct = Math.round((holdingsPct + cashPct) * 10) / 10;
  const deltaFrom100 = Math.round((totalPct - 100) * 10) / 10;
  return {
    holdingsPct,
    cashPct,
    totalPct,
    isBalanced: Math.abs(deltaFrom100) < 0.05,
    deltaFrom100,
  };
}

export function sectorMix(holdings: MpHolding[]): { label: string; pct: number }[] {
  const map = new Map<string, number>();
  for (const h of holdings) {
    map.set(h.sector, (map.get(h.sector) ?? 0) + h.allocationPct);
  }
  return Array.from(map.entries())
    .map(([label, pct]) => ({ label, pct: Math.round(pct * 10) / 10 }))
    .sort((a, b) => b.pct - a.pct);
}

export function marketCapMix(holdings: MpHolding[]): { label: string; pct: number }[] {
  const map = new Map<string, number>();
  for (const h of holdings) {
    map.set(h.marketCapBand, (map.get(h.marketCapBand) ?? 0) + h.allocationPct);
  }
  return Array.from(map.entries())
    .map(([label, pct]) => ({ label, pct: Math.round(pct * 10) / 10 }))
    .sort((a, b) => b.pct - a.pct);
}

export function buildPortfolioReview(draft: ModelPortfolioDraft): PortfolioReviewView {
  const totals = computeAllocationTotals(draft.holdings, draft.cashAllocationPct);
  const top = [...draft.holdings].sort((a, b) => b.allocationPct - a.allocationPct)[0];
  const sectors = sectorMix(draft.holdings);
  return {
    strengths: [
      `${draft.holdings.length} researched holdings with reused DSP envelopes`,
      `Objective: ${draft.objective}`,
      sectors[0] ? `Primary sector weight in ${sectors[0].label}` : "Sector mix pending",
    ],
    potentialRisks: [
      totals.isBalanced ? "Allocation sums to 100% (demo)" : `Allocation off by ${totals.deltaFrom100}%`,
      top && top.allocationPct >= 30
        ? `Concentration — ${top.companyLabel} at ${top.allocationPct}%`
        : "No single holding ≥ 30% (demo heuristic)",
      "Illustrative model — not investable advice",
    ],
    diversification:
      sectors.length >= 3
        ? `Spread across ${sectors.length} sector buckets (demo)`
        : `Limited sector spread (${sectors.length} buckets)`,
    concentration: top
      ? `Largest sleeve ${top.companyLabel} · ${top.allocationPct}%`
      : "No holdings",
    researchCoverage: `${draft.holdings.length} of ${demoResearchEnvelopes.length} demo envelopes referenced`,
    evidenceCompleteness:
      "Each holding reuses Evidence · Confidence · Methodology · Limitations from demo envelopes — not recomputed.",
  };
}

function note(kind: MpNote["kind"], title: string, body: string, id: string): MpNote {
  return { id, kind, title, body, updatedAt: "2026-07-22T10:00:00.000Z" };
}

function holding(envelopeId: string, allocationPct: number): MpHolding {
  const meta = holdingMeta(envelopeId);
  return { envelopeId, allocationPct, ...meta };
}

export const seedModelPortfolioLibrary: ModelPortfolioDraft[] = [
  {
    id: "mp-lib-growth",
    name: "Growth Core",
    category: "growth",
    objective: "Long-horizon equity growth (demo)",
    riskLevel: "aggressive",
    targetHorizon: "7–10 years",
    cashAllocationPct: 5,
    holdings: [holding("re-aurora", 40), holding("re-ember", 35), holding("re-delta", 20)],
    notes: [
      note("advisor", "Growth bias", "Tilt toward Aurora/Ember — demo only.", "mpn-1"),
    ],
    templateId: "tpl-aggressive-growth",
  },
  {
    id: "mp-lib-balanced",
    name: "Balanced Blend",
    category: "balanced",
    objective: "Balanced growth with income overlay (demo)",
    riskLevel: "moderate",
    targetHorizon: "5–7 years",
    cashAllocationPct: 10,
    holdings: [holding("re-aurora", 30), holding("re-beacon", 30), holding("re-delta", 30)],
    notes: [],
    templateId: "tpl-balanced-growth",
  },
  {
    id: "mp-lib-income",
    name: "Income Focus",
    category: "income",
    objective: "Cash-flow oriented sleeve (demo)",
    riskLevel: "conservative",
    targetHorizon: "3–5 years",
    cashAllocationPct: 15,
    holdings: [holding("re-beacon", 50), holding("re-delta", 35)],
    notes: [
      note("suitability", "Income preference", "Prefer Beacon envelope framing.", "mpn-2"),
    ],
    templateId: "tpl-conservative-income",
  },
  {
    id: "mp-lib-value",
    name: "Value Opportunities",
    category: "value",
    objective: "Mean-reversion candidates (demo)",
    riskLevel: "growth",
    targetHorizon: "5+ years",
    cashAllocationPct: 10,
    holdings: [holding("re-cedar", 45), holding("re-beacon", 25), holding("re-aurora", 20)],
    notes: [],
    templateId: "tpl-value-opportunities",
  },
  {
    id: "mp-lib-quality",
    name: "Quality Compounders",
    category: "quality",
    objective: "High-quality durable growers (demo)",
    riskLevel: "moderate",
    targetHorizon: "10+ years",
    cashAllocationPct: 5,
    holdings: [holding("re-aurora", 45), holding("re-delta", 50)],
    notes: [note("review", "Quality check", "Coverage rated strong on envelopes.", "mpn-3")],
    templateId: "tpl-quality-compounders",
  },
  {
    id: "mp-lib-small",
    name: "Small Cap Satellite",
    category: "small_cap",
    objective: "Satellite growth exposure (demo)",
    riskLevel: "aggressive",
    targetHorizon: "7+ years",
    cashAllocationPct: 10,
    holdings: [holding("re-ember", 60), holding("re-cedar", 30)],
    notes: [],
    templateId: "tpl-aggressive-growth",
  },
  {
    id: "mp-lib-large",
    name: "Large Cap Anchor",
    category: "large_cap",
    objective: "Core large-cap quality (demo)",
    riskLevel: "moderate",
    targetHorizon: "5–10 years",
    cashAllocationPct: 5,
    holdings: [holding("re-delta", 50), holding("re-aurora", 45)],
    notes: [],
    templateId: "tpl-quality-compounders",
  },
  {
    id: "mp-lib-custom",
    name: "Custom Workshop",
    category: "custom",
    objective: "Advisor workshop blank (demo)",
    riskLevel: "moderate",
    targetHorizon: "TBD",
    cashAllocationPct: 20,
    holdings: [holding("re-aurora", 40), holding("re-beacon", 40)],
    notes: [note("version", "v0 draft", "Session template — not persisted.", "mpn-4")],
    templateId: "tpl-custom",
  },
];

export type PortfolioTemplate = {
  id: MpTemplateId;
  name: string;
  category: MpCategory;
  blurb: string;
  seedPortfolioId: string;
};

export const portfolioTemplates: PortfolioTemplate[] = [
  {
    id: "tpl-aggressive-growth",
    name: "Aggressive Growth",
    category: "growth",
    blurb: "Higher equity / small-cap tilt — illustrative.",
    seedPortfolioId: "mp-lib-growth",
  },
  {
    id: "tpl-balanced-growth",
    name: "Balanced Growth",
    category: "balanced",
    blurb: "Core blend with income overlay — illustrative.",
    seedPortfolioId: "mp-lib-balanced",
  },
  {
    id: "tpl-conservative-income",
    name: "Conservative Income",
    category: "income",
    blurb: "Cash-flow oriented — illustrative.",
    seedPortfolioId: "mp-lib-income",
  },
  {
    id: "tpl-quality-compounders",
    name: "Quality Compounders",
    category: "quality",
    blurb: "Durable quality names — illustrative.",
    seedPortfolioId: "mp-lib-quality",
  },
  {
    id: "tpl-dividend-focus",
    name: "Dividend Focus",
    category: "income",
    blurb: "Income sleeve emphasis — illustrative.",
    seedPortfolioId: "mp-lib-income",
  },
  {
    id: "tpl-value-opportunities",
    name: "Value Opportunities",
    category: "value",
    blurb: "Mean-reversion candidates — illustrative.",
    seedPortfolioId: "mp-lib-value",
  },
  {
    id: "tpl-custom",
    name: "Custom",
    category: "custom",
    blurb: "Start from workshop blank — session only.",
    seedPortfolioId: "mp-lib-custom",
  },
];

export function cloneDraft(id: string): ModelPortfolioDraft | null {
  const src = seedModelPortfolioLibrary.find((p) => p.id === id);
  if (!src) return null;
  return {
    ...src,
    id: `session-${src.id}-${Date.now().toString(36)}`,
    holdings: src.holdings.map((h) => ({ ...h })),
    notes: src.notes.map((n) => ({ ...n })),
  };
}

export function emptyDraft(): ModelPortfolioDraft {
  return {
    id: `session-empty-${Date.now().toString(36)}`,
    name: "Untitled model (session)",
    category: "custom",
    objective: "Define objective (demo)",
    riskLevel: "moderate",
    targetHorizon: "TBD",
    cashAllocationPct: 10,
    holdings: [],
    notes: [],
    templateId: "tpl-custom",
  };
}

export function listLibraryByCategory(category: MpCategory | "all"): ModelPortfolioDraft[] {
  if (category === "all") return seedModelPortfolioLibrary;
  return seedModelPortfolioLibrary.filter((p) => p.category === category);
}

export function compareDrafts(a: ModelPortfolioDraft, b: ModelPortfolioDraft) {
  const aMap = new Map(a.holdings.map((h) => [h.envelopeId, h.allocationPct]));
  const bMap = new Map(b.holdings.map((h) => [h.envelopeId, h.allocationPct]));
  const ids = new Set([...aMap.keys(), ...bMap.keys()]);
  const allocationDiffs = Array.from(ids).map((id) => {
    const meta = holdingMeta(id);
    const av = aMap.get(id) ?? 0;
    const bv = bMap.get(id) ?? 0;
    return {
      companyLabel: meta.companyLabel,
      modelA: av,
      modelB: bv,
      delta: Math.round((bv - av) * 10) / 10,
    };
  });
  const sectorA = sectorMix(a.holdings);
  const sectorB = sectorMix(b.holdings);
  return {
    allocationDiffs,
    sectorA,
    sectorB,
    riskA: a.riskLevel,
    riskB: b.riskLevel,
    diversificationA: sectorA.length,
    diversificationB: sectorB.length,
    characteristics: [
      `${a.name}: ${a.objective}`,
      `${b.name}: ${b.objective}`,
      `Cash ${a.cashAllocationPct}% vs ${b.cashAllocationPct}%`,
    ],
  };
}

export { demoResearchEnvelopes };
