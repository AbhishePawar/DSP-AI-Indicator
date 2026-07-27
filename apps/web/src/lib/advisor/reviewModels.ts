/**
 * Client review fixtures + pure helpers — reuses research/portfolio/presentation demos.
 */

import { demoResearchEnvelopes } from "./advisorResearchModels";
import { listAdvisorResearchTimeline } from "./advisorResearchViewModel";
import { buildPortfolioReview, seedModelPortfolioLibrary } from "./modelPortfolioManager";
import { seedPresentations } from "./presentationModels";
import type {
  ClientReview,
  ReviewChecklistItem,
  ReviewChecklistItemId,
  ReviewTemplateId,
  ReviewTimelineEvent,
} from "./reviewTypes";
import { CHECKLIST_LABELS, DEFAULT_CHECKLIST_ORDER } from "./reviewTypes";

export const REVIEW_TRUST =
  "Client Review Workflow reuses existing DSP demo research, model portfolios, and presentation packs — never alters Evidence, Confidence, Methodology, Limitations, or research conclusions.";

export function defaultChecklist(
  done: ReviewChecklistItemId[] = [],
): ReviewChecklistItem[] {
  const set = new Set(done);
  return DEFAULT_CHECKLIST_ORDER.map((id) => ({
    id,
    label: CHECKLIST_LABELS[id],
    done: set.has(id),
  }));
}

export type ReviewTemplate = {
  id: ReviewTemplateId;
  name: string;
  blurb: string;
};

export const reviewTemplates: ReviewTemplate[] = [
  {
    id: "tpl-initial-consultation",
    name: "Initial Consultation",
    blurb: "First meeting — profile, objectives, research framing.",
  },
  {
    id: "tpl-quarterly",
    name: "Quarterly Review",
    blurb: "Standard quarterly pack and checklist.",
  },
  {
    id: "tpl-half-year",
    name: "Half-Year Review",
    blurb: "Mid-year risk and allocation check-in.",
  },
  {
    id: "tpl-annual",
    name: "Annual Review",
    blurb: "Full-year research, portfolio, and actions.",
  },
  {
    id: "tpl-special",
    name: "Special Review",
    blurb: "Ad-hoc event-driven review.",
  },
  {
    id: "tpl-custom",
    name: "Custom",
    blurb: "Blank checklist — toggle items in session.",
  },
];

export const seedReviews: ClientReview[] = [
  {
    id: "rev-upcoming-1",
    title: "Client Alpha — Quarterly Review",
    clientAlias: "Client Alpha",
    status: "upcoming",
    templateId: "tpl-quarterly",
    scheduledAt: "2026-07-22T15:00:00.000Z",
    presentationId: "pres-1",
    modelPortfolioId: "mp-lib-balanced",
    envelopeIds: ["re-aurora", "re-beacon"],
    checklist: defaultChecklist(["client_information"]),
    actions: [
      {
        id: "ra-1",
        title: "Confirm education overlay narrative",
        status: "open",
        owner: "Alex Rivera (Demo)",
      },
      {
        id: "ra-2",
        title: "Attach High Quality collection",
        status: "waiting",
        owner: "Research Desk (Demo)",
      },
    ],
    clientQuestions: [
      "How has quality coverage changed? (demo)",
      "Is income overlay still appropriate? (demo)",
    ],
    advisorNotes: "Prep pack linked to Presentation pres-1 — demo only.",
    updatedAt: "2026-07-21T10:00:00.000Z",
  },
  {
    id: "rev-progress-1",
    title: "Client Beta — Income Proposal Review",
    clientAlias: "Client Beta",
    status: "in_progress",
    templateId: "tpl-special",
    scheduledAt: "2026-07-22T17:30:00.000Z",
    presentationId: "pres-2",
    modelPortfolioId: "mp-lib-income",
    envelopeIds: ["re-beacon", "re-delta"],
    checklist: defaultChecklist([
      "client_information",
      "research_updated",
      "portfolio_reviewed",
    ]),
    actions: [
      {
        id: "ra-3",
        title: "Document payout sustainability discussion",
        status: "open",
        owner: "Alex Rivera (Demo)",
      },
      {
        id: "ra-4",
        title: "Mark presentation ready",
        status: "completed",
        owner: "Alex Rivera (Demo)",
      },
    ],
    clientQuestions: ["Dividend coverage outlook? (demo)"],
    advisorNotes: "Income sleeve focus — reuse Beacon/Delta envelopes.",
    updatedAt: "2026-07-22T09:00:00.000Z",
  },
  {
    id: "rev-done-1",
    title: "Client Epsilon — Thematic Review",
    clientAlias: "Client Epsilon",
    status: "completed",
    templateId: "tpl-quarterly",
    scheduledAt: "2026-07-01T16:00:00.000Z",
    presentationId: null,
    modelPortfolioId: "mp-lib-growth",
    envelopeIds: ["re-ember", "re-aurora"],
    checklist: defaultChecklist(DEFAULT_CHECKLIST_ORDER),
    actions: [
      {
        id: "ra-5",
        title: "Archive thematic pins",
        status: "completed",
        owner: "Coverage (Demo)",
      },
      {
        id: "ra-6",
        title: "Defer satellite sleeve change",
        status: "deferred",
        owner: "Alex Rivera (Demo)",
      },
    ],
    clientQuestions: [],
    advisorNotes: "Completed demo review — no engine mutations.",
    updatedAt: "2026-07-02T12:00:00.000Z",
  },
  {
    id: "rev-arch-1",
    title: "Client Delta — Overdue Income Review (archived)",
    clientAlias: "Client Delta",
    status: "archived",
    templateId: "tpl-half-year",
    scheduledAt: "2026-06-15T14:00:00.000Z",
    presentationId: null,
    modelPortfolioId: "mp-lib-income",
    envelopeIds: ["re-beacon"],
    checklist: defaultChecklist(["client_information", "research_updated"]),
    actions: [
      {
        id: "ra-7",
        title: "Reschedule overdue review",
        status: "deferred",
        owner: "Alex Rivera (Demo)",
      },
    ],
    clientQuestions: ["When is the next income check-in? (demo)"],
    advisorNotes: "Archived placeholder for history timeline.",
    updatedAt: "2026-06-20T10:00:00.000Z",
  },
];

export function createReviewFromTemplate(
  templateId: ReviewTemplateId,
  title?: string,
): ClientReview {
  const tpl = reviewTemplates.find((t) => t.id === templateId) ?? reviewTemplates[5];
  return {
    id: `rev-session-${Date.now().toString(36)}`,
    title: title?.trim() || `${tpl.name} (session)`,
    clientAlias: "Client Alpha",
    status: "upcoming",
    templateId: tpl.id,
    scheduledAt: new Date().toISOString(),
    presentationId: seedPresentations[0]?.id ?? null,
    modelPortfolioId: "mp-lib-balanced",
    envelopeIds: ["re-aurora", "re-beacon"],
    checklist: defaultChecklist(),
    actions: [
      {
        id: `ra-${Date.now().toString(36)}`,
        title: "Prepare review pack",
        status: "open",
        owner: "Alex Rivera (Demo)",
      },
    ],
    clientQuestions: ["What changed since last review? (demo)"],
    advisorNotes: "Created from template — session only.",
    updatedAt: new Date().toISOString(),
  };
}

export function checklistCompletionPct(review: ClientReview): number {
  if (!review.checklist.length) return 0;
  const done = review.checklist.filter((c) => c.done).length;
  return Math.round((done / review.checklist.length) * 100);
}

export function buildReviewTimeline(review: ClientReview): ReviewTimelineEvent[] {
  const events: ReviewTimelineEvent[] = [
    {
      id: `${review.id}-current`,
      kind: "current_review",
      label: `Current — ${review.title}`,
      occurredAt: review.scheduledAt,
    },
    {
      id: `${review.id}-upcoming`,
      kind: "upcoming_review",
      label: `Scheduled ${new Date(review.scheduledAt).toLocaleString()}`,
      occurredAt: review.scheduledAt,
    },
  ];
  for (const r of seedReviews.filter((x) => x.clientAlias === review.clientAlias && x.id !== review.id)) {
    events.push({
      id: `prev-${r.id}`,
      kind: r.status === "upcoming" ? "upcoming_review" : "previous_review",
      label: `${r.status.replace(/_/g, " ")} — ${r.title}`,
      occurredAt: r.scheduledAt,
    });
  }
  for (const t of listAdvisorResearchTimeline().slice(0, 3)) {
    events.push({
      id: `res-${t.id}`,
      kind: "research",
      label: t.label,
      occurredAt: t.occurredAt,
    });
  }
  events.push({
    id: `${review.id}-port`,
    kind: "portfolio_change",
    label: `Model portfolio referenced — ${review.modelPortfolioId}`,
    occurredAt: review.updatedAt,
  });
  events.push({
    id: `${review.id}-mtg`,
    kind: "meeting",
    label: `Meeting slot — ${review.clientAlias}`,
    occurredAt: review.scheduledAt,
  });
  return events.sort((a, b) => b.occurredAt.localeCompare(a.occurredAt));
}

export function buildReviewSummary(review: ClientReview) {
  const portfolio =
    seedModelPortfolioLibrary.find((p) => p.id === review.modelPortfolioId) ??
    seedModelPortfolioLibrary[0];
  const envelopes = demoResearchEnvelopes.filter((e) =>
    review.envelopeIds.includes(e.id),
  );
  const reviewHeuristics = buildPortfolioReview(portfolio);
  return {
    executiveSummary: `${review.title} for ${review.clientAlias} using ${portfolio.name} (${portfolio.riskLevel}). Checklist ${checklistCompletionPct(review)}% complete.`,
    discussionPoints: [
      portfolio.objective,
      ...review.clientQuestions,
      `Presentation: ${review.presentationId ?? "not linked"}`,
    ],
    keyRisks: envelopes.flatMap((e) => e.topRisks.map((r) => `${e.companyLabel}: ${r}`)),
    portfolioReview: [
      reviewHeuristics.diversification,
      reviewHeuristics.concentration,
      reviewHeuristics.evidenceCompleteness,
    ],
    recommendedFollowUps: review.actions
      .filter((a) => a.status === "open" || a.status === "waiting")
      .map((a) => a.title),
  };
}

export function buildWorkflowDashboard(reviews: ClientReview[]) {
  const active = reviews.filter((r) => r.status !== "archived");
  const inProgress = reviews.filter((r) => r.status === "in_progress");
  const upcoming = reviews.filter((r) => r.status === "upcoming");
  const actions = reviews.flatMap((r) => r.actions);
  const outstanding = actions.filter(
    (a) => a.status === "open" || a.status === "waiting",
  );
  const avgCompletion =
    active.length === 0
      ? 0
      : Math.round(
          active.reduce((s, r) => s + checklistCompletionPct(r), 0) / active.length,
        );
  const presentationReady = active.filter((r) =>
    r.checklist.some((c) => c.id === "presentation_ready" && c.done),
  ).length;
  const researchCurrency = `${demoResearchEnvelopes.length} demo envelopes available · timeline events loaded`;

  return {
    reviewCompletionPct: avgCompletion,
    outstandingActions: outstanding.length,
    upcomingMeetings: upcoming.length,
    inProgressCount: inProgress.length,
    presentationStatus: `${presentationReady}/${active.length} packs marked ready`,
    researchCurrency,
  };
}
