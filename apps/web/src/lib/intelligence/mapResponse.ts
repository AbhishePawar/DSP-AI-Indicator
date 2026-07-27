/** Presentation view-models — reflect API payloads only; no scoring. */

import type {
  AnalyseResponse,
  DecisionSummary,
  PipelinePayload,
  StageSummary,
} from "@/lib/api/compositionTypes";

export type IntelligenceView = {
  ok: boolean;
  correlationId: string | null;
  pipelineVersion: string | null;
  platformVersion: string | null;
  recommendation: string;
  recommendationConfidence: number | null;
  marginOfSafety: number | null;
  businessQualityLabel: string;
  businessQualityScore: number | null;
  businessQualityConfidence: number | null;
  committeeDecision: string;
  committeeConfidence: number | null;
  committeeConsensus: string | null;
  stages: StageSummary[];
  evidenceCounts: Record<string, number>;
  confidenceSummary: Record<string, number | null>;
  warnings: string[];
  errors: string[];
  limitations: string[];
  totalElapsedMs: number | null;
  failedStage: string | null;
  packageVersions: Record<string, string>;
  executionOrder: string[];
  strengths: string[];
  weaknesses: string[];
  risks: string[];
  minorityNotes: string[];
};

function text(value: unknown, fallback = "Unavailable"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function num(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function pickDecision(summary: DecisionSummary | null | undefined): string {
  if (!summary) return "Unavailable";
  return text(
    summary.decision ?? summary.action ?? summary.recommendation ?? summary.label,
  );
}

function stageByName(
  stages: StageSummary[],
  name: string,
): StageSummary | undefined {
  return stages.find((s) => s.stage === name);
}

/** Map AnalyseResponse → display model. No calculations. */
export function mapAnalyseResponse(response: AnalyseResponse): IntelligenceView {
  const payload: PipelinePayload = response.payload ?? { ok: false };
  const stages = payload.stage_summaries ?? [];
  const rec = payload.recommendation_summary;
  const committee = payload.committee_summary;
  const bq = stageByName(stages, "business_quality_aggregator");
  const meta = payload.metadata ?? {};
  const warnings = [
    ...(meta.warnings ?? []),
    ...(response.errors ?? []).filter((e) => e.toLowerCase().includes("warn")),
  ];

  const strengths: string[] = [];
  const weaknesses: string[] = [];
  const risks: string[] = [];
  const minorityNotes: string[] = [];

  for (const stage of stages) {
    if (stage.status === "succeeded" && stage.label) {
      strengths.push(`${stage.stage}: ${stage.label}`);
    }
    if (stage.status === "failed" || stage.error) {
      weaknesses.push(`${stage.stage}: ${stage.error || stage.status}`);
    }
    if (stage.warnings?.length) {
      risks.push(...stage.warnings.map((w) => `${stage.stage}: ${w}`));
    }
  }

  if (committee?.rationale) {
    minorityNotes.push(String(committee.rationale));
  }
  if (typeof committee?.consensus === "string" && committee.consensus) {
    minorityNotes.push(`Consensus: ${committee.consensus}`);
  }

  return {
    ok: Boolean(response.ok && payload.ok),
    correlationId: response.correlation_id,
    pipelineVersion: response.pipeline_version ?? meta.pipeline_version ?? null,
    platformVersion: response.platform_version ?? meta.platform_version ?? null,
    recommendation: pickDecision(rec),
    recommendationConfidence: num(rec?.confidence),
    marginOfSafety: num(rec?.margin_of_safety),
    businessQualityLabel: text(bq?.label ?? bq?.decision),
    businessQualityScore: num(bq?.score),
    businessQualityConfidence: num(bq?.confidence),
    committeeDecision: pickDecision(committee),
    committeeConfidence: num(committee?.confidence),
    committeeConsensus:
      committee?.consensus != null ? String(committee.consensus) : null,
    stages,
    evidenceCounts: meta.evidence_counts ?? {},
    confidenceSummary: meta.confidence_summary ?? {},
    warnings: [...new Set(warnings)],
    errors: [
      ...(payload.errors ?? []),
      ...(response.errors ?? []),
    ],
    limitations: [
      ...(payload.limitations ?? []),
      ...(response.limitations ?? []),
    ],
    totalElapsedMs: num(meta.total_elapsed_ms),
    failedStage: meta.failed_stage ?? null,
    packageVersions: meta.package_versions ?? {},
    executionOrder: meta.execution_order ?? stages.map((s) => s.stage),
    strengths,
    weaknesses,
    risks,
    minorityNotes,
  };
}

export function emptyIntelligenceView(): IntelligenceView {
  return {
    ok: false,
    correlationId: null,
    pipelineVersion: null,
    platformVersion: null,
    recommendation: "—",
    recommendationConfidence: null,
    marginOfSafety: null,
    businessQualityLabel: "—",
    businessQualityScore: null,
    businessQualityConfidence: null,
    committeeDecision: "—",
    committeeConfidence: null,
    committeeConsensus: null,
    stages: [],
    evidenceCounts: {},
    confidenceSummary: {},
    warnings: [],
    errors: [],
    limitations: [],
    totalElapsedMs: null,
    failedStage: null,
    packageVersions: {},
    executionOrder: [],
    strengths: [],
    weaknesses: [],
    risks: [],
    minorityNotes: [],
  };
}

export function formatPct(value: number | null): string {
  if (value === null) return "Unavailable";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatMs(value: number | null): string {
  if (value === null) return "Unavailable";
  return `${value.toFixed(1)} ms`;
}

export function formatScore(value: number | null): string {
  if (value === null) return "Unavailable";
  return value.toFixed(2);
}
