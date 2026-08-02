/**
 * EPIC-010 / GA-003 — jsdom-safe axe runner for Vitest automation.
 *
 * color-contrast and target-size need real computed layout/styles; they are
 * disabled here and covered by Lighthouse (see docs/releases/*_CERTIFICATION.md).
 */

import { configureAxe } from "vitest-axe";

/** Rules that are unreliable or false-positive-prone under jsdom. */
const JSDOM_DISABLED_RULES = {
  "color-contrast": { enabled: false },
  "target-size": { enabled: false },
  // Landmark uniqueness often fails on isolated component mounts.
  "region": { enabled: false },
} as const;

export const runAxe = configureAxe({
  rules: { ...JSDOM_DISABLED_RULES },
});

export const A11Y_AUTOMATION_SCOPE = [
  "keyboard-escape-dialogs",
  "aria-dialog-modal",
  "aria-live-loading",
  "empty-state-status",
  "skeleton-decorative",
  "reduced-motion-hooks",
  "touch-target-conventions",
  "axe-core-component-scan",
] as const;
