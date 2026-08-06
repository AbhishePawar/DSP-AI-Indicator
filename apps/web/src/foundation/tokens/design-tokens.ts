/**
 * EPIC-F000 — Design tokens (PR1.2 Visual Language aligned).
 * Source of truth for TypeScript consumers; CSS vars remain in globals.css.
 */

export const colorTokens = {
  light: {
    bg: "#f3efe6",
    fg: "#1c2421",
    muted: "#5c6b66",
    surface: "#fffdf8",
    surface2: "#ebe4d6",
    border: "#d5ccbc",
    accent: "#0f6e56",
    accentFg: "#f4fff9",
    accentSoft: "#d8f0e6",
    dangerBg: "#fde8e4",
    dangerFg: "#7a2e22",
    dangerBorder: "#e7b1a6",
    warningBg: "#f7ecd2",
    warningFg: "#7a5a12",
  },
  dark: {
    bg: "#0a0e12",
    fg: "#d4dce4",
    muted: "#7b8fa0",
    surface: "#0f1318",
    surface2: "#161c22",
    border: "#1e2830",
    accent: "#2cb67d",
    accentFg: "#0a0e12",
    accentSoft: "#1a2f26",
    dangerBg: "#2a1215",
    dangerFg: "#f87171",
    dangerBorder: "#4c1d1d",
    warningBg: "#2a2412",
    warningFg: "#fbbf24",
  },
} as const;

/** Forbidden brand accents (VLIS / product constitution). */
export const forbiddenAccents = ["purple", "magenta", "neon"] as const;

export const typographyTokens = {
  display: 'var(--font-display)',
  body: 'var(--font-body)',
  scale: {
    xs: "0.75rem",
    sm: "0.875rem",
    base: "1rem",
    lg: "1.125rem",
    xl: "1.25rem",
    "2xl": "1.5rem",
    "3xl": "1.875rem",
    "4xl": "2.25rem",
  },
  weight: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  lineHeight: {
    tight: 1.25,
    snug: 1.375,
    normal: 1.5,
    relaxed: 1.625,
  },
} as const;

export const spacingTokens = {
  0: "0",
  1: "0.25rem",
  2: "0.5rem",
  3: "0.75rem",
  4: "1rem",
  5: "1.25rem",
  6: "1.5rem",
  8: "2rem",
  10: "2.5rem",
  12: "3rem",
  16: "4rem",
  20: "5rem",
  24: "6rem",
} as const;

/** Responsive-first breakpoints (min-width). */
export const breakpointTokens = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;

export const radiusTokens = {
  sm: "0.375rem",
  md: "0.5rem",
  lg: "0.75rem",
  xl: "1rem",
} as const;

export const zIndexTokens = {
  base: 0,
  sticky: 20,
  header: 40,
  sidebar: 30,
  overlay: 50,
  modal: 60,
  toast: 70,
} as const;
