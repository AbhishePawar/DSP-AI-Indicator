/**
 * EPIC-014 — Research Canvas UI preferences (layout only).
 */

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { CanvasTabId } from "./sections";

type CanvasPrefsState = {
  activeTab: CanvasTabId;
  symbol: string | null;
  leftOpen: boolean;
  rightOpen: boolean;
  bottomOpen: boolean;
  setActiveTab: (id: CanvasTabId) => void;
  setSymbol: (symbol: string | null) => void;
  setLeftOpen: (open: boolean) => void;
  setRightOpen: (open: boolean) => void;
  setBottomOpen: (open: boolean) => void;
  toggleLeft: () => void;
  toggleRight: () => void;
  toggleBottom: () => void;
};

export const useResearchCanvasPrefsStore = create<CanvasPrefsState>()(
  persist(
    (set) => ({
      activeTab: "overview",
      symbol: null,
      leftOpen: true,
      rightOpen: true,
      bottomOpen: true,
      setActiveTab: (id) => set({ activeTab: id }),
      setSymbol: (symbol) =>
        set({
          symbol: symbol ? symbol.trim().toUpperCase() || null : null,
        }),
      setLeftOpen: (open) => set({ leftOpen: open }),
      setRightOpen: (open) => set({ rightOpen: open }),
      setBottomOpen: (open) => set({ bottomOpen: open }),
      toggleLeft: () => set((s) => ({ leftOpen: !s.leftOpen })),
      toggleRight: () => set((s) => ({ rightOpen: !s.rightOpen })),
      toggleBottom: () => set((s) => ({ bottomOpen: !s.bottomOpen })),
    }),
    {
      name: "dsp.research-canvas.prefs.v1",
      partialize: (s) => ({
        activeTab: s.activeTab,
        symbol: s.symbol,
        leftOpen: s.leftOpen,
        rightOpen: s.rightOpen,
        bottomOpen: s.bottomOpen,
      }),
    },
  ),
);
