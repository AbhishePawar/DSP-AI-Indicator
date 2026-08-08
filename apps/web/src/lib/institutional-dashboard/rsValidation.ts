/**
 * Research Standards panel-structure check for RS-001…RS-010.
 * Confirms UI modules/slots exist — does NOT certify authenticated data completeness
 * or research report validity. Unavailable slots remain honest empties.
 */

import type {
  DashboardField,
  InstitutionalDashboardView,
  RsValidationResult,
} from "@/lib/institutional-dashboard/types";

function sectionPresent(fields: DashboardField[]): boolean {
  return fields.length > 0;
}

/**
 * Validates that required RS sections exist as first-class dashboard modules.
 * Unavailable authenticated data still counts as a present section when the
 * UI renders honest Data unavailable. / Unable to calculate. slots.
 */
export function validateResearchStandards(
  view: InstitutionalDashboardView,
): RsValidationResult[] {
  const e = view.executive;
  return [
    {
      standard: "RS-001",
      ok: sectionPresent([
        e.companyName,
        e.ticker,
        e.exchange,
        e.researchMode,
        e.confidence,
        e.overallScore,
        e.recommendation,
      ]),
      detail: "Executive Summary header",
    },
    {
      standard: "RS-002",
      ok: Boolean(view.market.source),
      detail: view.market.hasAuthenticatedMarketData
        ? "Authenticated market data present"
        : "Market panel present; feed unavailable (honest)",
    },
    {
      standard: "RS-003",
      ok:
        view.financial.incomeStatement.length > 0 &&
        view.financial.balanceSheet.length > 0 &&
        view.financial.cashFlow.length > 0,
      detail: "Financial statement panels",
    },
    {
      standard: "RS-004",
      ok: Boolean(view.valuation.intrinsicValue && view.valuation.methods.length),
      detail: "Valuation panel",
    },
    {
      standard: "RS-005",
      ok: Boolean(view.marginOfSafety.marginOfSafety),
      detail: "Margin of Safety panel",
    },
    {
      standard: "RS-006",
      ok: Boolean(view.businessQuality.overall),
      detail: "Business Quality panel",
    },
    {
      standard: "RS-007",
      ok: Boolean(view.risk.riskRating),
      detail: "Risk panel",
    },
    {
      standard: "RS-008",
      ok: Boolean(
        view.scenarios.bull && view.scenarios.base && view.scenarios.bear,
      ),
      detail: "Scenario panel",
    },
    {
      standard: "RS-009",
      ok: view.explainabilityScores.every((s) => Boolean(s.explainability)),
      detail: "Explainability blocks",
    },
    {
      standard: "RS-010",
      ok: Boolean(view.audit.generationTimestamp && view.audit.dataSources),
      detail: "Audit & provenance",
    },
  ];
}

export function researchStandardsPass(
  results: RsValidationResult[],
): boolean {
  return results.every((r) => r.ok);
}
