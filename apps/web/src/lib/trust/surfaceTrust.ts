/**
 * EPIC-019A — Surface trust presentation helpers.
 * Presentation only: no client valuation, scoring, or fabricated confidence.
 */

import type { ConfidenceLevel } from "@/lib/trust/labels";

export const DATA_UNAVAILABLE = "Data unavailable.";
export const UNABLE_TO_CALCULATE = "Unable to calculate.";

export type TrustLadderLayerId =
  | "facts"
  | "analysis"
  | "inference"
  | "recommendation";

export type TrustLadderLayer = {
  id: TrustLadderLayerId;
  title: string;
  summary: string;
  presence: "available" | "partial" | "unavailable";
};

export type EvidenceCompleteness = {
  /** Count of mandatory presentation slots that are present. */
  present: number;
  /** Count of mandatory presentation slots expected on this surface. */
  expected: number;
  /** Missing-data penalty label — never invents a score. */
  missingDataPenalty: "none" | "partial" | "blocking";
  label: string;
};

export type SurfaceTrustSummary = {
  surface:
    | "dashboard"
    | "portfolio"
    | "research_workspace"
    | "ird"
    | "company_analysis"
    | "institutional_reports";
  layers: TrustLadderLayer[];
  evidence: EvidenceCompleteness;
  confidenceDisplay: string;
  confidenceLevel: ConfidenceLevel | "unavailable";
  contradictoryEvidence: string[];
  auditTrail: string[];
  researchMode: boolean;
};

function penalty(
  present: number,
  expected: number,
): EvidenceCompleteness["missingDataPenalty"] {
  if (expected <= 0) return "blocking";
  if (present <= 0) return "blocking";
  if (present < expected) return "partial";
  return "none";
}

export function buildEvidenceCompleteness(
  present: number,
  expected: number,
): EvidenceCompleteness {
  const safeExpected = Math.max(0, expected);
  const safePresent = Math.min(Math.max(0, present), safeExpected || present);
  const p = penalty(safePresent, safeExpected);
  const label =
    safeExpected === 0
      ? DATA_UNAVAILABLE
      : p === "none"
        ? `Evidence complete (${safePresent}/${safeExpected})`
        : p === "partial"
          ? `Evidence incomplete (${safePresent}/${safeExpected}) — missing-data penalty applied in presentation`
          : `Evidence blocking (${safePresent}/${safeExpected}) — ${DATA_UNAVAILABLE}`;
  return {
    present: safePresent,
    expected: safeExpected,
    missingDataPenalty: p,
    label,
  };
}

/** Idle / empty surface ladder — honest unavailable layers. */
export function emptySurfaceTrust(
  surface: SurfaceTrustSummary["surface"],
  opts?: { auditNote?: string },
): SurfaceTrustSummary {
  const layers: TrustLadderLayer[] = [
    {
      id: "facts",
      title: "1 · Facts · Verified / market signals",
      summary: DATA_UNAVAILABLE,
      presence: "unavailable",
    },
    {
      id: "analysis",
      title: "2 · Analysis · Calculated outputs",
      summary: DATA_UNAVAILABLE,
      presence: "unavailable",
    },
    {
      id: "inference",
      title: "3 · Inference · AI / Committee",
      summary: DATA_UNAVAILABLE,
      presence: "unavailable",
    },
    {
      id: "recommendation",
      title: "4 · Recommendation · Research Mode",
      summary:
        "Research Mode — educational investigation only. No personalised investment advice.",
      presence: "partial",
    },
  ];
  return {
    surface,
    layers,
    evidence: buildEvidenceCompleteness(0, 4),
    confidenceDisplay: DATA_UNAVAILABLE,
    confidenceLevel: "unavailable",
    contradictoryEvidence: [],
    auditTrail: [
      opts?.auditNote ??
        "Audit: no authenticated research payload on this surface yet.",
      "Source before score — thin client renders frozen /api/v1 only.",
    ],
    researchMode: true,
  };
}

export function portfolioSurfaceTrust(input: {
  holdingsCount: number;
  researchCovered: number;
  researchTotal: number;
  intelStatus: string;
  confidenceDisplay?: string | null;
  opposingNotes?: string[];
}): SurfaceTrustSummary {
  const factsPresent = input.holdingsCount > 0 ? 1 : 0;
  const analysisPresent =
    input.researchTotal > 0 && input.researchCovered > 0 ? 1 : 0;
  const inferencePresent = /ok|success|available/i.test(input.intelStatus)
    ? 1
    : 0;
  const present = factsPresent + analysisPresent + inferencePresent;
  const layers: TrustLadderLayer[] = [
    {
      id: "facts",
      title: "1 · Facts · Session holdings",
      summary:
        input.holdingsCount > 0
          ? `${input.holdingsCount} holding(s) in session — user input / authenticated portfolio store`
          : DATA_UNAVAILABLE,
      presence: factsPresent ? "available" : "unavailable",
    },
    {
      id: "analysis",
      title: "2 · Analysis · Research coverage",
      summary:
        input.researchTotal > 0
          ? `${input.researchCovered}/${input.researchTotal} research-available (session) — missing symbols stay ${DATA_UNAVAILABLE}`
          : "No holdings — coverage not applicable",
      presence: analysisPresent
        ? "available"
        : input.researchTotal > 0
          ? "partial"
          : "unavailable",
    },
    {
      id: "inference",
      title: "3 · Inference · Portfolio intelligence API",
      summary: input.intelStatus?.trim()
        ? input.intelStatus
        : DATA_UNAVAILABLE,
      presence: inferencePresent ? "available" : "unavailable",
    },
    {
      id: "recommendation",
      title: "4 · Recommendation · Research Mode",
      summary:
        "Research Mode — portfolio intelligence does not issue buy/sell instructions.",
      presence: "partial",
    },
  ];
  return {
    surface: "portfolio",
    layers,
    evidence: buildEvidenceCompleteness(present, 3),
    confidenceDisplay: input.confidenceDisplay?.trim() || DATA_UNAVAILABLE,
    confidenceLevel: input.confidenceDisplay?.trim()
      ? "moderate"
      : "unavailable",
    contradictoryEvidence: (input.opposingNotes ?? []).filter(Boolean),
    auditTrail: [
      `Audit: portfolio surface · holdings=${input.holdingsCount} · coverage=${input.researchCovered}/${input.researchTotal}`,
      "Presentation map only — no client-side portfolio scoring.",
    ],
    researchMode: true,
  };
}

export function researchWorkspaceSurfaceTrust(input: {
  ticker: string | null;
  analyseOk: boolean | null;
  stagesCount: number;
  recommendation: string | null;
  confidenceDisplay: string | null;
  opposingNotes?: string[];
  analysedAt?: string | null;
}): SurfaceTrustSummary {
  const hasTicker = Boolean(input.ticker);
  const factsPresent = hasTicker && input.analyseOk === true ? 1 : 0;
  const analysisPresent = input.stagesCount > 0 ? 1 : 0;
  const inferencePresent = Boolean(input.recommendation?.trim()) ? 1 : 0;
  const present = (hasTicker ? 1 : 0) + factsPresent + analysisPresent;
  const layers: TrustLadderLayer[] = [
    {
      id: "facts",
      title: "1 · Facts · Authenticated analyse payload",
      summary: !hasTicker
        ? DATA_UNAVAILABLE
        : input.analyseOk === true
          ? `Ticker ${input.ticker} · analyse succeeded · stages ${input.stagesCount || DATA_UNAVAILABLE}`
          : input.analyseOk === false
            ? `Ticker ${input.ticker} · analyse incomplete / failed · ${DATA_UNAVAILABLE}`
            : `Ticker ${input.ticker} · load research to populate facts`,
      presence: factsPresent
        ? "available"
        : hasTicker
          ? "partial"
          : "unavailable",
    },
    {
      id: "analysis",
      title: "2 · Analysis · Stage outputs",
      summary:
        analysisPresent > 0
          ? `${input.stagesCount} stage(s) present from /api/v1`
          : DATA_UNAVAILABLE,
      presence: analysisPresent ? "available" : "unavailable",
    },
    {
      id: "inference",
      title: "3 · Inference · Committee / recommendation text",
      summary: input.recommendation?.trim() || DATA_UNAVAILABLE,
      presence: inferencePresent ? "available" : "unavailable",
    },
    {
      id: "recommendation",
      title: "4 · Recommendation · Research Mode",
      summary:
        "Research Mode — educational investigation; confidence shown when API provides it.",
      presence: "partial",
    },
  ];
  return {
    surface: "research_workspace",
    layers,
    evidence: buildEvidenceCompleteness(present, 3),
    confidenceDisplay: input.confidenceDisplay?.trim() || DATA_UNAVAILABLE,
    confidenceLevel: input.confidenceDisplay?.trim()
      ? "moderate"
      : "insufficient_evidence",
    contradictoryEvidence: (input.opposingNotes ?? []).filter(Boolean),
    auditTrail: [
      `Audit: research workspace · ticker=${input.ticker ?? "none"} · at=${input.analysedAt ?? DATA_UNAVAILABLE}`,
      "Thin client — mapResearchView presentation only.",
    ],
    researchMode: true,
  };
}

export function irdSurfaceTrust(input: {
  ticker: string | null;
  loaded: boolean;
  priceDisplay: string | null;
  mosDisplay: string | null;
  confidenceDisplay: string | null;
  recommendationDisplay: string | null;
  unavailableFieldCount: number;
  opposingNotes?: string[];
  reportTimestamp?: string | null;
}): SurfaceTrustSummary {
  const factsPresent = input.loaded && Boolean(input.priceDisplay) ? 1 : 0;
  const analysisPresent = input.loaded && Boolean(input.mosDisplay) ? 1 : 0;
  const inferencePresent = Boolean(input.recommendationDisplay) ? 1 : 0;
  const present =
    (input.loaded ? 1 : 0) + factsPresent + analysisPresent + inferencePresent;
  const layers: TrustLadderLayer[] = [
    {
      id: "facts",
      title: "1 · Facts · Market / header fields",
      summary: !input.loaded
        ? DATA_UNAVAILABLE
        : `Ticker ${input.ticker ?? DATA_UNAVAILABLE} · Price ${input.priceDisplay ?? DATA_UNAVAILABLE}`,
      presence: factsPresent ? "available" : input.loaded ? "partial" : "unavailable",
    },
    {
      id: "analysis",
      title: "2 · Analysis · Valuation / MoS panels",
      summary: input.mosDisplay?.trim() || DATA_UNAVAILABLE,
      presence: analysisPresent ? "available" : "unavailable",
    },
    {
      id: "inference",
      title: "3 · Inference · Recommendation display",
      summary: input.recommendationDisplay?.trim() || DATA_UNAVAILABLE,
      presence: inferencePresent ? "available" : "unavailable",
    },
    {
      id: "recommendation",
      title: "4 · Recommendation · Research Mode",
      summary:
        "Research Mode — IRD presents composition panels; full publish ladder on Institutional Reports.",
      presence: "partial",
    },
  ];
  const expected = 4;
  const evidencePresent = Math.max(0, expected - input.unavailableFieldCount);
  return {
    surface: "ird",
    layers,
    evidence: buildEvidenceCompleteness(
      Math.min(present, evidencePresent || present),
      expected,
    ),
    confidenceDisplay: input.confidenceDisplay?.trim() || DATA_UNAVAILABLE,
    confidenceLevel: input.confidenceDisplay?.trim()
      ? "moderate"
      : "insufficient_evidence",
    contradictoryEvidence: (input.opposingNotes ?? []).filter(Boolean),
    auditTrail: [
      `Audit: IRD · ticker=${input.ticker ?? "none"} · loaded=${input.loaded} · ts=${input.reportTimestamp ?? DATA_UNAVAILABLE}`,
      "RS panels from analyse composition — no invented numbers.",
    ],
    researchMode: true,
  };
}

export function dashboardSurfaceTrust(input: {
  widgetCount: number;
  note?: string;
}): SurfaceTrustSummary {
  const base = emptySurfaceTrust("dashboard", {
    auditNote: `Audit: executive dashboard · visible widgets=${input.widgetCount}`,
  });
  base.layers[0] = {
    id: "facts",
    title: "1 · Facts · Authenticated probes / local history",
    summary:
      input.widgetCount > 0
        ? `${input.widgetCount} widget slot(s) — each widget must keep Data unavailable. when probes fail`
        : DATA_UNAVAILABLE,
    presence: input.widgetCount > 0 ? "partial" : "unavailable",
  };
  base.evidence = buildEvidenceCompleteness(input.widgetCount > 0 ? 1 : 0, 4);
  if (input.note) base.auditTrail = [input.note, ...base.auditTrail];
  return base;
}
