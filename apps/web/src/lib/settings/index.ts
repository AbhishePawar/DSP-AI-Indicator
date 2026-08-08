/** EPIC-F009 — Settings & User Preferences public exports. */

export {
  LANDING_PAGE_OPTIONS,
  SETTINGS_SECTIONS,
  isSettingsSectionId,
  type ContrastPreference,
  type DensityPreference,
  type FontSizePreference,
  type MotionPreference,
  type SettingsSectionId,
  type SettingsSectionMeta,
} from "./sections";

export {
  applyAppearanceToDocument,
  useSettingsPrefsStore,
  type SettingsNote,
} from "./prefsStore";
