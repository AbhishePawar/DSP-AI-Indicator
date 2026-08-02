/**
 * EPIC-012/013 — Personal Research Workspace (user-authored only).
 * Local persistence — never sent to /analyse.
 */

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { ComparisonSectionId } from "./sections";
import type { SavedComparison } from "./types";

export type PersonalNote = {
  id: string;
  kind: "note" | "thesis" | "question" | "decision";
  text: string;
  symbols: string[];
  at: string;
};

export type WatchItem = {
  id: string;
  symbol: string;
  at: string;
};

type ComparisonPrefsState = {
  activeSection: ComparisonSectionId;
  leftOpen: boolean;
  symbols: string[];
  pinned: string[];
  notes: PersonalNote[];
  watch: WatchItem[];
  saved: SavedComparison[];
  setActiveSection: (id: ComparisonSectionId) => void;
  setLeftOpen: (open: boolean) => void;
  toggleLeft: () => void;
  setSymbols: (symbols: string[]) => void;
  pinSymbol: (symbol: string) => void;
  unpinSymbol: (symbol: string) => void;
  addNote: (
    kind: PersonalNote["kind"],
    text: string,
    symbols: string[],
  ) => void;
  removeNote: (id: string) => void;
  addWatch: (symbol: string) => void;
  removeWatch: (id: string) => void;
  saveComparison: (title: string, symbols: string[], notes?: string) => void;
  removeSaved: (id: string) => void;
};

export const useComparisonPrefsStore = create<ComparisonPrefsState>()(
  persist(
    (set) => ({
      activeSection: "summary",
      leftOpen: true,
      symbols: [],
      pinned: [],
      notes: [],
      watch: [],
      saved: [],
      setActiveSection: (id) => set({ activeSection: id }),
      setLeftOpen: (open) => set({ leftOpen: open }),
      toggleLeft: () => set((s) => ({ leftOpen: !s.leftOpen })),
      setSymbols: (symbols) =>
        set({
          symbols: symbols
            .map((s) => s.trim().toUpperCase())
            .filter(Boolean)
            .slice(0, 5),
        }),
      pinSymbol: (symbol) =>
        set((s) => {
          const sym = symbol.toUpperCase();
          if (s.pinned.includes(sym)) return s;
          return { pinned: [...s.pinned, sym].slice(0, 20) };
        }),
      unpinSymbol: (symbol) =>
        set((s) => ({
          pinned: s.pinned.filter((p) => p !== symbol.toUpperCase()),
        })),
      addNote: (kind, text, symbols) =>
        set((s) => {
          const trimmed = text.trim();
          if (!trimmed) return s;
          return {
            notes: [
              {
                id: `cn-${Date.now()}`,
                kind,
                text: trimmed,
                symbols: symbols.map((x) => x.toUpperCase()),
                at: new Date().toISOString(),
              },
              ...s.notes,
            ].slice(0, 80),
          };
        }),
      removeNote: (id) =>
        set((s) => ({ notes: s.notes.filter((n) => n.id !== id) })),
      addWatch: (symbol) =>
        set((s) => {
          const sym = symbol.toUpperCase();
          if (s.watch.some((w) => w.symbol === sym)) return s;
          return {
            watch: [
              { id: `w-${Date.now()}`, symbol: sym, at: new Date().toISOString() },
              ...s.watch,
            ].slice(0, 40),
          };
        }),
      removeWatch: (id) =>
        set((s) => ({ watch: s.watch.filter((w) => w.id !== id) })),
      saveComparison: (title, symbols, notes) =>
        set((s) => {
          const trimmed = title.trim() || `Comparison ${new Date().toLocaleString()}`;
          return {
            saved: [
              {
                id: `sc-${Date.now()}`,
                title: trimmed,
                symbols: symbols.map((x) => x.toUpperCase()),
                savedAt: new Date().toISOString(),
                notes,
              },
              ...s.saved,
            ].slice(0, 30),
          };
        }),
      removeSaved: (id) =>
        set((s) => ({ saved: s.saved.filter((x) => x.id !== id) })),
    }),
    {
      name: "dsp.company-comparison.prefs.v1",
      partialize: (state) => ({
        leftOpen: state.leftOpen,
        symbols: state.symbols,
        pinned: state.pinned,
        notes: state.notes,
        watch: state.watch,
        saved: state.saved,
        activeSection: state.activeSection,
      }),
    },
  ),
);
