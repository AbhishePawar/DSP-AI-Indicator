/**
 * Winner Matrix — presentation ranking from server-provided scores only.
 * Dimensions without a dedicated engine field remain Data unavailable. (no medals).
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import { DATA_UNAVAILABLE } from "./constants";
import {
  assignMedals,
  honestDisplay,
  isUnavailableDisplay,
  parseExistingScore,
} from "./ranking";
import type {
  WinnerMatrixDimensionId,
  WinnerMatrixRow,
} from "./types";

type ScoreExtractor = (view: ResearchView) => {
  display: string;
  numeric: number | null;
  evidence: string;
};

function fromStageScore(
  section: ResearchView["businessQuality"],
  evidenceLabel: string,
): ReturnType<ScoreExtractor> {
  const display = honestDisplay(section.score);
  return {
    display,
    numeric: parseExistingScore(section.score),
    evidence: `${evidenceLabel} stage=${section.stage} status=${section.status} score=${section.score}`,
  };
}

function fromModuleScore(
  module: ResearchView["ratings"]["modules"]["valuation"],
): ReturnType<ScoreExtractor> {
  const display = honestDisplay(module.scoreOutOf10);
  return {
    display: isUnavailableDisplay(module.scoreOutOf10)
      ? DATA_UNAVAILABLE
      : `${module.scoreOutOf10} (${module.grade})`,
    numeric: parseExistingScore(module.scoreOutOf10),
    evidence: `module=${module.id} sources=${module.sourceStages.join(",")}`,
  };
}

function unavailableExtractor(reason: string): ScoreExtractor {
  return () => ({
    display: DATA_UNAVAILABLE,
    numeric: null,
    evidence: reason,
  });
}

const DIMENSIONS: {
  id: WinnerMatrixDimensionId;
  label: string;
  extract: ScoreExtractor;
}[] = [
  {
    id: "businessQuality",
    label: "Business Quality",
    extract: (v) => fromStageScore(v.businessQuality, "business_quality_aggregator"),
  },
  {
    id: "management",
    label: "Management",
    extract: (v) => fromStageScore(v.management, "management_quality"),
  },
  {
    id: "moat",
    label: "Moat",
    extract: (v) => fromStageScore(v.moat, "economic_moat"),
  },
  {
    id: "risk",
    label: "Risk",
    extract: (v) => {
      // Book-07 risk is not a typed score on /analyse — ratings module may be unavailable.
      const mod = v.ratings.modules.riskAssessment;
      if (isUnavailableDisplay(mod.scoreOutOf10)) {
        return {
          display: DATA_UNAVAILABLE,
          numeric: null,
          evidence:
            "No dedicated risk score on frozen /analyse contract; riskAssessment module unavailable.",
        };
      }
      return fromModuleScore(mod);
    },
  },
  {
    id: "valuation",
    label: "Valuation",
    extract: (v) => fromModuleScore(v.ratings.modules.valuation),
  },
  {
    id: "capitalAllocation",
    label: "Capital Allocation",
    extract: (v) => fromModuleScore(v.ratings.modules.capitalAllocation),
  },
  {
    id: "cashFlow",
    label: "Cash Flow",
    extract: unavailableExtractor(
      "No dedicated cash-flow score field on frozen /analyse stage summaries.",
    ),
  },
  {
    id: "roce",
    label: "ROCE",
    extract: unavailableExtractor(
      "No dedicated ROCE field on frozen /analyse response — CV-001 forbids catalogue substitution.",
    ),
  },
  {
    id: "margins",
    label: "Margins",
    extract: unavailableExtractor(
      "No dedicated margin score field on frozen /analyse stage summaries.",
    ),
  },
  {
    id: "growth",
    label: "Growth",
    extract: (v) => fromStageScore(v.growth, "growth_quality"),
  },
  {
    id: "financialStrength",
    label: "Financial Strength",
    extract: (v) => fromStageScore(v.financialStrength, "financial_strength"),
  },
  {
    id: "confidence",
    label: "Confidence",
    extract: (v) => {
      const pct =
        v.recommendationConfidence != null
          ? `${Math.round(v.recommendationConfidence * 100)}%`
          : DATA_UNAVAILABLE;
      return {
        display: pct,
        numeric:
          v.recommendationConfidence != null
            ? v.recommendationConfidence * 100
            : null,
        evidence: "recommendation_summary.confidence",
      };
    },
  },
  {
    id: "overall",
    label: "Overall",
    extract: (v) => {
      const o = v.ratings.overall;
      const display = isUnavailableDisplay(o.scoreOutOf10)
        ? DATA_UNAVAILABLE
        : `${o.scoreOutOf10} (${o.grade})`;
      return {
        display,
        numeric: parseExistingScore(o.scoreOutOf10),
        evidence: "institutional_rating_framework.overall (presentation remap)",
      };
    },
  },
];

export function mapWinnerMatrix(views: ResearchView[]): WinnerMatrixRow[] {
  return DIMENSIONS.map((dim) => {
    const extracted = views.map((v) => ({
      symbol: v.ticker,
      ...dim.extract(v),
    }));
    const medals = assignMedals(
      extracted.map((e) => ({ symbol: e.symbol, numeric: e.numeric })),
    );
    const cells = extracted.map((e) => ({
      symbol: e.symbol,
      display: e.display,
      numeric: e.numeric,
      medal: medals[e.symbol] ?? null,
      evidence: e.evidence,
    }));
    const gold = cells.find((c) => c.medal === "gold");
    return {
      id: dim.id,
      label: dim.label,
      cells,
      leader: gold ? gold.symbol : DATA_UNAVAILABLE,
    };
  });
}
