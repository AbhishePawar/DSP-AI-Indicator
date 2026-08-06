/**
 * EPIC-F005 — Export helpers for mapped ResearchView only.
 * No recalculation — serializes display fields.
 */

import type { ResearchView } from "@/lib/research/mapResearchView";

export function researchViewToJson(view: ResearchView): string {
  return JSON.stringify(
    {
      exportedAt: new Date().toISOString(),
      source: "dsp_platform /analyse mapped ResearchView",
      note: "Display snapshot only — no client-side scoring.",
      ticker: view.ticker,
      company: view.company,
      exchange: view.exchange,
      analysedAt: view.analysedAt,
      correlationId: view.correlationId,
      platformVersion: view.platformVersion,
      pipelineVersion: view.pipelineVersion,
      valuation: view.valuation,
      recommendation: view.recommendation,
      committee: {
        decision: view.committeeDecision,
        consensus: view.committeeConsensus,
        confidence: view.committeeConfidence,
        finalRecommendation: view.committee.finalRecommendation,
        supportingReasons: view.committee.supportingReasons,
        opposingReasons: view.committee.opposingReasons,
      },
      quality: {
        moat: view.moat,
        management: view.management,
        financialStrength: view.financialStrength,
        earnings: view.earnings,
        businessQuality: view.businessQuality,
      },
      buffettIndicator: view.buffett,
      institutionalRatings: view.ratings,
      reportInformation: view.transparency,
      explainability: view.explainability,
      valuationTransparency: view.valuationTransparency,
      stages: view.stages,
      limitations: view.limitations,
      errors: view.errors,
      warnings: view.warnings,
    },
    null,
    2,
  );
}

function csvEscape(value: string): string {
  if (/[",\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

export function researchViewToCsv(view: ResearchView): string {
  const rows: string[][] = [
    ["field", "value"],
    ["ticker", view.ticker],
    ["company", view.company],
    ["exchange", view.exchange],
    ["analysedAt", view.analysedAt ?? "Data unavailable."],
    ["intrinsicValue", view.valuation.intrinsicValue],
    ["currentPrice", view.valuation.currentPrice],
    ["marginOfSafety", view.valuation.marginOfSafety],
    ["valuationMethod", view.valuation.method],
    ["valuationConfidence", view.valuation.confidence],
    ["recommendation", view.recommendation],
    ["committeeDecision", view.committeeDecision],
    ["committeeConsensus", view.committeeConsensus ?? "Data unavailable."],
    ["moat", view.moat.label],
    ["management", view.management.label],
    ["financialStrength", view.financialStrength.label],
    ["earningsQuality", view.earnings.label],
    ["businessQuality", view.businessQualityLabel],
    ["buffettOverallRating", view.buffett.overallRating],
    ["buffettAction", view.buffett.recommendation.action],
    ["overallInvestmentGrade", view.ratings.overall.grade],
    ["overallInvestmentScore", view.ratings.overall.scoreOutOf10],
    ["overallInvestmentAction", view.ratings.overall.recommendation],
    ["reportId", view.transparency.reportId],
    ["analysisDate", view.transparency.analysisDate],
    ["dataFreshness", view.transparency.dataInformation.dataFreshness],
    ["overallConfidence", view.transparency.confidence],
    ["explainabilityVersion", view.explainability.version],
    ["explainabilityModules", String(view.explainability.modules.length)],
    ["valuationTransparencyVersion", view.valuationTransparency.version],
    [
      "valuationTransparencyMethods",
      String(view.valuationTransparency.methods.length),
    ],
    [
      "valuationTransparencyVerdict",
      view.valuationTransparency.executive.valuationVerdict,
    ],
    ["correlationId", view.correlationId ?? "Data unavailable."],
    ["platformVersion", view.platformVersion ?? "Data unavailable."],
  ];
  return rows.map((r) => r.map(csvEscape).join(",")).join("\n");
}

export function downloadText(
  filename: string,
  content: string,
  mime: string,
): void {
  if (typeof window === "undefined") return;
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Downloads base64-encoded bytes from `POST /research/export` (docx/pptx/pdf/xlsx). */
export function downloadBase64(
  filename: string,
  base64: string,
  mime: string,
): void {
  if (typeof window === "undefined") return;
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  const blob = new Blob([bytes], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function researchViewToHtml(view: ResearchView): string {
  const matrixRows = view.buffett.decisionMatrix
    .map(
      (m) =>
        `<tr><td>${m.criterion}</td><td>${m.state}</td><td>${m.evidence}</td></tr>`,
    )
    .join("");
  const scoreRows = view.buffett.scorecard
    .map((r) => `<tr><td>${r.dimension}</td><td>${r.grade}</td></tr>`)
    .join("");
  const instRows = view.ratings.scorecard
    .map(
      (r) =>
        `<tr><td>${r.module}</td><td>${r.scoreOutOf10}</td><td>${r.grade}</td><td>${r.confidence}</td></tr>`,
    )
    .join("");
  return `<!doctype html><html><head><meta charset="utf-8"/><title>${view.ticker} Research</title>
<style>body{font-family:system-ui,sans-serif;padding:24px;color:#111}h1{font-size:1.5rem}h2{font-size:1.2rem;margin-top:2rem}table{border-collapse:collapse;width:100%;margin:12px 0}td,th{border:1px solid #ccc;padding:6px;text-align:left}.note{color:#555;font-size:0.9rem}</style>
</head><body>
<h1>${view.company} (${view.ticker})</h1>
<p>Exchange: ${view.exchange} · Analysed: ${view.analysedAt ?? "Data unavailable."}</p>
<p class="note">Display snapshot from /api/v1/analyse — no client scoring.</p>
<h2>Report Information</h2>
<p class="note">${view.transparency.disclaimer}</p>
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td>Analysis Date</td><td>${view.transparency.analysisDate}</td></tr>
<tr><td>Report ID</td><td>${view.transparency.reportId}</td></tr>
<tr><td>Frontend</td><td>${view.transparency.analysisVersions.frontend}</td></tr>
<tr><td>Backend</td><td>${view.transparency.analysisVersions.backend}</td></tr>
<tr><td>Buffett Framework</td><td>${view.transparency.analysisVersions.buffettFramework}</td></tr>
<tr><td>Institutional Rating Framework</td><td>${view.transparency.analysisVersions.institutionalRatingFramework}</td></tr>
<tr><td>Pipeline</td><td>${view.transparency.transparency.pipelineVersion}</td></tr>
<tr><td>Recommendation Engine</td><td>${view.transparency.transparency.recommendationEngineVersion}</td></tr>
<tr><td>Data Freshness</td><td>${view.transparency.dataInformation.dataFreshness}</td></tr>
<tr><td>Confidence</td><td>${view.transparency.confidence}</td></tr>
</table>
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td>Intrinsic Value</td><td>${view.valuation.intrinsicValue}</td></tr>
<tr><td>Current Price</td><td>${view.valuation.currentPrice}</td></tr>
<tr><td>Margin of Safety</td><td>${view.valuation.marginOfSafety}</td></tr>
<tr><td>Recommendation</td><td>${view.recommendation}</td></tr>
<tr><td>Committee</td><td>${view.committeeDecision}</td></tr>
<tr><td>Moat</td><td>${view.moat.label}</td></tr>
</table>
<h2>Institutional Ratings</h2>
<p class="note">${view.ratings.disclaimer}</p>
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td>Overall Grade</td><td>${view.ratings.overall.grade}</td></tr>
<tr><td>Overall Score</td><td>${view.ratings.overall.scoreOutOf10}</td></tr>
<tr><td>Stars</td><td>${view.ratings.overall.stars}/5</td></tr>
<tr><td>Recommendation</td><td>${view.ratings.overall.recommendation}</td></tr>
<tr><td>Business Quality</td><td>${view.ratings.overall.businessQuality}</td></tr>
</table>
<h3>Investment Scorecard</h3>
<table><tr><th>Module</th><th>Score</th><th>Grade</th><th>Confidence</th></tr>${instRows}</table>
<p>${view.ratings.overall.explanation}</p>
<h2>Valuation Transparency</h2>
<p class="note">${view.valuationTransparency.disclaimer}</p>
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td>Overall Score</td><td>${view.valuationTransparency.executive.overallScoreOutOf10}</td></tr>
<tr><td>Grade</td><td>${view.valuationTransparency.executive.grade}</td></tr>
<tr><td>Confidence</td><td>${view.valuationTransparency.executive.confidence}</td></tr>
<tr><td>Current Market Price</td><td>${view.valuationTransparency.executive.currentMarketPrice}</td></tr>
<tr><td>Intrinsic Value</td><td>${view.valuationTransparency.executive.intrinsicValue}</td></tr>
<tr><td>Margin of Safety</td><td>${view.valuationTransparency.executive.marginOfSafety}</td></tr>
<tr><td>Valuation Verdict</td><td>${view.valuationTransparency.executive.valuationVerdict}</td></tr>
<tr><td>Consensus Value</td><td>${view.valuationTransparency.consensus.consensusValue}</td></tr>
<tr><td>Valuation Category</td><td>${view.valuationTransparency.marginOfSafety.valuationCategory}</td></tr>
</table>
<h3>Methods</h3>
<table><tr><th>Method</th><th>Status</th><th>Intrinsic Value</th><th>Confidence</th></tr>${view.valuationTransparency.methods
  .map(
    (m) =>
      `<tr><td>${m.methodName}</td><td>${m.status}</td><td>${m.intrinsicValue}</td><td>${m.confidence}</td></tr>`,
  )
  .join("")}</table>
<h2>Explainability Framework</h2>
<p class="note">Presentation-only expansion of institutional module ratings. No recalculation.</p>
${view.explainability.modules
  .map((m) => {
    const evidenceRows = m.evidence
      .map(
        (e) =>
          `<tr><td>${e.label}</td><td>${e.value}</td><td>${e.sourceField}</td></tr>`,
      )
      .join("");
    return `<h3>${m.title} (${m.scoreOutOf10} · ${m.grade} · ${m.confidence})</h3>
<p><strong>Summary:</strong> ${m.oneLineSummary}</p>
<p><strong>Explanation:</strong> ${m.explanation}</p>
<p><strong>Strengths:</strong> ${m.strengths.join("; ") || "Unavailable"}</p>
<p><strong>Weaknesses:</strong> ${m.weaknesses.join("; ") || "Unavailable"}</p>
<table><tr><th>Evidence</th><th>Value</th><th>Source field</th></tr>${evidenceRows || "<tr><td colspan=3>Unavailable</td></tr>"}</table>`;
  })
  .join("")}
<h2>Buffett Indicator Analysis</h2>
<p class="note">${view.buffett.disclaimer}</p>
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td>Overall Buffett Rating</td><td>${view.buffett.overallRating}</td></tr>
<tr><td>Buffett Action</td><td>${view.buffett.recommendation.action}</td></tr>
<tr><td>Confidence</td><td>${view.buffett.confidence}</td></tr>
</table>
<h3>Decision Matrix</h3>
<table><tr><th>Criterion</th><th>State</th><th>Evidence</th></tr>${matrixRows}</table>
<h3>Scorecard</h3>
<table><tr><th>Dimension</th><th>Grade</th></tr>${scoreRows}</table>
<h3>Verdict</h3>
<p>${view.buffett.verdict}</p>
</body></html>`;
}
