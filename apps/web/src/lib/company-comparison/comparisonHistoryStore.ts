/**
 * Comparison History — immutable append-only local persistence.
 * Entries are never mutated after append; only new snapshots are added.
 */

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { ComparisonHistoryEntry } from "./types";

const MAX_HISTORY = 80;

type HistoryState = {
  entries: ComparisonHistoryEntry[];
  /** Append-only. Returns the frozen entry id. */
  appendHistory: (
    entry: Omit<ComparisonHistoryEntry, "id" | "immutable">,
  ) => string;
  /** Filter helpers (read-only views). */
  search: (query: string) => ComparisonHistoryEntry[];
  filterBySymbol: (symbol: string) => ComparisonHistoryEntry[];
};

function freezeEntry(
  entry: Omit<ComparisonHistoryEntry, "id" | "immutable">,
  id: string,
): ComparisonHistoryEntry {
  return Object.freeze({
    id,
    at: entry.at,
    symbols: Object.freeze([...entry.symbols]) as string[],
    researchVersion: entry.researchVersion,
    confidence: entry.confidence,
    winnerSummary: entry.winnerSummary,
    changes: entry.changes,
    immutable: true as const,
  });
}

export const useComparisonHistoryStore = create<HistoryState>()(
  persist(
    (set, get) => ({
      entries: [],
      appendHistory: (entry) => {
        const id = `ch-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        const frozen = freezeEntry(entry, id);
        set((s) => ({
          entries: [frozen, ...s.entries].slice(0, MAX_HISTORY),
        }));
        return id;
      },
      search: (query) => {
        const q = query.trim().toLowerCase();
        if (!q) return get().entries;
        return get().entries.filter(
          (e) =>
            e.symbols.some((s) => s.toLowerCase().includes(q)) ||
            e.winnerSummary.toLowerCase().includes(q) ||
            e.researchVersion.toLowerCase().includes(q) ||
            e.changes.toLowerCase().includes(q),
        );
      },
      filterBySymbol: (symbol) => {
        const sym = symbol.trim().toUpperCase();
        return get().entries.filter((e) => e.symbols.includes(sym));
      },
    }),
    {
      name: "dsp.company-comparison.history.v1",
      partialize: (state) => ({ entries: state.entries }),
      merge: (persisted, current) => {
        const p = persisted as { entries?: ComparisonHistoryEntry[] } | undefined;
        const entries = (p?.entries ?? []).map((e) =>
          freezeEntry(
            {
              at: e.at,
              symbols: e.symbols,
              researchVersion: e.researchVersion,
              confidence: e.confidence,
              winnerSummary: e.winnerSummary,
              changes: e.changes,
            },
            e.id,
          ),
        );
        return { ...current, entries };
      },
    },
  ),
);

/**
 * Pure helper for tests: compute change note vs previous immutable entry.
 * Does not mutate prior entries.
 */
export function describeHistoryChanges(
  previous: ComparisonHistoryEntry | null | undefined,
  nextSymbols: string[],
  nextWinner: string,
): string {
  if (!previous) {
    return "Initial comparison snapshot.";
  }
  const prevSet = new Set(previous.symbols);
  const nextSet = new Set(nextSymbols);
  const added = nextSymbols.filter((s) => !prevSet.has(s));
  const removed = previous.symbols.filter((s) => !nextSet.has(s));
  const parts: string[] = [];
  if (added.length) parts.push(`added ${added.join(", ")}`);
  if (removed.length) parts.push(`removed ${removed.join(", ")}`);
  if (previous.winnerSummary !== nextWinner) {
    parts.push("winner summary changed");
  }
  if (parts.length === 0) {
    parts.push("same symbol set; re-run snapshot appended");
  }
  return parts.join("; ");
}

/** Test/util: attempt mutation must fail or be ineffective on frozen entry. */
export function isHistoryEntryImmutable(entry: ComparisonHistoryEntry): boolean {
  return entry.immutable === true && Object.isFrozen(entry);
}
