export const ANALYSIS_INTENTS = {
  company: "company",
  dspIndicator: "dsp_indicator",
} as const;

export type AnalysisIntent = (typeof ANALYSIS_INTENTS)[keyof typeof ANALYSIS_INTENTS];

export function parseAnalysisIntent(value: string | null): AnalysisIntent {
  return value === ANALYSIS_INTENTS.dspIndicator
    ? ANALYSIS_INTENTS.dspIndicator
    : ANALYSIS_INTENTS.company;
}
