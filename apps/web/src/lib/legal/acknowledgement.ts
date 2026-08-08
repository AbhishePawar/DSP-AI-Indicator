/**
 * P4.1 — Persist first-time investment research disclaimer acknowledgement (browser only).
 */

export const RESEARCH_DISCLAIMER_ACK_KEY =
  "dsp.researchDisclaimer.acknowledged.v1" as const;

export function isResearchDisclaimerAcknowledged(
  storage: Pick<Storage, "getItem"> | null = typeof window !== "undefined"
    ? window.localStorage
    : null,
): boolean {
  if (!storage) return false;
  try {
    return storage.getItem(RESEARCH_DISCLAIMER_ACK_KEY) === "1";
  } catch {
    return false;
  }
}

export function acknowledgeResearchDisclaimer(
  storage: Pick<Storage, "setItem"> | null = typeof window !== "undefined"
    ? window.localStorage
    : null,
  at: string = new Date().toISOString(),
): void {
  if (!storage) return;
  try {
    storage.setItem(RESEARCH_DISCLAIMER_ACK_KEY, "1");
    storage.setItem(`${RESEARCH_DISCLAIMER_ACK_KEY}.at`, at);
  } catch {
    /* private mode / quota — gate may reappear */
  }
}

export function clearResearchDisclaimerAcknowledgement(
  storage: Pick<Storage, "removeItem"> | null = typeof window !== "undefined"
    ? window.localStorage
    : null,
): void {
  if (!storage) return;
  try {
    storage.removeItem(RESEARCH_DISCLAIMER_ACK_KEY);
    storage.removeItem(`${RESEARCH_DISCLAIMER_ACK_KEY}.at`);
  } catch {
    /* ignore */
  }
}
