export const ANALYSIS_INTENTS = {
  company: "company",
  dspIndicator: "dsp_indicator",
} as const;

export type AnalysisIntent = (typeof ANALYSIS_INTENTS)[keyof typeof ANALYSIS_INTENTS];

export type ResearchMode = "simple" | "full";

export function parseAnalysisIntent(value: string | null): AnalysisIntent {
  return value === ANALYSIS_INTENTS.dspIndicator
    ? ANALYSIS_INTENTS.dspIndicator
    : ANALYSIS_INTENTS.company;
}

export function parseResearchMode(
  mode: string | null | undefined,
  intent?: string | null | undefined,
): ResearchMode {
  if (mode === "simple") return "simple";
  if (mode === "full") return "full";
  if (intent === ANALYSIS_INTENTS.company) return "simple";
  if (intent === ANALYSIS_INTENTS.dspIndicator) return "full";
  return "full";
}

export function getIntentForMode(mode: ResearchMode): AnalysisIntent {
  return mode === "full" ? ANALYSIS_INTENTS.dspIndicator : ANALYSIS_INTENTS.company;
}

export function buildAnalysisUrl({
  symbol,
  mode,
  intent,
}: {
  symbol?: string | null;
  mode: ResearchMode;
  intent?: AnalysisIntent;
}): string {
  const resolvedIntent = intent || getIntentForMode(mode);
  const params = new URLSearchParams();
  if (symbol && symbol.trim()) {
    params.set("symbol", symbol.trim().toUpperCase());
  }
  params.set("mode", mode);
  params.set("intent", resolvedIntent);
  return `/analysis?${params.toString()}`;
}
