/**
 * P2.2 — Map ModuleRating → explainability (no recalculation).
 */

import type { ModuleRating } from "@/lib/institutional-rating";
import type {
  InstitutionalExplainabilityFramework,
  ModuleExplainability,
  TraceableMetric,
} from "./types";

export const EXPLAINABILITY_FRAMEWORK_VERSION = "1.0.0" as const;

const DISCLAIMER =
  "Explainability expands existing institutional rating fields only. Metrics are attributed to prior stage/report sources. Missing values stay Unavailable — never estimated.";

const MAX_EXPLANATION_WORDS = 120;

export function truncateWords(text: string, maxWords: number): string {
  const words = text.trim().split(/\s+/).filter(Boolean);
  if (words.length <= maxWords) return text.trim();
  return `${words.slice(0, maxWords).join(" ")}…`;
}

export function oneLineSummaryFromModule(module: ModuleRating): string {
  const raw = module.explanation.trim();
  if (!raw || /^unavailable$/i.test(raw) || /^data unavailable\.?$/i.test(raw)) {
    return "Unavailable";
  }
  const firstSentence = raw.split(/(?<=[.!?])\s+/)[0] ?? raw;
  return truncateWords(firstSentence, 28);
}

export function mapModuleExplainability(module: ModuleRating): ModuleExplainability {
  const evidence: TraceableMetric[] = module.dimensions.map((d) => ({
    label: d.label,
    value: d.value,
    sourceField: d.evidence,
  }));

  // Fall back to evidence strings when dimensions empty
  if (evidence.length === 0) {
    for (const line of module.evidence.slice(0, 12)) {
      evidence.push({
        label: "Evidence",
        value: line,
        sourceField: module.sourceStages.join(", ") || "stage_summaries",
      });
    }
  }

  if (evidence.length === 0) {
    evidence.push({
      label: "Evidence",
      value: "Unavailable",
      sourceField: "none",
    });
  }

  const traceability: TraceableMetric[] = [
    ...evidence,
    ...module.sourceStages.map((s) => ({
      label: "Source stage",
      value: s,
      sourceField: "sourceStages",
    })),
  ];

  return {
    moduleId: module.id,
    title: module.title,
    scoreOutOf10: module.scoreOutOf10,
    grade: module.grade,
    confidence: module.confidence,
    oneLineSummary: oneLineSummaryFromModule(module),
    evidence,
    strengths:
      module.strengths.length > 0 ? module.strengths : ["Unavailable"],
    weaknesses:
      module.weaknesses.length > 0 ? module.weaknesses : ["Unavailable"],
    explanation: truncateWords(module.explanation, MAX_EXPLANATION_WORDS),
    traceability,
  };
}

export function mapInstitutionalExplainability(modules: {
  financialStrength: ModuleRating;
  valuation: ModuleRating;
  economicMoat: ModuleRating;
  managementQuality: ModuleRating;
  earningsQuality: ModuleRating;
  financialFortress: ModuleRating;
  capitalAllocation: ModuleRating;
  riskAssessment: ModuleRating;
  aiCommittee: ModuleRating;
  buffettIndicator: ModuleRating;
}): InstitutionalExplainabilityFramework {
  const list = [
    modules.financialStrength,
    modules.valuation,
    modules.economicMoat,
    modules.managementQuality,
    modules.earningsQuality,
    modules.financialFortress,
    modules.capitalAllocation,
    modules.riskAssessment,
    modules.aiCommittee,
    modules.buffettIndicator,
  ];

  return {
    kind: "institutional_explainability_framework",
    version: EXPLAINABILITY_FRAMEWORK_VERSION,
    disclaimer: DISCLAIMER,
    modules: list.map(mapModuleExplainability),
  };
}
