/** Marketing copy — Design System brand voice; Research Mode safe. */

export const MARKETING_NAV = [
  { href: "/#features", label: "Features" },
  { href: "/#trust", label: "Trust" },
  { href: "/#workflow", label: "Workflow" },
  { href: "/pricing", label: "Pricing" },
  { href: "/faq", label: "FAQ" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
] as const;

export const FEATURES = [
  {
    title: "Research Workspace",
    body: "Structured company analysis with evidence, explanations, and next investigation steps.",
  },
  {
    title: "Valuation Transparency",
    body: "Intrinsic value language with assumptions, ranges, and confidence — not black-box scores.",
  },
  {
    title: "Business Quality",
    body: "Durability, competitive position, and quality signals independent of short-term price noise.",
  },
  {
    title: "AI Committee",
    body: "Governed AI review that separates interpretation from raw data and calculated metrics.",
  },
  {
    title: "Explainability",
    body: "Every material insight answers what, why, why it matters, and what to investigate next.",
  },
  {
    title: "Institutional Governance",
    body: "Traceability, auditability, and human oversight designed for research accountability.",
  },
] as const;

export const TRUST_PILLARS = [
  {
    title: "Traceable",
    body: "Insights declare their source — statements, calculated metrics, valuation, AI, consensus, or user input.",
  },
  {
    title: "Explainable",
    body: "Conclusions answer the four questions investors need before they act on research.",
  },
  {
    title: "Honest",
    body: "Epistemic categories mark Verified, Calculated, Estimated, AI, Consensus, User, Unknown, or Unavailable.",
  },
  {
    title: "Research first",
    body: "Research Mode educates before recommending. Advice chrome stays gated by policy and compliance flags.",
  },
] as const;

export const WORKFLOW_STEPS = [
  {
    step: "01",
    title: "Gather evidence",
    body: "Filings, statements, and verified datasets enter the research object layer.",
  },
  {
    step: "02",
    title: "Analyse quality & risk",
    body: "Business quality, management, moat, and risk meanings stay distinct and inspectable.",
  },
  {
    step: "03",
    title: "Value with confidence",
    body: "Valuation expresses range, assumptions, and confidence — never false precision.",
  },
  {
    step: "04",
    title: "Conclude & review",
    body: "Decision framework integrates domains; AI Committee and humans can challenge and revise.",
  },
] as const;

export const FAQ_ITEMS = [
  {
    q: "Is DSP AI Indicator investment advice?",
    a: "No. The platform is built for investment research and education. Research Mode is the default presentation. Recommendation surfaces remain policy-gated.",
  },
  {
    q: "Where does analysis run?",
    a: "Analytical reasoning stays on the backend. The web client is a thin presentation layer over frozen /api/v1 responses.",
  },
  {
    q: "How does the AI Committee work?",
    a: "It is a governed review construct for AI-mediated interpretation. It must remain explainable, traceable, and subject to human oversight — not an opaque tip generator.",
  },
  {
    q: "Can I use dark mode?",
    a: "Yes. Light and dark themes use the Institutional Design System tokens. Prefer system, light, or dark from the marketing header or in-app settings.",
  },
  {
    q: "Who is the product for?",
    a: "Independent researchers, boutique desks, and institutions that need calm, evidence-first research tooling rather than tip-app chrome.",
  },
] as const;

export const ABOUT_PARAGRAPHS = [
  "DSP AI Indicator is an institutional research platform designed to make complex analysis understandable without sacrificing honesty.",
  "Our visual and interaction language follows a quiet research-desk philosophy: teal and slate, clear hierarchy, evidence before ornament.",
  "Meaning is governed by the REP-002 Research Ontology and the User Trust Standard. Interfaces present those meanings — they do not invent parallel vocabularies.",
] as const;
