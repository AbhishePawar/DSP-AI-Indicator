/**
 * EPIC-F000 — UX strategies (loading / empty / error / notifications).
 */

export const loadingStrategy = {
  page: "Route-level loading.tsx skeletons — no spinner-only dead ends",
  section: "Inline skeleton matching final layout geometry",
  button: "Disable + aria-busy during mutation",
  rules: ["Never block entire app on non-critical queries"],
} as const;

export const emptyStrategy = {
  copy: "Data unavailable.",
  rules: [
    "Explain what is missing and the next investigation step",
    "Never invent placeholder metrics",
    "Offer navigation to a valid next route when possible",
  ],
} as const;

export const errorStrategy = {
  boundary: "GlobalErrorBoundary (existing)",
  api: "Map ApiClientError → toast + inline alert",
  rules: [
    "No stack traces in production UI",
    "Preserve request id / correlation when present",
    "Auth 401 → session recovery / login redirect",
    "Auth 403 → permission denied empty state",
  ],
} as const;

export const notificationStrategy = {
  provider: "providers/NotificationProvider (existing)",
  types: ["info", "success", "warning", "error"],
  rules: [
    "Trust-critical failures stay visible until dismissed",
    "Do not use toasts for primary research conclusions",
  ],
} as const;
