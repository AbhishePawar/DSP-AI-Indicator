/**
 * EPIC-014 — Research Notebook (user-authored only).
 * Local persistence — NEVER sent to /analyse or overwriting institutional research.
 */

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type NotebookEntryKind =
  | "note"
  | "thesis"
  | "question"
  | "watch"
  | "observation"
  | "risk"
  | "catalyst"
  | "conclusion"
  | "action";

export type NotebookEntry = {
  id: string;
  kind: NotebookEntryKind;
  text: string;
  symbol: string | null;
  at: string;
  /** Soft bookmark / pin within the notebook */
  bookmarked?: boolean;
};

export type SavedResearchSession = {
  id: string;
  title: string;
  symbol: string | null;
  tab: string;
  at: string;
};

type NotebookState = {
  entries: NotebookEntry[];
  savedSessions: SavedResearchSession[];
  bookmarks: { id: string; label: string; href: string; at: string }[];
  addEntry: (
    kind: NotebookEntryKind,
    text: string,
    symbol?: string | null,
  ) => void;
  removeEntry: (id: string) => void;
  toggleBookmarkEntry: (id: string) => void;
  saveSession: (title: string, symbol: string | null, tab: string) => void;
  removeSavedSession: (id: string) => void;
  addBookmark: (label: string, href: string) => void;
  removeBookmark: (id: string) => void;
  entriesForSymbol: (symbol: string | null) => NotebookEntry[];
};

const MAX_ENTRIES = 200;
const MAX_SAVED = 40;
const MAX_BOOKMARKS = 40;

export const useResearchNotebookStore = create<NotebookState>()(
  persist(
    (set, get) => ({
      entries: [],
      savedSessions: [],
      bookmarks: [],
      addEntry: (kind, text, symbol = null) =>
        set((s) => {
          const trimmed = text.trim();
          if (!trimmed) return s;
          return {
            entries: [
              {
                id: `nb-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
                kind,
                text: trimmed,
                symbol: symbol ? symbol.toUpperCase() : null,
                at: new Date().toISOString(),
              },
              ...s.entries,
            ].slice(0, MAX_ENTRIES),
          };
        }),
      removeEntry: (id) =>
        set((s) => ({ entries: s.entries.filter((e) => e.id !== id) })),
      toggleBookmarkEntry: (id) =>
        set((s) => ({
          entries: s.entries.map((e) =>
            e.id === id ? { ...e, bookmarked: !e.bookmarked } : e,
          ),
        })),
      saveSession: (title, symbol, tab) =>
        set((s) => {
          const trimmed =
            title.trim() ||
            `${symbol ?? "Research"} · ${new Date().toLocaleString()}`;
          return {
            savedSessions: [
              {
                id: `ss-${Date.now()}`,
                title: trimmed,
                symbol: symbol ? symbol.toUpperCase() : null,
                tab,
                at: new Date().toISOString(),
              },
              ...s.savedSessions,
            ].slice(0, MAX_SAVED),
          };
        }),
      removeSavedSession: (id) =>
        set((s) => ({
          savedSessions: s.savedSessions.filter((x) => x.id !== id),
        })),
      addBookmark: (label, href) =>
        set((s) => {
          const trimmed = label.trim();
          if (!trimmed || !href) return s;
          return {
            bookmarks: [
              {
                id: `bm-${Date.now()}`,
                label: trimmed,
                href,
                at: new Date().toISOString(),
              },
              ...s.bookmarks,
            ].slice(0, MAX_BOOKMARKS),
          };
        }),
      removeBookmark: (id) =>
        set((s) => ({
          bookmarks: s.bookmarks.filter((b) => b.id !== id),
        })),
      entriesForSymbol: (symbol) => {
        const entries = get().entries;
        if (!symbol) return entries;
        const sym = symbol.toUpperCase();
        return entries.filter((e) => !e.symbol || e.symbol === sym);
      },
    }),
    {
      name: "dsp.research-canvas.notebook.v1",
      partialize: (s) => ({
        entries: s.entries,
        savedSessions: s.savedSessions,
        bookmarks: s.bookmarks,
      }),
    },
  ),
);

/** Isolation invariant: notebook kinds are user-authored labels only. */
export const NOTEBOOK_KINDS: readonly NotebookEntryKind[] = [
  "note",
  "thesis",
  "question",
  "watch",
  "observation",
  "risk",
  "catalyst",
  "conclusion",
  "action",
] as const;

export const NOTEBOOK_KIND_LABELS: Record<NotebookEntryKind, string> = {
  note: "Notes",
  thesis: "Thesis",
  question: "Questions",
  watch: "Watch Items",
  observation: "Observations",
  risk: "Risks",
  catalyst: "Catalysts",
  conclusion: "Conclusions",
  action: "Action Items",
};
