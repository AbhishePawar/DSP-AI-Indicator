/** Sprint 7 — Reports & Export Center (presentation only — no backend generation). */

import type { AnalysisWorkspaceView } from "@/lib/analysis/types";
import { CONFIDENCE_LABELS } from "@/lib/trust/labels";
import { presentFieldLabel } from "@/lib/terminology";
import { RESEARCH_DISCLAIMER } from "@/lib/product";

export type ReportTemplateId =
  | "executive_summary"
  | "full_research"
  | "business_quality"
  | "financial_strength"
  | "valuation"
  | "risk"
  | "management"
  | "competitive_advantage"
  | "decision_trace"
  | "evidence"
  | "knowledge_graph_snapshot";

export type ReportSectionId =
  | "cover"
  | "company_overview"
  | "executive_summary"
  | "research_conclusion"
  | "business_analysis"
  | "financial_analysis"
  | "growth"
  | "risk"
  | "management"
  | "competitive_advantage"
  | "market_intelligence"
  | "decision_trace"
  | "evidence_summary"
  | "confidence_summary"
  | "research_limitations"
  | "methodology"
  | "disclosures"
  | "assumptions"
  | "knowledge_graph";

export type ExportFormatId = "pdf" | "docx" | "markdown" | "html" | "json" | "csv";

export type DateFormatId = "iso" | "locale_long" | "locale_short";

export type ReportCustomization = {
  title: string;
  dateFormat: DateFormatId;
  includedSections: ReportSectionId[];
  showEvidence: boolean;
  showAssumptions: boolean;
  includeMethodology: boolean;
  includeConfidence: boolean;
};

export type ReportCitation = {
  evidenceReference: string;
  confidence: string;
  methodology: string;
  timestamp: string | null;
};

export type ReportBlock = {
  id: string;
  heading: string;
  paragraphs: string[];
  bullets?: string[];
  citation?: ReportCitation;
};

export type BuiltReport = {
  templateId: ReportTemplateId;
  title: string;
  companyLabel: string;
  generatedAt: string;
  blocks: ReportBlock[];
  disclosures: string[];
  metadata: {
    analysisVersion: string;
    methodologyVersion: string;
    researchMode: string;
    dataCurrency: string;
    analysisDate: string | null;
    coveragePercent: number;
  };
};

export type ReportTemplateDef = {
  id: ReportTemplateId;
  title: string;
  description: string;
  defaultSections: ReportSectionId[];
};

/** Trust-required sections — never omitted from exports. */
export const MANDATORY_SECTIONS: ReportSectionId[] = [
  "research_limitations",
  "confidence_summary",
  "methodology",
  "evidence_summary",
  "disclosures",
];

export const REPORT_SECTION_LABELS: Record<ReportSectionId, string> = {
  cover: "Cover Page",
  company_overview: "Company Overview",
  executive_summary: "Executive Summary",
  research_conclusion: "Research Conclusion",
  business_analysis: "Business Analysis",
  financial_analysis: "Financial Analysis",
  growth: "Growth",
  risk: "Risk",
  management: "Management",
  competitive_advantage: "Competitive Advantage",
  market_intelligence: "Market Intelligence",
  decision_trace: "Decision Trace",
  evidence_summary: "Evidence Summary",
  confidence_summary: "Confidence Summary",
  research_limitations: "Research Limitations",
  methodology: "Methodology",
  disclosures: "Disclosures",
  assumptions: "Assumptions",
  knowledge_graph: "Knowledge Graph Snapshot",
};

export const REPORT_TEMPLATES: ReportTemplateDef[] = [
  {
    id: "executive_summary",
    title: "Executive Summary",
    description: "Cover, overview, conclusion, confidence, limitations, disclosures",
    defaultSections: [
      "cover",
      "company_overview",
      "executive_summary",
      "research_conclusion",
      "confidence_summary",
      "evidence_summary",
      "research_limitations",
      "methodology",
      "disclosures",
    ],
  },
  {
    id: "full_research",
    title: "Full Research Report",
    description: "Complete DSP research pack with all major sections",
    defaultSections: [
      "cover",
      "company_overview",
      "executive_summary",
      "research_conclusion",
      "business_analysis",
      "financial_analysis",
      "growth",
      "risk",
      "management",
      "competitive_advantage",
      "market_intelligence",
      "decision_trace",
      "evidence_summary",
      "assumptions",
      "confidence_summary",
      "research_limitations",
      "methodology",
      "knowledge_graph",
      "disclosures",
    ],
  },
  {
    id: "business_quality",
    title: "Business Quality Report",
    description: "Business quality metrics with evidence and confidence",
    defaultSections: [
      "cover",
      "company_overview",
      "business_analysis",
      "evidence_summary",
      "confidence_summary",
      "research_limitations",
      "methodology",
      "disclosures",
    ],
  },
  {
    id: "financial_strength",
    title: "Financial Strength Report",
    description: "Financial strength metrics and limitations",
    defaultSections: [
      "cover",
      "company_overview",
      "financial_analysis",
      "evidence_summary",
      "confidence_summary",
      "research_limitations",
      "methodology",
      "disclosures",
    ],
  },
  {
    id: "valuation",
    title: "Valuation Report",
    description: `Valuation presentation — ${presentFieldLabel("target_price")} when available`,
    defaultSections: [
      "cover",
      "company_overview",
      "research_conclusion",
      "financial_analysis",
      "evidence_summary",
      "confidence_summary",
      "research_limitations",
      "methodology",
      "disclosures",
    ],
  },
  {
    id: "risk",
    title: "Risk Report",
    description: "Risk taxonomy, watchpoints, and limitations",
    defaultSections: [
      "cover",
      "company_overview",
      "risk",
      "evidence_summary",
      "confidence_summary",
      "research_limitations",
      "methodology",
      "disclosures",
    ],
  },
  {
    id: "management",
    title: "Management Report",
    description: "Management quality insights",
    defaultSections: [
      "cover",
      "company_overview",
      "management",
      "evidence_summary",
      "confidence_summary",
      "research_limitations",
      "methodology",
      "disclosures",
    ],
  },
  {
    id: "competitive_advantage",
    title: "Competitive Advantage Report",
    description: "Moat / competitive advantage snapshot",
    defaultSections: [
      "cover",
      "company_overview",
      "competitive_advantage",
      "evidence_summary",
      "confidence_summary",
      "research_limitations",
      "methodology",
      "disclosures",
    ],
  },
  {
    id: "decision_trace",
    title: "Decision Trace Report",
    description: "How DSP reached the research conclusion",
    defaultSections: [
      "cover",
      "company_overview",
      "research_conclusion",
      "decision_trace",
      "evidence_summary",
      "assumptions",
      "confidence_summary",
      "research_limitations",
      "methodology",
      "disclosures",
    ],
  },
  {
    id: "evidence",
    title: "Evidence Report",
    description: "Grouped evidence explorer export",
    defaultSections: [
      "cover",
      "company_overview",
      "evidence_summary",
      "assumptions",
      "confidence_summary",
      "research_limitations",
      "methodology",
      "disclosures",
    ],
  },
  {
    id: "knowledge_graph_snapshot",
    title: "Knowledge Graph Snapshot",
    description: "Graph node/edge overview with trust disclosures",
    defaultSections: [
      "cover",
      "company_overview",
      "knowledge_graph",
      "evidence_summary",
      "confidence_summary",
      "research_limitations",
      "methodology",
      "disclosures",
    ],
  },
];

export const EXPORT_FORMATS: {
  id: ExportFormatId;
  label: string;
  description: string;
  ready: boolean;
}[] = [
  { id: "pdf", label: "PDF", description: "Printable research pack", ready: false },
  { id: "docx", label: "DOCX", description: "Editable Word document", ready: false },
  { id: "markdown", label: "Markdown", description: "Preview-ready text export", ready: true },
  { id: "html", label: "HTML", description: "Browser-readable report", ready: true },
  { id: "json", label: "JSON", description: "Structured report payload", ready: true },
  { id: "csv", label: "CSV", description: "Metrics only", ready: true },
];

function companyLabel(view: AnalysisWorkspaceView): string {
  return (
    view.snapshot.companyName.value ??
    view.snapshot.ticker.value ??
    "Company"
  );
}

function formatDate(iso: string | null, format: DateFormatId): string {
  if (!iso) return "Unavailable";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  if (format === "iso") return d.toISOString().slice(0, 10);
  if (format === "locale_short") return d.toLocaleDateString();
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function citation(
  view: AnalysisWorkspaceView,
  evidenceRef: string,
): ReportCitation {
  return {
    evidenceReference: evidenceRef,
    confidence: CONFIDENCE_LABELS[view.confidenceBreakdown.overall],
    methodology: view.methodologyPanel.presentationVersion,
    timestamp:
      view.freshness.lastUpdated ??
      view.snapshot.lastUpdated.value ??
      view.conclusion.evidence.lastUpdated,
  };
}

function ensureMandatory(sections: ReportSectionId[]): ReportSectionId[] {
  const set = new Set(sections);
  for (const m of MANDATORY_SECTIONS) set.add(m);
  return Array.from(set);
}

export function defaultCustomization(
  view: AnalysisWorkspaceView,
  template: ReportTemplateDef,
): ReportCustomization {
  const name = companyLabel(view);
  return {
    title: `${template.title} — ${name}`,
    dateFormat: "locale_long",
    includedSections: ensureMandatory([...template.defaultSections]),
    showEvidence: true,
    showAssumptions: template.defaultSections.includes("assumptions"),
    includeMethodology: true,
    includeConfidence: true,
  };
}

export function buildReport(
  view: AnalysisWorkspaceView,
  templateId: ReportTemplateId,
  custom: ReportCustomization,
): BuiltReport {
  const template =
    REPORT_TEMPLATES.find((t) => t.id === templateId) ?? REPORT_TEMPLATES[1];
  const name = companyLabel(view);
  const sections = ensureMandatory(
    custom.includedSections.filter((s) => {
      // Assumptions may be hidden; trust-required sections cannot.
      if (s === "assumptions" && !custom.showAssumptions) return false;
      return true;
    }),
  );
  const finalSections = ensureMandatory(sections);

  // Optional: when showEvidence is false, still keep Evidence Summary but trim bullets later
  const trimEvidence = !custom.showEvidence;

  const generatedAt = new Date().toISOString();
  const analysisDate = formatDate(
    view.freshness.researchDate ?? view.snapshot.researchDate.value,
    custom.dateFormat,
  );
  const blocks: ReportBlock[] = [];

  for (const section of finalSections) {
    switch (section) {
      case "cover":
        blocks.push({
          id: "cover",
          heading: "Cover Page",
          paragraphs: [
            custom.title,
            `Company: ${name}`,
            `Ticker: ${view.snapshot.ticker.value ?? "Unavailable"}`,
            `Generated: ${formatDate(generatedAt, custom.dateFormat)}`,
            `Analysis date: ${analysisDate}`,
            "DSP AI Indicator — Explainable Investment Research",
          ],
          citation: citation(view, "Report cover metadata"),
        });
        break;
      case "company_overview":
        blocks.push({
          id: "company_overview",
          heading: "Company Overview",
          paragraphs: [
            `Industry: ${view.snapshot.industry.value ?? "Unavailable"}`,
            `Sector: ${view.snapshot.sector.value ?? "Unavailable"}`,
            `Exchange: ${view.snapshot.exchange.value ?? "Unavailable"}`,
            `Market price: ${view.snapshot.currentMarketPrice.value ?? "Unavailable"}`,
            `Research status: ${view.snapshot.researchStatus.value ?? "Unavailable"}`,
          ],
          citation: citation(view, "Company Snapshot"),
        });
        break;
      case "executive_summary":
        blocks.push({
          id: "executive_summary",
          heading: "Executive Summary",
          paragraphs: view.executiveSummary.available
            ? view.executiveSummary.paragraphs
            : [
                "Executive summary paragraphs are Unavailable in the current envelope. DSP does not invent narrative.",
              ],
          citation: citation(view, "Executive Summary section"),
        });
        break;
      case "research_conclusion":
        blocks.push({
          id: "research_conclusion",
          heading: "Research Conclusion",
          paragraphs: [
            `${presentFieldLabel("recommendation")}: ${view.conclusion.conclusion.value ?? "Unavailable"}`,
            `${presentFieldLabel("target_price")}: ${view.conclusion.intrinsicValueRange.value ?? "Unavailable"}`,
            `Research confidence: ${view.conclusion.researchConfidence.value ?? CONFIDENCE_LABELS[view.confidenceBreakdown.overall]}`,
            `Primary opportunity: ${view.conclusion.primaryOpportunity.value ?? "Unavailable"}`,
            `Primary risk: ${view.conclusion.primaryRisk.value ?? "Unavailable"}`,
          ],
          bullets: view.conclusion.evidence.supportingEvidence.slice(0, 6),
          citation: citation(view, "Research Conclusion + Evidence"),
        });
        break;
      case "business_analysis":
        blocks.push({
          id: "business_analysis",
          heading: "Business Analysis",
          paragraphs: [
            "Business quality metrics from the Company Analysis workspace.",
          ],
          bullets: view.businessQuality.map(
            (m) =>
              `${m.title}: ${m.available ? m.actualValue : "Unavailable"} — ${m.investorTakeaway}`,
          ),
          citation: citation(view, "Business Quality metrics"),
        });
        break;
      case "financial_analysis":
        blocks.push({
          id: "financial_analysis",
          heading: "Financial Analysis",
          paragraphs: [
            "Financial strength metrics — values only when present in the envelope.",
            `Valuation summary: ${view.valuation.summary.value ?? "Unavailable"}`,
            `Intrinsic range: ${view.valuation.intrinsicValueRange.value ?? "Unavailable"}`,
          ],
          bullets: view.financialStrength.map(
            (m) =>
              `${m.title}: ${m.available ? m.actualValue : "Unavailable"}`,
          ),
          citation: citation(view, "Financial Strength / Valuation"),
        });
        break;
      case "growth":
        blocks.push({
          id: "growth",
          heading: "Growth",
          paragraphs: ["Growth drivers from DSP research templates."],
          bullets: view.growth.map(
            (g) =>
              `${g.title}: ${g.available ? g.rating : "Unavailable"} — ${g.meaning}`,
          ),
          citation: citation(view, "Growth Analysis"),
        });
        break;
      case "risk":
        blocks.push({
          id: "risk",
          heading: "Risk",
          paragraphs: ["Risk categories — severity Unavailable without evidence."],
          bullets: view.risks.map((r) => `${r.title}: ${r.reason}`),
          citation: citation(view, "Risk Analysis"),
        });
        break;
      case "management":
        blocks.push({
          id: "management",
          heading: "Management",
          paragraphs: ["Management quality insights."],
          bullets: view.management.map(
            (m) =>
              `${m.title}: ${m.available ? m.evidence : "Unavailable"} — ${m.meaning}`,
          ),
          citation: citation(view, "Management Quality"),
        });
        break;
      case "competitive_advantage":
        blocks.push({
          id: "competitive_advantage",
          heading: "Competitive Advantage",
          paragraphs: ["Moat / competitive advantage cards."],
          bullets: view.moat.map(
            (m) =>
              `${m.title}: ${m.available ? m.rating : "Unavailable"} — ${m.investorTakeaway}`,
          ),
          citation: citation(view, "Competitive Advantage"),
        });
        break;
      case "market_intelligence":
        blocks.push({
          id: "market_intelligence",
          heading: "Market Intelligence",
          paragraphs: [
            view.marketIntelligence.available
              ? "Market intelligence fields present."
              : "External market consensus is Unavailable — providers not connected. DSP Research remains primary.",
            view.marketIntelligence.researchCoverageNote.value ?? "",
            view.marketIntelligence.dataAvailability.value ?? "",
          ].filter(Boolean),
          citation: citation(view, "Market Intelligence / DSP vs Street"),
        });
        break;
      case "decision_trace":
        blocks.push({
          id: "decision_trace",
          heading: "Decision Trace",
          paragraphs: [
            `Conclusion: ${view.decisionTrace.conclusionLabel}`,
            view.decisionTrace.inputs.summary,
            view.decisionTrace.calculations.summary,
            view.decisionTrace.output.summary,
          ],
          bullets: [
            ...view.decisionTrace.evidenceUsed.details.slice(0, 4),
            ...view.decisionTrace.limitations.details.slice(0, 4),
          ],
          citation: citation(view, "Decision Trace"),
        });
        break;
      case "evidence_summary":
        blocks.push({
          id: "evidence_summary",
          heading: "Evidence Summary",
          paragraphs: [
            "Evidence is grouped by category. Supporting and contradicting items stay separate.",
            trimEvidence
              ? "Detail list condensed by customization — evidence references remain mandatory."
              : "",
          ].filter(Boolean),
          bullets: (trimEvidence
            ? view.evidenceExplorer.items.slice(0, 3)
            : view.evidenceExplorer.items
          ).map(
            (e) =>
              `[${e.group}] ${e.title} — ${e.confidence} — ${e.source}`,
          ),
          citation: citation(view, "Evidence Explorer"),
        });
        break;
      case "assumptions":
        blocks.push({
          id: "assumptions",
          heading: "Assumptions",
          paragraphs: ["Core assumptions that affect the DSP View."],
          bullets: view.assumptionExplorer.items.map(
            (a) =>
              `${a.statement} (sensitivity ${a.sensitivity}; if wrong: ${a.whatChangesIfWrong})`,
          ),
          citation: citation(view, "Assumption Explorer"),
        });
        break;
      case "confidence_summary":
        blocks.push({
          id: "confidence_summary",
          heading: "Confidence Summary",
          paragraphs: [
            `Overall: ${CONFIDENCE_LABELS[view.confidenceBreakdown.overall]}`,
            `Coverage completeness (meta): ${view.coverage.coveragePercent}%`,
            `Evidence strength label: ${view.coverage.evidenceStrength}`,
          ],
          bullets: view.confidenceBreakdown.rows.map(
            (r) =>
              `${r.label}: ${CONFIDENCE_LABELS[r.level]} — ${r.whyDifferent}`,
          ),
          citation: citation(view, "Confidence Breakdown"),
        });
        break;
      case "research_limitations":
        blocks.push({
          id: "research_limitations",
          heading: "Research Limitations",
          paragraphs: ["Professional limitations — required in every export."],
          bullets: [
            ...view.researchLimitations.unavailableData.map((x) => `Unavailable: ${x}`),
            ...view.researchLimitations.unknownFactors.map((x) => `Unknown: ${x}`),
            ...view.researchLimitations.pendingImprovements.map(
              (x) => `Pending: ${x}`,
            ),
          ],
          citation: citation(view, "Research Limitations"),
        });
        break;
      case "methodology":
        blocks.push({
          id: "methodology",
          heading: "Methodology",
          paragraphs: [
            view.methodologyPanel.researchMethodology,
            `Analysis version: ${view.methodologyPanel.analysisVersion}`,
            `Calculation version: ${view.methodologyPanel.calculationVersion}`,
            `Presentation version: ${view.methodologyPanel.presentationVersion}`,
            `Compliance version: ${view.methodologyPanel.complianceVersion}`,
          ],
          citation: citation(view, "Methodology Panel"),
        });
        break;
      case "knowledge_graph":
        blocks.push({
          id: "knowledge_graph",
          heading: "Knowledge Graph Snapshot",
          paragraphs: [
            `Graph version: ${view.knowledgeGraph.version}`,
            `Nodes: ${view.knowledgeGraph.nodes.length} · Edges: ${view.knowledgeGraph.edges.length}`,
            `Available nodes: ${view.knowledgeGraph.nodes.filter((n) => n.available).length}`,
            view.knowledgeGraph.emptyState.whyIncomplete,
          ],
          bullets: view.knowledgeGraph.nodes.slice(0, 20).map(
            (n) =>
              `${n.label} (${n.nodeType}) — ${CONFIDENCE_LABELS[n.confidence]} — ev ${n.evidenceCount}`,
          ),
          citation: citation(view, "Knowledge Graph"),
        });
        break;
      case "disclosures":
        blocks.push({
          id: "disclosures",
          heading: "Disclosures",
          paragraphs: [
            RESEARCH_DISCLAIMER,
            `Research Mode: ${view.freshness.researchMode}`,
            `Methodology version: ${view.freshness.methodologyVersion}`,
            `Analysis version: ${view.freshness.analysisVersion}`,
            `Analysis date: ${analysisDate}`,
            `Data currency: ${view.freshness.dataCurrency}`,
            "AI assistance disclosure: Research Copilot (when used) is an explainability assistant. It does not produce independent investment recommendations and does not invent numbers.",
            "This report is for research discussion — not a Buy, Sell, or Hold recommendation.",
          ],
          citation: citation(view, "Disclosures / Trust Standard"),
        });
        break;
    }
  }

  return {
    templateId: template.id,
    title: custom.title,
    companyLabel: name,
    generatedAt,
    blocks,
    disclosures: [
      RESEARCH_DISCLAIMER,
      view.freshness.researchMode,
      view.freshness.methodologyVersion,
      view.freshness.dataCurrency,
      "Limitations and confidence are mandatory in every DSP export.",
    ],
    metadata: {
      analysisVersion: view.freshness.analysisVersion,
      methodologyVersion: view.freshness.methodologyVersion,
      researchMode: view.freshness.researchMode,
      dataCurrency: view.freshness.dataCurrency,
      analysisDate: view.freshness.researchDate,
      coveragePercent: view.coverage.coveragePercent,
    },
  };
}

export function reportToMarkdown(report: BuiltReport): string {
  const lines: string[] = [`# ${report.title}`, ""];
  for (const b of report.blocks) {
    lines.push(`## ${b.heading}`, "");
    for (const p of b.paragraphs) lines.push(p, "");
    if (b.bullets?.length) {
      for (const item of b.bullets) lines.push(`- ${item}`);
      lines.push("");
    }
    if (b.citation) {
      lines.push(
        `> Evidence: ${b.citation.evidenceReference} · Confidence: ${b.citation.confidence} · Methodology: ${b.citation.methodology} · Timestamp: ${b.citation.timestamp ?? "Unavailable"}`,
        "",
      );
    }
  }
  return lines.join("\n");
}

export function reportToJson(report: BuiltReport): string {
  return JSON.stringify(report, null, 2);
}

export function reportToHtml(report: BuiltReport): string {
  const body = report.blocks
    .map((b) => {
      const paras = b.paragraphs.map((p) => `<p>${escapeHtml(p)}</p>`).join("");
      const list = b.bullets?.length
        ? `<ul>${b.bullets.map((i) => `<li>${escapeHtml(i)}</li>`).join("")}</ul>`
        : "";
      const cite = b.citation
        ? `<aside><strong>Citation:</strong> ${escapeHtml(b.citation.evidenceReference)} · ${escapeHtml(b.citation.confidence)} · ${escapeHtml(b.citation.methodology)} · ${escapeHtml(b.citation.timestamp ?? "Unavailable")}</aside>`
        : "";
      return `<section><h2>${escapeHtml(b.heading)}</h2>${paras}${list}${cite}</section>`;
    })
    .join("\n");
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/><title>${escapeHtml(report.title)}</title></head><body><h1>${escapeHtml(report.title)}</h1>${body}</body></html>`;
}

export function reportMetricsCsv(view: AnalysisWorkspaceView): string {
  const rows = [["section", "metric", "value", "available", "category"]];
  for (const m of [...view.businessQuality, ...view.financialStrength]) {
    rows.push([
      "metrics",
      m.title,
      m.actualValue,
      String(m.available),
      m.category,
    ]);
  }
  return rows.map((r) => r.map(csvEscape).join(",")).join("\n");
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function csvEscape(s: string): string {
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

export function downloadText(filename: string, content: string, mime: string) {
  // Sprint 9: path-safe filenames only (no business logic change)
  const safe = filename.replace(/[\\/:*?"<>|]+/g, "_").replace(/\.\./g, "_").slice(0, 180) || "dsp-export.txt";
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = safe;
  a.click();
  URL.revokeObjectURL(url);
}
