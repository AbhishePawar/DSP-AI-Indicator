/**
 * EPIC-F000 — Global layout specifications (define only — no new chrome in F000).
 * Existing AppLayout / chrome remain authoritative until F001 redesign.
 */

export const headerSpec = {
  heightPx: 56,
  regions: [
    "brand",
    "globalSearch",
    "legalLinks",
    "themeToggle",
    "notifications",
    "userMenu",
  ],
  a11y: {
    landmark: "banner",
    skipLinkTarget: "#main-content",
  },
  rules: [
    "Brand is visible; never overpowered by secondary chrome",
    "No valuation or recommendation badges in header",
    "Research Mode label when research mode flag is on",
    "Expose Privacy / Terms / Disclaimer links (P4.1)",
  ],
} as const;

export const sidebarSpec = {
  widthPx: { collapsed: 64, expanded: 240 },
  sections: [
    { id: "overview", items: ["dashboard"] },
    { id: "research", items: ["analysis", "research", "portfolio"] },
    { id: "ops", items: ["admin"] },
    { id: "account", items: ["settings", "profile"] },
  ],
  a11y: {
    landmark: "navigation",
    keyboard: "arrow keys + home/end within nav list",
  },
  responsive: {
    mdAndUp: "persistent sidebar",
    belowMd: "drawer / off-canvas",
  },
} as const;

export const footerSpec = {
  regions: ["disclaimer", "legalLinks", "docsLink", "version"],
  rules: [
    "Always show research / not-advice disclaimer in Research Mode",
    "Link Privacy Policy, Terms of Service, and Disclaimer (P4.1)",
    "Show foundation + app version for supportability",
    "No promotional clutter",
  ],
} as const;

export const globalLayoutSpec = {
  structure: ["header", "sidebar", "main", "footer"],
  mainId: "main-content",
  responsiveFirst: true,
  accessibleFirst: true,
} as const;
