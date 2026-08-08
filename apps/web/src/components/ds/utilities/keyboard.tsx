"use client";

import { useEffect } from "react";

export type KeyboardShortcutOptions = {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  alt?: boolean;
  shift?: boolean;
  enabled?: boolean;
  preventDefault?: boolean;
  /** When true, match either Ctrl (Windows/Linux) or Meta (macOS). */
  mod?: boolean;
};

export function useKeyboardShortcut(
  options: KeyboardShortcutOptions,
  handler: (event: KeyboardEvent) => void,
): void {
  const {
    key,
    ctrl = false,
    meta = false,
    alt = false,
    shift = false,
    enabled = true,
    preventDefault = true,
    mod = false,
  } = options;

  useEffect(() => {
    if (!enabled) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key.toLowerCase() !== key.toLowerCase()) return;

      const modPressed = event.ctrlKey || event.metaKey;
      if (mod) {
        if (!modPressed) return;
      } else {
        if (event.ctrlKey !== ctrl) return;
        if (event.metaKey !== meta) return;
      }
      if (event.altKey !== alt) return;
      if (event.shiftKey !== shift) return;

      if (preventDefault) event.preventDefault();
      handler(event);
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [key, ctrl, meta, alt, shift, enabled, preventDefault, mod, handler]);
}
