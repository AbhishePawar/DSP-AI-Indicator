/**
 * EPIC-F007 — Research workspace UI preferences.
 * No research generation or scoring.
 */

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { ResearchSectionId } from "./sections";

export type ResearchNote = {
  id: string;
  text: string;
  at: string;
  ticker: string;
};

export type ResearchTag = {
  id: string;
  label: string;
  ticker: string;
};

export type FavouriteResearch = {
  ticker: string;
  company?: string;
  favouritedAt: string;
};

type ResearchWorkspacePrefsState = {
  activeSection: ResearchSectionId;
  leftOpen: boolean;
  rightOpen: boolean;
  selectedTicker: string | null;
  favourites: FavouriteResearch[];
  pinnedTickers: string[];
  notes: ResearchNote[];
  tags: ResearchTag[];
  setActiveSection: (id: ResearchSectionId) => void;
  setLeftOpen: (open: boolean) => void;
  setRightOpen: (open: boolean) => void;
  toggleLeft: () => void;
  toggleRight: () => void;
  setSelectedTicker: (ticker: string | null) => void;
  toggleFavourite: (ticker: string, company?: string) => void;
  isFavourite: (ticker: string) => boolean;
  togglePinned: (ticker: string) => void;
  isPinned: (ticker: string) => boolean;
  addNote: (ticker: string, text: string) => void;
  removeNote: (id: string) => void;
  addTag: (ticker: string, label: string) => void;
  removeTag: (id: string) => void;
};

export const useResearchWorkspacePrefsStore =
  create<ResearchWorkspacePrefsState>()(
    persist(
      (set, get) => ({
        activeSection: "library",
        leftOpen: true,
        rightOpen: true,
        selectedTicker: null,
        favourites: [],
        pinnedTickers: [],
        notes: [],
        tags: [],
        setActiveSection: (id) => set({ activeSection: id }),
        setLeftOpen: (open) => set({ leftOpen: open }),
        setRightOpen: (open) => set({ rightOpen: open }),
        toggleLeft: () => set((s) => ({ leftOpen: !s.leftOpen })),
        toggleRight: () => set((s) => ({ rightOpen: !s.rightOpen })),
        setSelectedTicker: (ticker) =>
          set({
            selectedTicker: ticker ? ticker.trim().toUpperCase() : null,
          }),
        toggleFavourite: (ticker, company) =>
          set((s) => {
            const sym = ticker.trim().toUpperCase();
            if (!sym) return s;
            const exists = s.favourites.some((f) => f.ticker === sym);
            if (exists) {
              return {
                favourites: s.favourites.filter((f) => f.ticker !== sym),
              };
            }
            return {
              favourites: [
                {
                  ticker: sym,
                  company,
                  favouritedAt: new Date().toISOString(),
                },
                ...s.favourites,
              ].slice(0, 24),
            };
          }),
        isFavourite: (ticker) =>
          get().favourites.some(
            (f) => f.ticker === ticker.trim().toUpperCase(),
          ),
        togglePinned: (ticker) =>
          set((s) => {
            const sym = ticker.trim().toUpperCase();
            if (!sym) return s;
            if (s.pinnedTickers.includes(sym)) {
              return {
                pinnedTickers: s.pinnedTickers.filter((t) => t !== sym),
              };
            }
            return {
              pinnedTickers: [sym, ...s.pinnedTickers].slice(0, 24),
            };
          }),
        isPinned: (ticker) =>
          get().pinnedTickers.includes(ticker.trim().toUpperCase()),
        addNote: (ticker, text) =>
          set((s) => {
            const trimmed = text.trim();
            const sym = ticker.trim().toUpperCase();
            if (!trimmed || !sym) return s;
            return {
              notes: [
                {
                  id: `n-${Date.now()}`,
                  text: trimmed,
                  at: new Date().toISOString(),
                  ticker: sym,
                },
                ...s.notes,
              ].slice(0, 40),
            };
          }),
        removeNote: (id) =>
          set((s) => ({ notes: s.notes.filter((n) => n.id !== id) })),
        addTag: (ticker, label) =>
          set((s) => {
            const trimmed = label.trim();
            const sym = ticker.trim().toUpperCase();
            if (!trimmed || !sym) return s;
            if (
              s.tags.some(
                (t) =>
                  t.ticker === sym &&
                  t.label.toLowerCase() === trimmed.toLowerCase(),
              )
            ) {
              return s;
            }
            return {
              tags: [
                {
                  id: `t-${Date.now()}`,
                  label: trimmed,
                  ticker: sym,
                },
                ...s.tags,
              ].slice(0, 40),
            };
          }),
        removeTag: (id) =>
          set((s) => ({ tags: s.tags.filter((t) => t.id !== id) })),
      }),
      {
        name: "dsp.research-workspace.prefs.v1",
        partialize: (state) => ({
          leftOpen: state.leftOpen,
          rightOpen: state.rightOpen,
          activeSection: state.activeSection,
          selectedTicker: state.selectedTicker,
          favourites: state.favourites,
          pinnedTickers: state.pinnedTickers,
          notes: state.notes,
          tags: state.tags,
        }),
      },
    ),
  );
