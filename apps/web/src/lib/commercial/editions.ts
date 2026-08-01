/**
 * P6.1 — Commercial product packaging (presentation / ops metadata only).
 * Does not gate engines or invent analytical capabilities.
 */

export type ProductEditionId = "research" | "professional" | "enterprise";

export type ProductEdition = {
  id: ProductEditionId;
  name: string;
  tagline: string;
  audience: string;
  monthlyPriceUsd: number | null;
  annualPriceUsd: number | null;
  trialDays: number;
  seatsIncluded: number | "custom";
  analysesPerMonth: number | "unlimited";
  exportsPerMonth: number | "unlimited";
  features: Record<string, boolean | string>;
};

/** Feature matrix — commercial packaging only; Research Mode remains default. */
export const PRODUCT_EDITIONS: ProductEdition[] = [
  {
    id: "research",
    name: "Research",
    tagline: "Individual research workspace",
    audience: "Independent analysts and learners",
    monthlyPriceUsd: 0,
    annualPriceUsd: 0,
    trialDays: 0,
    seatsIncluded: 1,
    analysesPerMonth: 25,
    exportsPerMonth: 10,
    features: {
      companyAnalysis: true,
      researchWorkspace: true,
      explainability: true,
      valuationTransparency: true,
      buffettIndicator: true,
      institutionalRatings: true,
      portfolioDemo: true,
      adminConsole: false,
      closedBetaTools: true,
      sso: false,
      dedicatedSupport: false,
      sla: "Best effort",
    },
  },
  {
    id: "professional",
    name: "Professional",
    tagline: "Team research operations",
    audience: "Boutique research desks and RIAs (research use)",
    monthlyPriceUsd: 149,
    annualPriceUsd: 1490,
    trialDays: 14,
    seatsIncluded: 5,
    analysesPerMonth: 500,
    exportsPerMonth: 200,
    features: {
      companyAnalysis: true,
      researchWorkspace: true,
      explainability: true,
      valuationTransparency: true,
      buffettIndicator: true,
      institutionalRatings: true,
      portfolioDemo: true,
      adminConsole: true,
      closedBetaTools: true,
      sso: false,
      dedicatedSupport: false,
      sla: "Business hours",
    },
  },
  {
    id: "enterprise",
    name: "Enterprise",
    tagline: "Institutional deployment",
    audience: "Banks, funds, and platforms needing SSO and SLAs",
    monthlyPriceUsd: null,
    annualPriceUsd: null,
    trialDays: 30,
    seatsIncluded: "custom",
    analysesPerMonth: "unlimited",
    exportsPerMonth: "unlimited",
    features: {
      companyAnalysis: true,
      researchWorkspace: true,
      explainability: true,
      valuationTransparency: true,
      buffettIndicator: true,
      institutionalRatings: true,
      portfolioDemo: true,
      adminConsole: true,
      closedBetaTools: true,
      sso: true,
      dedicatedSupport: true,
      sla: "Contracted",
    },
  },
];

export const FEATURE_MATRIX_ROWS = [
  { key: "companyAnalysis", label: "Company Analysis" },
  { key: "researchWorkspace", label: "Research Workspace" },
  { key: "explainability", label: "Explainability" },
  { key: "valuationTransparency", label: "Valuation Transparency" },
  { key: "buffettIndicator", label: "Buffett Indicator" },
  { key: "institutionalRatings", label: "Institutional Ratings" },
  { key: "portfolioDemo", label: "Portfolio Intelligence (demo)" },
  { key: "adminConsole", label: "Admin Console" },
  { key: "sso", label: "SSO / IdP" },
  { key: "dedicatedSupport", label: "Dedicated support" },
  { key: "sla", label: "Support SLA" },
] as const;

export const SUPPORT_CONTACT = {
  /** Placeholder domain — not a live mailbox until ops publishes production channels. */
  email: "support@dsp-ai-indicator.example",
  salesEmail: "sales@dsp-ai-indicator.example",
  securityEmail: "security@dsp-ai-indicator.example",
  hours: "Mon–Fri 09:00–18:00 IST (Enterprise per contract)",
  knowledgeBasePath: "/docs",
  faqPath: "/docs/faq",
  statusPageNote: "Operator-managed status page (configure externally)",
  /** Honest RC disclosure when contacts are not yet production mailboxes. */
  channelsPublished: false,
  unpublishedNote:
    "Contact channels are not published for this release candidate. Use in-app beta feedback or your programme administrator.",
} as const;

/**
 * RC honesty gate: dollar amounts and quotas in PRODUCT_EDITIONS are packaging
 * sketches, not live checkout / entitlement facts until a commercial CMS or
 * billing API is wired.
 */
export const COMMERCIAL_PRICING_DISCLOSURE =
  "Illustrative packaging for this release candidate — not a live offer, checkout, or entitlement. Contact your programme administrator for access.";

export const SAMPLE_ANALYSIS_SYMBOL = "AAPL" as const;

export const COMMERCIAL_CHANNEL = "rc" as const;
