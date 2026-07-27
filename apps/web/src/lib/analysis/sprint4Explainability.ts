/** Sprint 4 — Explainability builders (presentation only — no math / no LLM). */

import type {
  AssumptionExplorerView,
  ConfidenceBreakdownView,
  DecisionTraceStep,
  DecisionTraceView,
  EvidenceExplorerView,
  MethodologyPanelView,
  ReasoningFlowView,
  ResearchLimitationsView,
  TransparencyPanelView,
} from "@/lib/analysis/types";
import type { ConfidenceLevel, SourceKind, ValueCategory } from "@/lib/trust/labels";
import { CONFIDENCE_LABELS } from "@/lib/trust/labels";

function step(
  id: string,
  title: string,
  summary: string,
  details: string[],
  category: ValueCategory,
  source: SourceKind,
): DecisionTraceStep {
  return { id, title, summary, details, category, source };
}

export function buildDecisionTrace(args: {
  conclusionLabel: string | null;
  rationale: string | null;
  confidence: ConfidenceLevel;
  errors: string[];
  limitations: string[];
  coveragePercent: number;
}): DecisionTraceView {
  const has = Boolean(args.conclusionLabel);
  const label = args.conclusionLabel ?? "Unavailable";
  const confLabel = CONFIDENCE_LABELS[args.confidence];

  return {
    conclusionLabel: label,
    available: has,
    inputs: step(
      "inputs",
      "Inputs",
      has
        ? "Analyze envelope fields mapped into the workspace (symbol, posture, rationale when present)."
        : "No conclusion inputs yet — run Analyze via API.",
      [
        `DSP View label: ${label}`,
        args.rationale
          ? `Envelope rationale present (${Math.min(args.rationale.length, 120)} chars shown in Evidence).`
          : "Envelope rationale: Unavailable",
        `Research coverage (completeness meta): ${args.coveragePercent}%`,
        "Fundamentals / quotes: often Unavailable in this RC envelope",
      ],
      has ? "user_input" : "unavailable",
      has ? "user_input" : "unavailable",
    ),
    calculations: step(
      "calculations",
      "Calculations",
      "Presentation mapping only — no valuation or scoring math runs in the browser.",
      [
        "Thin client remaps Research Mode labels (presentAction / presentFieldLabel)",
        "Coverage % = available workspace fields ÷ cataloged fields (not company quality)",
        "Intrinsic value / MOS / scores: Unavailable unless present in envelope",
        "Decision Engine remains server-side; UI does not recompute",
      ],
      "calculated",
      "calculated_metric",
    ),
    businessRules: step(
      "business_rules",
      "Business Rules",
      "Research Mode + User Trust Standard govern what may be shown.",
      [
        "No BUY / SELL / HOLD or Official Target Price in Research Mode UI",
        "Unavailable is preferred over invented figures",
        "External Consensus may not be fabricated when providers are offline",
        "Evidence supporting vs contradicting kept separate",
      ],
      "calculated",
      "calculated_metric",
    ),
    evidenceUsed: step(
      "evidence_used",
      "Evidence Used",
      has
        ? "Evidence drawn from envelope artifacts and honest Unavailable markers."
        : "No evidence artifacts until an envelope loads.",
      [
        args.rationale ? "Supporting: envelope rationale cited" : "Supporting: none listed",
        args.errors.length
          ? `Contradicting / limiting: ${args.errors.length} envelope error(s)`
          : "Contradicting: none listed (absence ≠ proof)",
        "Street consensus: Unavailable — providers not connected",
        "See Evidence Explorer for grouped catalog",
      ],
      has ? "ai_interpretation" : "unavailable",
      has ? "ai_interpretation" : "unavailable",
    ),
    confidence: step(
      "confidence",
      "Confidence",
      `Overall research confidence: ${confLabel}`,
      [
        `Mapped level: ${confLabel}`,
        "Domain confidence often Insufficient Evidence when metrics are missing",
        "Confidence Breakdown explains why domains differ",
        "Coverage % is completeness meta — not a confidence score alone",
      ],
      has ? "calculated" : "unavailable",
      has ? "calculated_metric" : "unavailable",
    ),
    limitations: step(
      "limitations",
      "Limitations",
      "Known limits are surfaced so users do not over-trust sparse envelopes.",
      [
        ...(args.limitations.length
          ? args.limitations.slice(0, 4)
          : ["No API limitations array entries"]),
        ...(args.errors.length ? args.errors.slice(0, 3) : []),
        "Knowledge Graph / Copilot / LLM chat not in Sprint 4",
        "See Research Limitations section for the full professional list",
      ],
      "user_input",
      "user_input",
    ),
    reasoningChain: step(
      "reasoning_chain",
      "Reasoning Chain",
      "Raw data → normalized → metrics → business → valuation → risk → conclusion.",
      [
        "Follow Reasoning Flow for the visual pipeline",
        "Each node expands to status + what is missing",
        "AI interpretation appears only where envelope/posture exists",
        "No hidden LLM step in this sprint",
      ],
      "calculated",
      "calculated_metric",
    ),
    output: step(
      "output",
      "Output",
      has
        ? `Research conclusion surfaced as: ${label}`
        : "Output Unavailable — no DSP View mapped yet.",
      [
        `Displayed DSP View: ${label}`,
        "Dashboard mirrors conclusion + next investigation prompts",
        "Export / Portfolio deferred (Sprint 5+)",
        "Traceable via this Decision Trace + Methodology Panel",
      ],
      has ? "ai_interpretation" : "unavailable",
      has ? "ai_interpretation" : "unavailable",
    ),
  };
}

export function buildEvidenceExplorer(args: {
  conclusionLabel: string | null;
  rationale: string | null;
  lastUpdated: string | null;
  coveragePercent: number;
  errors: string[];
}): EvidenceExplorerView {
  const ts = args.lastUpdated;
  return {
    items: [
      {
        id: "ev-verified",
        title: "Verified financial statement line items",
        group: "verified_fact",
        source: "Not present in /analyze/company envelope (RC)",
        timestamp: null,
        confidence: "Insufficient Evidence",
        methodology: "Would require verified statement artifacts from backend providers",
        detail: "No fabricated filings. Cards stay Unavailable until verified facts arrive.",
      },
      {
        id: "ev-calc-coverage",
        title: "Research coverage percent",
        group: "calculated",
        source: "DSP presentation mapper (coverage.ts)",
        timestamp: ts,
        confidence: "Moderate",
        methodology:
          "available workspace fields ÷ cataloged fields — completeness meta, not company quality",
        detail: `Current coverage: ${args.coveragePercent}%`,
      },
      {
        id: "ev-estimated",
        title: "Estimated intrinsic / scenario bands",
        group: "estimated",
        source: "Unavailable — Decision Engine outputs not projected into UI",
        timestamp: null,
        confidence: "Insufficient Evidence",
        methodology: "Estimates only when envelope exposes them; browser never invents IV",
        detail: "Valuation cards remain educational until estimated fields arrive.",
      },
      {
        id: "ev-ai",
        title: "DSP View / research posture",
        group: "ai_interpretation",
        source: args.conclusionLabel
          ? "Mapped from analyze envelope action/posture"
          : "Unavailable",
        timestamp: ts,
        confidence: args.conclusionLabel ? "Low to Moderate" : "Insufficient Evidence",
        methodology: "Research Mode remaps engine tokens for display; no client LLM",
        detail: args.rationale
          ? `Rationale excerpt: ${args.rationale.slice(0, 180)}${args.rationale.length > 180 ? "…" : ""}`
          : args.conclusionLabel
            ? `Label only: ${args.conclusionLabel}`
            : "No AI interpretation artifact yet.",
      },
      {
        id: "ev-external",
        title: "External / Street consensus",
        group: "external_consensus",
        source: "Providers not connected",
        timestamp: null,
        confidence: "Insufficient Evidence",
        methodology: "Compliance consensus port exists; Sprint 3 UI stays Unavailable",
        detail: "DSP Research remains primary. No fabricated Street opinion.",
      },
      {
        id: "ev-user",
        title: "User-entered symbol / session context",
        group: "user_input",
        source: "Analysis workspace form",
        timestamp: ts,
        confidence: "High",
        methodology: "User-supplied ticker drives POST /api/v1/analyze/company",
        detail: "Symbol is a user input — not a verified fundamental.",
      },
      {
        id: "ev-unavailable",
        title: "Envelope errors & missing domains",
        group: "unavailable",
        source: "API envelope errors / empty domains",
        timestamp: ts,
        confidence: "Insufficient Evidence",
        methodology: "Honest Unavailable markers per User Trust Standard",
        detail: args.errors.length
          ? args.errors.slice(0, 5).join(" · ")
          : "Growth, risk, management, moat, and Street layers often Unavailable in this RC.",
      },
    ],
  };
}

export function buildAssumptionExplorer(args: {
  hasConclusion: boolean;
}): AssumptionExplorerView {
  return {
    items: [
      {
        id: "as-envelope",
        statement: "The analyze envelope is complete enough for a decade-style research view",
        sensitivity: "High",
        impact: "Most Sprint 2–3 cards stay Unavailable when this is wrong",
        confidence: args.hasConclusion ? "low" : "insufficient_evidence",
        alternativeAssumptions: [
          "Treat envelope as a thin posture signal only",
          "Require fundamentals before forming a DSP View",
        ],
        whatChangesIfWrong:
          "Investors should ignore sparse conclusions and wait for verified metrics",
        category: "ai_interpretation",
      },
      {
        id: "as-research-mode",
        statement: "Research Mode remapping fairly represents engine posture without advice",
        sensitivity: "High",
        impact: "Mislabeling could feel like a recommendation",
        confidence: "moderate",
        alternativeAssumptions: [
          "Show raw engine tokens with a disclaimer",
          "Hide posture until compliance-reviewed copy exists",
        ],
        whatChangesIfWrong:
          "UI copy and Trace wording would need a compliance terminology pass",
        category: "calculated",
      },
      {
        id: "as-street",
        statement: "External consensus is not required to hold a DSP Research view",
        sensitivity: "Medium",
        impact: "Users may over-weight DSP without Street context",
        confidence: "moderate",
        alternativeAssumptions: [
          "Block conclusion until Street providers connect",
          "Always show 'Street Unavailable' next to DSP View",
        ],
        whatChangesIfWrong:
          "Market Intelligence / DSP vs Street sections become mandatory gates",
        category: "user_input",
      },
      {
        id: "as-coverage",
        statement: "Coverage % reflects DSP research completeness, not business quality",
        sensitivity: "Medium",
        impact: "Misreading coverage as quality inflates trust",
        confidence: "high",
        alternativeAssumptions: [
          "Hide coverage until quality scores exist",
          "Rename to 'Research completeness'",
        ],
        whatChangesIfWrong:
          "Dashboard and sticky summary would need clearer labeling",
        category: "calculated",
      },
    ],
  };
}

export function buildReasoningFlow(args: {
  hasConclusion: boolean;
  coveragePercent: number;
  hasRationale: boolean;
}): ReasoningFlowView {
  const dataStatus =
    args.coveragePercent >= 40 ? "partial" : args.coveragePercent > 0 ? "partial" : "unavailable";
  return {
    nodes: [
      {
        id: "raw",
        label: "Raw Data",
        status: args.hasConclusion || args.coveragePercent > 0 ? "partial" : "unavailable",
        summary: "API envelope + user symbol",
        details: [
          "POST /api/v1/analyze/company response",
          "Many fundamental fields still absent in RC",
        ],
      },
      {
        id: "normalized",
        label: "Normalized Data",
        status: dataStatus,
        summary: "Presentation map → DisplayField / MetricView",
        details: [
          "mapEnvelope.ts normalizes presence, category, source",
          "Unavailable preferred over invention",
        ],
      },
      {
        id: "metrics",
        label: "Financial Metrics",
        status: "unavailable",
        summary: "Catalog cards educational until calculated values arrive",
        details: [
          "Business Quality & Financial Strength templates",
          "No client-side ratio math",
        ],
      },
      {
        id: "business",
        label: "Business Analysis",
        status: "unavailable",
        summary: "Growth · Risk · Management · Moat scaffolds",
        details: [
          "Sprint 2 insight cards",
          "Evidence empty until artifacts land",
        ],
      },
      {
        id: "valuation",
        label: "Valuation",
        status: "unavailable",
        summary: "IV / MOS / scenarios Unavailable in Research Mode UI when missing",
        details: [
          "No Official Target Price label",
          "Decision Engine remains server-side",
        ],
      },
      {
        id: "risk",
        label: "Risk",
        status: "unavailable",
        summary: "Risk categories listed; severity Unavailable without evidence",
        details: ["Educational risk taxonomy", "Challenge Mode lists invalidators"],
      },
      {
        id: "conclusion",
        label: "Research Conclusion",
        status: args.hasConclusion ? (args.hasRationale ? "complete" : "partial") : "unavailable",
        summary: args.hasConclusion
          ? "DSP View mapped from envelope"
          : "No conclusion until Analyze succeeds",
        details: [
          "Decision Trace + Evidence Explorer explain this step",
          "Confidence Breakdown labels overall research confidence",
        ],
      },
    ],
  };
}

export function buildConfidenceBreakdown(args: {
  overall: ConfidenceLevel;
  hasConclusion: boolean;
  coveragePercent: number;
}): ConfidenceBreakdownView {
  const miss = "insufficient_evidence" as const;
  const overall = args.hasConclusion ? args.overall : miss;
  const whyMissing =
    "Domain metrics are not in the envelope — confidence cannot rise above Insufficient Evidence without evidence.";
  return {
    overall,
    rows: [
      {
        id: "financial",
        label: "Financial Data",
        level: miss,
        whyDifferent: whyMissing,
      },
      {
        id: "business",
        label: "Business Quality",
        level: miss,
        whyDifferent: whyMissing,
      },
      {
        id: "growth",
        label: "Growth",
        level: miss,
        whyDifferent: whyMissing,
      },
      {
        id: "risk",
        label: "Risk",
        level: miss,
        whyDifferent:
          "Risk taxonomy is educational; severity/probability Unavailable without artifacts.",
      },
      {
        id: "management",
        label: "Management",
        level: miss,
        whyDifferent: whyMissing,
      },
      {
        id: "valuation",
        label: "Valuation",
        level: miss,
        whyDifferent:
          "IV and scenario bands are not projected; Research Mode does not invent prices.",
      },
      {
        id: "external",
        label: "External Data",
        level: miss,
        whyDifferent: "Street / consensus providers are not connected in this RC.",
      },
      {
        id: "overall",
        label: "Overall Research",
        level: overall,
        whyDifferent: args.hasConclusion
          ? `Posture mapped from envelope (${CONFIDENCE_LABELS[overall]}). Coverage completeness ${args.coveragePercent}% does not upgrade domain confidence.`
          : "No DSP View mapped — overall remains Insufficient Evidence.",
      },
    ],
  };
}

export function buildResearchLimitations(args: {
  apiLimitations: string[];
  errors: string[];
}): ResearchLimitationsView {
  return {
    unavailableData: [
      "Verified statement line items",
      "Market quotes / 52-week bands (often)",
      "Intrinsic value range & margin of safety",
      "Street consensus & analyst coverage",
      ...args.errors.slice(0, 3),
    ],
    unknownFactors: [
      "Material events after last envelope refresh",
      "Unmodeled competitive shocks",
      "Governance issues not present in artifacts",
      "Liquidity / microstructure not assessed in UI",
    ],
    assumptions: [
      "Envelope posture is a fair research signal when present",
      "Unavailable means missing — not neutral or bullish",
      "Coverage % is completeness, not quality",
    ],
    externalDependencies: [
      "Frozen backend v1.0.0-rc1 /api/v1",
      "Future consensus providers (compliance ports)",
      "Fundamentals / market data refresh jobs",
    ],
    pendingImprovements: [
      "Knowledge Graph (Sprint 5+)",
      "Copilot / LLM challenge (later)",
      "Export & Portfolio (non-goals this sprint)",
      ...(args.apiLimitations.length
        ? args.apiLimitations.slice(0, 3)
        : ["Richer envelope fields for domain metrics"]),
    ],
  };
}

export function buildMethodologyPanel(args: {
  platformVersion: string | null;
}): MethodologyPanelView {
  return {
    researchMethodology:
      "Thin-client presentation of Decision Engine envelopes under Research Mode + User Trust Standard. No browser valuation math. No LLM in Sprint 4.",
    analysisVersion: "web-0.3.3 / L1.2 Sprint 4 Explainability",
    calculationVersion: "Server Decision Engine (frozen RC) — UI does not recalculate",
    presentationVersion: "presentation-map v4 (L1.2 Sprint 4)",
    complianceVersion: args.platformVersion
      ? `Platform ${args.platformVersion} · packages/compliance terminology mirrored in web`
      : "packages/compliance terminology · Research Mode flags (web mirror)",
  };
}

export function buildTransparencyPanel(args: {
  hasConclusion: boolean;
  coveragePercent: number;
}): TransparencyPanelView {
  return {
    knownUnknowns: [
      "Whether missing fundamentals would change the DSP View",
      "Street agreement or disagreement (providers offline)",
      "True domain confidence once metrics load",
    ],
    unavailableData: [
      "Most Sprint 2 metric ratings",
      "External consensus",
      "Full AI Challenge model output",
    ],
    estimatedFields: [
      "Intrinsic value / scenarios — estimated only when envelope provides them (currently Unavailable)",
    ],
    aiGeneratedSections: args.hasConclusion
      ? [
          "Research Conclusion posture (mapped from envelope — not a live LLM chat)",
          "AI Challenge scaffold (structured prompts, not model text)",
        ]
      : ["No AI-generated conclusion in this session"],
    externalSources: [
      "None connected for Street consensus in this RC",
      `Internal coverage completeness: ${args.coveragePercent}%`,
    ],
  };
}
