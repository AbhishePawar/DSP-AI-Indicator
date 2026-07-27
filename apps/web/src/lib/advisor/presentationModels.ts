/**
 * Advisor presentation fixtures + builders — reuses research envelopes & model portfolios.
 */

import { listAdvisorResearchTimeline } from "./advisorResearchViewModel";
import { demoResearchEnvelopes } from "./advisorResearchModels";
import {
  buildPortfolioReview,
  marketCapMix,
  sectorMix,
  seedModelPortfolioLibrary,
} from "./modelPortfolioManager";
import type {
  AdvisorCommentary,
  AdvisorPresentation,
  PresentationSectionDef,
  PresentationSectionId,
  PresentationTemplateId,
} from "./presentationTypes";
import {
  DEFAULT_SECTION_ORDER,
  SECTION_LABELS,
} from "./presentationTypes";

export const PRESENTATION_TRUST =
  "Advisor presentations assemble existing DSP demo research and model portfolios only — conclusions, Evidence, Confidence, Methodology, Limitations, and Decision Trace are never rewritten.";

export function defaultSections(
  visible: PresentationSectionId[] = DEFAULT_SECTION_ORDER,
): PresentationSectionDef[] {
  const vis = new Set(visible);
  return DEFAULT_SECTION_ORDER.map((id) => ({
    id,
    label: SECTION_LABELS[id],
    visible: vis.has(id),
  }));
}

export type PresentationTemplate = {
  id: PresentationTemplateId;
  name: string;
  blurb: string;
  sectionIds: PresentationSectionId[];
};

export const presentationTemplates: PresentationTemplate[] = [
  {
    id: "tpl-initial-consultation",
    name: "Initial Consultation",
    blurb: "Objectives, profile, and high-level research framing.",
    sectionIds: [
      "executive_summary",
      "investment_objectives",
      "client_profile",
      "research_summary",
      "disclosures",
    ],
  },
  {
    id: "tpl-quarterly-review",
    name: "Quarterly Review",
    blurb: "Portfolio allocation, risks, notes, timeline.",
    sectionIds: [
      "executive_summary",
      "model_portfolio",
      "portfolio_allocation",
      "risk_review",
      "research_timeline",
      "advisor_notes",
      "disclosures",
    ],
  },
  {
    id: "tpl-annual-review",
    name: "Annual Review",
    blurb: "Full pack with research, opportunities, and disclosures.",
    sectionIds: DEFAULT_SECTION_ORDER,
  },
  {
    id: "tpl-investment-proposal",
    name: "Investment Proposal",
    blurb: "Model portfolio + opportunities + risk review.",
    sectionIds: [
      "executive_summary",
      "investment_objectives",
      "model_portfolio",
      "portfolio_allocation",
      "top_opportunities",
      "risk_review",
      "disclosures",
    ],
  },
  {
    id: "tpl-portfolio-update",
    name: "Portfolio Update",
    blurb: "Allocation and holding summaries.",
    sectionIds: [
      "executive_summary",
      "model_portfolio",
      "portfolio_allocation",
      "advisor_notes",
      "disclosures",
    ],
  },
  {
    id: "tpl-market-commentary",
    name: "Market Commentary",
    blurb: "Research summary and timeline framing.",
    sectionIds: [
      "executive_summary",
      "research_summary",
      "research_timeline",
      "advisor_notes",
      "disclosures",
    ],
  },
  {
    id: "tpl-custom",
    name: "Custom",
    blurb: "All sections available — toggle in builder.",
    sectionIds: DEFAULT_SECTION_ORDER,
  },
];

export const seedPresentations: AdvisorPresentation[] = [
  {
    id: "pres-1",
    title: "Client Alpha — Quarterly Review (demo)",
    clientAlias: "Client Alpha",
    templateId: "tpl-quarterly-review",
    lifecycle: "active",
    sections: defaultSections(presentationTemplates[1].sectionIds),
    modelPortfolioId: "mp-lib-balanced",
    envelopeIds: ["re-aurora", "re-beacon"],
    updatedAt: "2026-07-21T12:00:00.000Z",
  },
  {
    id: "pres-2",
    title: "Client Beta — Income Proposal (demo)",
    clientAlias: "Client Beta",
    templateId: "tpl-investment-proposal",
    lifecycle: "active",
    sections: defaultSections(presentationTemplates[3].sectionIds),
    modelPortfolioId: "mp-lib-income",
    envelopeIds: ["re-beacon", "re-delta"],
    updatedAt: "2026-07-20T09:00:00.000Z",
  },
  {
    id: "pres-3",
    title: "Market Commentary Draft (demo)",
    clientAlias: "Internal",
    templateId: "tpl-market-commentary",
    lifecycle: "active",
    sections: defaultSections(presentationTemplates[5].sectionIds),
    modelPortfolioId: "mp-lib-quality",
    envelopeIds: ["re-aurora", "re-delta", "re-cedar"],
    updatedAt: "2026-07-18T16:00:00.000Z",
  },
];

export const demoCommentaries: AdvisorCommentary[] = [
  {
    id: "ac-1",
    kind: "meeting",
    title: "Meeting notes",
    body: "Demo meeting note: confirmed moderate risk band and income preference.",
  },
  {
    id: "ac-2",
    kind: "action",
    title: "Action items",
    body: "Share High Quality collection · schedule follow-up after quarterly pack.",
  },
  {
    id: "ac-3",
    kind: "suitability",
    title: "Client suitability",
    body: "Demo suitability note: income overlay aligns with stated objectives.",
  },
  {
    id: "ac-4",
    kind: "review",
    title: "Review notes",
    body: "Demo review note: evidence coverage adequate on selected envelopes.",
  },
];

export function createPresentationFromTemplate(
  templateId: PresentationTemplateId,
  title?: string,
): AdvisorPresentation {
  const tpl =
    presentationTemplates.find((t) => t.id === templateId) ?? presentationTemplates[6];
  return {
    id: `pres-session-${Date.now().toString(36)}`,
    title: title?.trim() || `${tpl.name} (session)`,
    clientAlias: "Client Alpha",
    templateId: tpl.id,
    lifecycle: "active",
    sections: defaultSections(tpl.sectionIds),
    modelPortfolioId: "mp-lib-balanced",
    envelopeIds: ["re-aurora", "re-beacon", "re-delta"],
    updatedAt: new Date().toISOString(),
  };
}

export function clonePresentation(src: AdvisorPresentation): AdvisorPresentation {
  return {
    ...src,
    id: `pres-dup-${Date.now().toString(36)}`,
    title: `${src.title} (copy)`,
    lifecycle: "active",
    sections: src.sections.map((s) => ({ ...s })),
    envelopeIds: [...src.envelopeIds],
    updatedAt: new Date().toISOString(),
  };
}

export function buildPresentationMarkdown(pres: AdvisorPresentation): string {
  const lines: string[] = [
    `# ${pres.title}`,
    ``,
    `Client: ${pres.clientAlias} (demo alias)`,
    ``,
    `> ${PRESENTATION_TRUST}`,
    ``,
  ];
  const visible = pres.sections.filter((s) => s.visible);
  for (const section of visible) {
    lines.push(`## ${section.label}`, ``);
    lines.push(...sectionMarkdownBody(pres, section.id), ``);
  }
  return lines.join("\n");
}

export function buildPresentationHtml(pres: AdvisorPresentation): string {
  const md = buildPresentationMarkdown(pres);
  const escaped = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/><title>${pres.title}</title></head><body><pre style="font-family:system-ui;white-space:pre-wrap">${escaped}</pre><p><em>HTML preview — demo presentation pack</em></p></body></html>`;
}

function sectionMarkdownBody(
  pres: AdvisorPresentation,
  id: PresentationSectionId,
): string[] {
  const portfolio =
    seedModelPortfolioLibrary.find((p) => p.id === pres.modelPortfolioId) ??
    seedModelPortfolioLibrary[0];
  const envelopes = demoResearchEnvelopes.filter((e) =>
    pres.envelopeIds.includes(e.id),
  );

  switch (id) {
    case "executive_summary":
      return [
        `Session presentation for **${pres.clientAlias}** using template ${pres.templateId}.`,
        `Model: ${portfolio.name} · Risk ${portfolio.riskLevel} · Horizon ${portfolio.targetHorizon}.`,
        `Research envelopes referenced: ${envelopes.map((e) => e.companyLabel).join(", ")}.`,
      ];
    case "investment_objectives":
      return [`Objective (from model): ${portfolio.objective}`];
    case "client_profile":
      return [
        `Alias: ${pres.clientAlias}`,
        `Demo profile only — no personal information.`,
      ];
    case "research_summary":
      return envelopes.flatMap((e) => [
        `### ${e.companyLabel}`,
        `Thesis: ${e.thesis}`,
        `Business quality: ${e.businessQuality}`,
        `Financial strength: ${e.financialStrength}`,
        `Valuation: ${e.valuationSummary}`,
        `Risk: ${e.risk}`,
        `Confidence: ${e.confidence}`,
        `Evidence: ${e.evidence.join("; ")}`,
        `Methodology: ${e.methodology}`,
        `Limitations: ${e.limitations.join("; ")}`,
        ``,
      ]);
    case "model_portfolio":
      return [
        `${portfolio.name} (${portfolio.category})`,
        `Objective: ${portfolio.objective}`,
        `Risk: ${portfolio.riskLevel}`,
      ];
    case "portfolio_allocation": {
      const sectors = sectorMix(portfolio.holdings);
      const caps = marketCapMix(portfolio.holdings);
      return [
        `Cash: ${portfolio.cashAllocationPct}%`,
        ...portfolio.holdings.map(
          (h) => `- ${h.companyLabel}: ${h.allocationPct}% (${h.sector})`,
        ),
        `Sectors: ${sectors.map((s) => `${s.label} ${s.pct}%`).join("; ")}`,
        `Market caps: ${caps.map((c) => `${c.label} ${c.pct}%`).join("; ")}`,
      ];
    }
    case "top_opportunities":
      return envelopes.flatMap((e) =>
        e.keyOpportunities.map((o) => `- ${e.companyLabel}: ${o}`),
      );
    case "risk_review": {
      const review = buildPortfolioReview(portfolio);
      return [
        ...envelopes.flatMap((e) => e.topRisks.map((r) => `- ${e.companyLabel}: ${r}`)),
        `Diversification: ${review.diversification}`,
        `Concentration: ${review.concentration}`,
      ];
    }
    case "research_timeline":
      return listAdvisorResearchTimeline()
        .slice(0, 5)
        .map((t) => `- ${t.label} (${t.occurredAt})`);
    case "advisor_notes":
      return demoCommentaries.map((c) => `- **${c.title}**: ${c.body}`);
    case "disclosures":
      return [
        "Not investment advice. Demo presentation only.",
        "Research Mode: no BUY/SELL/HOLD or Target Price recommendations.",
        PRESENTATION_TRUST,
      ];
    default:
      return [];
  }
}

export function getPortfolioForPresentation(pres: AdvisorPresentation) {
  return (
    seedModelPortfolioLibrary.find((p) => p.id === pres.modelPortfolioId) ??
    seedModelPortfolioLibrary[0]
  );
}

export function getEnvelopesForPresentation(pres: AdvisorPresentation) {
  return demoResearchEnvelopes.filter((e) => pres.envelopeIds.includes(e.id));
}
