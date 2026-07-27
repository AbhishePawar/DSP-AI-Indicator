/** Sprint 3 — Market Intelligence builders (presentation only). */

import type {
  AgreementLevel,
  AiChallengeView,
  AnalystConsensusView,
  ConfidenceMatrixView,
  DisplayField,
  MarketIntelligenceView,
  ResearchTimelineView,
  StreetComparisonRow,
} from "@/lib/analysis/types";
import type { ConfidenceLevel, SourceKind, ValueCategory } from "@/lib/trust/labels";
import { presentFieldLabel } from "@/lib/terminology";

function unavailable<T = string>(fallback: T | null = null): DisplayField<T> {
  return {
    presence: "unavailable",
    value: fallback,
    category: "unavailable",
    source: "unavailable",
  };
}

function available<T = string>(
  value: T,
  category: ValueCategory,
  source: SourceKind,
): DisplayField<T> {
  return { presence: "available", value, category, source };
}

const STREET_DIMS = [
  { id: "business_quality", label: "Business Quality" },
  { id: "financial_strength", label: "Financial Strength" },
  { id: "growth", label: "Growth" },
  { id: "risk", label: "Risk" },
  { id: "management", label: "Management" },
  { id: "competitive_advantage", label: "Competitive Advantage" },
  { id: "valuation", label: "Valuation" },
  { id: "research_confidence", label: "Research Confidence" },
] as const;

export function buildMarketIntelligence(args: {
  coveragePercent: number;
  lastUpdated: string | null;
}): MarketIntelligenceView {
  // External providers not wired — honest empty market layer.
  return {
    overallSentiment: unavailable(),
    coverageCount: unavailable(),
    consensusStrength: unavailable(),
    marketConfidence: unavailable(),
    researchCoverageNote: available(
      `DSP research coverage ${args.coveragePercent}% (internal completeness — not Street coverage)`,
      "calculated",
      "calculated_metric",
    ),
    lastUpdated: args.lastUpdated
      ? available(args.lastUpdated, "calculated", "calculated_metric")
      : unavailable(),
    dataAvailability: available(
      "External market consensus providers are not connected in this RC",
      "user_input",
      "user_input",
    ),
    available: false,
  };
}

export function buildAnalystConsensus(): AnalystConsensusView {
  return {
    summary: unavailable(),
    trend: unavailable(),
    agreementLevel: unavailable(),
    coverage: unavailable(),
    confidence: unavailable(),
    bullCase: unavailable(),
    baseCase: unavailable(),
    bearCase: unavailable(),
    historicalTrend: unavailable(),
    consensusChanges: unavailable(),
    coverageQuality: unavailable(),
    available: false,
  };
}

export function buildStreetComparison(args: {
  dspConclusion: string | null;
  dspConfidence: string | null;
}): StreetComparisonRow[] {
  return STREET_DIMS.map((dim) => {
    const dspValue =
      dim.id === "research_confidence"
        ? args.dspConfidence
        : dim.id === "valuation"
          ? presentFieldLabel("target_price") + " (see Valuation section)"
          : args.dspConclusion
            ? `DSP View context: ${args.dspConclusion}`
            : null;

    const dspField: DisplayField = dspValue
      ? available(dspValue, "calculated", "calculated_metric")
      : unavailable();

    const marketField = unavailable(
      "External consensus unavailable — providers not connected",
    );

    const agreement: AgreementLevel = "unavailable";

    return {
      id: dim.id,
      dimension: dim.label,
      dspResearch: dspField,
      marketConsensus: marketField,
      agreement,
      reasonForDifference:
        "Street data is not present in the API envelope. DSP Research remains the primary source of truth; no fabricated Street opinion is shown.",
      supportingEvidence: [
        "DSP conclusion mapped from analyze envelope when present",
        "Market consensus port defined in compliance architecture — not integrated yet",
      ],
      investorInterpretation:
        "Treat DSP Research independently until External Consensus is available. Do not assume Street agreement or disagreement.",
    };
  });
}

export function buildAiChallenge(args: {
  conclusionLabel: string | null;
  rationale: string | null;
  errors: string[];
  confidence: ConfidenceLevel;
}): AiChallengeView {
  const hasConclusion = Boolean(args.conclusionLabel);
  return {
    conclusionLabel: args.conclusionLabel ?? "Unavailable",
    supportingEvidence: args.rationale
      ? [
          `Envelope rationale cited: ${args.rationale}`,
          `Mapped DSP View: ${args.conclusionLabel}`,
        ]
      : hasConclusion
        ? [`DSP View label present: ${args.conclusionLabel}`]
        : [],
    contradictingEvidence: args.errors.length
      ? args.errors.map((e) => `Envelope error/limitation: ${e}`)
      : [
          "No contradicting artifacts in envelope — absence of dissent is not proof of correctness",
        ],
    assumptions: [
      {
        id: "a1",
        statement: "Backend envelope fields are complete enough for a decade view",
        importance: "High — many Sprint 2/3 cards remain Unavailable",
        category: "ai_interpretation",
      },
      {
        id: "a2",
        statement: "Mapped action tokens fairly represent research posture",
        importance: "High — Research Mode remaps engine tokens for display",
        category: "calculated",
      },
      {
        id: "a3",
        statement: "External consensus is not required to hold a DSP View",
        importance: "Medium — Street layer pending providers",
        category: "user_input",
      },
    ],
    confidence: args.confidence,
    limitations: [
      "AI Challenge is a structured prompt scaffold in Sprint 3 — full model challenge arrives with Copilot",
      "No fabricated bull/bear Street cases",
    ],
    researchGaps: [
      "Fundamentals & market quotes often missing",
      "Street consensus providers not connected",
      "Knowledge Graph / Copilot not in this sprint",
    ],
    investorWatchpoints: [
      "Re-run analysis when fundamentals load",
      "Compare filings against DSP View assumptions",
      "Do not treat Unavailable Street data as agreement",
    ],
    whatCouldInvalidate: [
      "Material change in leverage or liquidity",
      "Loss of competitive position",
      "Evidence that mapped posture was based on incomplete data",
    ],
    whatWouldChangeOpinion: [
      "Verified improvement in cash generation",
      "Durable moat evidence in filings",
      "Consistent execution vs prior plans",
    ],
    category: hasConclusion ? "ai_interpretation" : "unavailable",
    source: hasConclusion ? "ai_interpretation" : "unavailable",
    available: hasConclusion,
  };
}

export function buildConfidenceMatrix(args: {
  overall: ConfidenceLevel;
  hasConclusion: boolean;
}): ConfidenceMatrixView {
  const levelFor = (hasSignal: boolean): ConfidenceLevel =>
    hasSignal ? args.overall : "insufficient_evidence";

  return {
    overall: args.hasConclusion ? args.overall : "insufficient_evidence",
    rows: [
      { id: "business", label: "Business", level: levelFor(false) },
      { id: "financial", label: "Financial", level: levelFor(false) },
      { id: "growth", label: "Growth", level: levelFor(false) },
      { id: "risk", label: "Risk", level: levelFor(false) },
      { id: "management", label: "Management", level: levelFor(false) },
      { id: "valuation", label: "Valuation", level: levelFor(false) },
      {
        id: "overall",
        label: "Overall Research",
        level: args.hasConclusion ? args.overall : "insufficient_evidence",
      },
    ],
  };
}

export function buildResearchTimeline(args: {
  researchDate: string | null;
  lastUpdated: string | null;
  methodologyVersion: string;
}): ResearchTimelineView {
  return {
    events: [
      {
        id: "created",
        label: "Analysis created",
        at: args.researchDate,
        status: args.researchDate ? "done" : "placeholder",
        detail: "First successful analyze envelope for this session symbol",
      },
      {
        id: "updated",
        label: "Analysis updated",
        at: args.lastUpdated,
        status: args.lastUpdated ? "current" : "placeholder",
        detail: "Last envelope refresh in the workspace",
      },
      {
        id: "data_refresh",
        label: "Data refresh",
        at: null,
        status: "future",
        detail: "Awaiting scheduled fundamentals / market data refresh",
      },
      {
        id: "methodology",
        label: "Methodology version",
        at: args.methodologyVersion,
        status: "current",
        detail: "Presentation mapping version (thin client)",
      },
      {
        id: "future_research",
        label: "Future research events",
        at: null,
        status: "future",
        detail: "Street consensus connect · KG · Copilot challenge runs",
      },
      {
        id: "user_history",
        label: "User research history",
        at: null,
        status: "placeholder",
        detail: "Placeholder — personal history arrives in a later phase",
      },
    ],
  };
}
