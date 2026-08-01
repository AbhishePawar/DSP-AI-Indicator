/**
 * P9.6 / EPIC-007 — Institutional Research Reports UI preferences.
 * No financial scores or fabricated research.
 */

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { ReportMode, ReportSectionId } from "./sections";

export type ReportNote = {
  id: string;
  text: string;
  at: string;
  symbol: string;
};

export type ReportTag = {
  id: string;
  label: string;
  symbol: string;
};

type InstitutionalReportsPrefsState = {
  activeSection: ReportSectionId;
  leftOpen: boolean;
  rightOpen: boolean;
  reportMode: ReportMode;
  selectedTicker: string;
  favourites: string[];
  notes: ReportNote[];
  tags: ReportTag[];
  setActiveSection: (id: ReportSectionId) => void;
  setLeftOpen: (open: boolean) => void;
  setRightOpen: (open: boolean) => void;
  toggleLeft: () => void;
  toggleRight: () => void;
  setReportMode: (mode: ReportMode) => void;
  setSelectedTicker: (ticker: string) => void;
  toggleFavourite: (ticker: string) => void;
  addNote: (symbol: string, text: string) => void;
  removeNote: (id: string) => void;
  addTag: (symbol: string, label: string) => void;
  removeTag: (id: string) => void;
};

export const useInstitutionalReportsPrefsStore =
  create<InstitutionalReportsPrefsState>()(
    persist(
      (set) => ({
        activeSection: "cover",
        leftOpen: true,
        rightOpen: true,
        reportMode: "interactive",
        selectedTicker: "AAPL",
        favourites: [],
        notes: [],
        tags: [],
        setActiveSection: (id) => set({ activeSection: id }),
        setLeftOpen: (open) => set({ leftOpen: open }),
        setRightOpen: (open) => set({ rightOpen: open }),
        toggleLeft: () => set((s) => ({ leftOpen: !s.leftOpen })),
        toggleRight: () => set((s) => ({ rightOpen: !s.rightOpen })),
        setReportMode: (mode) => set({ reportMode: mode }),
        setSelectedTicker: (ticker) =>
          set({ selectedTicker: ticker.trim().toUpperCase() }),
        toggleFavourite: (ticker) =>
          set((s) => {
            const sym = ticker.trim().toUpperCase();
            if (!sym) return s;
            if (s.favourites.includes(sym)) {
              return {
                favourites: s.favourites.filter((f) => f !== sym),
              };
            }
            return {
              favourites: [sym, ...s.favourites].slice(0, 24),
            };
          }),
        addNote: (symbol, text) =>
          set((s) => {
            const trimmed = text.trim();
            if (!trimmed) return s;
            return {
              notes: [
                {
                  id: `n-${Date.now()}`,
                  text: trimmed,
                  at: new Date().toISOString(),
                  symbol: symbol.toUpperCase(),
                },
                ...s.notes,
              ].slice(0, 40),
            };
          }),
        removeNote: (id) =>
          set((s) => ({ notes: s.notes.filter((n) => n.id !== id) })),
        addTag: (symbol, label) =>
          set((s) => {
            const trimmed = label.trim();
            if (!trimmed) return s;
            const sym = symbol.toUpperCase();
            if (
              s.tags.some(
                (t) =>
                  t.symbol === sym &&
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
                  symbol: sym,
                },
                ...s.tags,
              ].slice(0, 40),
            };
          }),
        removeTag: (id) =>
          set((s) => ({ tags: s.tags.filter((t) => t.id !== id) })),
      }),
      {
        name: "dsp.institutional-reports.prefs.v1",
        partialize: (state) => ({
          leftOpen: state.leftOpen,
          rightOpen: state.rightOpen,
          activeSection: state.activeSection,
          reportMode: state.reportMode,
          selectedTicker: state.selectedTicker,
          favourites: state.favourites,
          notes: state.notes,
          tags: state.tags,
        }),
      },
    ),
  );
