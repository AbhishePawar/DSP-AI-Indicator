/**
 * EPIC-F009 — Settings & UI preferences (local only).
 * No business logic or client calculations.
 */

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type {
  ContrastPreference,
  DensityPreference,
  FontSizePreference,
  MotionPreference,
  SettingsSectionId,
} from "./sections";

export type SettingsNote = {
  id: string;
  text: string;
  at: string;
};

type SettingsPrefsState = {
  activeSection: SettingsSectionId;
  leftOpen: boolean;
  rightOpen: boolean;
  density: DensityPreference;
  fontSize: FontSizePreference;
  motionPreference: MotionPreference;
  contrastPreference: ContrastPreference;
  focusVisible: boolean;
  toastEnabled: boolean;
  toastDurationMs: number;
  soundEnabled: boolean;
  defaultWorkspace: string;
  recentItemsLimit: number;
  searchHistoryEnabled: boolean;
  notes: SettingsNote[];
  setActiveSection: (id: SettingsSectionId) => void;
  setLeftOpen: (open: boolean) => void;
  setRightOpen: (open: boolean) => void;
  toggleLeft: () => void;
  toggleRight: () => void;
  setDensity: (density: DensityPreference) => void;
  setFontSize: (size: FontSizePreference) => void;
  setMotionPreference: (value: MotionPreference) => void;
  setContrastPreference: (value: ContrastPreference) => void;
  setFocusVisible: (value: boolean) => void;
  setToastEnabled: (value: boolean) => void;
  setToastDurationMs: (value: number) => void;
  setSoundEnabled: (value: boolean) => void;
  setDefaultWorkspace: (path: string) => void;
  setRecentItemsLimit: (value: number) => void;
  setSearchHistoryEnabled: (value: boolean) => void;
  addNote: (text: string) => void;
  removeNote: (id: string) => void;
  resetAppearance: () => void;
};

const APPEARANCE_DEFAULTS = {
  density: "comfortable" as DensityPreference,
  fontSize: "md" as FontSizePreference,
  motionPreference: "system" as MotionPreference,
  contrastPreference: "system" as ContrastPreference,
  focusVisible: true,
};

export const useSettingsPrefsStore = create<SettingsPrefsState>()(
  persist(
    (set) => ({
      activeSection: "profile",
      leftOpen: true,
      rightOpen: true,
      ...APPEARANCE_DEFAULTS,
      toastEnabled: true,
      toastDurationMs: 4000,
      soundEnabled: false,
      defaultWorkspace: "/dashboard",
      recentItemsLimit: 8,
      searchHistoryEnabled: true,
      notes: [],
      setActiveSection: (id) => set({ activeSection: id }),
      setLeftOpen: (open) => set({ leftOpen: open }),
      setRightOpen: (open) => set({ rightOpen: open }),
      toggleLeft: () => set((s) => ({ leftOpen: !s.leftOpen })),
      toggleRight: () => set((s) => ({ rightOpen: !s.rightOpen })),
      setDensity: (density) => set({ density }),
      setFontSize: (fontSize) => set({ fontSize }),
      setMotionPreference: (motionPreference) => set({ motionPreference }),
      setContrastPreference: (contrastPreference) =>
        set({ contrastPreference }),
      setFocusVisible: (focusVisible) => set({ focusVisible }),
      setToastEnabled: (toastEnabled) => set({ toastEnabled }),
      setToastDurationMs: (toastDurationMs) =>
        set({
          toastDurationMs: Math.min(15000, Math.max(1500, toastDurationMs)),
        }),
      setSoundEnabled: (soundEnabled) => set({ soundEnabled }),
      setDefaultWorkspace: (defaultWorkspace) => set({ defaultWorkspace }),
      setRecentItemsLimit: (recentItemsLimit) =>
        set({
          recentItemsLimit: Math.min(24, Math.max(3, Math.round(recentItemsLimit))),
        }),
      setSearchHistoryEnabled: (searchHistoryEnabled) =>
        set({ searchHistoryEnabled }),
      addNote: (text) =>
        set((s) => {
          const trimmed = text.trim();
          if (!trimmed) return s;
          return {
            notes: [
              {
                id: `n-${Date.now()}`,
                text: trimmed,
                at: new Date().toISOString(),
              },
              ...s.notes,
            ].slice(0, 20),
          };
        }),
      removeNote: (id) =>
        set((s) => ({ notes: s.notes.filter((n) => n.id !== id) })),
      resetAppearance: () => set({ ...APPEARANCE_DEFAULTS }),
    }),
    {
      name: "dsp.settings.prefs.v1",
      partialize: (state) => ({
        leftOpen: state.leftOpen,
        rightOpen: state.rightOpen,
        activeSection: state.activeSection,
        density: state.density,
        fontSize: state.fontSize,
        motionPreference: state.motionPreference,
        contrastPreference: state.contrastPreference,
        focusVisible: state.focusVisible,
        toastEnabled: state.toastEnabled,
        toastDurationMs: state.toastDurationMs,
        soundEnabled: state.soundEnabled,
        defaultWorkspace: state.defaultWorkspace,
        recentItemsLimit: state.recentItemsLimit,
        searchHistoryEnabled: state.searchHistoryEnabled,
        notes: state.notes,
      }),
    },
  ),
);

/** Apply UI appearance preferences to the document root (no business logic). */
export function applyAppearanceToDocument(prefs: {
  density: DensityPreference;
  fontSize: FontSizePreference;
  motionPreference: MotionPreference;
  contrastPreference: ContrastPreference;
  focusVisible: boolean;
}): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.dataset.density = prefs.density;
  root.dataset.fontScale = prefs.fontSize;
  root.dataset.motion = prefs.motionPreference;
  root.dataset.contrast = prefs.contrastPreference;
  root.dataset.focusVisible = prefs.focusVisible ? "on" : "off";
}
