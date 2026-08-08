/**
 * Investment Committee Memo Generator — presentation assembly only.
 * Platform NEVER produces the investment decision.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";
import {
  BUFFETT_DISCLAIMER,
  BUFFETT_FRAMEWORK_PREFIX,
  DATA_UNAVAILABLE,
  WORKSPACE_DISCLAIMER,
} from "./constants";
import type {
  CommitteeMemo,
  ContradictoryEvidenceCell,
  TradeOffItem,
  WinnerMatrixRow,
} from "./types";

export function mapCommitteeMemo(
  views: ResearchView[],
  winnerMatrix: WinnerMatrixRow[],
  tradeOffs: TradeOffItem[],
  contradictory: ContradictoryEvidenceCell[],
  personalNotes: { kind: string; text: string }[] = [],
  outstandingQuestions: string[] = [],
): CommitteeMemo {
  const companies = views.map((v) => v.ticker);
  const leaders = winnerMatrix
    .filter((r) => r.leader !== DATA_UNAVAILABLE)
    .map((r) => `${r.label}: ${r.leader}`);

  const confidences = views
    .map((v) => v.recommendationConfidence)
    .filter((c): c is number => c != null);
  const confidence =
    confidences.length === 0
      ? DATA_UNAVAILABLE
      : `${Math.round(
          (confidences.reduce((a, b) => a + b, 0) / confidences.length) * 100,
        )}% mean recommendation confidence across packs with values`;

  const supportingEvidence = contradictory.flatMap((c) =>
    c.supporting
      .filter((s) => !s.startsWith("Data unavailable."))
      .map((s) => `${c.symbol}: ${s}`),
  );
  const contradictoryEvidence = contradictory.flatMap((c) =>
    c.contradictory
      .filter((s) => !s.startsWith("Data unavailable."))
      .map((s) => `${c.symbol}: ${s}`),
  );

  const buffettBits = views.map((v) => {
    const rating = v.buffett.overallRating;
    return `${v.ticker}: ${rating === "Unavailable" || !rating ? DATA_UNAVAILABLE : rating}`;
  });

  const questions = [
    ...outstandingQuestions,
    ...personalNotes
      .filter((n) => n.kind === "question")
      .map((n) => n.text),
  ];

  const decisionNotes = personalNotes
    .filter((n) => n.kind === "decision" || n.kind === "thesis")
    .map((n) => `[${n.kind}] ${n.text}`);

  return {
    title: `Executive Committee Memo — ${companies.join(" vs ") || "Comparison"}`,
    companies,
    executiveSummary:
      companies.length >= 2
        ? `Institutional comparison of ${companies.join(", ")} assembled from existing /api/v1/analyse research packs. This memo assists Investment Committee review and never makes the investment decision.`
        : DATA_UNAVAILABLE,
    winnerMatrixSummary:
      leaders.length > 0
        ? leaders.join("; ")
        : DATA_UNAVAILABLE,
    tradeOffs:
      tradeOffs.length > 0
        ? tradeOffs.map((t) => `${t.dimension}: ${t.summary}`)
        : [DATA_UNAVAILABLE],
    supportingEvidence:
      supportingEvidence.length > 0
        ? supportingEvidence.slice(0, 20)
        : [DATA_UNAVAILABLE],
    contradictoryEvidence:
      contradictoryEvidence.length > 0
        ? contradictoryEvidence.slice(0, 20)
        : [DATA_UNAVAILABLE],
    buffettSummary: `${BUFFETT_FRAMEWORK_PREFIX}, preference alignment across the set is: ${buffettBits.join("; ")}. ${BUFFETT_DISCLAIMER}`,
    confidence,
    outstandingQuestions:
      questions.length > 0
        ? questions
        : [
            "What differs most across evidence-backed dimensions?",
            "Which contradictory evidence remains unresolved?",
            "Does research confidence / evidence strength support a decision now?",
          ],
    decisionNotes:
      decisionNotes.length > 0
        ? decisionNotes
        : [
            "Decision notes are user-authored. The platform never produces the investment decision.",
          ],
    disclaimer: WORKSPACE_DISCLAIMER,
    generatedAt: new Date().toISOString(),
    exportNote:
      "Export via Print/PDF, HTML, or JSON. Native DOCX generation is not available in current export patterns.",
  };
}

export function committeeMemoToHtml(memo: CommitteeMemo): string {
  const list = (items: string[]) =>
    items.map((i) => `<li>${escapeHtml(i)}</li>`).join("");

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>${escapeHtml(memo.title)}</title>
<style>
  body { font-family: Georgia, "Times New Roman", serif; margin: 2rem; color: #111; line-height: 1.45; }
  h1,h2 { font-family: "Segoe UI", system-ui, sans-serif; }
  .disclaimer { font-size: 0.85rem; color: #444; max-width: 48rem; }
  @media print { body { margin: 1rem; } }
</style>
</head>
<body>
<h1>${escapeHtml(memo.title)}</h1>
<p class="disclaimer">${escapeHtml(memo.disclaimer)}</p>
<p><strong>Companies:</strong> ${escapeHtml(memo.companies.join(", "))}</p>
<h2>Executive Summary</h2>
<p>${escapeHtml(memo.executiveSummary)}</p>
<h2>Winner Matrix</h2>
<p>${escapeHtml(memo.winnerMatrixSummary)}</p>
<h2>Trade-offs</h2>
<ul>${list(memo.tradeOffs)}</ul>
<h2>Supporting Evidence</h2>
<ul>${list(memo.supportingEvidence)}</ul>
<h2>Contradictory Evidence</h2>
<ul>${list(memo.contradictoryEvidence)}</ul>
<h2>Buffett-style Framework Summary</h2>
<p>${escapeHtml(memo.buffettSummary)}</p>
<h2>Confidence</h2>
<p>${escapeHtml(memo.confidence)}</p>
<h2>Outstanding Questions</h2>
<ul>${list(memo.outstandingQuestions)}</ul>
<h2>Decision Notes (user-authored)</h2>
<ul>${list(memo.decisionNotes)}</ul>
<p class="disclaimer">${escapeHtml(memo.exportNote)}</p>
<p><em>Generated ${escapeHtml(memo.generatedAt)}. Print this page for PDF. The platform never produces the investment decision.</em></p>
</body>
</html>`;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
