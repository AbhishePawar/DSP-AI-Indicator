/**
 * EPIC-F010 — Responsive workspace chrome helpers (quality only).
 */

"use client";

import { useEffect } from "react";

/** Collapse stacked left/right workspace panels on viewports below lg (1024px). */
export function useCollapsePanelsBelowLg(
  setLeftOpen: (open: boolean) => void,
  setRightOpen: (open: boolean) => void,
): void {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (typeof window.matchMedia !== "function") return;
    if (window.matchMedia("(max-width: 1023px)").matches) {
      setLeftOpen(false);
      setRightOpen(false);
    }
  }, [setLeftOpen, setRightOpen]);
}

/** Canonical viewport widths for responsive validation (px). */
export const RESPONSIVE_VIEWPORTS = [
  320, 375, 390, 414, 768, 1024, 1280, 1440, 1920,
] as const;

export const CRITICAL_ROUTES = [
  "/login",
  "/dashboard",
  "/analysis",
  "/portfolio",
  "/research",
  "/admin",
  "/settings",
] as const;
