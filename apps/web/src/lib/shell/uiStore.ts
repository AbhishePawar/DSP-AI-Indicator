/**
 * EPIC-F003 — Layout preferences & navigation history (Zustand).
 * UI state only — no financial data.
 */

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

const MAX_RECENT = 8;
const MAX_FAVOURITES = 12;

export type NavHistoryEntry = {
  path: string;
  title: string;
  visitedAt: string;
};

type UiStoreState = {
  sidebarCollapsed: boolean;
  mobileDrawerOpen: boolean;
  commandPaletteOpen: boolean;
  recentPages: NavHistoryEntry[];
  favouritePages: NavHistoryEntry[];
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebarCollapsed: () => void;
  setMobileDrawerOpen: (open: boolean) => void;
  setCommandPaletteOpen: (open: boolean) => void;
  recordRecentPage: (path: string, title: string) => void;
  toggleFavourite: (path: string, title: string) => void;
  isFavourite: (path: string) => boolean;
};

export const useUiStore = create<UiStoreState>()(
  persist(
    (set, get) => ({
      sidebarCollapsed: false,
      mobileDrawerOpen: false,
      commandPaletteOpen: false,
      recentPages: [],
      favouritePages: [],
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleSidebarCollapsed: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setMobileDrawerOpen: (open) => set({ mobileDrawerOpen: open }),
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      recordRecentPage: (path, title) =>
        set((s) => {
          if (!path || path.startsWith("/login")) return s;
          const entry: NavHistoryEntry = {
            path,
            title,
            visitedAt: new Date().toISOString(),
          };
          const filtered = s.recentPages.filter((p) => p.path !== path);
          return {
            recentPages: [entry, ...filtered].slice(0, MAX_RECENT),
          };
        }),
      toggleFavourite: (path, title) =>
        set((s) => {
          const exists = s.favouritePages.some((p) => p.path === path);
          if (exists) {
            return {
              favouritePages: s.favouritePages.filter((p) => p.path !== path),
            };
          }
          const entry: NavHistoryEntry = {
            path,
            title,
            visitedAt: new Date().toISOString(),
          };
          return {
            favouritePages: [entry, ...s.favouritePages].slice(
              0,
              MAX_FAVOURITES,
            ),
          };
        }),
      isFavourite: (path) => get().favouritePages.some((p) => p.path === path),
    }),
    {
      name: "dsp.shell.ui.v1",
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        recentPages: state.recentPages,
        favouritePages: state.favouritePages,
      }),
    },
  ),
);
