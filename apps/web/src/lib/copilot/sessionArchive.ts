/**
 * Multi-company research archive for Copilot compare mode.
 * Session-only — no durable persistence.
 */

import type { AnalyseRequest, AnalyseResponse } from "@/lib/api/compositionTypes";

export type ArchivedResearchSession = {
  ticker: string;
  exchange: string | null;
  company: string | null;
  analysedAt: string;
  request: AnalyseRequest;
  response: AnalyseResponse;
};

const STORAGE_KEY = "dsp.researchArchive.v1";
const MAX_SESSIONS = 8;

let memoryArchive: ArchivedResearchSession[] = [];

function readArchive(): ArchivedResearchSession[] {
  if (typeof window === "undefined") return [...memoryArchive];
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [...memoryArchive];
    const parsed = JSON.parse(raw) as ArchivedResearchSession[];
    memoryArchive = Array.isArray(parsed) ? parsed : [];
    return [...memoryArchive];
  } catch {
    return [...memoryArchive];
  }
}

function writeArchive(sessions: ArchivedResearchSession[]): void {
  memoryArchive = sessions;
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch {
    /* ignore */
  }
}

export function archiveResearchSession(session: ArchivedResearchSession): void {
  const next = [
    session,
    ...readArchive().filter(
      (item) => item.ticker.toUpperCase() !== session.ticker.toUpperCase(),
    ),
  ].slice(0, MAX_SESSIONS);
  writeArchive(next);
}

export function listArchivedSessions(): ArchivedResearchSession[] {
  return readArchive();
}

export function loadArchivedSession(
  ticker: string,
): ArchivedResearchSession | null {
  const normalized = ticker.trim().toUpperCase();
  return (
    readArchive().find((item) => item.ticker.toUpperCase() === normalized) ??
    null
  );
}

export function clearResearchArchive(): void {
  writeArchive([]);
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
