/**
 * P2.3 — Map existing valuation outputs → Valuation Transparency (no recalculation).
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import { isUnavailableDisplay } from "@/lib/institutional-rating";
import type {
  ConsensusPanel,
  ExecutiveValuationCard,
  MarginOfSafetyPanel,
  ValuationMethodCard,
  ValuationTransparencyView,
} from "./types";

export const VALUATION_TRANSPARENCY_VERSION = "1.0.0" as const;

const DISCLAIMER =
  "Valuation Transparency remaps existing analyse valuation signals, stage summaries, and institutional valuation rating fields only. Sub-method values, weights, and categories that are not on the API stay Unavailable — never estimated.";

const METHOD_DEFS: { name: string; purpose: string; matchToken: string }[] = [
  {
    name: "DCF",
    purpose: "Discounted cash flow of projected free cash flows to equity or firm.",
    matchToken: "dcf",
  },
  {
    name: "Reverse DCF",
    purpose: "Implied growth or returns embedded in the current market price.",
    matchToken: "reverse",
  },
  {
    name: "Residual Income",
    purpose: "Book value plus the present value of expected residual earnings.",
    matchToken: "residual",
  },
  {
    name: "EPV",
    purpose: "Earnings power value based on normalized sustainable earnings.",
    matchToken: "epv",
  },
  {
    name: "Dividend Discount Model",
    purpose: "Present value of expected dividends under a stated growth path.",
    matchToken: "dividend",
  },
  {
    name: "Asset Based Valuation",
    purpose: "Net asset or liquidation-oriented estimate of equity value.",
    matchToken: "asset",
  },
  {
    name: "Relative Valuation",
    purpose: "Market multiples versus peers or historical trading ranges.",
    matchToken: "relative",
  },
  {
    name: "Cross Method Consensus",
    purpose: "Reported cross-method or stage consensus valuation label when present.",
    matchToken: "consensus",
  },
];

function orUnavailable(value: string | null | undefined): string {
  if (value == null || value === "" || isUnavailableDisplay(value)) {
    return "Unavailable";
  }
  return value;
}

function methodMatches(methodLabel: string, matchToken: string): boolean {
  const hay = methodLabel.toLowerCase();
  if (isUnavailableDisplay(methodLabel)) return false;
  if (matchToken === "dcf") {
    return hay.includes("dcf") && !hay.includes("reverse");
  }
  return hay.includes(matchToken);
}

function mapMethods(
  view: Omit<ResearchView, "valuationTransparency">,
): ValuationMethodCard[] {
  const methodLabel = view.valuation.method;
  const valuationStage = view.stages.find((s) => s.stage === "valuation");
  const stageAvailable =
    valuationStage?.status === "succeeded" || valuationStage?.has_result === true;
  const missingFromStage =
    valuationStage?.warnings?.length
      ? valuationStage.warnings.join("; ")
      : valuationStage?.error
        ? valuationStage.error
        : "Unavailable";

  return METHOD_DEFS.map((def) => {
    const matched = methodMatches(methodLabel, def.matchToken);
    const available = matched && (stageAvailable || !isUnavailableDisplay(methodLabel));
    const status = available ? "Available" : "Unavailable";

    return {
      methodName: def.name,
      purpose: def.purpose,
      status,
      intrinsicValue: available
        ? orUnavailable(view.valuation.intrinsicValue)
        : "Unavailable",
      weight: "Unavailable",
      contributionToConsensus: "Unavailable",
      explanation: available
        ? `Method label from valuation stage / signals matches “${def.name}” (${methodLabel}). Intrinsic value shown only when present on existing valuation outputs.`
        : `Sub-method “${def.name}” is not separately exposed on AnalyseResponse stage_summaries — not invented.`,
      confidence: available
        ? orUnavailable(view.valuation.confidence)
        : "Unavailable",
      dataCompleteness: "Unavailable",
      missingInputs: available ? orUnavailable(missingFromStage) : "Unavailable",
      assumptionsUsed: "Unavailable",
      sourceField: available
        ? "valuation.method + valuation_signals / stage_summaries.valuation"
        : "stage_summaries.valuation (sub-method not exposed)",
    };
  });
}

function mapConsensus(
  view: Omit<ResearchView, "valuationTransparency">,
  methods: ValuationMethodCard[],
): ConsensusPanel {
  const consensusMethod = methods.find(
    (m) => m.methodName === "Cross Method Consensus" && m.status === "Available",
  );
  const consensusValue = consensusMethod
    ? orUnavailable(view.valuation.intrinsicValue)
    : "Unavailable";

  return {
    highestValuation: "Unavailable",
    lowestValuation: "Unavailable",
    consensusValue,
    dispersionIndicator: "Unavailable",
    numberOfMethodsUsed: "Unavailable",
  };
}

function mapMarginOfSafety(
  view: Omit<ResearchView, "valuationTransparency">,
  consensus: ConsensusPanel,
): MarginOfSafetyPanel {
  return {
    currentPrice: orUnavailable(view.valuation.currentPrice),
    consensusIntrinsicValue: consensus.consensusValue,
    marginOfSafety: orUnavailable(view.valuation.marginOfSafety),
    /** Deep Discount / Fairly Valued bands are not on AnalyseResponse — never invent. */
    valuationCategory: "Unavailable",
  };
}

function mapExecutive(
  view: Omit<ResearchView, "valuationTransparency">,
): ExecutiveValuationCard {
  const valuationModule = view.ratings.modules.valuation;
  return {
    overallScoreOutOf10: orUnavailable(valuationModule.scoreOutOf10),
    grade: orUnavailable(valuationModule.grade),
    confidence: orUnavailable(view.valuation.confidence),
    currentMarketPrice: orUnavailable(view.valuation.currentPrice),
    intrinsicValue: orUnavailable(view.valuation.intrinsicValue),
    marginOfSafety: orUnavailable(view.valuation.marginOfSafety),
    valuationVerdict: orUnavailable(view.recommendationStage.label),
  };
}

export function mapValuationTransparency(
  view: Omit<ResearchView, "valuationTransparency">,
): ValuationTransparencyView {
  const methods = mapMethods(view);
  const consensus = mapConsensus(view, methods);
  return {
    kind: "valuation_transparency",
    version: VALUATION_TRANSPARENCY_VERSION,
    disclaimer: DISCLAIMER,
    executive: mapExecutive(view),
    methods,
    consensus,
    marginOfSafety: mapMarginOfSafety(view, consensus),
  };
}
