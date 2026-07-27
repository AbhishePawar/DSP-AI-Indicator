/** Portfolio report builders — reuses Sprint 7 export download helpers. */

import {
  downloadText,
  reportToHtml,
  reportToJson,
  reportToMarkdown,
  type BuiltReport,
  type ExportFormatId,
  type ReportBlock,
} from "@/lib/analysis/sprint7Reports";
import type { PortfolioWorkspaceView } from "@/lib/portfolio/portfolioWorkspace";

export type PortfolioReportKind =
  | "portfolio_report"
  | "allocation_report"
  | "risk_report"
  | "watchlist_report";

function citations(view: PortfolioWorkspaceView): ReportBlock["citation"] {
  return {
    evidenceReference: "Session portfolio model · Sprint 8 presentation aggregations",
    confidence: "Moderate to Insufficient Evidence (field-dependent)",
    methodology: view.version,
    timestamp: view.asOf,
  };
}

function trustLine(m: { label: string; value: string | null; confidence: string; evidence: string; methodology: string; timestamp: string | null }) {
  return `${m.label}: ${m.value ?? "Unavailable"} · confidence ${m.confidence} · ${m.evidence}`;
}

export function buildPortfolioReport(
  view: PortfolioWorkspaceView,
  kind: PortfolioReportKind,
): BuiltReport {
  const citation = citations(view);
  const blocks: ReportBlock[] = [
    {
      id: "cover",
      heading: "Cover",
      paragraphs: [
        `DSP Portfolio Intelligence — ${kind.replace(/_/g, " ")}`,
        `Currency ${view.currency} · As of ${view.asOf ?? "Unavailable"}`,
      ],
      citation,
    },
  ];

  if (kind === "portfolio_report" || kind === "allocation_report") {
    blocks.push({
      id: "overview",
      heading: "Portfolio Overview",
      paragraphs: [
        trustLine({ ...view.overview.portfolioValue, confidence: view.overview.portfolioValue.confidence }),
        trustLine({ ...view.overview.cashPercent, confidence: view.overview.cashPercent.confidence }),
        trustLine({ ...view.overview.averageMos, confidence: view.overview.averageMos.confidence }),
        trustLine({ ...view.overview.expectedCagr, confidence: view.overview.expectedCagr.confidence }),
      ],
      bullets: view.holdings.map(
        (h) =>
          `${h.symbol}: weight ${h.weight?.toFixed(1) ?? "Unavailable"}% · MOS ${h.marginOfSafety?.toFixed(1) ?? "Unavailable"}% · confidence ${h.confidence}`,
      ),
      citation,
    });
  }

  if (kind === "allocation_report" || kind === "portfolio_report") {
    blocks.push({
      id: "allocations",
      heading: "Allocations",
      paragraphs: ["Sector and theme weights from session market values."],
      bullets: view.allocations.sector.map(
        (s) => `${s.label}: ${s.weight.toFixed(1)}%`,
      ),
      citation,
    });
  }

  if (kind === "risk_report" || kind === "portfolio_report") {
    blocks.push({
      id: "risk",
      heading: "Risk Summary",
      paragraphs: [
        trustLine({ ...view.risk.largestPosition, confidence: view.risk.largestPosition.confidence }),
        trustLine({ ...view.risk.largestSector, confidence: view.risk.largestSector.confidence }),
        trustLine({
          ...view.overview.portfolioRiskScore,
          confidence: view.overview.portfolioRiskScore.confidence,
        }),
      ],
      bullets: [
        ...view.risk.topRisks,
        `Overvalued: ${view.risk.overvaluedHoldings.join(", ") || "None listed"}`,
        `Undervalued: ${view.risk.undervaluedHoldings.join(", ") || "None listed"}`,
        `Low confidence: ${view.risk.lowConfidenceHoldings.join(", ") || "None listed"}`,
      ],
      citation,
    });
  }

  if (kind === "watchlist_report" || kind === "portfolio_report") {
    blocks.push({
      id: "watchlist",
      heading: "Watchlist",
      paragraphs: ["Watchlist is session presentation — alerts deferred."],
      bullets: view.watchlist.map(
        (w) =>
          `${w.symbol}: target ${w.targetBuyPrice ?? "Unavailable"} · reason: ${w.reasonToWatch}`,
      ),
      citation,
    });
  }

  blocks.push(
    {
      id: "limitations",
      heading: "Limitations",
      paragraphs: [
        "Not broker-synced. No automatic trading. Missing research fields remain Unavailable.",
      ],
      bullets: view.notes,
      citation,
    },
    {
      id: "methodology",
      heading: "Methodology",
      paragraphs: [
        view.version,
        "Aggregations weight available holding fields only. Decision Engine / valuation math unchanged.",
      ],
      citation,
    },
    {
      id: "disclosures",
      heading: "Disclosures",
      paragraphs: view.disclosures,
      citation,
    },
  );

  return {
    templateId: "full_research",
    title: `DSP ${kind.replace(/_/g, " ")}`,
    companyLabel: "Portfolio",
    generatedAt: new Date().toISOString(),
    blocks,
    disclosures: view.disclosures,
    metadata: {
      analysisVersion: "web-0.7.0 / L1.2 Sprint 8",
      methodologyVersion: view.version,
      researchMode: "Research Mode (active)",
      dataCurrency: view.asOf
        ? `Session portfolio as of ${view.asOf}`
        : "No portfolio session date",
      analysisDate: view.asOf,
      coveragePercent: view.holdings.length
        ? Math.round(
            (view.holdings.filter((h) => h.intrinsicValue != null).length /
              view.holdings.length) *
              100,
          )
        : 0,
    },
  };
}

export function exportPortfolioReport(
  view: PortfolioWorkspaceView,
  kind: PortfolioReportKind,
  format: ExportFormatId,
) {
  const report = buildPortfolioReport(view, kind);
  if (format === "pdf" || format === "docx") {
    return { ok: false as const, reason: "PDF/DOCX await backend export services" };
  }
  if (format === "markdown") {
    downloadText(`${kind}.md`, reportToMarkdown(report), "text/markdown");
  } else if (format === "html") {
    downloadText(`${kind}.html`, reportToHtml(report), "text/html");
  } else if (format === "json") {
    downloadText(`${kind}.json`, reportToJson(report), "application/json");
  } else if (format === "csv") {
    const rows = [
      "symbol,weight,mos,confidence,sector",
      ...view.holdings.map(
        (h) =>
          `${h.symbol},${h.weight ?? ""},${h.marginOfSafety ?? ""},${h.confidence},${h.sector}`,
      ),
    ];
    downloadText(`${kind}-metrics.csv`, rows.join("\n"), "text/csv");
  }
  return { ok: true as const };
}

export { downloadText };
