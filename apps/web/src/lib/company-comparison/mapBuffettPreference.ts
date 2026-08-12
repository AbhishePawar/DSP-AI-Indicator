/**
 * Buffett-style Preference Analysis — presentation alignment only.
 *
 * CRITICAL wording:
 * Always: "According to the Buffett-inspired framework implemented by DSP AI Indicator..."
 * Never: "Buffett would buy."
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import type { BuffettMatrixState } from "@/lib/buffett-indicator";
import {
  BUFFETT_FRAMEWORK_PREFIX,
  DATA_UNAVAILABLE,
} from "./constants";
import { isUnavailableDisplay } from "./ranking";
import type {
  BuffettAlignment,
  BuffettPreferenceDimensionId,
  BuffettPreferenceRow,
} from "./types";

function stateToAlignment(state: BuffettMatrixState | undefined): BuffettAlignment {
  if (!state || state === "unavailable") return "unavailable";
  if (state === "met") return "aligned";
  return "not_aligned";
}

function gradeToAlignment(grade: string): BuffettAlignment {
  if (isUnavailableDisplay(grade)) return "unavailable";
  const g = grade.trim().toUpperCase();
  if (g.startsWith("A") || g.startsWith("B+")) return "aligned";
  if (g.startsWith("B") || g === "C") return "partial";
  if (g === "D" || g === "F") return "not_aligned";
  return "partial";
}

function matrixState(
  view: ResearchView,
  criterionIncludes: string,
): BuffettMatrixState | undefined {
  const hit = view.buffett.decisionMatrix.find((m) =>
    m.criterion.toLowerCase().includes(criterionIncludes.toLowerCase()),
  );
  return hit?.state;
}

function matrixEvidence(
  view: ResearchView,
  criterionIncludes: string,
): string {
  const hit = view.buffett.decisionMatrix.find((m) =>
    m.criterion.toLowerCase().includes(criterionIncludes.toLowerCase()),
  );
  return hit?.evidence ?? DATA_UNAVAILABLE;
}

function scorecardGrade(
  view: ResearchView,
  dimensionIncludes: string,
): string {
  const hit = view.buffett.scorecard.find((r) =>
    r.dimension.toLowerCase().includes(dimensionIncludes.toLowerCase()),
  );
  return hit?.grade ?? DATA_UNAVAILABLE;
}

type DimSpec = {
  id: BuffettPreferenceDimensionId;
  label: string;
  cell: (view: ResearchView) => {
    alignment: BuffettAlignment;
    reason: string;
    evidence: string;
    confidence: string;
  };
};

const DIMENSIONS: DimSpec[] = [
  {
    id: "understandability",
    label: "Understandability / Circle of Competence",
    cell: (v) => {
      const alignment = stateToAlignment(
        matrixState(v, "circle") ?? matrixState(v, "competence"),
      );
      const sub = v.buffett.circleOfCompetence;
      return {
        alignment:
          alignment !== "unavailable"
            ? alignment
            : isUnavailableDisplay(sub.verdict)
              ? "unavailable"
              : "partial",
        reason: `${BUFFETT_FRAMEWORK_PREFIX}, understandability is assessed from the existing Circle of Competence synthesis: ${sub.verdict}.`,
        evidence: matrixEvidence(v, "circle") !== DATA_UNAVAILABLE
          ? matrixEvidence(v, "circle")
          : sub.bullets[0] ?? DATA_UNAVAILABLE,
        confidence: v.buffett.confidence,
      };
    },
  },
  {
    id: "moat",
    label: "Economic Moat",
    cell: (v) => {
      const alignment =
        stateToAlignment(matrixState(v, "moat")) !== "unavailable"
          ? stateToAlignment(matrixState(v, "moat"))
          : gradeToAlignment(scorecardGrade(v, "moat"));
      return {
        alignment,
        reason: `${BUFFETT_FRAMEWORK_PREFIX}, moat alignment uses the existing economic moat stage/synthesis (label ${v.moat.label}, score ${v.moat.score}).`,
        evidence: v.buffett.economicMoat.bullets[0] ?? matrixEvidence(v, "moat"),
        confidence: honestConf(v.moat.confidence, v.buffett.confidence),
      };
    },
  },
  {
    id: "management",
    label: "Management Quality",
    cell: (v) => {
      const alignment =
        stateToAlignment(matrixState(v, "management")) !== "unavailable"
          ? stateToAlignment(matrixState(v, "management"))
          : gradeToAlignment(scorecardGrade(v, "management"));
      return {
        alignment,
        reason: `${BUFFETT_FRAMEWORK_PREFIX}, management preference uses the existing management_quality stage (label ${v.management.label}).`,
        evidence:
          v.buffett.managementQuality.bullets[0] ??
          matrixEvidence(v, "management"),
        confidence: honestConf(v.management.confidence, v.buffett.confidence),
      };
    },
  },
  {
    id: "capitalAllocation",
    label: "Capital Allocation",
    cell: (v) => {
      const mod = v.ratings.modules.capitalAllocation;
      const alignment = isUnavailableDisplay(mod.scoreOutOf10)
        ? stateToAlignment(matrixState(v, "capital"))
        : gradeToAlignment(mod.grade);
      return {
        alignment,
        reason: `${BUFFETT_FRAMEWORK_PREFIX}, capital-allocation alignment remaps existing capital allocation / management outputs (grade ${mod.grade}).`,
        evidence: mod.evidence[0] ?? v.buffett.capitalAllocation.bullets[0] ?? DATA_UNAVAILABLE,
        confidence: honestConf(mod.confidence, v.buffett.confidence),
      };
    },
  },
  {
    id: "roce",
    label: "ROCE",
    cell: () => ({
      alignment: "unavailable",
      reason: `${BUFFETT_FRAMEWORK_PREFIX}, ROCE preference cannot be stated — no dedicated ROCE field exists on the frozen /analyse contract.`,
      evidence: DATA_UNAVAILABLE,
      confidence: DATA_UNAVAILABLE,
    }),
  },
  {
    id: "debt",
    label: "Debt / Leverage Discipline",
    cell: (v) => {
      const fortress = v.buffett.financialFortress;
      const alignment = isUnavailableDisplay(fortress.verdict)
        ? "unavailable"
        : gradeToAlignment(scorecardGrade(v, "financial") !== DATA_UNAVAILABLE
            ? scorecardGrade(v, "financial")
            : v.financialStrength.score);
      return {
        alignment,
        reason: `${BUFFETT_FRAMEWORK_PREFIX}, debt discipline is inferred only from existing financial fortress / financial_strength synthesis: ${fortress.verdict}.`,
        evidence: fortress.bullets[0] ?? DATA_UNAVAILABLE,
        confidence: honestConf(v.financialStrength.confidence, v.buffett.confidence),
      };
    },
  },
  {
    id: "cash",
    label: "Cash / Liquidity",
    cell: (v) => {
      // Liquidity metric on FS stage is label remapping — treat as unavailable for preference unless fortress speaks to cash.
      const bullet =
        v.buffett.financialFortress.bullets.find((b) =>
          /cash|liquidity|fortress/i.test(b),
        ) ?? null;
      if (!bullet) {
        return {
          alignment: "unavailable",
          reason: `${BUFFETT_FRAMEWORK_PREFIX}, cash preference remains unavailable — no dedicated cash score on /analyse.`,
          evidence: DATA_UNAVAILABLE,
          confidence: DATA_UNAVAILABLE,
        };
      }
      return {
        alignment: "partial",
        reason: `${BUFFETT_FRAMEWORK_PREFIX}, cash commentary is limited to existing fortress synthesis text (not a cash score).`,
        evidence: bullet,
        confidence: honestConf(v.financialStrength.confidence, v.buffett.confidence),
      };
    },
  },
  {
    id: "reinvestment",
    label: "Reinvestment Opportunity",
    cell: (v) => {
      const metric = v.businessQuality.metrics.find((m) =>
        m.label.toLowerCase().includes("reinvestment"),
      );
      // toSection maps unused metric slots to "Unavailable" — honour that.
      if (!metric || isUnavailableDisplay(metric.value)) {
        const growthOk =
          v.growth.status === "succeeded" &&
          !isUnavailableDisplay(v.growth.score);
        if (!growthOk) {
          return {
            alignment: "unavailable",
            reason: `${BUFFETT_FRAMEWORK_PREFIX}, reinvestment preference cannot be calculated from available stage fields.`,
            evidence: DATA_UNAVAILABLE,
            confidence: DATA_UNAVAILABLE,
          };
        }
        return {
          alignment: gradeToAlignment(v.growth.score),
          reason: `${BUFFETT_FRAMEWORK_PREFIX}, reinvestment cues use the existing growth_quality stage only (score ${v.growth.score}) — not a dedicated reinvestment engine.`,
          evidence: `growth_quality label=${v.growth.label}`,
          confidence: v.growth.confidence,
        };
      }
      return {
        alignment: "partial",
        reason: `${BUFFETT_FRAMEWORK_PREFIX}, reinvestment references the existing business-quality metric slot: ${metric.value}.`,
        evidence: `${metric.label}=${metric.value}`,
        confidence: v.businessQuality.confidence,
      };
    },
  },
  {
    id: "marginOfSafety",
    label: "Margin of Safety",
    cell: (v) => {
      const mos = v.valuation.marginOfSafety;
      const iv = v.buffett.intrinsicValue;
      if (isUnavailableDisplay(mos) && isUnavailableDisplay(iv.marginOfSafety)) {
        return {
          alignment: "unavailable",
          reason: `${BUFFETT_FRAMEWORK_PREFIX}, margin-of-safety preference is unavailable — MoS not present on research outputs.`,
          evidence: DATA_UNAVAILABLE,
          confidence: DATA_UNAVAILABLE,
        };
      }
      const display = !isUnavailableDisplay(mos) ? mos : iv.marginOfSafety;
      const n = Number(String(display).replace(/%/g, ""));
      let alignment: BuffettAlignment = "partial";
      if (!Number.isFinite(n)) alignment = "partial";
      else if (n >= 30) alignment = "aligned";
      else if (n >= 10) alignment = "partial";
      else alignment = "not_aligned";
      return {
        alignment,
        reason: `${BUFFETT_FRAMEWORK_PREFIX}, MoS preference uses the existing recommendation/valuation MoS field (${display}) — thresholds are display banding only, not a new valuation.`,
        evidence: `MoS=${display}; IV=${iv.intrinsicValue}; Price=${iv.currentPrice}`,
        confidence: honestConf(v.valuation.confidence, v.buffett.confidence),
      };
    },
  },
  {
    id: "durability",
    label: "Long-term Durability",
    cell: (v) => {
      const risks = v.buffett.longTermRisks;
      const moatAligned = stateToAlignment(matrixState(v, "moat"));
      if (
        moatAligned === "unavailable" &&
        isUnavailableDisplay(risks.verdict) &&
        isUnavailableDisplay(v.moat.score)
      ) {
        return {
          alignment: "unavailable",
          reason: `${BUFFETT_FRAMEWORK_PREFIX}, durability preference cannot be stated from available outputs.`,
          evidence: DATA_UNAVAILABLE,
          confidence: DATA_UNAVAILABLE,
        };
      }
      return {
        alignment:
          moatAligned !== "unavailable"
            ? moatAligned
            : gradeToAlignment(v.moat.score),
        reason: `${BUFFETT_FRAMEWORK_PREFIX}, durability alignment combines existing moat and long-term risk synthesis (${risks.verdict}).`,
        evidence: risks.bullets[0] ?? `moat=${v.moat.label}`,
        confidence: honestConf(v.moat.confidence, v.buffett.confidence),
      };
    },
  },
];

function honestConf(primary: string, fallback: string): string {
  if (!isUnavailableDisplay(primary)) return primary;
  if (!isUnavailableDisplay(fallback)) return fallback;
  return DATA_UNAVAILABLE;
}

function tradeOffForRow(
  cells: { symbol: string; alignment: BuffettAlignment }[],
): string {
  const aligned = cells.filter((c) => c.alignment === "aligned").map((c) => c.symbol);
  const notAligned = cells
    .filter((c) => c.alignment === "not_aligned")
    .map((c) => c.symbol);
  const unavailable = cells
    .filter((c) => c.alignment === "unavailable")
    .map((c) => c.symbol);
  if (aligned.length && notAligned.length) {
    return `${BUFFETT_FRAMEWORK_PREFIX}, ${aligned.join(", ")} show stronger framework alignment than ${notAligned.join(", ")} on this dimension.`;
  }
  if (unavailable.length === cells.length) {
    return `${BUFFETT_FRAMEWORK_PREFIX}, coverage is insufficient to state a trade-off on this dimension.`;
  }
  if (aligned.length === cells.length) {
    return `${BUFFETT_FRAMEWORK_PREFIX}, all compared companies present aligned signals on this dimension.`;
  }
  return `${BUFFETT_FRAMEWORK_PREFIX}, alignment differs across the set; review evidence cells rather than treating any company as a buy recommendation.`;
}

/** Forbidden phrases for copy compliance tests / runtime guards. */
export const FORBIDDEN_BUFFETT_PHRASES = [
  "buffett would buy",
  "buffett would sell",
  "warren buffett would",
  "buffett recommends",
] as const;

export function containsForbiddenBuffettCopy(text: string): boolean {
  const lower = text.toLowerCase();
  return FORBIDDEN_BUFFETT_PHRASES.some((p) => lower.includes(p));
}

export function mapBuffettPreference(
  views: ResearchView[],
): BuffettPreferenceRow[] {
  return DIMENSIONS.map((dim) => {
    const cells = views.map((v) => {
      const c = dim.cell(v);
      // Hard guard — never emit forbidden endorsement language.
      const reason = containsForbiddenBuffettCopy(c.reason)
        ? `${BUFFETT_FRAMEWORK_PREFIX}, alignment is presented from existing research outputs only.`
        : c.reason;
      return {
        symbol: v.ticker,
        alignment: c.alignment,
        reason,
        evidence: c.evidence,
        confidence: c.confidence,
      };
    });
    return {
      id: dim.id,
      label: dim.label,
      framing: `${BUFFETT_FRAMEWORK_PREFIX}…`,
      cells,
      tradeOff: tradeOffForRow(cells),
    };
  });
}
