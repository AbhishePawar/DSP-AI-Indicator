/**
 * EPIC-F006 — Portfolio workspace UI preferences.
 * No financial scores or allocation math.
 */

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { PortfolioSectionId } from "./sections";

export type PortfolioNote = {
  id: string;
  text: string;
  at: string;
  portfolioId: string;
};

export type PortfolioTag = {
  id: string;
  label: string;
  portfolioId: string;
};

export type WatchlistEntry = {
  symbol: string;
  label?: string;
  addedAt: string;
};

export type NamedPortfolioMeta = {
  id: string;
  name: string;
  favourite: boolean;
  lastOpenedAt: string;
};

/** Well-known benchmark presets — free-text entry is always also available. */
export type BenchmarkPreset = { symbol: string; label: string };

export const BENCHMARK_PRESETS: readonly BenchmarkPreset[] = [
  { symbol: "SPY", label: "S&P 500 (SPY)" },
  { symbol: "QQQ", label: "NASDAQ 100 (QQQ)" },
  { symbol: "DIA", label: "Dow Jones (DIA)" },
  { symbol: "NIFTYBEES", label: "NIFTY 50 (NIFTYBEES)" },
] as const;

type PortfolioIntelPrefsState = {
  activeSection: PortfolioSectionId;
  leftOpen: boolean;
  rightOpen: boolean;
  activePortfolioId: string;
  portfolios: NamedPortfolioMeta[];
  watchlist: WatchlistEntry[];
  notes: PortfolioNote[];
  tags: PortfolioTag[];
  /** Selected benchmark symbol for Performance/Stress analytics — null = none selected. */
  benchmarkSymbol: string | null;
  setActiveSection: (id: PortfolioSectionId) => void;
  setLeftOpen: (open: boolean) => void;
  setRightOpen: (open: boolean) => void;
  toggleLeft: () => void;
  toggleRight: () => void;
  setActivePortfolioId: (id: string) => void;
  touchPortfolio: (id: string) => void;
  toggleFavourite: (id: string) => void;
  addWatchlistSymbol: (symbol: string, label?: string) => void;
  removeWatchlistSymbol: (symbol: string) => void;
  addNote: (portfolioId: string, text: string) => void;
  removeNote: (id: string) => void;
  addTag: (portfolioId: string, label: string) => void;
  removeTag: (id: string) => void;
  setBenchmarkSymbol: (symbol: string | null) => void;
};

const PRIMARY: NamedPortfolioMeta = {
  id: "primary",
  name: "Primary session portfolio",
  favourite: true,
  lastOpenedAt: new Date(0).toISOString(),
};

export const usePortfolioIntelPrefsStore = create<PortfolioIntelPrefsState>()(
  persist(
    (set, get) => ({
      activeSection: "summary",
      leftOpen: true,
      rightOpen: true,
      activePortfolioId: "primary",
      portfolios: [PRIMARY],
      watchlist: [],
      notes: [],
      tags: [],
      benchmarkSymbol: null,
      setActiveSection: (id) => set({ activeSection: id }),
      setLeftOpen: (open) => set({ leftOpen: open }),
      setRightOpen: (open) => set({ rightOpen: open }),
      toggleLeft: () => set((s) => ({ leftOpen: !s.leftOpen })),
      toggleRight: () => set((s) => ({ rightOpen: !s.rightOpen })),
      setActivePortfolioId: (id) => {
        set({ activePortfolioId: id });
        get().touchPortfolio(id);
      },
      touchPortfolio: (id) =>
        set((s) => ({
          portfolios: s.portfolios.map((p) =>
            p.id === id
              ? { ...p, lastOpenedAt: new Date().toISOString() }
              : p,
          ),
        })),
      toggleFavourite: (id) =>
        set((s) => ({
          portfolios: s.portfolios.map((p) =>
            p.id === id ? { ...p, favourite: !p.favourite } : p,
          ),
        })),
      addWatchlistSymbol: (symbol, label) =>
        set((s) => {
          const sym = symbol.trim().toUpperCase();
          if (!sym) return s;
          if (s.watchlist.some((w) => w.symbol === sym)) return s;
          return {
            watchlist: [
              {
                symbol: sym,
                label,
                addedAt: new Date().toISOString(),
              },
              ...s.watchlist,
            ].slice(0, 40),
          };
        }),
      removeWatchlistSymbol: (symbol) =>
        set((s) => ({
          watchlist: s.watchlist.filter(
            (w) => w.symbol !== symbol.trim().toUpperCase(),
          ),
        })),
      addNote: (portfolioId, text) =>
        set((s) => {
          const trimmed = text.trim();
          if (!trimmed) return s;
          return {
            notes: [
              {
                id: `n-${Date.now()}`,
                text: trimmed,
                at: new Date().toISOString(),
                portfolioId,
              },
              ...s.notes,
            ].slice(0, 40),
          };
        }),
      removeNote: (id) =>
        set((s) => ({ notes: s.notes.filter((n) => n.id !== id) })),
      addTag: (portfolioId, label) =>
        set((s) => {
          const trimmed = label.trim();
          if (!trimmed) return s;
          if (
            s.tags.some(
              (t) =>
                t.portfolioId === portfolioId &&
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
                portfolioId,
              },
              ...s.tags,
            ].slice(0, 40),
          };
        }),
      removeTag: (id) =>
        set((s) => ({ tags: s.tags.filter((t) => t.id !== id) })),
      setBenchmarkSymbol: (symbol) => {
        const cleaned = symbol?.trim().toUpperCase() || null;
        set({ benchmarkSymbol: cleaned });
      },
    }),
    {
      name: "dsp.portfolio-intelligence.prefs.v1",
      partialize: (state) => ({
        leftOpen: state.leftOpen,
        rightOpen: state.rightOpen,
        activeSection: state.activeSection,
        activePortfolioId: state.activePortfolioId,
        portfolios: state.portfolios,
        watchlist: state.watchlist,
        notes: state.notes,
        tags: state.tags,
        benchmarkSymbol: state.benchmarkSymbol,
      }),
    },
  ),
);
