/**
 * EPIC-F000 — State management architecture (freeze).
 *
 * Server state → TanStack Query (existing QueryProvider)
 * Client UI state → Zustand (adopt in F001; shell types here)
 * Forms → React Hook Form + Zod (F001+)
 */

export const stateArchitecture = {
  serverState: {
    library: "@tanstack/react-query",
    owner: "providers/QueryProvider",
    rules: [
      "All /api/v1 reads/writes go through Query or typed api client",
      "No parallel ad-hoc caches for the same resource key",
      "Keys must be deterministic tuples",
    ],
  },
  clientState: {
    library: "zustand",
    stores: ["uiStore", "sessionPreferencesStore"],
    rules: [
      "No financial scores or valuation results in Zustand",
      "No duplication of server entity caches",
      "Persist only explicit preference keys",
    ],
  },
  forms: {
    library: "react-hook-form",
    validation: "zod",
    rules: ["Validate at boundary before API mutation"],
  },
  authSession: {
    existing: "lib/auth/sessionStore + AuthProvider",
    rules: [
      "JWT access token only in memory/storage per existing policy",
      "A009 /auth/rbac/* is additive — do not break legacy /auth/login",
    ],
  },
} as const;

/** UI store shape — implemented in F003 (`lib/shell/uiStore`). */
export type UiStoreState = {
  sidebarCollapsed: boolean;
  themePreference: "light" | "dark" | "system";
  notificationCount: number;
};

export const uiStoreDefaults: UiStoreState = {
  sidebarCollapsed: false,
  themePreference: "system",
  notificationCount: 0,
};
