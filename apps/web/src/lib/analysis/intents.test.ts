import { describe, expect, it } from "vitest";
import {
  ANALYSIS_INTENTS,
  buildAnalysisUrl,
  getIntentForMode,
  parseAnalysisIntent,
  parseResearchMode,
} from "./intents";

describe("analysis intents and research mode helpers", () => {
  it("parses analysis intent correctly", () => {
    expect(parseAnalysisIntent(ANALYSIS_INTENTS.dspIndicator)).toBe("dsp_indicator");
    expect(parseAnalysisIntent("company")).toBe("company");
    expect(parseAnalysisIntent(null)).toBe("company");
    expect(parseAnalysisIntent("unknown")).toBe("company");
  });

  it("parses research mode with intent fallback and safe default", () => {
    expect(parseResearchMode("simple")).toBe("simple");
    expect(parseResearchMode("full")).toBe("full");
    expect(parseResearchMode(null, ANALYSIS_INTENTS.company)).toBe("simple");
    expect(parseResearchMode(null, ANALYSIS_INTENTS.dspIndicator)).toBe("full");
    expect(parseResearchMode(null, null)).toBe("full");
    expect(parseResearchMode("invalid", null)).toBe("full");
  });

  it("resolves intent for mode", () => {
    expect(getIntentForMode("simple")).toBe(ANALYSIS_INTENTS.company);
    expect(getIntentForMode("full")).toBe(ANALYSIS_INTENTS.dspIndicator);
  });

  it("builds analysis URLs preserving mode and intent", () => {
    expect(buildAnalysisUrl({ symbol: "INFY", mode: "simple" })).toBe(
      "/analysis?symbol=INFY&mode=simple&intent=company",
    );
    expect(buildAnalysisUrl({ symbol: "INFY", mode: "full" })).toBe(
      "/analysis?symbol=INFY&mode=full&intent=dsp_indicator",
    );
    expect(buildAnalysisUrl({ symbol: "TCS", mode: "full" })).toBe(
      "/analysis?symbol=TCS&mode=full&intent=dsp_indicator",
    );
    expect(buildAnalysisUrl({ symbol: "TCS", mode: "simple" })).toBe(
      "/analysis?symbol=TCS&mode=simple&intent=company",
    );
    expect(buildAnalysisUrl({ symbol: null, mode: "full" })).toBe(
      "/analysis?mode=full&intent=dsp_indicator",
    );
  });
});
