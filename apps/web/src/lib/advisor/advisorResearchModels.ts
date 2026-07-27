/**
 * Demo advisor research fixtures — presentation only, no engine coupling.
 */

import type {
  AdvisorResearchBookmark,
  AdvisorResearchCollection,
  AdvisorResearchNote,
  AdvisorResearchTimelineEvent,
  DemoResearchEnvelope,
} from "./advisorResearchTypes";

export const ADVISOR_RESEARCH_TRUST =
  "Advisor Research reuses demo DSP research envelopes for organization only — conclusions, evidence, confidence, methodology, and limitations are not modified.";

function envelope(
  partial: Omit<DemoResearchEnvelope, "limitations"> & { limitations?: string[] },
): DemoResearchEnvelope {
  return {
    limitations: partial.limitations ?? [
      "Demo envelope — not live market data",
      "Presentation layer only; Research Engine untouched",
    ],
    ...partial,
  };
}

export const demoResearchEnvelopes: DemoResearchEnvelope[] = [
  envelope({
    id: "re-aurora",
    companyId: "co-aurora",
    companyLabel: "Demo Co. Aurora",
    thesis: "Quality compounder narrative with durable demand (demo summary).",
    topRisks: ["Multiple compression (demo)", "Customer concentration (demo)"],
    keyOpportunities: ["Adjacent market expansion (demo)", "Margin recovery path (demo)"],
    valuationSummary: "Within historical band vs peers — illustrative only.",
    confidence: "Medium",
    methodology: "DSP Research Mode envelope fields — reused, not recomputed.",
    evidence: ["Demo filing excerpt", "Demo peer table", "Demo growth series"],
    businessQuality: "High",
    financialStrength: "Strong",
    valuation: "Fair",
    growth: "Moderate+",
    risk: "Moderate",
    management: "Aligned (demo)",
    moat: "Narrow–Wide (demo)",
    evidenceCoverage: "Good",
    viewedAt: "2026-07-21T10:00:00.000Z",
  }),
  envelope({
    id: "re-beacon",
    companyId: "co-beacon",
    companyLabel: "Demo Co. Beacon",
    thesis: "Income-oriented cash generative profile (demo summary).",
    topRisks: ["Rate sensitivity (demo)", "Payout sustainability (demo)"],
    keyOpportunities: ["Dividend coverage stability (demo)"],
    valuationSummary: "Yield-relative framing — illustrative only.",
    confidence: "Medium–High",
    methodology: "DSP Research Mode envelope fields — reused, not recomputed.",
    evidence: ["Demo cash flow bridge", "Demo payout history"],
    businessQuality: "Solid",
    financialStrength: "Adequate",
    valuation: "Attractive (demo)",
    growth: "Low–Moderate",
    risk: "Moderate–High",
    management: "Steady (demo)",
    moat: "Narrow (demo)",
    evidenceCoverage: "Adequate",
    viewedAt: "2026-07-20T14:00:00.000Z",
  }),
  envelope({
    id: "re-cedar",
    companyId: "co-cedar",
    companyLabel: "Demo Co. Cedar",
    thesis: "Value mean-reversion candidate with balance-sheet support (demo).",
    topRisks: ["Cyclical demand (demo)", "Working capital swings (demo)"],
    keyOpportunities: ["Normalization of margins (demo)"],
    valuationSummary: "Discount to asset value — illustrative only.",
    confidence: "Low–Medium",
    methodology: "DSP Research Mode envelope fields — reused, not recomputed.",
    evidence: ["Demo balance sheet", "Demo cycle chart"],
    businessQuality: "Average",
    financialStrength: "Moderate",
    valuation: "Cheap (demo)",
    growth: "Cyclical",
    risk: "Elevated",
    management: "Mixed (demo)",
    moat: "None–Narrow (demo)",
    evidenceCoverage: "Partial",
    viewedAt: "2026-07-19T09:30:00.000Z",
  }),
  envelope({
    id: "re-delta",
    companyId: "co-delta",
    companyLabel: "Demo Co. Delta",
    thesis: "Large-cap compounder with diversified end markets (demo).",
    topRisks: ["Regulatory overhang (demo)"],
    keyOpportunities: ["Share repurchase capacity (demo)"],
    valuationSummary: "Premium justified by quality — illustrative.",
    confidence: "High",
    methodology: "DSP Research Mode envelope fields — reused, not recomputed.",
    evidence: ["Demo segment mix", "Demo ROIC series"],
    businessQuality: "Very High",
    financialStrength: "Very Strong",
    valuation: "Rich (demo)",
    growth: "Steady",
    risk: "Low–Moderate",
    management: "Strong (demo)",
    moat: "Wide (demo)",
    evidenceCoverage: "Excellent",
    viewedAt: "2026-07-18T16:00:00.000Z",
  }),
  envelope({
    id: "re-ember",
    companyId: "co-ember",
    companyLabel: "Demo Co. Ember",
    thesis: "Small-cap growth with execution risk (demo).",
    topRisks: ["Liquidity (demo)", "Execution (demo)"],
    keyOpportunities: ["Category leadership path (demo)"],
    valuationSummary: "Growth-adjusted — illustrative only.",
    confidence: "Low",
    methodology: "DSP Research Mode envelope fields — reused, not recomputed.",
    evidence: ["Demo TAM sketch", "Demo cohort metrics"],
    businessQuality: "Emerging",
    financialStrength: "Thin",
    valuation: "Expensive (demo)",
    growth: "High",
    risk: "High",
    management: "Founder-led (demo)",
    moat: "Nascent (demo)",
    evidenceCoverage: "Limited",
    viewedAt: "2026-07-17T11:00:00.000Z",
  }),
];

export const seedAdvisorCollections: AdvisorResearchCollection[] = [
  {
    id: "acol-growth",
    name: "Growth",
    theme: "growth",
    itemIds: ["re-aurora", "re-ember"],
    lifecycle: "active",
    updatedAt: "2026-07-21T08:00:00.000Z",
  },
  {
    id: "acol-value",
    name: "Value",
    theme: "value",
    itemIds: ["re-cedar"],
    lifecycle: "active",
    updatedAt: "2026-07-20T08:00:00.000Z",
  },
  {
    id: "acol-dividend",
    name: "Dividend",
    theme: "dividend",
    itemIds: ["re-beacon"],
    lifecycle: "active",
    updatedAt: "2026-07-19T08:00:00.000Z",
  },
  {
    id: "acol-small",
    name: "Small Cap",
    theme: "small_cap",
    itemIds: ["re-ember"],
    lifecycle: "active",
    updatedAt: "2026-07-18T08:00:00.000Z",
  },
  {
    id: "acol-large",
    name: "Large Cap",
    theme: "large_cap",
    itemIds: ["re-delta", "re-aurora"],
    lifecycle: "active",
    updatedAt: "2026-07-17T08:00:00.000Z",
  },
  {
    id: "acol-quality",
    name: "High Quality",
    theme: "high_quality",
    itemIds: ["re-aurora", "re-delta"],
    lifecycle: "active",
    updatedAt: "2026-07-16T08:00:00.000Z",
  },
  {
    id: "acol-custom",
    name: "Custom",
    theme: "custom",
    itemIds: ["re-beacon", "re-cedar"],
    lifecycle: "active",
    updatedAt: "2026-07-15T08:00:00.000Z",
  },
];

export const demoAdvisorResearchNotes: AdvisorResearchNote[] = [
  {
    id: "arn-1",
    kind: "pinned",
    title: "Pinned — methodology reminder",
    body: "Always surface Evidence · Confidence · Methodology · Limitations when reviewing.",
    companyId: null,
    pinned: true,
    updatedAt: "2026-07-21T09:00:00.000Z",
  },
  {
    id: "arn-2",
    kind: "private",
    title: "Private — Aurora watch",
    body: "Demo private note: revisit peer table next week.",
    companyId: "co-aurora",
    pinned: false,
    updatedAt: "2026-07-20T12:00:00.000Z",
  },
  {
    id: "arn-3",
    kind: "client",
    title: "Client — Beta income framing",
    body: "Demo client note: prefer Beacon income envelope for next meeting.",
    companyId: "co-beacon",
    pinned: false,
    updatedAt: "2026-07-19T15:00:00.000Z",
  },
  {
    id: "arn-4",
    kind: "meeting",
    title: "Meeting — Cedar deep dive",
    body: "Demo meeting note: stress cyclical risk language.",
    companyId: "co-cedar",
    pinned: false,
    updatedAt: "2026-07-18T10:00:00.000Z",
  },
  {
    id: "arn-5",
    kind: "finding",
    title: "Finding — Delta evidence coverage",
    body: "Demo finding: evidence coverage rated Excellent on envelope.",
    companyId: "co-delta",
    pinned: true,
    updatedAt: "2026-07-17T14:00:00.000Z",
  },
];

export const demoAdvisorResearchTimeline: AdvisorResearchTimelineEvent[] = [
  {
    id: "atl-1",
    kind: "analysis_created",
    label: "Analysis created — Demo Co. Aurora",
    occurredAt: "2026-07-21T10:05:00.000Z",
  },
  {
    id: "atl-2",
    kind: "research_updated",
    label: "Research updated — Demo Co. Beacon envelope fields refreshed (demo)",
    occurredAt: "2026-07-20T14:10:00.000Z",
  },
  {
    id: "atl-3",
    kind: "report_generated",
    label: "Report generated — Income sleeve memo (demo export)",
    occurredAt: "2026-07-19T16:00:00.000Z",
  },
  {
    id: "atl-4",
    kind: "collection_modified",
    label: "Collection modified — High Quality (+ Aurora)",
    occurredAt: "2026-07-16T08:30:00.000Z",
  },
  {
    id: "atl-5",
    kind: "favorite",
    label: "Favorite — Demo Co. Delta",
    occurredAt: "2026-07-15T11:00:00.000Z",
  },
];

export const demoAdvisorBookmarks: AdvisorResearchBookmark[] = [
  {
    id: "abm-1",
    kind: "favorite",
    label: "Demo Co. Aurora",
    target: "re-aurora",
    tags: ["quality", "growth"],
  },
  {
    id: "abm-2",
    kind: "recent",
    label: "Demo Co. Beacon",
    target: "re-beacon",
    tags: ["dividend"],
  },
  {
    id: "abm-3",
    kind: "pinned",
    label: "Methodology reminder",
    target: "arn-1",
    tags: ["trust"],
  },
  {
    id: "abm-4",
    kind: "collection",
    label: "High Quality collection",
    target: "acol-quality",
    tags: ["quality"],
  },
  {
    id: "abm-5",
    kind: "tag",
    label: "Tag: cyclical",
    target: "tag:cyclical",
    tags: ["cyclical", "value"],
  },
];

export const demoFavoriteCompanies = ["Demo Co. Aurora", "Demo Co. Delta", "Demo Co. Beacon"];
export const demoRecentReports = [
  "Demo Report — Quality Screen",
  "Demo Report — Income Sleeve",
  "Demo Report — Value Mean Reversion",
];
export const demoSavedResearch = [
  "Saved — Quality Screen folder",
  "Saved — Income ideas",
  "Saved — Small cap watch",
];
export const demoPinnedResearch = [
  "Pinned — Methodology reminder",
  "Pinned — Risk band glossary",
  "Pinned — Evidence coverage guide",
];
