/** Pipeline stage presentation helpers — map API stages to terminal labels. */

import type { StageSummary } from "@/lib/api/compositionTypes";

export type PipelineUiStatus = "Pending" | "Running" | "Completed" | "Failed";

export type PipelineStageView = {
  id: string;
  label: string;
  apiStage: string;
  status: PipelineUiStatus;
};

export const PIPELINE_STAGE_DEFS = [
  { id: "financial", label: "Financial Analysis", apiStage: "financial" },
  { id: "valuation", label: "Valuation", apiStage: "valuation" },
  { id: "economic_moat", label: "Economic Moat", apiStage: "economic_moat" },
  {
    id: "management_quality",
    label: "Management Quality",
    apiStage: "management_quality",
  },
  {
    id: "financial_strength",
    label: "Financial Strength",
    apiStage: "financial_strength",
  },
  {
    id: "earnings_quality",
    label: "Earnings Quality",
    apiStage: "earnings_quality",
  },
  {
    id: "growth_quality",
    label: "Growth Quality",
    apiStage: "growth_quality",
  },
  {
    id: "investment_recommendation",
    label: "Recommendation",
    apiStage: "investment_recommendation",
  },
  {
    id: "investment_committee",
    label: "Committee",
    apiStage: "investment_committee",
  },
] as const;

function mapApiStatus(status: string | undefined): PipelineUiStatus {
  const s = (status ?? "").toLowerCase();
  if (s === "succeeded" || s === "completed" || s === "ok") return "Completed";
  if (s === "failed" || s === "error") return "Failed";
  if (s === "running" || s === "in_progress") return "Running";
  return "Pending";
}

/** Build visual pipeline rows from API stage summaries + run state. */
export function buildPipelineStages(
  stages: StageSummary[],
  options?: { running?: boolean; failed?: boolean },
): PipelineStageView[] {
  const byName = new Map(stages.map((stage) => [stage.stage, stage]));
  const running = Boolean(options?.running);
  const failed = Boolean(options?.failed);

  return PIPELINE_STAGE_DEFS.map((def, index) => {
    const api = byName.get(def.apiStage);
    if (api) {
      return {
        id: def.id,
        label: def.label,
        apiStage: def.apiStage,
        status: mapApiStatus(api.status),
      };
    }

    if (running && index === 0) {
      return {
        id: def.id,
        label: def.label,
        apiStage: def.apiStage,
        status: "Running" as const,
      };
    }

    if (failed && stages.length === 0 && index === 0) {
      return {
        id: def.id,
        label: def.label,
        apiStage: def.apiStage,
        status: "Failed" as const,
      };
    }

    return {
      id: def.id,
      label: def.label,
      apiStage: def.apiStage,
      status: "Pending" as const,
    };
  });
}
