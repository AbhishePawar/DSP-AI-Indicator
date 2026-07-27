/**
 * AnswerComposer — compose deterministic answers from CopilotCompanyContext.
 * Never invents facts. Returns UNAVAILABLE_ANSWER when fields are missing.
 */

import { formatPct, formatScore } from "@/lib/intelligence/mapResponse";
import { compareCompanyContexts } from "./comparison";
import { UNAVAILABLE_ANSWER } from "./questions";
import type {
  CopilotCompanyContext,
  CopilotComposedAnswer,
  CopilotIntent,
  ResearchCitationId,
  StageFieldSummary,
} from "./types";

function isMissingText(value: string | null | undefined): boolean {
  if (value == null) return true;
  const v = value.trim();
  return (
    v === "" ||
    v === "—" ||
    v.toLowerCase() === "unavailable" ||
    v.toLowerCase() === "none reported"
  );
}

function formatStage(stage: StageFieldSummary): string | null {
  if (!stage.available) return null;
  const parts = [
    stage.label ? `Label: ${stage.label}` : null,
    stage.decision ? `Decision: ${stage.decision}` : null,
    stage.score != null ? `Score: ${formatScore(stage.score)}` : null,
    stage.confidence != null
      ? `Confidence: ${formatPct(stage.confidence)}`
      : null,
    stage.status ? `Status: ${stage.status}` : null,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : null;
}

function joinBullets(items: string[]): string | null {
  const cleaned = items.filter((item) => !isMissingText(item));
  if (!cleaned.length) return null;
  return cleaned.map((item) => `• ${item}`).join("\n");
}

function answer(
  content: string,
  citations: ResearchCitationId[],
  intent: CopilotIntent,
  unavailable = false,
): CopilotComposedAnswer {
  return { content, citations, intent, unavailable };
}

function unavailable(intent: CopilotIntent): CopilotComposedAnswer {
  return answer(UNAVAILABLE_ANSWER, [], intent, true);
}

export function composeAnswer(
  intent: CopilotIntent,
  primary: CopilotCompanyContext | null,
  secondary: CopilotCompanyContext | null = null,
): CopilotComposedAnswer {
  if (!primary) {
    return answer(
      `${UNAVAILABLE_ANSWER} Run an analysis first, then return to Copilot with a research session loaded.`,
      [],
      intent,
      true,
    );
  }

  const { ticker, company } = primary;

  switch (intent) {
    case "explain_recommendation": {
      if (isMissingText(primary.recommendation)) return unavailable(intent);
      return answer(
        [
          `For ${company} (${ticker}), the composition pipeline returned recommendation: ${primary.recommendation}.`,
          `Confidence: ${formatPct(primary.recommendationConfidence)}.`,
          `Margin of safety: ${formatPct(primary.marginOfSafety)}.`,
          "This restates API fields only — it is not a new recommendation.",
        ].join("\n"),
        ["Recommendation", "Valuation"],
        intent,
      );
    }
    case "explain_valuation": {
      if (
        primary.intrinsicValue == null &&
        primary.currentPrice == null &&
        primary.marginOfSafety == null
      ) {
        return unavailable(intent);
      }
      return answer(
        [
          `Valuation fields available for ${ticker}:`,
          primary.intrinsicValue != null
            ? `• Intrinsic value (request signal): ${primary.intrinsicValue}`
            : null,
          primary.currentPrice != null
            ? `• Current price (request signal): ${primary.currentPrice}`
            : null,
          `• Margin of safety (API summary): ${formatPct(primary.marginOfSafety)}`,
        ]
          .filter(Boolean)
          .join("\n"),
        ["Valuation"],
        intent,
      );
    }
    case "explain_margin_of_safety": {
      if (primary.marginOfSafety == null) return unavailable(intent);
      return answer(
        `Margin of safety for ${ticker}: ${formatPct(primary.marginOfSafety)}. This value comes from the recommendation summary on the analyse response.`,
        ["Valuation", "Recommendation"],
        intent,
      );
    }
    case "explain_moat": {
      const moat = formatStage(primary.economicMoat);
      if (!moat) return unavailable(intent);
      return answer(
        `Economic moat stage summary for ${ticker}:\n${moat}`,
        ["Economic Moat"],
        intent,
      );
    }
    case "explain_management": {
      const mgmt = formatStage(primary.managementQuality);
      if (!mgmt) return unavailable(intent);
      return answer(
        `Management quality stage summary for ${ticker}:\n${mgmt}`,
        ["Management Quality"],
        intent,
      );
    }
    case "explain_financial_strength": {
      const fs = formatStage(primary.financialStrength);
      if (!fs) return unavailable(intent);
      return answer(
        `Financial strength stage summary for ${ticker}:\n${fs}`,
        ["Financial Strength"],
        intent,
      );
    }
    case "explain_earnings_quality": {
      const eq = formatStage(primary.earningsQuality);
      if (!eq) return unavailable(intent);
      return answer(
        `Earnings quality stage summary for ${ticker}:\n${eq}`,
        ["Earnings Quality"],
        intent,
      );
    }
    case "explain_growth_quality": {
      const gq = formatStage(primary.growthQuality);
      if (!gq) return unavailable(intent);
      return answer(
        `Growth quality stage summary for ${ticker}:\n${gq}`,
        ["Growth Quality"],
        intent,
      );
    }
    case "summarise_strengths": {
      const list = joinBullets(primary.strengths);
      if (!list) return unavailable(intent);
      return answer(
        `Strengths reported for ${ticker}:\n${list}`,
        ["Overview"],
        intent,
      );
    }
    case "summarise_weaknesses": {
      const list = joinBullets([...primary.weaknesses, ...primary.risks]);
      if (!list) return unavailable(intent);
      return answer(
        `Weaknesses / risks reported for ${ticker}:\n${list}`,
        ["Overview"],
        intent,
      );
    }
    case "explain_committee": {
      if (isMissingText(primary.committeeDecision)) return unavailable(intent);
      const notes = joinBullets(primary.minorityNotes);
      return answer(
        [
          `Committee decision for ${ticker}: ${primary.committeeDecision}.`,
          `Confidence: ${formatPct(primary.committeeConfidence)}.`,
          `Consensus: ${primary.committeeConsensus || "Unavailable"}.`,
          notes ? `Notes:\n${notes}` : null,
        ]
          .filter(Boolean)
          .join("\n"),
        ["Investment Committee"],
        intent,
      );
    }
    case "compare_companies":
      return compareCompanyContexts(primary, secondary);
    case "unknown":
    default: {
      if (!isMissingText(primary.recommendation)) {
        return answer(
          [
            `I can explain fields already present for ${ticker}.`,
            `Current recommendation field: ${primary.recommendation}.`,
            "Try a suggested question for valuation, moat, management, strengths, weaknesses, or committee.",
          ].join("\n"),
          ["Recommendation", "Overview"],
          "unknown",
        );
      }
      return unavailable("unknown");
    }
  }
}
