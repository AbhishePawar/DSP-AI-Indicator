/** EPIC-F009 — Settings & User Preferences public exports. */

export {
  LANDING_PAGE_OPTIONS,
  SETTINGS_SECTIONS,
  isSettingsSectionId,
} from "./sections";

export type {
  ContrastPreference,
  DensityPreference,
  FontSizePreference,
  MotionPreference,
  SettingsSectionId,
  SettingsSectionMeta,
} from "./sections";

export {
  applyAppearanceToDocument,
  useSettingsPrefsStore,
} from "./prefsStore";

export type {
  SettingsNote,
} from "./prefsStore";
