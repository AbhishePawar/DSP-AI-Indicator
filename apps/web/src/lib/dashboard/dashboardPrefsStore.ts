/**
 * EPIC-F004 — Dashboard UI preferences (Zustand).
 * No financial scores or valuation results.
 */

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import {
  DEFAULT_WIDGET_ORDER,
  type DashboardWidgetId,
} from "./widgetRegistry";

const MAX_PINNED = 12;
const MAX_SEARCHES = 10;
const MAX_SAVED = 10;

export type PinnedCompany = {
  symbol: string;
  label?: string;
  pinnedAt: string;
};

export type SearchEntry = {
  query: string;
  at: string;
};

type DashboardPrefsState = {
  widgetOrder: DashboardWidgetId[];
  hiddenWidgets: DashboardWidgetId[];
  pinnedCompanies: PinnedCompany[];
  recentSearches: SearchEntry[];
  savedSearches: SearchEntry[];
  setWidgetOrder: (order: DashboardWidgetId[]) => void;
  toggleWidgetVisible: (id: DashboardWidgetId) => void;
  isWidgetVisible: (id: DashboardWidgetId) => boolean;
  moveWidget: (id: DashboardWidgetId, direction: "up" | "down") => void;
  pinCompany: (symbol: string, label?: string) => void;
  unpinCompany: (symbol: string) => void;
  isPinned: (symbol: string) => boolean;
  recordSearch: (query: string) => void;
  saveSearch: (query: string) => void;
  removeSavedSearch: (query: string) => void;
  resetLayout: () => void;
};

function normalizeOrder(order: DashboardWidgetId[]): DashboardWidgetId[] {
  const seen = new Set<DashboardWidgetId>();
  const next: DashboardWidgetId[] = [];
  for (const id of order) {
    if (!DEFAULT_WIDGET_ORDER.includes(id) || seen.has(id)) continue;
    seen.add(id);
    next.push(id);
  }
  for (const id of DEFAULT_WIDGET_ORDER) {
    if (!seen.has(id)) next.push(id);
  }
  return next;
}

export const useDashboardPrefsStore = create<DashboardPrefsState>()(
  persist(
    (set, get) => ({
      widgetOrder: [...DEFAULT_WIDGET_ORDER],
      hiddenWidgets: [],
      pinnedCompanies: [],
      recentSearches: [],
      savedSearches: [],
      setWidgetOrder: (order) => set({ widgetOrder: normalizeOrder(order) }),
      toggleWidgetVisible: (id) =>
        set((s) => ({
          hiddenWidgets: s.hiddenWidgets.includes(id)
            ? s.hiddenWidgets.filter((w) => w !== id)
            : [...s.hiddenWidgets, id],
        })),
      isWidgetVisible: (id) => !get().hiddenWidgets.includes(id),
      moveWidget: (id, direction) =>
        set((s) => {
          const order = [...s.widgetOrder];
          const index = order.indexOf(id);
          if (index < 0) return s;
          const target = direction === "up" ? index - 1 : index + 1;
          if (target < 0 || target >= order.length) return s;
          const tmp = order[index]!;
          order[index] = order[target]!;
          order[target] = tmp;
          return { widgetOrder: order };
        }),
      pinCompany: (symbol, label) =>
        set((s) => {
          const sym = symbol.trim().toUpperCase();
          if (!sym) return s;
          const rest = s.pinnedCompanies.filter((p) => p.symbol !== sym);
          return {
            pinnedCompanies: [
              {
                symbol: sym,
                label,
                pinnedAt: new Date().toISOString(),
              },
              ...rest,
            ].slice(0, MAX_PINNED),
          };
        }),
      unpinCompany: (symbol) =>
        set((s) => ({
          pinnedCompanies: s.pinnedCompanies.filter(
            (p) => p.symbol !== symbol.trim().toUpperCase(),
          ),
        })),
      isPinned: (symbol) =>
        get().pinnedCompanies.some(
          (p) => p.symbol === symbol.trim().toUpperCase(),
        ),
      recordSearch: (query) =>
        set((s) => {
          const q = query.trim();
          if (!q) return s;
          const rest = s.recentSearches.filter(
            (e) => e.query.toLowerCase() !== q.toLowerCase(),
          );
          return {
            recentSearches: [{ query: q, at: new Date().toISOString() }, ...rest].slice(
              0,
              MAX_SEARCHES,
            ),
          };
        }),
      saveSearch: (query) =>
        set((s) => {
          const q = query.trim();
          if (!q) return s;
          const rest = s.savedSearches.filter(
            (e) => e.query.toLowerCase() !== q.toLowerCase(),
          );
          return {
            savedSearches: [{ query: q, at: new Date().toISOString() }, ...rest].slice(
              0,
              MAX_SAVED,
            ),
          };
        }),
      removeSavedSearch: (query) =>
        set((s) => ({
          savedSearches: s.savedSearches.filter(
            (e) => e.query.toLowerCase() !== query.trim().toLowerCase(),
          ),
        })),
      resetLayout: () =>
        set({
          widgetOrder: [...DEFAULT_WIDGET_ORDER],
          hiddenWidgets: [],
        }),
    }),
    {
      name: "dsp.dashboard.prefs.v1",
      partialize: (state) => ({
        widgetOrder: state.widgetOrder,
        hiddenWidgets: state.hiddenWidgets,
        pinnedCompanies: state.pinnedCompanies,
        recentSearches: state.recentSearches,
        savedSearches: state.savedSearches,
      }),
    },
  ),
);
