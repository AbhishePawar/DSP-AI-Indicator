/** Map API analyze envelope → workspace view. Presentation only — no math. */

import { buildCoverage, buildFreshness } from "@/lib/analysis/coverage";
import {
  BUSINESS_QUALITY_METRICS,
  FINANCIAL_STRENGTH_METRICS,
  type MetricTemplate,
} from "@/lib/analysis/metricCatalog";
import {
  buildAiChallenge,
  buildAnalystConsensus,
  buildConfidenceMatrix,
  buildMarketIntelligence,
  buildResearchTimeline,
  buildStreetComparison,
} from "@/lib/analysis/sprint3Market";
import {
  buildAssumptionExplorer,
  buildConfidenceBreakdown,
  buildDecisionTrace,
  buildEvidenceExplorer,
  buildMethodologyPanel,
  buildReasoningFlow,
  buildResearchLimitations,
  buildTransparencyPanel,
} from "@/lib/analysis/sprint4Explainability";
import {
  buildKnowledgeGraph,
} from "@/lib/analysis/sprint5KnowledgeGraph";
import {
  GROWTH_METRICS,
  MANAGEMENT_METRICS,
  MOAT_METRICS,
  RISK_CATEGORIES,
} from "@/lib/analysis/sprint2Catalog";
import type {
  AnalysisWorkspaceView,
  CompanySnapshotView,
  DecisionDashboardView,
  DisplayField,
  EvidenceView,
  ExecutiveSummaryView,
  GrowthInsightView,
  InvestmentThesisView,
  ManagementInsightView,
  MetricView,
  MoatInsightView,
  ResearchConclusionView,
  RiskInsightView,
  ValuationView,
} from "@/lib/analysis/types";
import type { ApiResponse, AnalyzeCompanyPayload } from "@/lib/api/types";
import { presentAction, presentFieldLabel } from "@/lib/terminology";
import type { ConfidenceLevel, SourceKind, ValueCategory } from "@/lib/trust/labels";

function unavailable<T = string>(fallback: T | null = null): DisplayField<T> {
  return {
    presence: "unavailable",
    value: fallback,
    category: "unavailable",
    source: "unavailable",
  };
}

function available<T = string>(
  value: T,
  category: ValueCategory,
  source: SourceKind,
): DisplayField<T> {
  return { presence: "available", value, category, source };
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

function pickString(...candidates: unknown[]): string | null {
  for (const c of candidates) {
    if (typeof c === "string" && c.trim()) return c.trim();
    if (typeof c === "number" && Number.isFinite(c)) return String(c);
  }
  return null;
}

function nestedInstrument(result: Record<string, unknown>): Record<string, unknown> {
  return asRecord(result.instrument) ?? {};
}

function parseResultBlob(raw: unknown): {
  dict: Record<string, unknown>;
  text: string | null;
} {
  if (typeof raw === "string") {
    const actionMatch =
      raw.match(/action[=:][\s<]*RecommendationAction\.([A-Z_]+)/i) ??
      raw.match(/action[=:][\s']*([a-z_]+)/i);
    const rationaleMatch = raw.match(/rationale[=:][\s]*['"]([^'"]+)['"]/i);
    const convictionMatch = raw.match(/conviction[=:][\s]*([0-9.]+)/i);
    const symbolMatch = raw.match(/symbol[=:][\s]*['"]([A-Z0-9.]+)['"]/i);
    const dict: Record<string, unknown> = {};
    if (actionMatch?.[1]) dict.action = actionMatch[1].toLowerCase();
    if (rationaleMatch?.[1]) dict.rationale = rationaleMatch[1];
    if (convictionMatch?.[1]) dict.conviction = Number(convictionMatch[1]);
    if (symbolMatch?.[1]) dict.instrument = { symbol: symbolMatch[1] };
    return { dict, text: raw };
  }
  return { dict: asRecord(raw) ?? {}, text: null };
}

function convictionToConfidence(conviction: unknown): ConfidenceLevel {
  const n = typeof conviction === "number" ? conviction : Number(conviction);
  if (!Number.isFinite(n)) return "insufficient_evidence";
  if (n >= 0.85) return "very_high";
  if (n >= 0.7) return "high";
  if (n >= 0.5) return "moderate";
  if (n > 0) return "low";
  return "insufficient_evidence";
}

function metricFromTemplate(template: MetricTemplate): MetricView {
  return {
    id: template.id,
    title: template.title,
    rating: "Unavailable",
    actualValue: "Unavailable",
    meaning: template.meaning,
    whyItMatters: template.whyItMatters,
    investorTakeaway: template.investorTakeawayWhenMissing,
    learnMore: template.learnMore,
    aiPrompts: template.aiPrompts,
    category: "unavailable",
    source: "unavailable",
    available: false,
  };
}

function buildEvidence(args: {
  primary?: string[];
  supporting?: string[];
  contradicting?: string[];
  source: string;
  methodology: string;
  lastUpdated: string | null;
  confidence?: string | null;
  aiReasoning?: string | null;
  aiExplanation?: string | null;
  limitations?: string[];
}): EvidenceView {
  const supporting = args.supporting ?? [];
  return {
    primaryEvidence: args.primary ?? [],
    supportingMetrics: supporting,
    supportingEvidence: supporting,
    contradictingEvidence: args.contradicting ?? [],
    source: args.source,
    methodology: args.methodology,
    confidence: args.confidence ?? null,
    aiReasoning: args.aiReasoning ?? null,
    aiExplanation: args.aiExplanation ?? null,
    limitations: args.limitations ?? [],
    lastUpdated: args.lastUpdated,
  };
}

function emptyInsightEvidence(topic: string): EvidenceView {
  return buildEvidence({
    primary: [],
    supporting: [],
    source: "Not present in /analyze/company envelope",
    methodology: `Educational template for ${topic}. Values are Unavailable until calculated or verified fields arrive.`,
    lastUpdated: null,
    confidence: "Insufficient Evidence",
    aiReasoning: null,
    aiExplanation: "AI reasoning deferred — Copilot / Challenge arrive in later sprints.",
    limitations: [
      "Thin client will not invent figures",
      "Wire fundamentals/research artifacts to populate this insight",
    ],
  });
}

function buildGrowthInsights(): GrowthInsightView[] {
  return GROWTH_METRICS.map((t) => ({
    id: t.id,
    title: t.title,
    rating: "Unavailable",
    meaning: t.meaning,
    whyItMatters: t.whyItMatters,
    investorTakeaway: t.investorTakeaway,
    aiExplanation: t.aiExplanation,
    learnMore: t.learnMore,
    evidence: emptyInsightEvidence(t.title),
    category: "unavailable" as const,
    source: "unavailable" as const,
    available: false,
  }));
}

function buildRiskInsights(): RiskInsightView[] {
  return RISK_CATEGORIES.map((t) => ({
    id: t.id,
    title: t.title,
    severity: "Unavailable",
    probability: "Unavailable",
    impact: "Unavailable",
    reason: t.reason,
    supportingEvidence: [],
    mitigation: t.mitigation,
    investorWatchpoints: t.watchpoints,
    category: "unavailable" as const,
    source: "unavailable" as const,
    available: false,
  }));
}

function buildManagementInsights(): ManagementInsightView[] {
  return MANAGEMENT_METRICS.map((t) => ({
    id: t.id,
    title: t.title,
    meaning: t.meaning,
    importance: t.importance,
    evidence: "Unavailable — no management artifacts in envelope",
    aiInterpretation: t.aiInterpretation,
    confidence: "insufficient_evidence" as const,
    learnMore: t.learnMore,
    category: "unavailable" as const,
    source: "unavailable" as const,
    available: false,
  }));
}

function buildMoatInsights(): MoatInsightView[] {
  return MOAT_METRICS.map((t) => ({
    id: t.id,
    title: t.title,
    rating: "Unavailable",
    meaning: t.meaning,
    evidence: "Unavailable — moat evidence not in envelope",
    investorTakeaway: t.investorTakeaway,
    learnMore: t.learnMore,
    category: "unavailable" as const,
    source: "unavailable" as const,
    available: false,
  }));
}

function paragraphsFromRationale(rationale: string, symbol: string): string[] {
  const base = rationale.trim();
  return [
    `Business — ${symbol}: research artifacts describe the company context available from the backend envelope. ${base}`,
    `Current situation — The API returned a research posture for this request. Details beyond the envelope are marked Unavailable rather than invented.`,
    `Financial position — Line-item fundamentals are not fully projected. Treat financial metric cards as educational until calculated values arrive.`,
    `Valuation — ${presentFieldLabel("target_price")} and scenario bands remain Unavailable unless present. No Official Target Price in Research Mode.`,
    `Growth, risk, management, and moat — Sprint 2 sections teach what to investigate; ratings stay Unavailable without evidence.`,
  ];
}

function finalize(
  partial: Omit<AnalysisWorkspaceView, "coverage" | "freshness" | "knowledgeGraph">,
): AnalysisWorkspaceView {
  return {
    ...partial,
    coverage: buildCoverage(partial),
    freshness: buildFreshness(partial),
    knowledgeGraph: buildKnowledgeGraph(partial),
  };
}

const CONFIDENCE_DISPLAY: Record<ConfidenceLevel, string> = {
  very_high: "Very High",
  high: "High",
  moderate: "Moderate",
  low: "Low",
  insufficient_evidence: "Insufficient Evidence",
};

export function mapAnalyzeResponse(
  response: ApiResponse<AnalyzeCompanyPayload>,
  userSymbol: string,
): AnalysisWorkspaceView {
  const payload = response.payload;
  const reportId = payload?.report_id ?? null;
  const { dict, text } = parseResultBlob(payload?.result);
  const instrument = nestedInstrument(dict);

  const symbol =
    pickString(instrument.symbol, dict.symbol, userSymbol)?.toUpperCase() ??
    userSymbol.toUpperCase();
  const actionRaw = pickString(dict.action, dict.decision, dict.posture);
  const conclusionLabel = actionRaw
    ? presentAction(actionRaw)
    : response.ok
      ? "Unclassified"
      : "Insufficient Evidence";

  const rationale = pickString(dict.rationale, dict.summary, dict.brief) ?? null;
  const conviction = dict.conviction;
  const confidence = convictionToConfidence(conviction);
  const generatedAt = pickString(dict.generated_at, dict.as_of, dict.timestamp);
  const companyName = pickString(instrument.name, dict.name, symbol);
  const industry = pickString(instrument.industry, dict.industry);
  const sector = pickString(instrument.sector, dict.sector);
  const exchange = pickString(instrument.exchange, dict.exchange);
  const horizon = pickString(dict.time_horizon, dict.horizon);
  const targetPrice = pickString(dict.target_price);
  const margin = pickString(dict.margin_of_safety);
  const valuationSummary = pickString(dict.valuation_summary);

  const snapshot: CompanySnapshotView = {
    companyName: companyName
      ? available(
          companyName,
          companyName === symbol ? "user_input" : "unknown",
          companyName === symbol ? "user_input" : "unavailable",
        )
      : unavailable(),
    ticker: available(symbol, "user_input", "user_input"),
    industry: industry
      ? available(industry, "verified_fact", "verified_financial_statement")
      : unavailable(),
    sector: sector
      ? available(sector, "verified_fact", "verified_financial_statement")
      : unavailable(),
    exchange: exchange
      ? available(exchange, "verified_fact", "verified_financial_statement")
      : unavailable(),
    currentMarketPrice: unavailable(),
    lastUpdated: generatedAt
      ? available(generatedAt, "calculated", "calculated_metric")
      : available(new Date().toISOString(), "user_input", "user_input"),
    marketCap: unavailable(),
    week52High: unavailable(),
    week52Low: unavailable(),
    researchStatus: available(
      response.ok ? "Complete (envelope)" : "Partial / failed",
      "calculated",
      "calculated_metric",
    ),
    researchDate: generatedAt
      ? available(generatedAt, "calculated", "calculated_metric")
      : unavailable(),
  };

  if (snapshot.companyName.presence === "unavailable") {
    snapshot.companyName = available(symbol, "user_input", "user_input");
  }

  const evidence = buildEvidence({
    primary: actionRaw
      ? [`Engine action token: ${actionRaw} → ${conclusionLabel}`]
      : ["No action token in envelope"],
    supporting: rationale ? ["Rationale text present in envelope"] : [],
    source: "POST /api/v1/analyze/company envelope",
    methodology:
      "Thin-client presentation. Action tokens mapped via Research Mode terminology. No browser valuation.",
    lastUpdated: generatedAt,
    confidence: CONFIDENCE_DISPLAY[confidence],
    aiReasoning: null,
    aiExplanation: null,
    limitations: response.limitations ?? [],
  });

  const conclusion: ResearchConclusionView = {
    conclusion: available(conclusionLabel, "calculated", "calculated_metric"),
    intrinsicValueRange: targetPrice
      ? available(String(targetPrice), "estimated", "estimated_value")
      : unavailable(),
    marginOfSafety: margin
      ? available(margin, "estimated", "estimated_value")
      : unavailable(),
    researchHealth: available(
      response.ok ? "Envelope received" : "Errors in envelope",
      "calculated",
      "calculated_metric",
    ),
    researchConfidence: available(confidence, "calculated", "calculated_metric"),
    investmentHorizon: horizon
      ? available(horizon, "unknown", "unavailable")
      : unavailable(),
    suitableInvestor: unavailable(),
    primaryOpportunity: rationale
      ? available(
          "See rationale in Executive Summary — confirm with filings.",
          "ai_interpretation",
          "ai_interpretation",
        )
      : unavailable(),
    primaryRisk: available(
      response.errors?.[0] ??
        "Review Risk Analysis categories and confirm with filings.",
      response.errors?.length ? "calculated" : "unknown",
      response.errors?.length ? "calculated_metric" : "unavailable",
    ),
    evidence,
  };

  const executiveSummary: ExecutiveSummaryView = rationale
    ? {
        paragraphs: paragraphsFromRationale(rationale, symbol),
        available: true,
        category: "calculated",
        source: "calculated_metric",
      }
    : {
        paragraphs: [],
        available: false,
        category: "unavailable",
        source: "unavailable",
      };

  const thesis: InvestmentThesisView = {
    whyAttention: rationale
      ? available(rationale, "calculated", "calculated_metric")
      : unavailable(),
    keyStrengths: unavailable([]),
    keyConcerns: response.errors?.length
      ? available(response.errors.slice(0, 5), "calculated", "calculated_metric")
      : unavailable([]),
    longTermThesis: rationale
      ? available(
          `Long-term understanding should start from: ${rationale}`,
          "calculated",
          "calculated_metric",
        )
      : unavailable(),
    thingsToMonitor: available(
      [
        "Growth sustainability signals",
        "Top risk watchpoints",
        "Capital allocation evidence",
        "Moat durability hypotheses",
      ],
      "user_input",
      "user_input",
    ),
  };

  const valuation: ValuationView = {
    currentPrice: unavailable(),
    intrinsicValueRange: conclusion.intrinsicValueRange,
    marginOfSafety: conclusion.marginOfSafety,
    summary: valuationSummary
      ? available(valuationSummary, "estimated", "estimated_value")
      : unavailable(),
    bull: unavailable(),
    base: unavailable(),
    bear: unavailable(),
  };

  const dashboard: DecisionDashboardView = {
    researchConclusion: conclusion.conclusion,
    businessScore: unavailable(),
    financialScore: unavailable(),
    valuationScore: unavailable(),
    riskScore: unavailable(),
    managementScore: unavailable(),
    growthScore: unavailable(),
    researchConfidence: available(
      CONFIDENCE_DISPLAY[confidence],
      "calculated",
      "calculated_metric",
    ),
    topOpportunity: conclusion.primaryOpportunity,
    biggestRisk: conclusion.primaryRisk,
    nextInvestigation: available(
      "Challenge assumptions · Wait for Street data · Re-check filings vs DSP View",
      "user_input",
      "user_input",
    ),
  };

  const growth = buildGrowthInsights();
  const risks = buildRiskInsights();
  const management = buildManagementInsights();
  const moat = buildMoatInsights();

  const streetComparison = buildStreetComparison({
    dspConclusion: conclusionLabel,
    dspConfidence: CONFIDENCE_DISPLAY[confidence],
  });

  const partial = {
    reportId,
    apiOk: Boolean(response.ok),
    limitations: response.limitations ?? [],
    errors: response.errors ?? [],
    capability: response.capability ?? null,
    platformVersion: response.platform_version,
    rawResult: payload?.result ?? text,
    snapshot,
    conclusion,
    executiveSummary,
    thesis,
    businessQuality: BUSINESS_QUALITY_METRICS.map(metricFromTemplate),
    financialStrength: FINANCIAL_STRENGTH_METRICS.map(metricFromTemplate),
    valuation,
    growth,
    risks,
    management,
    moat,
    marketIntelligence: buildMarketIntelligence({
      coveragePercent: 0,
      lastUpdated: generatedAt,
    }),
    analystConsensus: buildAnalystConsensus(),
    streetComparison,
    aiChallenge: buildAiChallenge({
      conclusionLabel,
      rationale,
      errors: response.errors ?? [],
      confidence,
    }),
    confidenceMatrix: buildConfidenceMatrix({
      overall: confidence,
      hasConclusion: Boolean(actionRaw || rationale),
    }),
    researchTimeline: buildResearchTimeline({
      researchDate: snapshot.researchDate.value,
      lastUpdated: snapshot.lastUpdated.value,
      methodologyVersion: "presentation-map v5 (L1.2 Sprint 5)",
    }),
    decisionTrace: buildDecisionTrace({
      conclusionLabel,
      rationale,
      confidence,
      errors: response.errors ?? [],
      limitations: response.limitations ?? [],
      coveragePercent: 0,
    }),
    evidenceExplorer: buildEvidenceExplorer({
      conclusionLabel,
      rationale,
      lastUpdated: generatedAt,
      coveragePercent: 0,
      errors: response.errors ?? [],
    }),
    assumptionExplorer: buildAssumptionExplorer({
      hasConclusion: Boolean(conclusionLabel),
    }),
    reasoningFlow: buildReasoningFlow({
      hasConclusion: Boolean(conclusionLabel),
      coveragePercent: 0,
      hasRationale: Boolean(rationale),
    }),
    confidenceBreakdown: buildConfidenceBreakdown({
      overall: confidence,
      hasConclusion: Boolean(conclusionLabel),
      coveragePercent: 0,
    }),
    researchLimitations: buildResearchLimitations({
      apiLimitations: response.limitations ?? [],
      errors: response.errors ?? [],
    }),
    methodologyPanel: buildMethodologyPanel({
      platformVersion: response.platform_version,
    }),
    transparencyPanel: buildTransparencyPanel({
      hasConclusion: Boolean(conclusionLabel),
      coveragePercent: 0,
    }),
    dashboard,
  };

  const withCoverageSeed = finalize(partial);
  const cov = withCoverageSeed.coverage.coveragePercent;
  // Re-stamp market intelligence note with computed coverage %
  withCoverageSeed.marketIntelligence = buildMarketIntelligence({
    coveragePercent: cov,
    lastUpdated: generatedAt,
  });
  withCoverageSeed.decisionTrace = buildDecisionTrace({
    conclusionLabel,
    rationale,
    confidence,
    errors: response.errors ?? [],
    limitations: response.limitations ?? [],
    coveragePercent: cov,
  });
  withCoverageSeed.evidenceExplorer = buildEvidenceExplorer({
    conclusionLabel,
    rationale,
    lastUpdated: generatedAt,
    coveragePercent: cov,
    errors: response.errors ?? [],
  });
  withCoverageSeed.reasoningFlow = buildReasoningFlow({
    hasConclusion: Boolean(conclusionLabel),
    coveragePercent: cov,
    hasRationale: Boolean(rationale),
  });
  withCoverageSeed.confidenceBreakdown = buildConfidenceBreakdown({
    overall: confidence,
    hasConclusion: Boolean(conclusionLabel),
    coveragePercent: cov,
  });
  withCoverageSeed.transparencyPanel = buildTransparencyPanel({
    hasConclusion: Boolean(conclusionLabel),
    coveragePercent: cov,
  });
  withCoverageSeed.freshness = {
    ...withCoverageSeed.freshness,
    analysisVersion: "web-0.6.0 / L1.2 Sprint 8 Saved Analysis",
    methodologyVersion: "presentation-map v8 (L1.2 Sprint 8)",
  };
  // Rebuild graph after coverage re-stamps so evidence nodes reflect final coverage %
  withCoverageSeed.knowledgeGraph = buildKnowledgeGraph(withCoverageSeed);
  return withCoverageSeed;
}

export function emptyWorkspace(symbol: string): AnalysisWorkspaceView {
  const snapTicker = available(symbol.toUpperCase(), "user_input", "user_input");
  return finalize({
    reportId: null,
    apiOk: false,
    limitations: [],
    errors: [],
    capability: null,
    platformVersion: null,
    rawResult: null,
    snapshot: {
      companyName: snapTicker,
      ticker: snapTicker,
      industry: unavailable(),
      sector: unavailable(),
      exchange: unavailable(),
      currentMarketPrice: unavailable(),
      lastUpdated: unavailable(),
      marketCap: unavailable(),
      week52High: unavailable(),
      week52Low: unavailable(),
      researchStatus: available("Not started", "user_input", "user_input"),
      researchDate: unavailable(),
    },
    conclusion: {
      conclusion: unavailable(),
      intrinsicValueRange: unavailable(),
      marginOfSafety: unavailable(),
      researchHealth: unavailable(),
      researchConfidence: unavailable(),
      investmentHorizon: unavailable(),
      suitableInvestor: unavailable(),
      primaryOpportunity: unavailable(),
      primaryRisk: unavailable(),
      evidence: buildEvidence({
        supporting: [],
        source: "—",
        methodology: "Run Analyze via API to load an envelope.",
        lastUpdated: null,
        aiExplanation: null,
      }),
    },
    executiveSummary: {
      paragraphs: [],
      available: false,
      category: "unavailable",
      source: "unavailable",
    },
    thesis: {
      whyAttention: unavailable(),
      keyStrengths: unavailable([]),
      keyConcerns: unavailable([]),
      longTermThesis: unavailable(),
      thingsToMonitor: unavailable([]),
    },
    businessQuality: BUSINESS_QUALITY_METRICS.map(metricFromTemplate),
    financialStrength: FINANCIAL_STRENGTH_METRICS.map(metricFromTemplate),
    valuation: {
      currentPrice: unavailable(),
      intrinsicValueRange: unavailable(),
      marginOfSafety: unavailable(),
      summary: unavailable(),
      bull: unavailable(),
      base: unavailable(),
      bear: unavailable(),
    },
    growth: buildGrowthInsights(),
    risks: buildRiskInsights(),
    management: buildManagementInsights(),
    moat: buildMoatInsights(),
    marketIntelligence: buildMarketIntelligence({
      coveragePercent: 0,
      lastUpdated: null,
    }),
    analystConsensus: buildAnalystConsensus(),
    streetComparison: buildStreetComparison({
      dspConclusion: null,
      dspConfidence: null,
    }),
    aiChallenge: buildAiChallenge({
      conclusionLabel: null,
      rationale: null,
      errors: [],
      confidence: "insufficient_evidence",
    }),
    confidenceMatrix: buildConfidenceMatrix({
      overall: "insufficient_evidence",
      hasConclusion: false,
    }),
    researchTimeline: buildResearchTimeline({
      researchDate: null,
      lastUpdated: null,
      methodologyVersion: "presentation-map v5 (L1.2 Sprint 5)",
    }),
    decisionTrace: buildDecisionTrace({
      conclusionLabel: null,
      rationale: null,
      confidence: "insufficient_evidence",
      errors: [],
      limitations: [],
      coveragePercent: 0,
    }),
    evidenceExplorer: buildEvidenceExplorer({
      conclusionLabel: null,
      rationale: null,
      lastUpdated: null,
      coveragePercent: 0,
      errors: [],
    }),
    assumptionExplorer: buildAssumptionExplorer({ hasConclusion: false }),
    reasoningFlow: buildReasoningFlow({
      hasConclusion: false,
      coveragePercent: 0,
      hasRationale: false,
    }),
    confidenceBreakdown: buildConfidenceBreakdown({
      overall: "insufficient_evidence",
      hasConclusion: false,
      coveragePercent: 0,
    }),
    researchLimitations: buildResearchLimitations({
      apiLimitations: [],
      errors: [],
    }),
    methodologyPanel: buildMethodologyPanel({ platformVersion: null }),
    transparencyPanel: buildTransparencyPanel({
      hasConclusion: false,
      coveragePercent: 0,
    }),
    dashboard: {
      researchConclusion: unavailable(),
      businessScore: unavailable(),
      financialScore: unavailable(),
      valuationScore: unavailable(),
      riskScore: unavailable(),
      managementScore: unavailable(),
      growthScore: unavailable(),
      researchConfidence: unavailable(),
      topOpportunity: unavailable(),
      biggestRisk: unavailable(),
      nextInvestigation: available(
        "Enter a symbol and run Analyze via API",
        "user_input",
        "user_input",
      ),
    },
  });
}
