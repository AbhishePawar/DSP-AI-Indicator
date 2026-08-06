/**
 * EPIC-F005 — Workspace UI preferences (Zustand).
 * No financial scores.
 */

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import {
  type AnalysisSectionId,
} from "./sections";

export type WorkspaceNote = {
  id: string;
  text: string;
  at: string;
  symbol: string;
};

export type WorkspaceTag = {
  id: string;
  label: string;
  symbol: string;
};

type WorkspacePrefsState = {
  activeSection: AnalysisSectionId;
  leftOpen: boolean;
  rightOpen: boolean;
  notes: WorkspaceNote[];
  tags: WorkspaceTag[];
  setActiveSection: (id: AnalysisSectionId) => void;
  setLeftOpen: (open: boolean) => void;
  setRightOpen: (open: boolean) => void;
  toggleLeft: () => void;
  toggleRight: () => void;
  addNote: (symbol: string, text: string) => void;
  removeNote: (id: string) => void;
  addTag: (symbol: string, label: string) => void;
  removeTag: (id: string) => void;
};

export const useWorkspacePrefsStore = create<WorkspacePrefsState>()(
  persist(
    (set) => ({
      activeSection: "summary",
      leftOpen: true,
      rightOpen: true,
      notes: [],
      tags: [],
      setActiveSection: (id) => set({ activeSection: id }),
      setLeftOpen: (open) => set({ leftOpen: open }),
      setRightOpen: (open) => set({ rightOpen: open }),
      toggleLeft: () => set((s) => ({ leftOpen: !s.leftOpen })),
      toggleRight: () => set((s) => ({ rightOpen: !s.rightOpen })),
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
      name: "dsp.company-analysis.prefs.v1",
      partialize: (state) => ({
        leftOpen: state.leftOpen,
        rightOpen: state.rightOpen,
        notes: state.notes,
        tags: state.tags,
        activeSection: state.activeSection,
      }),
    },
  ),
);
