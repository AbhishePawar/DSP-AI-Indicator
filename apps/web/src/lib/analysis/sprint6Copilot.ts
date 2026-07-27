/** Sprint 6 — AI Research Copilot (explainability assistant — no LLM, no recommendations). */

import type { AnalysisWorkspaceView } from "@/lib/analysis/types";
import { CONFIDENCE_LABELS, type ConfidenceLevel } from "@/lib/trust/labels";
import { presentFieldLabel } from "@/lib/terminology";

export type CopilotAction =
  | "explain_metric"
  | "explain_section"
  | "summarize_company"
  | "show_supporting_evidence"
  | "show_contradicting_evidence"
  | "explain_confidence"
  | "explain_assumptions"
  | "explain_methodology"
  | "navigate_related"
  | "highlight_missing"
  | "summarize_risks"
  | "summarize_growth"
  | "summarize_valuation"
  | "compare"
  | "show_timeline"
  | "show_graph"
  | "free_text";

export type CopilotCitationKind =
  | "decision_trace"
  | "evidence"
  | "knowledge_graph"
  | "methodology"
  | "confidence";

export type CopilotCitation = {
  id: string;
  kind: CopilotCitationKind;
  label: string;
  href: string;
};

export type CopilotAnswer = {
  shortAnswer: string;
  detailedExplanation: string;
  supportingEvidence: string[];
  confidence: ConfidenceLevel;
  confidenceLabel: string;
  limitations: string[];
  relatedSections: { id: string; title: string; href: string }[];
  nextSuggestedQuestion: string;
  followUps: string[];
  citations: CopilotCitation[];
  sourceNote: string;
  methodologyNote: string;
  isUnavailable: boolean;
};

export type CopilotMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
  action?: CopilotAction;
  answer?: CopilotAnswer;
  createdAt: number;
};

export type CopilotSessionMemory = {
  companyLabel: string;
  expandedSections: string[];
  recentQuestions: string[];
  selectedGraphNodeId: string | null;
  selectedSectionId: string | null;
  selectedMetricId: string | null;
};

export type CopilotContextSnapshot = {
  sectionId: string | null;
  graphNodeId: string | null;
  metricId: string | null;
  metricTitle: string | null;
};

export const QUICK_ACTIONS: { id: CopilotAction; label: string }[] = [
  { id: "explain_section", label: "Explain" },
  { id: "compare", label: "Compare" },
  { id: "summarize_company", label: "Summarize" },
  { id: "show_supporting_evidence", label: "Show Evidence" },
  { id: "explain_assumptions", label: "Show Assumptions" },
  { id: "summarize_risks", label: "Show Risks" },
  { id: "summarize_growth", label: "Show Growth" },
  { id: "show_timeline", label: "Show Timeline" },
  { id: "show_graph", label: "Show Graph" },
];

const BASE_CITATIONS: CopilotCitation[] = [
  {
    id: "c-trace",
    kind: "decision_trace",
    label: "Decision Trace",
    href: "#decision_trace",
  },
  {
    id: "c-ev",
    kind: "evidence",
    label: "Evidence Explorer",
    href: "#evidence_explorer",
  },
  {
    id: "c-kg",
    kind: "knowledge_graph",
    label: "Knowledge Graph",
    href: "#knowledge_graph",
  },
  {
    id: "c-meth",
    kind: "methodology",
    label: "Methodology",
    href: "#methodology_panel",
  },
  {
    id: "c-conf",
    kind: "confidence",
    label: "Confidence Breakdown",
    href: "#confidence_breakdown",
  },
];

function unavailableAnswer(
  topic: string,
  related: CopilotAnswer["relatedSections"],
  followUps: string[],
): CopilotAnswer {
  return {
    shortAnswer: `${topic} is Unavailable in the current DSP Research envelope.`,
    detailedExplanation:
      "The Copilot only explains what DSP Research already contains. It will not invent figures, Street opinions, or a new investment conclusion.",
    supportingEvidence: ["No supporting artifacts present for this request"],
    confidence: "insufficient_evidence",
    confidenceLabel: CONFIDENCE_LABELS.insufficient_evidence,
    limitations: [
      "Sparse analyze envelope",
      "Copilot does not run autonomous analysis",
      "No LLM generation in this sprint — answers are research lookups",
    ],
    relatedSections: related,
    nextSuggestedQuestion: followUps[0] ?? "What information is missing?",
    followUps,
    citations: BASE_CITATIONS,
    sourceNote: "DSP Research workspace (presentation map) — not an independent AI opinion",
    methodologyNote: "Explainability assistant · Research Mode · no Buy/Sell/Target Price",
    isUnavailable: true,
  };
}

function companyLabel(view: AnalysisWorkspaceView): string {
  return (
    view.snapshot.companyName.value ??
    view.snapshot.ticker.value ??
    "this company"
  );
}

function overallConfidence(view: AnalysisWorkspaceView): ConfidenceLevel {
  return view.confidenceBreakdown.overall;
}

function defaultFollowUps(view: AnalysisWorkspaceView): string[] {
  const name = companyLabel(view);
  return [
    `What evidence supports the DSP View for ${name}?`,
    "Why is confidence different across domains?",
    "Which assumptions matter most?",
    "What information is still missing?",
    "Summarize the main risks",
  ];
}

function detectAction(text: string): CopilotAction {
  const t = text.toLowerCase();
  if (t.includes("contradict")) return "show_contradicting_evidence";
  if (t.includes("supporting evidence") || t.includes("show evidence"))
    return "show_supporting_evidence";
  if (t.includes("assumption")) return "explain_assumptions";
  if (t.includes("methodolog")) return "explain_methodology";
  if (t.includes("confidence")) return "explain_confidence";
  if (t.includes("missing") || t.includes("unavailable") || t.includes("gap"))
    return "highlight_missing";
  if (t.includes("risk")) return "summarize_risks";
  if (t.includes("growth")) return "summarize_growth";
  if (t.includes("valuation") || t.includes("intrinsic"))
    return "summarize_valuation";
  if (t.includes("timeline")) return "show_timeline";
  if (t.includes("graph") || t.includes("knowledge")) return "show_graph";
  if (t.includes("compare") || t.includes("street") || t.includes("vs"))
    return "compare";
  if (t.includes("summarize") && t.includes("compan")) return "summarize_company";
  if (t.includes("metric")) return "explain_metric";
  if (t.includes("section") || t.includes("explain")) return "explain_section";
  if (t.includes("related") || t.includes("navigate")) return "navigate_related";
  if (t.includes("summar")) return "summarize_company";
  return "free_text";
}

export function resolveCopilotAction(
  action: CopilotAction | "free_text",
  text: string,
): CopilotAction {
  if (action !== "free_text") return action;
  return detectAction(text);
}

export function buildCopilotAnswer(
  view: AnalysisWorkspaceView,
  action: CopilotAction,
  ctx: CopilotContextSnapshot,
  userText?: string,
): CopilotAnswer {
  const name = companyLabel(view);
  const conf = overallConfidence(view);
  const confLabel = CONFIDENCE_LABELS[conf];
  const followUps = defaultFollowUps(view);
  const meth = view.methodologyPanel;
  const sourceNote =
    "Answers cite DSP Research artifacts only. AI opinion is never presented as fact.";
  const methodologyNote = `${meth.analysisVersion} · ${meth.presentationVersion}`;

  const base = (partial: Omit<CopilotAnswer, "citations" | "sourceNote" | "methodologyNote" | "confidenceLabel">): CopilotAnswer => ({
    ...partial,
    confidenceLabel: CONFIDENCE_LABELS[partial.confidence],
    citations: BASE_CITATIONS,
    sourceNote,
    methodologyNote,
  });

  switch (action) {
    case "summarize_company": {
      const conclusion = view.conclusion.conclusion.value;
      const has = view.conclusion.conclusion.presence === "available";
      if (!has && !view.apiOk) {
        return unavailableAnswer(`A company summary for ${name}`, [
          { id: "company_snapshot", title: "Company Snapshot", href: "#company_snapshot" },
        ], followUps);
      }
      return base({
        shortAnswer: has
          ? `${name}: DSP View is “${conclusion}” with ${confLabel} overall research confidence.`
          : `${name}: DSP Research loaded, but a mapped research conclusion is still Unavailable.`,
        detailedExplanation: [
          view.executiveSummary.available
            ? view.executiveSummary.paragraphs.slice(0, 2).join(" ")
            : "Executive summary paragraphs are Unavailable — the Copilot will not invent a narrative.",
          `Coverage completeness (meta, not quality): ${view.coverage.coveragePercent}%.`,
          `Primary opportunity: ${view.conclusion.primaryOpportunity.value ?? "Unavailable"}.`,
          `Primary risk: ${view.conclusion.primaryRisk.value ?? "Unavailable"}.`,
        ].join(" "),
        supportingEvidence: [
          ...view.conclusion.evidence.supportingEvidence.slice(0, 4),
          ...view.conclusion.evidence.primaryEvidence.slice(0, 2),
        ].filter(Boolean),
        confidence: conf,
        limitations: [
          ...view.researchLimitations.unavailableData.slice(0, 3),
          "This is an explanation of DSP Research — not a Buy/Sell recommendation",
        ],
        relatedSections: [
          { id: "research_conclusion", title: "Research Conclusion", href: "#research_conclusion" },
          { id: "executive_summary", title: "Executive Summary", href: "#executive_summary" },
          { id: "decision_dashboard", title: "Decision Dashboard", href: "#decision_dashboard" },
        ],
        nextSuggestedQuestion: followUps[0],
        followUps,
        isUnavailable: !has,
      });
    }

    case "explain_metric": {
      const metrics = [...view.businessQuality, ...view.financialStrength];
      const metric =
        metrics.find((m) => m.id === ctx.metricId) ??
        metrics.find((m) =>
          (ctx.metricTitle ?? userText ?? "")
            .toLowerCase()
            .includes(m.title.toLowerCase()),
        ) ??
        metrics[0];
      if (!metric) {
        return unavailableAnswer("Metric explanation", [
          { id: "business_quality", title: "Business Quality", href: "#business_quality" },
        ], followUps);
      }
      return base({
        shortAnswer: metric.available
          ? `${metric.title}: ${metric.actualValue} (${metric.rating}).`
          : `${metric.title} is Unavailable — DSP has not supplied a calculated or verified value.`,
        detailedExplanation: [
          metric.meaning,
          `Why it matters: ${metric.whyItMatters}`,
          `Investor takeaway: ${metric.investorTakeaway}`,
          "The Copilot does not recalculate metrics in the browser.",
        ].join(" "),
        supportingEvidence: metric.available
          ? [`Displayed value: ${metric.actualValue}`, `Category: ${metric.category}`]
          : ["No metric value in envelope — educational template only"],
        confidence: metric.available ? "low" : "insufficient_evidence",
        limitations: [
          "Thin client performs no investment math",
          metric.available ? "Value depends on backend envelope fidelity" : "Unavailable until fundamentals load",
        ],
        relatedSections: [
          { id: "business_quality", title: "Business Quality", href: "#business_quality" },
          { id: "financial_strength", title: "Financial Strength", href: "#financial_strength" },
          { id: "evidence_explorer", title: "Evidence Explorer", href: "#evidence_explorer" },
        ],
        nextSuggestedQuestion: "Show supporting evidence for this research",
        followUps: [
          "Show supporting evidence for this research",
          "Explain confidence for financial data",
          "What information is still missing?",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: !metric.available,
      });
    }

    case "explain_section": {
      const section = ctx.sectionId ?? "research_conclusion";
      const title =
        section.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      return base({
        shortAnswer: `Section “${title}” is part of the DSP Company Analysis workspace — open it for the full research presentation.`,
        detailedExplanation: [
          `You asked about ${title}.`,
          "Use Decision Trace for how conclusions are formed, Evidence Explorer for grouped evidence, and Knowledge Graph for relationships.",
          ctx.graphNodeId
            ? `Selected graph node context: ${ctx.graphNodeId}.`
            : "No graph node is selected in session memory.",
          `Overall research confidence: ${confLabel}.`,
        ].join(" "),
        supportingEvidence: [
          `Navigate to #${section}`,
          view.decisionTrace.available
            ? `Decision Trace output: ${view.decisionTrace.output.summary}`
            : "Decision Trace scaffold present — conclusion may be Unavailable",
        ],
        confidence: conf,
        limitations: view.researchLimitations.assumptions.slice(0, 3),
        relatedSections: [
          { id: section, title, href: `#${section}` },
          { id: "decision_trace", title: "Decision Trace", href: "#decision_trace" },
          { id: "knowledge_graph", title: "Knowledge Graph", href: "#knowledge_graph" },
        ],
        nextSuggestedQuestion: "Explain the Decision Trace for this company",
        followUps: [
          "Explain the Decision Trace for this company",
          "Show supporting evidence",
          "Highlight missing information",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: false,
      });
    }

    case "show_supporting_evidence": {
      const items = [
        ...view.conclusion.evidence.supportingEvidence,
        ...view.conclusion.evidence.primaryEvidence,
        ...view.aiChallenge.supportingEvidence,
        ...view.evidenceExplorer.items
          .filter((i) => i.group !== "unavailable")
          .map((i) => i.title),
      ].filter(Boolean);
      if (!items.length) {
        return unavailableAnswer("Supporting evidence", [
          { id: "evidence_explorer", title: "Evidence Explorer", href: "#evidence_explorer" },
        ], followUps);
      }
      return base({
        shortAnswer: `Found ${items.length} supporting evidence item(s) already present in DSP Research.`,
        detailedExplanation:
          "Supporting evidence is listed separately from contradicting evidence. The Copilot only repeats what the workspace already shows.",
        supportingEvidence: items.slice(0, 8),
        confidence: items.length ? conf : "insufficient_evidence",
        limitations: [
          "Absence of contradicting items is not proof of correctness",
          ...view.conclusion.evidence.limitations.slice(0, 2),
        ],
        relatedSections: [
          { id: "evidence_explorer", title: "Evidence Explorer", href: "#evidence_explorer" },
          { id: "decision_trace", title: "Decision Trace", href: "#decision_trace" },
          { id: "ai_challenge", title: "AI Challenge", href: "#ai_challenge" },
        ],
        nextSuggestedQuestion: "Show contradicting evidence",
        followUps: [
          "Show contradicting evidence",
          "Explain assumptions",
          "Explain confidence",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: false,
      });
    }

    case "show_contradicting_evidence": {
      const items = [
        ...view.conclusion.evidence.contradictingEvidence,
        ...view.aiChallenge.contradictingEvidence,
      ].filter(Boolean);
      return base({
        shortAnswer: items.length
          ? `Found ${items.length} contradicting / limiting item(s).`
          : "No explicit contradicting evidence artifacts are listed — that does not mean the DSP View is proven.",
        detailedExplanation:
          "DSP keeps contradicting evidence separate for honesty. Empty contradicting lists must not be read as bullish confirmation.",
        supportingEvidence: items.length ? items.slice(0, 8) : ["None listed in envelope"],
        confidence: "insufficient_evidence",
        limitations: [
          "Sparse envelopes often omit dissent",
          "Copilot will not fabricate counter-arguments",
        ],
        relatedSections: [
          { id: "ai_challenge", title: "AI Challenge", href: "#ai_challenge" },
          { id: "evidence_explorer", title: "Evidence Explorer", href: "#evidence_explorer" },
        ],
        nextSuggestedQuestion: "What could invalidate this conclusion?",
        followUps: [
          "Highlight missing information",
          "Explain assumptions",
          "Summarize risks",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: items.length === 0,
      });
    }

    case "explain_confidence": {
      const rows = view.confidenceBreakdown.rows;
      return base({
        shortAnswer: `Overall research confidence is ${confLabel}. Domain confidence often stays Insufficient Evidence when metrics are missing.`,
        detailedExplanation: rows
          .map((r) => `${r.label}: ${CONFIDENCE_LABELS[r.level]} — ${r.whyDifferent}`)
          .join(" "),
        supportingEvidence: rows.map(
          (r) => `${r.label}: ${CONFIDENCE_LABELS[r.level]}`,
        ),
        confidence: conf,
        limitations: [
          "Coverage % is completeness meta, not a confidence score alone",
          "Copilot does not upgrade confidence without new evidence",
        ],
        relatedSections: [
          { id: "confidence_breakdown", title: "Confidence Breakdown", href: "#confidence_breakdown" },
          { id: "confidence_matrix", title: "Confidence Matrix", href: "#confidence_matrix" },
        ],
        nextSuggestedQuestion: "Why is valuation confidence low?",
        followUps: [
          "Highlight missing information",
          "Explain methodology",
          "Show supporting evidence",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: false,
      });
    }

    case "explain_assumptions": {
      const items = view.assumptionExplorer.items;
      return base({
        shortAnswer: `${items.length} core assumption(s) are documented in Assumption Explorer.`,
        detailedExplanation: items
          .map(
            (a) =>
              `${a.statement} (sensitivity ${a.sensitivity}; if wrong: ${a.whatChangesIfWrong})`,
          )
          .join(" "),
        supportingEvidence: items.flatMap((a) => a.alternativeAssumptions).slice(0, 6),
        confidence: conf,
        limitations: items.map((a) => a.impact).slice(0, 4),
        relatedSections: [
          { id: "assumption_explorer", title: "Assumption Explorer", href: "#assumption_explorer" },
          { id: "ai_challenge", title: "AI Challenge", href: "#ai_challenge" },
        ],
        nextSuggestedQuestion: "What changes if the envelope-completeness assumption is wrong?",
        followUps: [
          "Highlight missing information",
          "Explain confidence",
          "Show contradicting evidence",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: items.length === 0,
      });
    }

    case "explain_methodology": {
      return base({
        shortAnswer: "DSP presents Decision Engine envelopes under Research Mode — the browser does not recalculate valuation.",
        detailedExplanation: [
          meth.researchMethodology,
          `Analysis: ${meth.analysisVersion}`,
          `Calculation: ${meth.calculationVersion}`,
          `Presentation: ${meth.presentationVersion}`,
          `Compliance: ${meth.complianceVersion}`,
        ].join(" "),
        supportingEvidence: [
          meth.analysisVersion,
          meth.presentationVersion,
          view.freshness.researchMode,
        ],
        confidence: "high",
        limitations: [
          "No autonomous re-analysis in Copilot",
          `${presentFieldLabel("target_price")} is not an Official Target Price in Research Mode`,
        ],
        relatedSections: [
          { id: "methodology_panel", title: "Methodology", href: "#methodology_panel" },
          { id: "decision_trace", title: "Decision Trace", href: "#decision_trace" },
        ],
        nextSuggestedQuestion: "Explain the Decision Trace steps",
        followUps: [
          "Explain confidence",
          "Show the knowledge graph",
          "Highlight missing information",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: false,
      });
    }

    case "navigate_related": {
      return base({
        shortAnswer: "Related research surfaces: Decision Trace, Evidence, Knowledge Graph, Confidence, Methodology.",
        detailedExplanation:
          "Use the citations and related section links below. The Copilot navigates research — it does not replace it.",
        supportingEvidence: BASE_CITATIONS.map((c) => c.label),
        confidence: conf,
        limitations: ["Navigation only — no new analysis generated"],
        relatedSections: [
          { id: "decision_trace", title: "Decision Trace", href: "#decision_trace" },
          { id: "evidence_explorer", title: "Evidence Explorer", href: "#evidence_explorer" },
          { id: "knowledge_graph", title: "Knowledge Graph", href: "#knowledge_graph" },
          { id: "reasoning_flow", title: "Reasoning Flow", href: "#reasoning_flow" },
        ],
        nextSuggestedQuestion: "Show the knowledge graph",
        followUps: [
          "Show the knowledge graph",
          "Show research timeline",
          "Summarize this company",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: false,
      });
    }

    case "highlight_missing": {
      const missing = [
        ...view.researchLimitations.unavailableData,
        ...view.transparencyPanel.unavailableData,
        ...view.transparencyPanel.knownUnknowns,
      ];
      return base({
        shortAnswer: `${missing.length} known gap(s) / unavailable item(s) are documented — DSP will not fill them with guesses.`,
        detailedExplanation: missing.slice(0, 10).join(" · "),
        supportingEvidence: view.transparencyPanel.estimatedFields,
        confidence: "insufficient_evidence",
        limitations: view.researchLimitations.pendingImprovements.slice(0, 4),
        relatedSections: [
          { id: "research_limitations", title: "Research Limitations", href: "#research_limitations" },
          { id: "transparency_panel", title: "Transparency", href: "#transparency_panel" },
        ],
        nextSuggestedQuestion: "Explain assumptions behind the DSP View",
        followUps: [
          "Explain assumptions",
          "Explain confidence",
          "Summarize risks",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: true,
      });
    }

    case "summarize_risks": {
      const risks = view.risks;
      const available = risks.filter((r) => r.available);
      return base({
        shortAnswer: available.length
          ? `${available.length} risk insight(s) have evidence; others remain educational templates.`
          : "Risk categories are listed educationally — severity/probability remain Unavailable without artifacts.",
        detailedExplanation: risks
          .slice(0, 6)
          .map((r) => `${r.title}: ${r.reason}`)
          .join(" "),
        supportingEvidence: risks.flatMap((r) => r.supportingEvidence).slice(0, 6),
        confidence: available.length ? "low" : "insufficient_evidence",
        limitations: [
          "No fabricated risk scores",
          ...view.aiChallenge.investorWatchpoints.slice(0, 2),
        ],
        relatedSections: [
          { id: "risk", title: "Risk Analysis", href: "#risk" },
          { id: "ai_challenge", title: "AI Challenge", href: "#ai_challenge" },
        ],
        nextSuggestedQuestion: "What could invalidate this conclusion?",
        followUps: [
          "Show contradicting evidence",
          "Explain assumptions",
          "Summarize growth",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: available.length === 0,
      });
    }

    case "summarize_growth": {
      const growth = view.growth;
      const available = growth.filter((g) => g.available);
      return base({
        shortAnswer: available.length
          ? `${available.length} growth driver(s) have values.`
          : "Growth drivers are educational templates — ratings Unavailable until evidence arrives.",
        detailedExplanation: growth
          .slice(0, 6)
          .map((g) => `${g.title}: ${g.meaning}`)
          .join(" "),
        supportingEvidence: growth.flatMap((g) => g.evidence.supportingEvidence).slice(0, 6),
        confidence: available.length ? "low" : "insufficient_evidence",
        limitations: ["Copilot does not estimate growth rates"],
        relatedSections: [
          { id: "growth", title: "Growth Analysis", href: "#growth" },
          { id: "reasoning_flow", title: "Reasoning Flow", href: "#reasoning_flow" },
        ],
        nextSuggestedQuestion: "Summarize valuation",
        followUps: [
          "Summarize valuation",
          "Summarize risks",
          "Show supporting evidence",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: available.length === 0,
      });
    }

    case "summarize_valuation": {
      const v = view.valuation;
      const has =
        v.intrinsicValueRange.presence === "available" ||
        v.summary.presence === "available";
      return base({
        shortAnswer: has
          ? `Valuation summary present: ${v.summary.value ?? v.intrinsicValueRange.value}.`
          : `${presentFieldLabel("target_price")} and scenario bands are Unavailable — Copilot will not invent prices.`,
        detailedExplanation: [
          `Current price: ${v.currentPrice.value ?? "Unavailable"}`,
          `Intrinsic range: ${v.intrinsicValueRange.value ?? "Unavailable"}`,
          `Margin of safety: ${v.marginOfSafety.value ?? "Unavailable"}`,
          "Research Mode does not show Official Target Price labels.",
        ].join(" "),
        supportingEvidence: has
          ? [v.summary.value, v.bull.value, v.base.value, v.bear.value].filter(
              (x): x is string => Boolean(x),
            )
          : ["No valuation artifacts in envelope"],
        confidence: has ? "low" : "insufficient_evidence",
        limitations: [
          "No browser valuation math",
          "No Buy/Sell/Target Price advice from Copilot",
        ],
        relatedSections: [
          { id: "valuation", title: "Valuation", href: "#valuation" },
          { id: "decision_trace", title: "Decision Trace", href: "#decision_trace" },
        ],
        nextSuggestedQuestion: "Explain methodology for valuation presentation",
        followUps: [
          "Explain methodology",
          "Explain confidence",
          "Highlight missing information",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: !has,
      });
    }

    case "compare": {
      return base({
        shortAnswer: view.analystConsensus.available
          ? "Street consensus is available — see DSP vs Street."
          : "Street / External Consensus is Unavailable. DSP Research remains the primary source — no fabricated Street opinion.",
        detailedExplanation: view.streetComparison
          .slice(0, 4)
          .map((r) => `${r.dimension}: ${r.reasonForDifference}`)
          .join(" "),
        supportingEvidence: view.streetComparison
          .flatMap((r) => r.supportingEvidence)
          .slice(0, 6),
        confidence: "insufficient_evidence",
        limitations: [
          "Providers not connected in this RC",
          "Copilot will not invent analyst targets",
        ],
        relatedSections: [
          { id: "dsp_vs_street", title: "DSP vs Street", href: "#dsp_vs_street" },
          { id: "analyst_consensus", title: "Analyst Consensus", href: "#analyst_consensus" },
        ],
        nextSuggestedQuestion: "Show supporting evidence for the DSP View",
        followUps: [
          "Show supporting evidence",
          "Explain confidence",
          "Summarize this company",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: !view.analystConsensus.available,
      });
    }

    case "show_timeline": {
      const events = view.researchTimeline.events;
      return base({
        shortAnswer: `Research timeline has ${events.length} event slot(s) (some may be placeholders).`,
        detailedExplanation: events
          .map((e) => `${e.label}: ${e.detail}${e.at ? ` (${e.at})` : ""}`)
          .join(" "),
        supportingEvidence: events.filter((e) => e.at).map((e) => `${e.label}: ${e.at}`),
        confidence: conf,
        limitations: ["Future events are placeholders until enrichment jobs run"],
        relatedSections: [
          { id: "research_timeline", title: "Research Timeline", href: "#research_timeline" },
        ],
        nextSuggestedQuestion: "Explain methodology version",
        followUps: [
          "Explain methodology",
          "Show the knowledge graph",
          "Highlight missing information",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: false,
      });
    }

    case "show_graph": {
      const n = view.knowledgeGraph.nodes.length;
      const avail = view.knowledgeGraph.nodes.filter((x) => x.available).length;
      const selected = ctx.graphNodeId
        ? view.knowledgeGraph.nodes.find((x) => x.id === ctx.graphNodeId)
        : null;
      return base({
        shortAnswer: selected
          ? `Selected graph node: ${selected.label} (${selected.nodeType}).`
          : `Knowledge Graph has ${n} nodes (${avail} available). Open the graph to explore relationships.`,
        detailedExplanation: [
          view.knowledgeGraph.emptyState.whyIncomplete,
          selected
            ? `Node description: ${selected.description}`
            : "Select a node in the Knowledge Graph to attach it to Copilot session memory.",
        ].join(" "),
        supportingEvidence: selected?.evidence.slice(0, 5) ?? [
          `Graph version ${view.knowledgeGraph.version}`,
        ],
        confidence: selected?.confidence ?? conf,
        limitations: view.knowledgeGraph.emptyState.missingEvidence.slice(0, 4),
        relatedSections: [
          { id: "knowledge_graph", title: "Knowledge Graph", href: "#knowledge_graph" },
          { id: "decision_trace", title: "Decision Trace", href: "#decision_trace" },
        ],
        nextSuggestedQuestion: "Explain the selected graph node",
        followUps: [
          "Explain this section",
          "Show supporting evidence",
          "Explain confidence",
          ...followUps.slice(0, 2),
        ],
        isUnavailable: avail === 0,
      });
    }

    case "free_text":
    default: {
      const detected = detectAction(userText ?? "");
      if (detected !== "free_text") {
        return buildCopilotAnswer(view, detected, ctx, userText);
      }
      return base({
        shortAnswer:
          "I can explain DSP Research — metrics, sections, evidence, confidence, assumptions, methodology, risks, growth, and valuation. I do not give Buy/Sell advice.",
        detailedExplanation: [
          `Current company context: ${name}.`,
          `Overall confidence: ${confLabel}.`,
          userText ? `You asked: “${userText}”. Try a quick action below for a structured answer.` : "",
          "Every answer includes evidence, confidence, limitations, and citations back into the workspace.",
        ]
          .filter(Boolean)
          .join(" "),
        supportingEvidence: [
          "Quick actions map to Decision Trace, Evidence, Graph, and Methodology",
        ],
        confidence: conf,
        limitations: [
          "No autonomous analysis",
          "No fabricated numbers",
          "Session memory only — not persisted",
        ],
        relatedSections: [
          { id: "decision_dashboard", title: "Decision Dashboard", href: "#decision_dashboard" },
          { id: "decision_trace", title: "Decision Trace", href: "#decision_trace" },
        ],
        nextSuggestedQuestion: followUps[0],
        followUps,
        isUnavailable: false,
      });
    }
  }
}

export function createSessionMemory(view: AnalysisWorkspaceView): CopilotSessionMemory {
  return {
    companyLabel: companyLabel(view),
    expandedSections: [],
    recentQuestions: [],
    selectedGraphNodeId: null,
    selectedSectionId: null,
    selectedMetricId: null,
  };
}

export function uid(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}
