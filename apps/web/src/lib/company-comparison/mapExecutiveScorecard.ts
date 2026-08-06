/**
 * Executive Comparison Scorecard — institutional scorecard from existing outputs.
 * Overall, BQ, Mgmt, Moat, Risk, Valuation, Financial, Research Confidence,
 * Evidence Strength, Overall Position.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import { DATA_UNAVAILABLE } from "./constants";
import { mapEvidenceStrengthMeters } from "./mapEvidenceStrength";
import {
  honestDisplay,
  isUnavailableDisplay,
  parseExistingScore,
} from "./ranking";
import type {
  EvidenceStrengthMeter,
  ExecutiveScorecardRow,
  WinnerMatrixRow,
} from "./types";
import {
  getWeightingProfile,
  presentationEmphasis,
  type EmphasisDimensionId,
  type WeightingProfileId,
} from "./weightingProfiles";

function emphasisKey(
  id: ExecutiveScorecardRow["id"],
): EmphasisDimensionId {
  if (id === "financial") return "financialStrength";
  return id;
}

function moduleDisplay(
  score: string,
  label: string,
): { display: string; numeric: number | null } {
  const scoreDisp = honestDisplay(score);
  const labelDisp = honestDisplay(label);
  if (scoreDisp === DATA_UNAVAILABLE && labelDisp === DATA_UNAVAILABLE) {
    return { display: DATA_UNAVAILABLE, numeric: null };
  }
  if (scoreDisp === DATA_UNAVAILABLE) {
    return { display: labelDisp, numeric: null };
  }
  return {
    display:
      labelDisp === DATA_UNAVAILABLE
        ? scoreDisp
        : `${scoreDisp} (${labelDisp})`,
    numeric: parseExistingScore(score),
  };
}

export function mapExecutiveScorecard(
  views: ResearchView[],
  winnerMatrix: WinnerMatrixRow[],
  evidenceMeters?: EvidenceStrengthMeter[],
  weightingProfileId: WeightingProfileId = "equal",
): ExecutiveScorecardRow[] {
  const meters =
    evidenceMeters ?? mapEvidenceStrengthMeters(views);
  const meterBySymbol = new Map(meters.map((m) => [m.symbol, m]));
  const profile = getWeightingProfile(weightingProfileId);

  const overallRow = winnerMatrix.find((r) => r.id === "overall");

  const defs: {
    id: ExecutiveScorecardRow["id"];
    label: string;
    pick: (v: ResearchView) => { display: string; evidence: string };
  }[] = [
    {
      id: "overall",
      label: "Overall",
      pick: (v) => ({
        display: honestDisplay(v.ratings.overall.scoreOutOf10),
        evidence: `ratings.overall grade=${v.ratings.overall.grade}`,
      }),
    },
    {
      id: "businessQuality",
      label: "Business Quality",
      pick: (v) => {
        const m = moduleDisplay(v.businessQuality.score, v.businessQuality.label);
        return {
          display: m.display,
          evidence: `business_quality_aggregator status=${v.businessQuality.status}`,
        };
      },
    },
    {
      id: "management",
      label: "Management",
      pick: (v) => {
        const m = moduleDisplay(v.management.score, v.management.label);
        return {
          display: m.display,
          evidence: `management_quality status=${v.management.status}`,
        };
      },
    },
    {
      id: "moat",
      label: "Moat",
      pick: (v) => {
        const m = moduleDisplay(v.moat.score, v.moat.label);
        return {
          display: m.display,
          evidence: `economic_moat status=${v.moat.status}`,
        };
      },
    },
    {
      id: "risk",
      label: "Risk",
      pick: (v) => {
        const mod = v.ratings.modules.riskAssessment;
        const m = moduleDisplay(mod.scoreOutOf10, mod.grade);
        return {
          display: m.display,
          evidence: `riskAssessment module sources=${mod.sourceStages.join(",") || "none"}`,
        };
      },
    },
    {
      id: "valuation",
      label: "Valuation",
      pick: (v) => {
        const mod = v.ratings.modules.valuation;
        const mos = honestDisplay(v.valuation.marginOfSafety);
        const scoreDisp = honestDisplay(mod.scoreOutOf10);
        const display =
          scoreDisp === DATA_UNAVAILABLE && mos === DATA_UNAVAILABLE
            ? DATA_UNAVAILABLE
            : `score=${scoreDisp}; MoS=${mos}`;
        return {
          display,
          evidence: `valuation transparency + ratings.modules.valuation`,
        };
      },
    },
    {
      id: "financial",
      label: "Financial",
      pick: (v) => {
        const m = moduleDisplay(
          v.financialStrength.score,
          v.financialStrength.label,
        );
        return {
          display: m.display,
          evidence: `financial_strength status=${v.financialStrength.status}`,
        };
      },
    },
    {
      id: "researchConfidence",
      label: "Research Confidence",
      pick: (v) => ({
        display:
          v.recommendationConfidence != null
            ? `${Math.round(v.recommendationConfidence * 100)}%`
            : DATA_UNAVAILABLE,
        evidence: "recommendationConfidence from analyse payload",
      }),
    },
    {
      id: "evidenceStrength",
      label: "Evidence Strength",
      pick: (v) => {
        const meter = meterBySymbol.get(v.ticker);
        return {
          display: meter?.level ?? DATA_UNAVAILABLE,
          evidence: meter?.rationale ?? DATA_UNAVAILABLE,
        };
      },
    },
    {
      id: "overallPosition",
      label: "Overall Position",
      pick: (v) => {
        if (!overallRow) {
          return { display: DATA_UNAVAILABLE, evidence: DATA_UNAVAILABLE };
        }
        const cell = overallRow.cells.find((c) => c.symbol === v.ticker);
        if (!cell || isUnavailableDisplay(cell.display)) {
          return { display: DATA_UNAVAILABLE, evidence: cell?.evidence ?? DATA_UNAVAILABLE };
        }
        const medal = cell.medal ? ` [${cell.medal}]` : "";
        const leaderNote =
          overallRow.leader === v.ticker
            ? " · dimension leader"
            : overallRow.leader !== DATA_UNAVAILABLE
              ? ` · leader=${overallRow.leader}`
              : "";
        return {
          display: `${cell.display}${medal}${leaderNote}`,
          evidence: cell.evidence,
        };
      },
    },
  ];

  return defs.map((def) => ({
    id: def.id,
    label: def.label,
    emphasis: presentationEmphasis(profile, emphasisKey(def.id)),
    cells: views.map((v) => {
      const picked = def.pick(v);
      return {
        symbol: v.ticker,
        display: picked.display,
        evidence: picked.evidence,
        emphasis: presentationEmphasis(profile, emphasisKey(def.id)),
      };
    }),
  }));
}
