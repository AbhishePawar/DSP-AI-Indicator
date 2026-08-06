/**
 * EPIC-F009 — Settings section registry.
 */

export type SettingsSectionId =
  | "profile"
  | "appearance"
  | "dashboard"
  | "workspace"
  | "notifications"
  | "security"
  | "accessibility"
  | "about";

export type SettingsSectionMeta = {
  id: SettingsSectionId;
  label: string;
  description: string;
  shortcut: string;
};

export const SETTINGS_SECTIONS: readonly SettingsSectionMeta[] = [
  {
    id: "profile",
    label: "Profile",
    description: "Account, roles, and session summary",
    shortcut: "1",
  },
  {
    id: "appearance",
    label: "Appearance",
    description: "Theme, density, and typography",
    shortcut: "2",
  },
  {
    id: "dashboard",
    label: "Dashboard",
    description: "Widget layout preferences",
    shortcut: "3",
  },
  {
    id: "workspace",
    label: "Workspace",
    description: "Sidebar, landing, and recent items",
    shortcut: "4",
  },
  {
    id: "notifications",
    label: "Notifications",
    description: "Toast and alert preferences",
    shortcut: "5",
  },
  {
    id: "security",
    label: "Security",
    description: "Sessions and token information",
    shortcut: "6",
  },
  {
    id: "accessibility",
    label: "Accessibility",
    description: "Motion, contrast, and focus",
    shortcut: "7",
  },
  {
    id: "about",
    label: "About",
    description: "Versions and documentation",
    shortcut: "8",
  },
] as const;

export function isSettingsSectionId(value: string): value is SettingsSectionId {
  return SETTINGS_SECTIONS.some((s) => s.id === value);
}

export const LANDING_PAGE_OPTIONS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/analysis", label: "Analysis" },
  { href: "/research", label: "Research" },
  { href: "/companies", label: "Companies" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/settings", label: "Settings" },
] as const;

export type DensityPreference = "comfortable" | "compact";
export type FontSizePreference = "sm" | "md" | "lg";
export type MotionPreference = "system" | "full" | "reduce";
export type ContrastPreference = "system" | "more";
