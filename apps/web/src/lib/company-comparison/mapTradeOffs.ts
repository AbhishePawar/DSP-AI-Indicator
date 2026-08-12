/**
 * Trade-off Analysis — WHY differences, from existing research outputs only.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import { DATA_UNAVAILABLE } from "./constants";
import { isUnavailableDisplay, parseExistingScore } from "./ranking";
import type { TradeOffItem, WinnerMatrixRow } from "./types";

function pairTradeOff(
  dimension: string,
  a: ResearchView,
  b: ResearchView,
  scoreA: number | null,
  scoreB: number | null,
  labelA: string,
  labelB: string,
  evidence: string[],
): TradeOffItem | null {
  if (scoreA == null && scoreB == null) return null;
  if (scoreA == null || scoreB == null) {
    return {
      dimension,
      summary: `${dimension}: one peer lacks a server-provided score — comparison incomplete.`,
      stronger: scoreA != null ? a.ticker : DATA_UNAVAILABLE,
      weaker: scoreB != null ? b.ticker : DATA_UNAVAILABLE,
      evidence,
    };
  }
  if (scoreA === scoreB) {
    return {
      dimension,
      summary: `${dimension}: ${a.ticker} and ${b.ticker} present equivalent server scores (${labelA} vs ${labelB}).`,
      stronger: DATA_UNAVAILABLE,
      weaker: DATA_UNAVAILABLE,
      evidence,
    };
  }
  const aStronger = scoreA > scoreB;
  return {
    dimension,
    summary: aStronger
      ? `${dimension}: ${a.ticker} leads on existing research score (${labelA}) versus ${b.ticker} (${labelB}).`
      : `${dimension}: ${b.ticker} leads on existing research score (${labelB}) versus ${a.ticker} (${labelA}).`,
    stronger: aStronger ? a.ticker : b.ticker,
    weaker: aStronger ? b.ticker : a.ticker,
    evidence,
  };
}

/**
 * Build trade-offs from Winner Matrix leaders + stage labels/strengths/weaknesses.
 * Only emits conclusions grounded in existing outputs.
 */
export function mapTradeOffs(
  views: ResearchView[],
  winnerMatrix: WinnerMatrixRow[],
): TradeOffItem[] {
  if (views.length < 2) return [];

  const items: TradeOffItem[] = [];

  for (const row of winnerMatrix) {
    if (row.leader === DATA_UNAVAILABLE) continue;
    const withScores = row.cells.filter((c) => c.numeric != null);
    if (withScores.length < 2) continue;

    const sorted = [...withScores].sort(
      (a, b) => (b.numeric ?? 0) - (a.numeric ?? 0),
    );
    const top = sorted[0]!;
    const bottom = sorted[sorted.length - 1]!;
    if (top.symbol === bottom.symbol) continue;

    const topView = views.find((v) => v.ticker === top.symbol);
    const bottomView = views.find((v) => v.ticker === bottom.symbol);
    if (!topView || !bottomView) continue;

    items.push({
      dimension: row.label,
      summary: `${row.label}: ${top.symbol} ranks ahead of ${bottom.symbol} on server-provided scores (${top.display} vs ${bottom.display}).`,
      stronger: top.symbol,
      weaker: bottom.symbol,
      evidence: [
        top.evidence,
        bottom.evidence,
        ...topView.strengths.slice(0, 2),
        ...bottomView.weaknesses.slice(0, 2),
      ].filter((e) => !isUnavailableDisplay(e)),
    });
  }

  // Pairwise valuation MoS trade-off when both have numeric MoS
  if (views.length >= 2) {
    const a = views[0]!;
    const b = views[1]!;
    const mosA = parseExistingScore(
      a.valuation.marginOfSafety.replace("%", ""),
    );
    const mosB = parseExistingScore(
      b.valuation.marginOfSafety.replace("%", ""),
    );
    const mosItem = pairTradeOff(
      "Margin of Safety",
      a,
      b,
      mosA,
      mosB,
      a.valuation.marginOfSafety,
      b.valuation.marginOfSafety,
      [
        `${a.ticker} MoS=${a.valuation.marginOfSafety}`,
        `${b.ticker} MoS=${b.valuation.marginOfSafety}`,
      ],
    );
    if (mosItem) items.push(mosItem);
  }

  // Committee rationale differences
  for (let i = 0; i < views.length; i += 1) {
    for (let j = i + 1; j < views.length; j += 1) {
      const a = views[i]!;
      const b = views[j]!;
      if (
        !isUnavailableDisplay(a.committeeDecision) &&
        !isUnavailableDisplay(b.committeeDecision) &&
        a.committeeDecision.toLowerCase() !== b.committeeDecision.toLowerCase()
      ) {
        items.push({
          dimension: "AI Committee",
          summary: `Committee decisions diverge: ${a.ticker}=${a.committeeDecision}; ${b.ticker}=${b.committeeDecision}.`,
          stronger: DATA_UNAVAILABLE,
          weaker: DATA_UNAVAILABLE,
          evidence: [
            a.committeeConsensus ?? DATA_UNAVAILABLE,
            b.committeeConsensus ?? DATA_UNAVAILABLE,
            ...a.committee.supportingReasons.slice(0, 1),
            ...b.committee.opposingReasons.slice(0, 1),
          ].map((e) => (isUnavailableDisplay(e) ? DATA_UNAVAILABLE : e)),
        });
      }
    }
  }

  return items.slice(0, 24);
}
