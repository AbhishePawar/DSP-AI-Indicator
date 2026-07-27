/** Research coverage & freshness — meta about DSP research completeness, not company quality. */

import type {
  AnalysisWorkspaceView,
  CoverageBucket,
  DisplayField,
  ResearchCoverageView,
  ResearchFreshnessView,
} from "@/lib/analysis/types";
import { isResearchOnly } from "@/lib/featureFlags";

function fieldAvailable(field: DisplayField<unknown>): boolean {
  return field.presence === "available" && field.value != null && field.value !== "";
}

function countFields(fields: DisplayField<unknown>[]): { available: number; total: number } {
  return {
    available: fields.filter(fieldAvailable).length,
    total: fields.length,
  };
}

function bucket(
  id: string,
  label: string,
  available: number,
  total: number,
  forced?: CoverageBucket["status"],
): CoverageBucket {
  const status =
    forced ??
    (available <= 0 ? "unavailable" : available < total ? "pending" : "available");
  return { id, label, status, availableCount: available, totalCount: total };
}

export function buildCoverage(
  view: Omit<AnalysisWorkspaceView, "coverage" | "freshness" | "knowledgeGraph">,
): ResearchCoverageView {
  const business = countFields([
    view.snapshot.industry,
    view.snapshot.sector,
    ...view.businessQuality.map((m) => ({
      presence: m.available ? ("available" as const) : ("unavailable" as const),
      value: m.available ? m.actualValue : null,
      category: m.category,
      source: m.source,
    })),
  ]);

  const financial = countFields(
    view.financialStrength.map((m) => ({
      presence: m.available ? ("available" as const) : ("unavailable" as const),
      value: m.available ? m.actualValue : null,
      category: m.category,
      source: m.source,
    })),
  );

  const valuation = countFields([
    view.valuation.currentPrice,
    view.valuation.intrinsicValueRange,
    view.valuation.marginOfSafety,
    view.valuation.summary,
    view.valuation.bull,
    view.valuation.base,
    view.valuation.bear,
  ]);

  const growthAvail = view.growth.filter((g) => g.available).length;
  const growthTotal = view.growth.length || 1;

  const riskAvail = view.risks.filter((r) => r.available).length;
  const riskTotal = view.risks.length || 1;

  const mgmtAvail = view.management.filter((m) => m.available).length;
  const mgmtTotal = view.management.length || 1;

  const moatAvail = view.moat.filter((m) => m.available).length;
  const moatTotal = view.moat.length || 1;

  const conclusionBits = countFields([
    view.conclusion.conclusion,
    view.conclusion.intrinsicValueRange,
    view.dashboard.researchConclusion,
  ]);

  const breakdown: CoverageBucket[] = [
    bucket("business", "Business", business.available, business.total),
    bucket("financial", "Financial", financial.available, financial.total),
    bucket("valuation", "Valuation", valuation.available, valuation.total),
    bucket("growth", "Growth", growthAvail, growthTotal),
    bucket("risk", "Risk", riskAvail, riskTotal),
    bucket("management", "Management", mgmtAvail, mgmtTotal),
    bucket("moat", "Moat", moatAvail, moatTotal),
    bucket(
      "conclusion",
      "Research Conclusion",
      conclusionBits.available,
      conclusionBits.total,
    ),
  ];

  const futureSections: CoverageBucket[] = [
    bucket("explainability", "Explainability Layer", 1, 1),
    bucket("knowledge_graph", "Knowledge Graph", 1, 1),
    bucket("copilot", "AI Copilot", 1, 1),
    bucket("export", "Reports & Export", 1, 1),
    bucket("saved_workspace", "Saved Workspace", 1, 1),
  ];

  const availableMetrics = breakdown.reduce((s, b) => s + b.availableCount, 0);
  const totalMetrics = breakdown.reduce((s, b) => s + b.totalCount, 0);
  const coveragePercent =
    totalMetrics === 0 ? 0 : Math.round((availableMetrics / totalMetrics) * 100);

  let evidenceStrength = "Insufficient Evidence";
  if (coveragePercent >= 70) evidenceStrength = "Strong";
  else if (coveragePercent >= 40) evidenceStrength = "Moderate";
  else if (coveragePercent >= 15) evidenceStrength = "Limited";

  return {
    coveragePercent,
    evidenceStrength,
    availableMetrics,
    unavailableMetrics: Math.max(totalMetrics - availableMetrics, 0),
    breakdown,
    futureSections,
  };
}

export function buildFreshness(
  view: Omit<AnalysisWorkspaceView, "coverage" | "freshness" | "knowledgeGraph">,
): ResearchFreshnessView {
  return {
    researchDate:
      view.snapshot.researchDate.value ??
      view.conclusion.evidence.lastUpdated ??
      null,
    lastUpdated:
      view.snapshot.lastUpdated.value ??
      view.conclusion.evidence.lastUpdated ??
      null,
    dataCurrency: view.apiOk
      ? "Envelope received — many line items may still be Unavailable"
      : "No successful envelope yet",
    analysisVersion: "web-0.6.0 / L1.2 Sprint 8 Saved Analysis",
    methodologyVersion: "presentation-map v8 (L1.2 Sprint 8)",
    researchMode: isResearchOnly() ? "Research Mode (active)" : "Mixed / SEBI flags",
  };
}
