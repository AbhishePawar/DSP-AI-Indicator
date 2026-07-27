/** Sprint 5 — Explainable Knowledge Graph builders (presentation only — no LLM). */

import type {
  AnalysisWorkspaceView,
  KgEdgeType,
  KgNodeType,
  KnowledgeGraphEdge,
  KnowledgeGraphNode,
  KnowledgeGraphTab,
  KnowledgeGraphView,
} from "@/lib/analysis/types";
import type { ConfidenceLevel } from "@/lib/trust/labels";

type GraphSeed = Omit<AnalysisWorkspaceView, "coverage" | "freshness" | "knowledgeGraph">;

function node( partial: Omit<KnowledgeGraphNode, "searchText" | "relatedNodeIds"> & {
  relatedNodeIds?: string[];
}): KnowledgeGraphNode {
  const relatedNodeIds = partial.relatedNodeIds ?? [];
  const searchText = [
    partial.label,
    partial.nodeType,
    partial.description,
    ...partial.evidence,
    ...partial.supportingMetrics,
    ...partial.researchSectionIds,
    partial.tab,
  ]
    .join(" ")
    .toLowerCase();
  return { ...partial, relatedNodeIds, searchText };
}

function edge(
  id: string,
  from: string,
  to: string,
  edgeType: KgEdgeType,
  label: string,
): KnowledgeGraphEdge {
  return { id, from, to, edgeType, label };
}

function confFromAvailable(available: boolean, fallback: ConfidenceLevel = "moderate"): ConfidenceLevel {
  return available ? fallback : "insufficient_evidence";
}

function linkRelated(nodes: KnowledgeGraphNode[], edges: KnowledgeGraphEdge[]) {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  for (const e of edges) {
    const a = byId.get(e.from);
    const b = byId.get(e.to);
    if (a && !a.relatedNodeIds.includes(e.to)) a.relatedNodeIds.push(e.to);
    if (b && !b.relatedNodeIds.includes(e.from)) b.relatedNodeIds.push(e.from);
  }
}

export const KG_TAB_LABELS: Record<KnowledgeGraphTab, string> = {
  business: "Business",
  financial: "Financial",
  growth: "Growth",
  risk: "Risk",
  management: "Management",
  valuation: "Valuation",
  research: "Research",
};

export const KG_NODE_TYPE_LABELS: Record<KgNodeType, string> = {
  company: "Company",
  industry: "Industry",
  sector: "Sector",
  metric: "Metric",
  financial_statement: "Financial Statement",
  business_quality: "Business Quality",
  growth_driver: "Growth Driver",
  risk: "Risk",
  management: "Management",
  competitive_advantage: "Competitive Advantage",
  valuation: "Valuation",
  research_conclusion: "Research Conclusion",
  evidence: "Evidence",
  assumption: "Assumption",
  methodology: "Methodology",
  external_consensus: "External Consensus",
};

export const KG_EDGE_TYPE_LABELS: Record<KgEdgeType, string> = {
  supports: "Supports",
  influences: "Influences",
  depends_on: "Depends On",
  derived_from: "Derived From",
  conflicts_with: "Conflicts With",
  related_to: "Related To",
  explains: "Explains",
};

/**
 * Build an explainable knowledge graph from the workspace view-model.
 * Connects company → metrics → insights → conclusion → evidence/assumptions.
 */
export function buildKnowledgeGraph(view: GraphSeed): KnowledgeGraphView {
  const nodes: KnowledgeGraphNode[] = [];
  const edges: KnowledgeGraphEdge[] = [];
  const updated =
    view.snapshot.lastUpdated.value ?? view.conclusion.evidence.lastUpdated ?? null;

  const ticker =
    view.snapshot.ticker.value ?? view.snapshot.companyName.value ?? "Company";
  const companyAvailable = Boolean(view.snapshot.ticker.value);
  const conclusionAvailable = view.conclusion.conclusion.presence === "available";
  const conclusionLabel =
    view.conclusion.conclusion.value ?? view.decisionTrace.conclusionLabel ?? "Unavailable";

  const companyId = "kg-company";
  const conclusionId = "kg-conclusion";
  const methodologyId = "kg-methodology";
  const industryId = "kg-industry";
  const sectorId = "kg-sector";
  const stmtId = "kg-financial-statement";
  const consensusId = "kg-external-consensus";

  nodes.push(
    node({
      id: companyId,
      label: ticker,
      nodeType: "company",
      confidence: confFromAvailable(companyAvailable, "high"),
      evidenceCount: companyAvailable ? 1 : 0,
      dataCategory: companyAvailable ? "user_input" : "unavailable",
      lastUpdated: updated,
      sourceCategory: companyAvailable ? "user_input" : "unavailable",
      description: "Company entity under research — anchors all domain subgraphs.",
      evidence: companyAvailable
        ? [`User-selected symbol: ${ticker}`]
        : ["No symbol session yet"],
      supportingMetrics: [],
      researchSectionIds: ["company_snapshot"],
      decisionTraceLinks: ["#decision_trace", "#company_snapshot"],
      tab: "business",
      available: companyAvailable,
    }),
  );

  const industryAvail = view.snapshot.industry.presence === "available";
  nodes.push(
    node({
      id: industryId,
      label: view.snapshot.industry.value ?? "Industry (Unavailable)",
      nodeType: "industry",
      confidence: confFromAvailable(industryAvail),
      evidenceCount: industryAvail ? 1 : 0,
      dataCategory: industryAvail ? "verified_fact" : "unavailable",
      lastUpdated: updated,
      sourceCategory: industryAvail ? "verified_financial_statement" : "unavailable",
      description: "Industry classification for the company.",
      evidence: industryAvail
        ? [`Industry: ${view.snapshot.industry.value}`]
        : ["Industry not present in envelope"],
      supportingMetrics: [],
      researchSectionIds: ["company_snapshot"],
      decisionTraceLinks: ["#company_snapshot"],
      tab: "business",
      available: industryAvail,
    }),
  );

  const sectorAvail = view.snapshot.sector.presence === "available";
  nodes.push(
    node({
      id: sectorId,
      label: view.snapshot.sector.value ?? "Sector (Unavailable)",
      nodeType: "sector",
      confidence: confFromAvailable(sectorAvail),
      evidenceCount: sectorAvail ? 1 : 0,
      dataCategory: sectorAvail ? "verified_fact" : "unavailable",
      lastUpdated: updated,
      sourceCategory: sectorAvail ? "verified_financial_statement" : "unavailable",
      description: "Sector classification for the company.",
      evidence: sectorAvail
        ? [`Sector: ${view.snapshot.sector.value}`]
        : ["Sector not present in envelope"],
      supportingMetrics: [],
      researchSectionIds: ["company_snapshot"],
      decisionTraceLinks: ["#company_snapshot"],
      tab: "business",
      available: sectorAvail,
    }),
  );

  edges.push(
    edge("e-co-ind", companyId, industryId, "related_to", "Belongs to industry"),
    edge("e-co-sec", companyId, sectorId, "related_to", "Belongs to sector"),
  );

  nodes.push(
    node({
      id: stmtId,
      label: "Financial Statement Artifacts",
      nodeType: "financial_statement",
      confidence: "insufficient_evidence",
      evidenceCount: 0,
      dataCategory: "unavailable",
      lastUpdated: null,
      sourceCategory: "unavailable",
      description:
        "Verified statement line items are not projected into the thin client in this RC.",
      evidence: ["No verified statement payload in /analyze/company envelope"],
      supportingMetrics: view.financialStrength.map((m) => m.title),
      researchSectionIds: ["financial_strength"],
      decisionTraceLinks: ["#financial_strength", "#evidence_explorer"],
      tab: "financial",
      available: false,
    }),
  );
  edges.push(
    edge("e-stmt-co", stmtId, companyId, "depends_on", "Statements describe company"),
  );

  // Business quality metrics
  for (const m of view.businessQuality) {
    const id = `kg-bq-${m.id}`;
    nodes.push(
      node({
        id,
        label: m.title,
        nodeType: "business_quality",
        confidence: confFromAvailable(m.available, "low"),
        evidenceCount: m.available ? 1 : 0,
        dataCategory: m.category,
        lastUpdated: updated,
        sourceCategory: m.source,
        description: m.meaning,
        evidence: m.available
          ? [`Actual: ${m.actualValue}`, m.investorTakeaway]
          : ["Unavailable — educational template"],
        supportingMetrics: [m.title],
        researchSectionIds: ["business_quality"],
        decisionTraceLinks: ["#business_quality", "#decision_trace"],
        tab: "business",
        available: m.available,
      }),
    );
    edges.push(
      edge(`e-bq-${m.id}-co`, id, companyId, "influences", "Business quality signal"),
      edge(`e-bq-${m.id}-stmt`, id, stmtId, "derived_from", "Would derive from statements"),
    );
  }

  // Financial metrics
  for (const m of view.financialStrength) {
    const id = `kg-fin-${m.id}`;
    nodes.push(
      node({
        id,
        label: m.title,
        nodeType: "metric",
        confidence: confFromAvailable(m.available, "low"),
        evidenceCount: m.available ? 1 : 0,
        dataCategory: m.category,
        lastUpdated: updated,
        sourceCategory: m.source,
        description: m.meaning,
        evidence: m.available
          ? [`Actual: ${m.actualValue}`]
          : ["Unavailable — no calculated value in envelope"],
        supportingMetrics: [m.title],
        researchSectionIds: ["financial_strength"],
        decisionTraceLinks: ["#financial_strength", "#confidence_breakdown"],
        tab: "financial",
        available: m.available,
      }),
    );
    edges.push(
      edge(`e-fin-${m.id}-stmt`, id, stmtId, "derived_from", "Derived from statements"),
      edge(`e-fin-${m.id}-co`, id, companyId, "supports", "Supports financial view"),
    );
  }

  // Growth
  for (const g of view.growth) {
    const id = `kg-gr-${g.id}`;
    nodes.push(
      node({
        id,
        label: g.title,
        nodeType: "growth_driver",
        confidence: confFromAvailable(g.available, "low"),
        evidenceCount: g.evidence.primaryEvidence.length + g.evidence.supportingEvidence.length,
        dataCategory: g.category,
        lastUpdated: g.evidence.lastUpdated ?? updated,
        sourceCategory: g.source,
        description: g.meaning,
        evidence:
          g.evidence.supportingEvidence.length > 0
            ? g.evidence.supportingEvidence
            : ["No growth evidence artifacts yet"],
        supportingMetrics: [g.title],
        researchSectionIds: ["growth"],
        decisionTraceLinks: ["#growth", "#reasoning_flow"],
        tab: "growth",
        available: g.available,
      }),
    );
    edges.push(edge(`e-gr-${g.id}`, id, companyId, "influences", "Growth driver"));
  }

  // Risk
  for (const r of view.risks) {
    const id = `kg-risk-${r.id}`;
    nodes.push(
      node({
        id,
        label: r.title,
        nodeType: "risk",
        confidence: confFromAvailable(r.available, "low"),
        evidenceCount: r.supportingEvidence.length,
        dataCategory: r.category,
        lastUpdated: updated,
        sourceCategory: r.source,
        description: r.reason,
        evidence:
          r.supportingEvidence.length > 0
            ? r.supportingEvidence
            : ["Risk taxonomy only — severity Unavailable"],
        supportingMetrics: [],
        researchSectionIds: ["risk"],
        decisionTraceLinks: ["#risk", "#ai_challenge"],
        tab: "risk",
        available: r.available,
      }),
    );
    edges.push(
      edge(`e-risk-${r.id}`, id, companyId, "conflicts_with", "Risk pressure"),
      edge(`e-risk-${r.id}-conc`, id, conclusionId, "influences", "Affects conclusion"),
    );
  }

  // Management
  for (const m of view.management) {
    const id = `kg-mgmt-${m.id}`;
    nodes.push(
      node({
        id,
        label: m.title,
        nodeType: "management",
        confidence: m.confidence,
        evidenceCount: m.available ? 1 : 0,
        dataCategory: m.category,
        lastUpdated: updated,
        sourceCategory: m.source,
        description: m.meaning,
        evidence: [m.evidence],
        supportingMetrics: [],
        researchSectionIds: ["management"],
        decisionTraceLinks: ["#management"],
        tab: "management",
        available: m.available,
      }),
    );
    edges.push(edge(`e-mgmt-${m.id}`, id, companyId, "influences", "Management signal"));
  }

  // Moat / competitive advantage
  for (const m of view.moat) {
    const id = `kg-moat-${m.id}`;
    nodes.push(
      node({
        id,
        label: m.title,
        nodeType: "competitive_advantage",
        confidence: confFromAvailable(m.available, "low"),
        evidenceCount: m.available ? 1 : 0,
        dataCategory: m.category,
        lastUpdated: updated,
        sourceCategory: m.source,
        description: m.meaning,
        evidence: [m.evidence],
        supportingMetrics: [],
        researchSectionIds: ["competitive_advantage"],
        decisionTraceLinks: ["#competitive_advantage"],
        tab: "business",
        available: m.available,
      }),
    );
    edges.push(edge(`e-moat-${m.id}`, id, companyId, "supports", "Moat support"));
  }

  // Valuation hub
  const valAvail =
    view.valuation.intrinsicValueRange.presence === "available" ||
    view.valuation.summary.presence === "available";
  const valuationId = "kg-valuation";
  nodes.push(
    node({
      id: valuationId,
      label: "Valuation View",
      nodeType: "valuation",
      confidence: confFromAvailable(valAvail, "low"),
      evidenceCount: valAvail ? 1 : 0,
      dataCategory: valAvail ? "estimated" : "unavailable",
      lastUpdated: updated,
      sourceCategory: valAvail ? "estimated_value" : "unavailable",
      description:
        "Valuation presentation — IV / MOS remain Unavailable unless envelope provides them.",
      evidence: valAvail
        ? [
            view.valuation.summary.value ?? "Valuation summary present",
            view.valuation.intrinsicValueRange.value ?? "",
          ].filter(Boolean)
        : ["No intrinsic value / scenarios in envelope"],
      supportingMetrics: ["Intrinsic value range", "Margin of safety"],
      researchSectionIds: ["valuation"],
      decisionTraceLinks: ["#valuation", "#decision_trace"],
      tab: "valuation",
      available: valAvail,
    }),
  );
  edges.push(
    edge("e-val-co", valuationId, companyId, "depends_on", "Values the company"),
    edge("e-val-fin", valuationId, stmtId, "derived_from", "Would use financials"),
  );

  // Research conclusion
  nodes.push(
    node({
      id: conclusionId,
      label: `DSP View: ${conclusionLabel}`,
      nodeType: "research_conclusion",
      confidence: conclusionAvailable
        ? (view.confidenceBreakdown.overall ?? "moderate")
        : "insufficient_evidence",
      evidenceCount:
        view.conclusion.evidence.supportingEvidence.length +
        view.conclusion.evidence.primaryEvidence.length,
      dataCategory: conclusionAvailable ? "ai_interpretation" : "unavailable",
      lastUpdated: updated,
      sourceCategory: conclusionAvailable ? "ai_interpretation" : "unavailable",
      description:
        "Research conclusion mapped from the analyze envelope — not a live LLM answer.",
      evidence: [
        ...view.conclusion.evidence.primaryEvidence,
        ...view.conclusion.evidence.supportingEvidence,
      ].slice(0, 6),
      supportingMetrics: view.dashboard.researchConclusion.value
        ? [String(view.dashboard.researchConclusion.value)]
        : [],
      researchSectionIds: ["research_conclusion", "decision_dashboard"],
      decisionTraceLinks: [
        "#decision_trace",
        "#reasoning_flow",
        "#confidence_breakdown",
        "#research_conclusion",
      ],
      tab: "research",
      available: conclusionAvailable,
    }),
  );
  edges.push(
    edge("e-conc-co", conclusionId, companyId, "explains", "Concludes on company"),
    edge("e-conc-val", conclusionId, valuationId, "depends_on", "Uses valuation context"),
  );

  // Evidence explorer nodes (research tab)
  for (const ev of view.evidenceExplorer.items) {
    const id = `kg-ev-${ev.id}`;
    nodes.push(
      node({
        id,
        label: ev.title,
        nodeType: "evidence",
        confidence:
          ev.group === "unavailable" || ev.confidence.includes("Insufficient")
            ? "insufficient_evidence"
            : "low",
        evidenceCount: 1,
        dataCategory: ev.group,
        lastUpdated: ev.timestamp,
        sourceCategory:
          ev.group === "verified_fact"
            ? "verified_financial_statement"
            : ev.group === "calculated"
              ? "calculated_metric"
              : ev.group === "estimated"
                ? "estimated_value"
                : ev.group === "ai_interpretation"
                  ? "ai_interpretation"
                  : ev.group === "external_consensus"
                    ? "external_consensus"
                    : ev.group === "user_input"
                      ? "user_input"
                      : "unavailable",
        description: ev.detail,
        evidence: [ev.methodology, ev.source],
        supportingMetrics: [],
        researchSectionIds: ["evidence_explorer"],
        decisionTraceLinks: ["#evidence_explorer", "#decision_trace"],
        tab: "research",
        available: ev.group !== "unavailable",
      }),
    );
    edges.push(
      edge(`e-ev-${ev.id}-conc`, id, conclusionId, "supports", "Evidence for conclusion"),
    );
  }

  // Assumptions
  for (const a of view.assumptionExplorer.items) {
    const id = `kg-as-${a.id}`;
    nodes.push(
      node({
        id,
        label: a.statement.slice(0, 72) + (a.statement.length > 72 ? "…" : ""),
        nodeType: "assumption",
        confidence: a.confidence,
        evidenceCount: a.alternativeAssumptions.length,
        dataCategory: a.category,
        lastUpdated: updated,
        sourceCategory: "user_input",
        description: `${a.impact} Sensitivity: ${a.sensitivity}. If wrong: ${a.whatChangesIfWrong}`,
        evidence: a.alternativeAssumptions,
        supportingMetrics: [],
        researchSectionIds: ["assumption_explorer", "ai_challenge"],
        decisionTraceLinks: ["#assumption_explorer", "#decision_trace"],
        tab: "research",
        available: true,
      }),
    );
    edges.push(
      edge(`e-as-${a.id}`, id, conclusionId, "influences", "Assumption under conclusion"),
    );
  }

  // Methodology
  nodes.push(
    node({
      id: methodologyId,
      label: "Research Methodology",
      nodeType: "methodology",
      confidence: "high",
      evidenceCount: 5,
      dataCategory: "calculated",
      lastUpdated: updated,
      sourceCategory: "calculated_metric",
      description: view.methodologyPanel.researchMethodology,
      evidence: [
        view.methodologyPanel.analysisVersion,
        view.methodologyPanel.calculationVersion,
        view.methodologyPanel.presentationVersion,
        view.methodologyPanel.complianceVersion,
      ],
      supportingMetrics: [],
      researchSectionIds: ["methodology_panel"],
      decisionTraceLinks: ["#methodology_panel", "#decision_trace"],
      tab: "research",
      available: true,
    }),
  );
  edges.push(
    edge("e-meth-conc", methodologyId, conclusionId, "explains", "Methodology explains output"),
  );

  // External consensus
  const streetAvail = view.analystConsensus.available;
  nodes.push(
    node({
      id: consensusId,
      label: "External / Street Consensus",
      nodeType: "external_consensus",
      confidence: "insufficient_evidence",
      evidenceCount: 0,
      dataCategory: "unavailable",
      lastUpdated: null,
      sourceCategory: "unavailable",
      description:
        "Street consensus providers are not connected — node reserved for future enrichment.",
      evidence: ["External Consensus Unavailable — no fabricated Street opinion"],
      supportingMetrics: [],
      researchSectionIds: ["analyst_consensus", "dsp_vs_street", "market_intelligence"],
      decisionTraceLinks: ["#analyst_consensus", "#dsp_vs_street"],
      tab: "research",
      available: streetAvail,
    }),
  );
  edges.push(
    edge(
      "e-cons-conc",
      consensusId,
      conclusionId,
      streetAvail ? "related_to" : "conflicts_with",
      streetAvail ? "Street context" : "Missing Street context",
    ),
  );

  // Reasoning flow nodes as explains edges from conclusion
  for (const rn of view.reasoningFlow.nodes) {
    if (rn.id === "conclusion") continue;
    const id = `kg-flow-${rn.id}`;
    nodes.push(
      node({
        id,
        label: `Flow: ${rn.label}`,
        nodeType: "methodology",
        confidence:
          rn.status === "complete"
            ? "moderate"
            : rn.status === "partial"
              ? "low"
              : "insufficient_evidence",
        evidenceCount: rn.details.length,
        dataCategory: rn.status === "unavailable" ? "unavailable" : "calculated",
        lastUpdated: updated,
        sourceCategory: "calculated_metric",
        description: rn.summary,
        evidence: rn.details,
        supportingMetrics: [],
        researchSectionIds: ["reasoning_flow"],
        decisionTraceLinks: ["#reasoning_flow", "#decision_trace"],
        tab: "research",
        available: rn.status !== "unavailable",
      }),
    );
    edges.push(
      edge(`e-flow-${rn.id}`, id, conclusionId, "explains", "Pipeline step toward conclusion"),
    );
  }

  linkRelated(nodes, edges);

  const availableCount = nodes.filter((n) => n.available).length;
  return {
    nodes,
    edges,
    version: "kg-presentation v1 / web-0.4.0",
    emptyState: {
      whyIncomplete:
        availableCount < nodes.length * 0.35
          ? "The graph is a presentation scaffold over a sparse analyze envelope. Many domain nodes stay Unavailable until verified metrics and statements arrive."
          : "Some nodes remain Unavailable — DSP does not invent missing evidence to fill the graph.",
      missingEvidence: [
        ...view.researchLimitations.unavailableData.slice(0, 4),
        "Verified financial statement line items",
        "Street consensus provider payloads",
      ],
      futureEnrichment: [
        "Richer envelope fields will densify edges (supports / derived_from)",
        "Copilot will not invent nodes — it may only narrate this graph later",
        "Export of graph snapshots deferred",
        ...view.researchLimitations.pendingImprovements.slice(0, 2),
      ],
    },
  };
}

/** Empty graph for pre-analyze sessions. */
export function emptyKnowledgeGraph(): KnowledgeGraphView {
  return {
    nodes: [],
    edges: [],
    version: "kg-presentation v1 / web-0.4.0",
    emptyState: {
      whyIncomplete: "Run Analyze via API to materialize the explainable knowledge graph.",
      missingEvidence: ["No envelope loaded", "No company symbol session"],
      futureEnrichment: [
        "Company → metrics → insights → conclusion edges",
        "Evidence and assumption nodes from Sprint 4 explorers",
      ],
    },
  };
}

export type GraphFilterState = {
  query: string;
  confidence: ConfidenceLevel | "all";
  evidenceStrength: "all" | "has_evidence" | "no_evidence";
  nodeType: KgNodeType | "all";
  researchCategory: KnowledgeGraphTab | "all";
  availableOnly: boolean;
  hideUnknown: boolean;
};

export function defaultGraphFilters(): GraphFilterState {
  return {
    query: "",
    confidence: "all",
    evidenceStrength: "all",
    nodeType: "all",
    researchCategory: "all",
    availableOnly: false,
    hideUnknown: false,
  };
}

export function filterGraphNodes(
  nodes: KnowledgeGraphNode[],
  filters: GraphFilterState,
  activeTab: KnowledgeGraphTab | "all",
): KnowledgeGraphNode[] {
  const q = filters.query.trim().toLowerCase();
  return nodes.filter((n) => {
    if (activeTab !== "all" && n.tab !== activeTab) return false;
    if (filters.researchCategory !== "all" && n.tab !== filters.researchCategory) return false;
    if (filters.nodeType !== "all" && n.nodeType !== filters.nodeType) return false;
    if (filters.confidence !== "all" && n.confidence !== filters.confidence) return false;
    if (filters.availableOnly && !n.available) return false;
    if (filters.hideUnknown && (n.dataCategory === "unavailable" || n.dataCategory === "unknown"))
      return false;
    if (filters.evidenceStrength === "has_evidence" && n.evidenceCount <= 0) return false;
    if (filters.evidenceStrength === "no_evidence" && n.evidenceCount > 0) return false;
    if (q && !n.searchText.includes(q)) return false;
    return true;
  });
}

export function edgesForNodes(
  edges: KnowledgeGraphEdge[],
  visibleIds: Set<string>,
): KnowledgeGraphEdge[] {
  return edges.filter((e) => visibleIds.has(e.from) && visibleIds.has(e.to));
}
