/** Session handoff for Company Research — presentation cache only, no scoring. */

import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";
import { archiveResearchSession } from "@/lib/copilot/sessionArchive";

const STORAGE_KEY = "dsp.researchSession.v1";

export type ResearchSession = {
  ticker: string;
  exchange: string | null;
  company: string | null;
  analysedAt: string;
  request: AnalyseRequest;
  response: AnalyseResponse;
};

export function saveResearchSession(session: ResearchSession): void {
  if (typeof window === "undefined") {
    archiveResearchSession(session);
    return;
  }
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    /* quota / private mode — non-fatal */
  }
  archiveResearchSession(session);
}

export function loadResearchSession(ticker?: string): ResearchSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ResearchSession;
    if (!parsed?.ticker || !parsed?.response) return null;
    if (ticker && parsed.ticker.toUpperCase() !== ticker.toUpperCase()) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function clearResearchSession(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
