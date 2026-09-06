/**
 * SIMPLE-2 — ordinary-client shell profile.
 *
 * Hides secondary products from navigation and command palette.
 * Does not delete routes, APIs, or DSP engines.
 */

import { featureFlags } from "@/lib/featureFlags";

export const ORDINARY_SHELL_ITEM_IDS = new Set([
  "dashboard",
  "analysis",
  "settings",
]);

/** Recoverable in the sidebar only for operators — not ordinary clients. */
export const OPERATOR_SHELL_ITEM_IDS = new Set([
  "admin",
  "control-center",
]);

/** Ordinary left-nav order. Full ANALYSIS_SECTIONS remains recoverable. */
export const ORDINARY_ANALYSIS_SECTION_IDS = [
  "summary",
  "quality",
  "financial",
  "management",
  "moat",
  "risk",
  "valuation",
  "buffett",
  "evidence",
  "explainability",
  "export",
] as const;

export const ORDINARY_SETTINGS_SECTION_IDS = [
  "profile",
  "appearance",
  "security",
  "accessibility",
  "about",
] as const;

export const ORDINARY_LANDING_HREFS = [
  "/dashboard",
  "/analysis",
  "/settings",
] as const;

/** Command palette must not rediscover these surfaces. */
const PALETTE_HIDDEN_PREFIXES = [
  "/intelligence",
  "/companies",
  "/screening",
  "/copilot",
  "/ops",
  "/diagnostics",
  "/advisor",
  "/platform",
  "/launch",
  "/beta",
  "/health",
  "/research",
  "/portfolio",
  "/reports",
  "/dashboards",
  "/saas",
  "/portal",
  "/maintenance",
  "/documentation",
  "/docs",
  "/analysis/compare",
  "/compare",
] as const;

export function ordinaryClientShellEnabled(): boolean {
  return featureFlags.ordinaryClientShell;
}

export function isOperatorUser(
  permissions: readonly string[],
  roles: readonly string[],
): boolean {
  const perms = new Set(permissions.map((p) => p.toLowerCase()));
  const roleSet = new Set(roles.map((r) => r.toLowerCase()));
  if (
    ["manage_users", "manage_roles", "configure_platform", "view_audit", "admin.view", "admin.manage"].some(
      (p) => perms.has(p),
    )
  ) {
    return true;
  }
  return roleSet.has("administrator") || roleSet.has("owner");
}

export function isPaletteHiddenPath(path: string): boolean {
  return PALETTE_HIDDEN_PREFIXES.some(
    (prefix) => path === prefix || path.startsWith(`${prefix}/`),
  );
}

export function showOperationalChrome(): boolean {
  return !ordinaryClientShellEnabled();
}

export function isOrdinaryAnalysisSectionId(id: string): boolean {
  return (ORDINARY_ANALYSIS_SECTION_IDS as readonly string[]).includes(id);
}

export function isOrdinarySettingsSectionId(id: string): boolean {
  return (ORDINARY_SETTINGS_SECTION_IDS as readonly string[]).includes(id);
}
