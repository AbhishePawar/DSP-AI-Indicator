"use client";

/**
 * EPIC-F009 — Applies local appearance preferences to <html> dataset.
 */

import { useEffect } from "react";

import {
  applyAppearanceToDocument,
  useSettingsPrefsStore,
} from "@/lib/settings";

export function AppearanceApplicator() {
  const density = useSettingsPrefsStore((s) => s.density);
  const fontSize = useSettingsPrefsStore((s) => s.fontSize);
  const motionPreference = useSettingsPrefsStore((s) => s.motionPreference);
  const contrastPreference = useSettingsPrefsStore((s) => s.contrastPreference);
  const focusVisible = useSettingsPrefsStore((s) => s.focusVisible);

  useEffect(() => {
    applyAppearanceToDocument({
      density,
      fontSize,
      motionPreference,
      contrastPreference,
      focusVisible,
    });
  }, [
    density,
    fontSize,
    motionPreference,
    contrastPreference,
    focusVisible,
  ]);

  return null;
}
