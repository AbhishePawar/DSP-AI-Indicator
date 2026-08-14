/**
 * P2.1 — Report Transparency mapper.
 * Presentation only — reuses ResearchView / env metadata. Never estimates.
 */

import { env } from "@/lib/env";
import {
  BACKEND_PLATFORM_TARGET,
  FRONTEND_FOUNDATION_VERSION,
} from "@/foundation/version";
import { formatPct } from "@/lib/intelligence/mapResponse";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { buildReportId } from "./reportId";
import type {
  DataFreshnessLabel,
  ReportTransparencyView,
} from "./types";

/** Presentation framework versions (not backend packages). */
export const BUFFETT_FRAMEWORK_VERSION = "1.0.0" as const;
export const INSTITUTIONAL_RATING_FRAMEWORK_VERSION = "1.0.0" as const;

const DISCLAIMER =
  "Report Information is a transparency card over existing analysis metadata. It does not recalculate scores or invent data freshness. Research Mode — not investment advice.";

function display(value: string | null | undefined): string {
  if (value == null || value.trim() === "" || value === "—") return "Unavailable";
  return value;
}

/**
 * Freshness only when an explicit signal exists — never inferred from age.
 */
export function mapDataFreshness(
  marketStatus: string | null | undefined,
): DataFreshnessLabel {
  if (marketStatus == null || marketStatus.trim() === "") return "Unavailable";
  const s = marketStatus.toLowerCase();
  if (s.includes("delay") || s.includes("stale")) return "Delayed";
  if (
    s.includes("latest") ||
    s.includes("live") ||
    s.includes("real-time") ||
    s.includes("realtime")
  ) {
    return "Latest Available";
  }
  return "Unavailable";
}

export function mapReportTransparency(
  view: Omit<ResearchView, "transparency" | "explainability" | "valuationTransparency">,
  options?: { marketStatus?: string | null },
): ReportTransparencyView {
  const frontend = env.frontendVersion || FRONTEND_FOUNDATION_VERSION;
  const backend = display(view.platformVersion) !== "Unavailable"
    ? display(view.platformVersion)
    : BACKEND_PLATFORM_TARGET.replace("dsp_platform@", "") || "Unavailable";

  const recommendationEngineVersion =
    view.packageVersions?.investment_recommendation ??
    view.packageVersions?.["investment_recommendation"] ??
    "Unavailable";

  const confidence =
    view.recommendationConfidence != null
      ? formatPct(view.recommendationConfidence)
      : display(view.ratings?.overall?.confidence);

  return {
    kind: "report_transparency",
    analysisDate: display(view.analysedAt),
    analysisVersions: {
      frontend,
      backend,
      buffettFramework: BUFFETT_FRAMEWORK_VERSION,
      institutionalRatingFramework: INSTITUTIONAL_RATING_FRAMEWORK_VERSION,
    },
    reportId: buildReportId({
      ticker: view.ticker,
      exchange: view.exchange,
      analysedAt: view.analysedAt,
      correlationId: view.correlationId,
      pipelineVersion: view.pipelineVersion,
      platformVersion: view.platformVersion,
      frontendVersion: frontend,
    }),
    company: {
      name: display(view.company),
      exchange: display(view.exchange),
      symbol: display(view.ticker),
    },
    dataInformation: {
      primaryDataSource: "Frozen /api/v1/analyse (composition pipeline)",
      financialPeriodUsed: "Unavailable",
      latestAvailableDataDate: display(view.analysedAt),
      dataFreshness: mapDataFreshness(options?.marketStatus),
    },
    confidence,
    transparency: {
      analysisType: "Institutional Research Report",
      methodology: "Deterministic Multi-Stage Analysis",
      pipelineVersion: display(view.pipelineVersion),
      recommendationEngineVersion: display(recommendationEngineVersion),
    },
    qualityBadges: [
      { id: "deterministic", label: "Deterministic Analysis" },
      { id: "evidence", label: "Evidence Based" },
      { id: "no-hallucination", label: "No AI Hallucinated Financials" },
      { id: "existing-data", label: "Existing Financial Data Used" },
      { id: "missing-marked", label: "Missing Data Explicitly Marked" },
      { id: "institutional", label: "Institutional Rating Framework" },
    ],
    disclaimer: DISCLAIMER,
  };
}
