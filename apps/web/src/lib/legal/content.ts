/**
 * P4.1 — Legal & compliance presentation content (frontend only).
 * Operational summaries for transparency; not a substitute for jurisdictional counsel.
 */

export const LEGAL_DOC_VERSION = "1.6.0" as const;
export const LEGAL_EFFECTIVE_DATE = "2026-07-28" as const;

export type LegalSection = { heading: string; body: string[] };

export type LegalDocumentId =
  | "privacy"
  | "terms"
  | "disclaimer"
  | "risk"
  | "cookies"
  | "data-usage";

export const LEGAL_ROUTES = {
  privacy: "/docs/privacy",
  terms: "/docs/terms",
  disclaimer: "/docs/disclaimer",
  risk: "/docs/risk-disclosure",
  cookies: "/docs/cookie-policy",
  dataUsage: "/docs/data-usage",
  docsIndex: "/docs",
} as const;

export const privacyPolicySections: LegalSection[] = [
  {
    heading: "Overview",
    body: [
      "DSP AI Indicator (“DSP”) processes account credentials, session tokens, research request metadata, and optional browser-stored preferences to deliver research intelligence.",
      "This Privacy Policy describes what we collect, why we collect it, and how you can exercise your rights. It is an operational summary for product transparency and does not replace jurisdictional legal review.",
    ],
  },
  {
    heading: "Data we collect",
    body: [
      "Account and authentication data: username, display name, email (when provided), role/permissions, and session tokens issued by the backend.",
      "Research usage metadata: ticker symbols requested, timestamps, correlation identifiers returned by the API, and client-side session preferences.",
      "Optional local feedback: beta feedback stored in the browser after redaction of tokens/JWTs. Feedback must not include research envelopes, portfolio holdings, or API secrets.",
      "Technical logs (operator-controlled): server-side access and error logs configured by the platform operator. Operators should avoid unnecessary PII in logs.",
    ],
  },
  {
    heading: "How we use data",
    body: [
      "To authenticate users, authorize research endpoints, and display frozen /api/v1 research outputs.",
      "To persist optional UI preferences and research session caches in the browser for continuity.",
      "To improve reliability and security of the service (health, rate limits, audit trails) without changing valuation or recommendation engines in the browser.",
    ],
  },
  {
    heading: "Cookies and local storage",
    body: [
      "DSP uses first-party browser storage for session continuity, theme/preferences, research disclaimer acknowledgement, and optional feedback drafts.",
      "No third-party advertising analytics SDK is required for Web 1.6.0. See the Cookie Policy for details.",
    ],
  },
  {
    heading: "Sharing",
    body: [
      "Research requests are sent to your configured DSP API base URL. DSP does not sell personal data.",
      "Operators may engage infrastructure providers under their own agreements. Subprocessors are controlled by the deploying organization.",
    ],
  },
  {
    heading: "Retention",
    body: [
      "Browser-stored preferences and acknowledgement flags remain until cleared by the user or browser.",
      "Server-side retention follows the operator’s retention policy for auth sessions, logs, and research audit records.",
    ],
  },
  {
    heading: "Your rights",
    body: [
      "Account management: update profile and sessions via Profile / Settings where enabled.",
      "Data access: request a summary of account and research-metadata held by your operator.",
      "Data deletion: request deletion of account data and local clearance instructions for browser storage.",
      "Contact: privacy requests — privacy@dsp-ai-indicator.example (operator may substitute a production address).",
      "Complaints: escalate via your organization’s compliance channel, then to the contact above if unresolved.",
    ],
  },
  {
    heading: "Contact",
    body: [
      `Effective date: ${LEGAL_EFFECTIVE_DATE}. Document version: ${LEGAL_DOC_VERSION}.`,
      "For data requests or privacy questions, contact your DSP platform administrator or privacy@dsp-ai-indicator.example.",
    ],
  },
];

export const termsOfServiceSections: LegalSection[] = [
  {
    heading: "Agreement",
    body: [
      "By accessing DSP AI Indicator you agree to these Terms of Service and the Investment Research Disclaimer.",
      "If you use DSP on behalf of an organization, you represent that you are authorized to accept these terms for that organization.",
    ],
  },
  {
    heading: "Service description",
    body: [
      "DSP provides research intelligence, educational explanations, and related tooling via a thin client that consumes frozen /api/v1 contracts.",
      "DSP does not provide brokerage, order execution, custody, or personalized investment advice.",
    ],
  },
  {
    heading: "Acceptable use",
    body: [
      "Use DSP only within your authorization and applicable law.",
      "Do not bypass authentication, scrape undisclosed APIs, reverse-engineer restricted components, or attempt to extract secrets.",
      "Do not use DSP outputs as the sole basis for regulated investment decisions without independent review.",
    ],
  },
  {
    heading: "Accounts and security",
    body: [
      "You are responsible for safeguarding credentials and for activity under your account.",
      "Notify your administrator promptly of suspected unauthorized access.",
    ],
  },
  {
    heading: "Intellectual property",
    body: [
      "DSP software, branding, and documentation remain the property of their respective owners.",
      "Research outputs remain subject to source data licenses and operator policies.",
    ],
  },
  {
    heading: "Disclaimers and limitation of liability",
    body: [
      "The service is provided “as is” for research and education. See the Investment Research Disclaimer and Risk Disclosure.",
      "To the fullest extent permitted by law, DSP and operators are not liable for investment losses arising from use of research outputs.",
    ],
  },
  {
    heading: "Changes",
    body: [
      `We may update these terms; the effective date and version (${LEGAL_DOC_VERSION}) will be revised on this page.`,
      "Continued use after updates constitutes acceptance of the revised terms where permitted by law.",
    ],
  },
];

export const investmentResearchDisclaimerSections: LegalSection[] = [
  {
    heading: "Research and education only",
    body: [
      "DSP reports, scores, narratives, and dashboards are for research and educational purposes.",
      "They are not personalized investment advice, solicitations, or recommendations to buy, sell, or hold any security or instrument.",
    ],
  },
  {
    heading: "No personalised advice",
    body: [
      "Outputs are generated from shared models and published research pipelines. They do not consider your personal financial situation, objectives, or risk tolerance.",
      "Nothing in DSP constitutes a client–adviser relationship.",
    ],
  },
  {
    heading: "Investing involves risk",
    body: [
      "All investing involves risk, including possible loss of principal. Markets can move against any thesis.",
      "See the Risk Disclosure for additional risk categories.",
    ],
  },
  {
    heading: "Past performance",
    body: [
      "Past performance, historical patterns, backtests, and prior model scores do not guarantee future results.",
    ],
  },
  {
    heading: "Your due diligence",
    body: [
      "Users should perform their own due diligence and, where appropriate, consult a qualified financial adviser or other licensed professional.",
      "Always review Evidence, Confidence, Methodology, Limitations, and report metadata before relying on any insight.",
    ],
  },
  {
    heading: "Honest labelling",
    body: [
      "Missing inputs are labelled Unavailable. Categories such as Verified, Calculated, Estimated, AI, Consensus, User, Unknown, or Unavailable describe honesty of the claim — never fabricate values in the browser.",
    ],
  },
];

export const riskDisclosureSections: LegalSection[] = [
  {
    heading: "Market and investment risk",
    body: [
      "Equity and related instruments can decline in value. Liquidity, volatility, currency, and geopolitical events can amplify losses.",
    ],
  },
  {
    heading: "Model and data risk",
    body: [
      "Models may be wrong, incomplete, delayed, or based on unavailable inputs. Confidence scores are not guarantees.",
      "Data providers may revise filings or quotes; DSP reflects backend payloads as received.",
    ],
  },
  {
    heading: "Operational risk",
    body: [
      "Service interruptions, API errors, or client cache staleness may delay or prevent report generation.",
    ],
  },
  {
    heading: "Regulatory and jurisdiction risk",
    body: [
      "Availability of features may depend on SEBI / research-mode flags and operator configuration. Research Mode labels apply unless compliance flags unlock additional surfaces.",
    ],
  },
];

export const cookiePolicySections: LegalSection[] = [
  {
    heading: "What we use",
    body: [
      "DSP uses first-party cookies and/or localStorage / sessionStorage for authentication continuity (as configured), theme and UI preferences, research disclaimer acknowledgement, and optional beta feedback drafts.",
    ],
  },
  {
    heading: "Third parties",
    body: [
      "Web 1.6.0 does not require a third-party advertising or analytics cookie SDK. Operators may add infrastructure monitoring outside this client under their own policies.",
    ],
  },
  {
    heading: "Control",
    body: [
      "You can clear site data in your browser to remove local preferences and acknowledgement flags. Clearing storage may require re-acknowledging the research disclaimer before generating reports.",
    ],
  },
];

export const dataUsagePolicySections: LegalSection[] = [
  {
    heading: "Data sources",
    body: [
      "Primary research inputs arrive from the DSP backend via frozen /api/v1 (analyse and related composition routes).",
      "Underlying sources may include financial statements, calculated metrics, valuation engine outputs, AI committee narratives, and external consensus when the backend supplies them.",
      "The thin client does not invent valuations, recommendations, or AI reasoning in the browser.",
    ],
  },
  {
    heading: "Update frequency",
    body: [
      "Market quotes refresh according to client cache TTLs (typically on the order of one minute when configured) and backend availability.",
      "Full research reports refresh when the user (or workspace auto-run) requests analyse; cached browser sessions may show prior payloads until regenerated.",
      "Exact upstream filing/quote cadences are controlled by data providers and the backend — where unknown, DSP does not invent a cadence.",
    ],
  },
  {
    heading: "Unavailable data",
    body: [
      "When a field, stage, or metric is missing, the UI labels it Unavailable (or equivalent honest category). The client must not fabricate substitutes.",
    ],
  },
  {
    heading: "Confidence methodology",
    body: [
      "Confidence values displayed in the UI are those returned by the backend (for example confidence_summary and stage confidence). The client maps and explains them; it does not recompute institutional scores.",
    ],
  },
  {
    heading: "Report versioning",
    body: [
      "Reports expose metadata such as api_version, platform_version, pipeline_version, correlation_id, and stage execution order when present in the payload.",
      "Frontend foundation version is shown in the status bar for supportability and does not alter backend contracts.",
    ],
  },
  {
    heading: "User rights summary",
    body: [
      "Account management, data access, deletion requests, contact, and complaint process are described in the Privacy Policy.",
    ],
  },
];

export const LEGAL_DOCUMENTS: Record<
  LegalDocumentId,
  { title: string; href: string; sections: LegalSection[]; repoDoc: string }
> = {
  privacy: {
    title: "Privacy Policy",
    href: LEGAL_ROUTES.privacy,
    sections: privacyPolicySections,
    repoDoc: "docs/PRIVACY_POLICY_v1.6.0.md",
  },
  terms: {
    title: "Terms of Service",
    href: LEGAL_ROUTES.terms,
    sections: termsOfServiceSections,
    repoDoc: "docs/TERMS_OF_SERVICE_v1.6.0.md",
  },
  disclaimer: {
    title: "Investment Research Disclaimer",
    href: LEGAL_ROUTES.disclaimer,
    sections: investmentResearchDisclaimerSections,
    repoDoc: "docs/INVESTMENT_RESEARCH_DISCLAIMER_v1.6.0.md",
  },
  risk: {
    title: "Risk Disclosure",
    href: LEGAL_ROUTES.risk,
    sections: riskDisclosureSections,
    repoDoc: "docs/RISK_DISCLOSURE_v1.6.0.md",
  },
  cookies: {
    title: "Cookie Policy",
    href: LEGAL_ROUTES.cookies,
    sections: cookiePolicySections,
    repoDoc: "docs/COOKIE_POLICY_v1.6.0.md",
  },
  "data-usage": {
    title: "Data Usage Policy",
    href: LEGAL_ROUTES.dataUsage,
    sections: dataUsagePolicySections,
    repoDoc: "docs/DATA_USAGE_POLICY_v1.6.0.md",
  },
};

/** Short bullets shown in the first-report acknowledgement dialog. */
export const DISCLAIMER_ACK_BULLETS = [
  "Reports are for research and educational purposes only.",
  "They are not personalised investment advice.",
  "Investing involves risk, including loss of principal.",
  "Past performance does not guarantee future results.",
  "I will perform my own due diligence or consult a qualified financial adviser.",
] as const;
