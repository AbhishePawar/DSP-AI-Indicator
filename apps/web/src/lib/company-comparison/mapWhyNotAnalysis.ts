/**
 * Why Not Analysis — evidence-backed reasons why each company is not preferred.
 * Never emits generic placeholders when evidence exists; never fabricates.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import { DATA_UNAVAILABLE } from "./constants";
import type { WhyNotAnalysis, WinnerMatrixRow } from "./types";

export function mapWhyNotAnalysis(
  views: ResearchView[],
  winnerMatrix: WinnerMatrixRow[],
): WhyNotAnalysis[] {
  if (views.length < 2) return [];

  return views.map((view) => {
    const reasons: WhyNotAnalysis["reasons"] = [];

    for (const row of winnerMatrix) {
      if (row.leader === DATA_UNAVAILABLE) continue;
      const cell = row.cells.find((c) => c.symbol === view.ticker);
      if (!cell || cell.numeric == null) continue;
      if (row.leader === view.ticker && cell.medal === "gold") continue;

      const leaderCell = row.cells.find((c) => c.symbol === row.leader);
      if (!leaderCell || leaderCell.numeric == null) continue;
      if (cell.numeric >= leaderCell.numeric) continue;

      reasons.push({
        dimension: row.label,
        reason: `${view.ticker} trails ${row.leader} on ${row.label} using existing research scores (${cell.display} vs ${leaderCell.display}).`,
        evidence: cell.evidence || leaderCell.evidence || DATA_UNAVAILABLE,
      });
    }

    // Committee / recommendation opposing signals specific to this company.
    for (const opp of view.committee.opposingReasons.slice(0, 4)) {
      reasons.push({
        dimension: "Committee opposing",
        reason: `${view.ticker} carries opposing committee evidence: ${opp}`,
        evidence: `committee.opposingReasons / analyse weaknesses-risks`,
      });
    }

    for (const w of view.weaknesses.slice(0, 3)) {
      if (reasons.some((r) => r.reason.includes(w))) continue;
      reasons.push({
        dimension: "Weakness",
        reason: `${view.ticker} research pack lists weakness: ${w}`,
        evidence: "IntelligenceView.weaknesses from stage statuses",
      });
    }

    // MoS gap when peers have higher MoS.
    const mosSelf = view.valuation.marginOfSafety;
    const peerMos = views
      .filter((v) => v.ticker !== view.ticker)
      .map((v) => ({
        ticker: v.ticker,
        mos: v.valuation.marginOfSafety,
      }))
      .filter((p) => p.mos !== DATA_UNAVAILABLE && p.mos !== "Unavailable");

    if (mosSelf !== DATA_UNAVAILABLE && mosSelf !== "Unavailable") {
      for (const p of peerMos) {
        const selfN = Number(String(mosSelf).replace("%", ""));
        const peerN = Number(String(p.mos).replace("%", ""));
        if (
          Number.isFinite(selfN) &&
          Number.isFinite(peerN) &&
          peerN > selfN + 0.5
        ) {
          reasons.push({
            dimension: "Margin of Safety",
            reason: `${view.ticker} shows a lower Margin of Safety (${mosSelf}) than ${p.ticker} (${p.mos}) on existing valuation outputs.`,
            evidence: "valuation.marginOfSafety from /analyse",
          });
        }
      }
    }

    if (reasons.length === 0) {
      reasons.push({
        dimension: "Coverage",
        reason: `No evidence-backed “why not” differentials found for ${view.ticker} against peers on available Winner Matrix / opposing fields. This is not a preference endorsement.`,
        evidence: DATA_UNAVAILABLE,
      });
    }

    return {
      symbol: view.ticker,
      reasons: reasons.slice(0, 12),
      note: "Why-not reasons are evidence-backed differentials only. The platform never produces the investment decision.",
    };
  });
}
