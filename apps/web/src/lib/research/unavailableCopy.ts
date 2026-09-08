/** Honest client copy when required verified data is missing (SIMPLE-14G). */
export const VALUATION_UNAVAILABLE_COPY =
  "Some required data could not be verified. Valuation is unavailable until the required data is verified.";

export function formatAnalyseUnavailableMessage(message: string | undefined): string {
  const raw = (message || "").trim();
  if (raw.toLowerCase().includes("data unavailable")) {
    return VALUATION_UNAVAILABLE_COPY;
  }
  return raw || VALUATION_UNAVAILABLE_COPY;
}
