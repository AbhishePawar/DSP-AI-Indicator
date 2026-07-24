"use client";

import { memo, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import Link from "next/link";

import { AdvisorShell } from "@/components/advisor/AdvisorWorkspace";
import { ReviewSidebar } from "@/components/advisor/ReviewSidebar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { WindowedList } from "@/lib/perf/WindowedList";
import { getEnvelope } from "@/lib/advisor/advisorResearchViewModel";
import {
  REVIEW_TRUST,
  buildReviewSummary,
  buildReviewTimeline,
  buildWorkflowDashboard,
  checklistCompletionPct,
  reviewTemplates,
} from "@/lib/advisor/reviewModels";
import {
  archiveSessionReview,
  createSessionReview,
  getReviewSnapshot,
  setActionStatus,
  setActiveReviewId,
  setReviewStatus,
  subscribeReviews,
  toggleChecklistItem,
} from "@/lib/advisor/reviewSession";
import type {
  ClientReview,
  ReviewActionStatus,
  ReviewChecklistItem,
  ReviewStatus,
  ReviewTimelineEvent,
} from "@/lib/advisor/reviewTypes";
import { seedModelPortfolioLibrary } from "@/lib/advisor/modelPortfolioManager";
import { listTasks } from "@/lib/advisor/advisorViewModel";

function useReviewSession() {
  return useSyncExternalStore(subscribeReviews, getReviewSnapshot, getReviewSnapshot);
}

function useActiveReview(): ClientReview | null {
  const { reviews, activeId } = useReviewSession();
  return reviews.find((r) => r.id === activeId) ?? null;
}

function ReviewShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <AdvisorShell title={title} description={description}>
      <p
        role="note"
        className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm"
      >
        {REVIEW_TRUST}
      </p>
      <div className="flex flex-col gap-4 lg:flex-row">
        <ReviewSidebar />
        <div className="min-w-0 flex-1 space-y-4">{children}</div>
      </div>
    </AdvisorShell>
  );
}

function statusTone(status: ReviewStatus): "success" | "warning" | "accent" | "neutral" {
  if (status === "completed") return "success";
  if (status === "in_progress") return "warning";
  if (status === "upcoming") return "accent";
  return "neutral";
}

export function ReviewProgressBadge({ review }: { review: ClientReview }) {
  const pct = checklistCompletionPct(review);
  return (
    <Badge tone={pct === 100 ? "success" : pct > 0 ? "warning" : "neutral"}>
      {pct}% complete
    </Badge>
  );
}

export function ReviewChecklist({
  items,
  reviewId,
}: {
  items: ReviewChecklistItem[];
  reviewId: string;
}) {
  return (
    <Card>
      <CardHeader title="Review checklist" description="Toggle items independently — session only" />
      <CardBody>
        <ul className="space-y-2" aria-label="Review checklist">
          {items.map((item) => (
            <li key={item.id}>
              <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-md border border-[var(--border)] px-3 py-2 text-sm focus-within:ring-2 focus-within:ring-[var(--accent)]">
                <input
                  type="checkbox"
                  checked={item.done}
                  onChange={() => toggleChecklistItem(reviewId, item.id)}
                  aria-label={item.label}
                />
                <span className={item.done ? "text-[var(--muted)] line-through" : "font-medium"}>
                  {item.label}
                </span>
              </label>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

export function ReviewTimeline({ events }: { events: ReviewTimelineEvent[] }) {
  return (
    <Card>
      <CardHeader title="Review timeline" description="Previous · current · upcoming · meetings · research · portfolio" />
      <CardBody>
        <ol className="space-y-3 border-l-2 border-[var(--border)] pl-4" aria-label="Review timeline">
          {events.map((e) => (
            <li key={e.id} className="relative text-sm">
              <span
                className="absolute -left-[1.35rem] top-1.5 h-2.5 w-2.5 rounded-full bg-[var(--accent)]"
                aria-hidden
              />
              <p className="font-medium">{e.label}</p>
              <p className="text-xs text-[var(--muted)]">
                {e.kind.replace(/_/g, " ")} · {new Date(e.occurredAt).toLocaleString()}
              </p>
            </li>
          ))}
        </ol>
      </CardBody>
    </Card>
  );
}

export function MeetingPreparationCard({ review }: { review: ClientReview }) {
  const portfolio =
    seedModelPortfolioLibrary.find((p) => p.id === review.modelPortfolioId) ??
    seedModelPortfolioLibrary[0];
  const tasks = listTasks().filter((t) => t.status !== "done").slice(0, 4);
  const envelopes = review.envelopeIds
    .map((id) => getEnvelope(id))
    .filter(Boolean);

  return (
    <Card>
      <CardHeader
        title="Meeting preparation"
        description={`${review.clientAlias} · ${new Date(review.scheduledAt).toLocaleString()}`}
        action={<ReviewProgressBadge review={review} />}
      />
      <CardBody className="grid gap-4 sm:grid-cols-2 text-sm">
        <section>
          <h3 className="font-medium">Latest research</h3>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {envelopes.map((e) => (
              <li key={e!.id}>
                {e!.companyLabel}: {e!.thesis.slice(0, 80)}…
              </li>
            ))}
          </ul>
        </section>
        <section>
          <h3 className="font-medium">Portfolio summary</h3>
          <p className="mt-1 text-[var(--muted)]">
            {portfolio.name} · {portfolio.riskLevel} · {portfolio.objective}
          </p>
        </section>
        <section>
          <h3 className="font-medium">Outstanding tasks</h3>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {tasks.length === 0 ? (
              <li>None</li>
            ) : (
              tasks.map((t) => <li key={t.id}>{t.title}</li>)
            )}
          </ul>
        </section>
        <section>
          <h3 className="font-medium">Advisor notes</h3>
          <p className="mt-1 text-[var(--muted)] whitespace-pre-wrap">{review.advisorNotes}</p>
        </section>
        <section>
          <h3 className="font-medium">Client questions</h3>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {review.clientQuestions.length === 0 ? (
              <li>None</li>
            ) : (
              review.clientQuestions.map((q) => <li key={q}>{q}</li>)
            )}
          </ul>
        </section>
        <section>
          <h3 className="font-medium">Presentation pack</h3>
          <p className="mt-1 text-[var(--muted)]">
            {review.presentationId ? (
              <Link
                className="text-[var(--accent)] underline"
                href="/advisor/presentations/preview"
              >
                Linked pack {review.presentationId}
              </Link>
            ) : (
              "No presentation linked"
            )}
          </p>
        </section>
      </CardBody>
    </Card>
  );
}

export function ReviewSummaryCard({ review }: { review: ClientReview }) {
  const summary = useMemo(() => buildReviewSummary(review), [review]);
  return (
    <Card>
      <CardHeader
        title="Review summary"
        description="Assembled from existing DSP demo outputs — not regenerated conclusions"
      />
      <CardBody className="space-y-3 text-sm">
        <p>
          <span className="font-medium">Executive summary — </span>
          {summary.executiveSummary}
        </p>
        <div>
          <p className="font-medium">Discussion points</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {summary.discussionPoints.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-medium">Key risks</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {summary.keyRisks.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-medium">Portfolio review</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {summary.portfolioReview.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-medium">Recommended follow-ups</p>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {summary.recommendedFollowUps.length === 0 ? (
              <li>None open</li>
            ) : (
              summary.recommendedFollowUps.map((f) => <li key={f}>{f}</li>)
            )}
          </ul>
        </div>
      </CardBody>
    </Card>
  );
}

const ACTION_STATUSES: ReviewActionStatus[] = ["open", "waiting", "completed", "deferred"];

export function ActionTracker({ review }: { review: ClientReview }) {
  return (
    <Card>
      <CardHeader title="Action tracker" description="Open · Waiting · Completed · Deferred" />
      <CardBody className="space-y-3">
        {ACTION_STATUSES.map((status) => {
          const items = review.actions.filter((a) => a.status === status);
          return (
            <section key={status} aria-labelledby={`actions-${status}`}>
              <h3 id={`actions-${status}`} className="text-sm font-medium capitalize">
                {status} ({items.length})
              </h3>
              {items.length === 0 ? (
                <p className="text-xs text-[var(--muted)]">None</p>
              ) : (
                <ul className="mt-1 space-y-2">
                  {items.map((a) => (
                    <li
                      key={a.id}
                      className="flex flex-wrap items-center gap-2 rounded-md border border-[var(--border)] px-3 py-2 text-sm"
                    >
                      <span className="flex-1 font-medium">{a.title}</span>
                      <span className="text-xs text-[var(--muted)]">{a.owner}</span>
                      <label className="text-xs">
                        Status
                        <select
                          className="ml-1 min-h-9 rounded-md border border-[var(--border)] bg-[var(--surface)] px-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                          value={a.status}
                          onChange={(e) =>
                            setActionStatus(
                              review.id,
                              a.id,
                              e.target.value as ReviewActionStatus,
                            )
                          }
                          aria-label={`Status for ${a.title}`}
                        >
                          {ACTION_STATUSES.map((s) => (
                            <option key={s} value={s}>
                              {s}
                            </option>
                          ))}
                        </select>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          );
        })}
      </CardBody>
    </Card>
  );
}

export function ReviewTemplateCard({
  name,
  blurb,
  onUse,
}: {
  name: string;
  blurb: string;
  onUse?: () => void;
}) {
  return (
    <Card className="dsp-interactive">
      <CardHeader title={name} description={blurb} action={<Badge tone="accent">Template</Badge>} />
      <CardBody>
        {onUse ? (
          <Button type="button" variant="secondary" onClick={onUse}>
            Start review
          </Button>
        ) : null}
      </CardBody>
    </Card>
  );
}

export function WorkflowDashboard({ reviews }: { reviews: ClientReview[] }) {
  const dash = useMemo(() => buildWorkflowDashboard(reviews), [reviews]);
  const tiles = [
    { label: "Review completion", value: `${dash.reviewCompletionPct}%` },
    { label: "Outstanding actions", value: String(dash.outstandingActions) },
    { label: "Upcoming meetings", value: String(dash.upcomingMeetings) },
    { label: "In progress", value: String(dash.inProgressCount) },
    { label: "Presentation status", value: dash.presentationStatus },
    { label: "Research currency", value: dash.researchCurrency },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {tiles.map((t) => (
        <Card key={t.label} className="dsp-interactive">
          <CardHeader title={t.label} />
          <CardBody className="text-sm font-medium leading-snug">{t.value}</CardBody>
        </Card>
      ))}
    </div>
  );
}

function ReviewLane({
  status,
  label,
  reviews,
}: {
  status: ReviewStatus;
  label: string;
  reviews: ClientReview[];
}) {
  const items = reviews.filter((r) => r.status === status);
  return (
    <section aria-labelledby={`lane-${status}`} className="space-y-2">
      <h2 id={`lane-${status}`} className="font-[family-name:var(--font-display)] text-lg">
        {label}{" "}
        <span className="text-[var(--muted)]">({items.length})</span>
      </h2>
      <WindowedList
        items={items}
        initial={6}
        empty={<p className="text-sm text-[var(--muted)]">None</p>}
        className="grid gap-3 md:grid-cols-2"
        renderItem={(r) => (
          <Card key={r.id} className="dsp-interactive">
            <CardHeader
              title={r.title}
              description={r.clientAlias}
              action={
                <div className="flex flex-wrap gap-1">
                  <Badge tone={statusTone(r.status)}>{r.status.replace(/_/g, " ")}</Badge>
                  <ReviewProgressBadge review={r} />
                </div>
              }
            />
            <CardBody className="flex flex-wrap gap-2">
              <Link href="/advisor/reviews/active">
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => setActiveReviewId(r.id)}
                >
                  Open
                </Button>
              </Link>
              {r.status === "upcoming" ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => setReviewStatus(r.id, "in_progress")}
                >
                  Start
                </Button>
              ) : null}
              {r.status === "in_progress" ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => setReviewStatus(r.id, "completed")}
                >
                  Complete
                </Button>
              ) : null}
              {r.status !== "archived" ? (
                <Button
                  type="button"
                  size="sm"
                  variant="danger"
                  onClick={() => archiveSessionReview(r.id)}
                >
                  Archive
                </Button>
              ) : null}
            </CardBody>
          </Card>
        )}
      />
    </section>
  );
}

export const ClientReviewWorkspace = memo(function ClientReviewWorkspace() {
  const { reviews } = useReviewSession();
  return (
    <ReviewShell
      title="Client Review Workspace"
      description="Upcoming · In Progress · Completed · Archived — session guided workflow."
    >
      <ReviewLane status="upcoming" label="Upcoming Reviews" reviews={reviews} />
      <ReviewLane status="in_progress" label="In Progress" reviews={reviews} />
      <ReviewLane status="completed" label="Completed" reviews={reviews} />
      <ReviewLane status="archived" label="Archived" reviews={reviews} />
    </ReviewShell>
  );
});

export const ActiveReviewWorkspace = memo(function ActiveReviewWorkspace() {
  const { reviews, activeId } = useReviewSession();
  const review = reviews.find((r) => r.id === activeId) ?? null;
  const timeline = useMemo(
    () => (review ? buildReviewTimeline(review) : []),
    [review],
  );

  if (!review) {
    return (
      <ReviewShell title="Active Review">
        <EmptyState title="No active review" description="Open one from the workspace." />
      </ReviewShell>
    );
  }

  return (
    <ReviewShell
      title={review.title}
      description={`${review.clientAlias} · ${review.templateId}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={statusTone(review.status)}>{review.status.replace(/_/g, " ")}</Badge>
        <ReviewProgressBadge review={review} />
        <label className="text-sm">
          Switch review
          <select
            className="ml-2 min-h-11 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            value={review.id}
            onChange={(e) => setActiveReviewId(e.target.value)}
          >
            {reviews
              .filter((r) => r.status !== "archived")
              .map((r) => (
                <option key={r.id} value={r.id}>
                  {r.title}
                </option>
              ))}
          </select>
        </label>
      </div>
      <MeetingPreparationCard review={review} />
      <ReviewChecklist items={review.checklist} reviewId={review.id} />
      <ReviewTimeline events={timeline} />
      <ReviewSummaryCard review={review} />
      <ActionTracker review={review} />
    </ReviewShell>
  );
});

export const WorkflowDashboardWorkspace = memo(function WorkflowDashboardWorkspace() {
  const { reviews } = useReviewSession();
  return (
    <ReviewShell
      title="Workflow Dashboard"
      description="Completion · actions · meetings · presentations · research currency"
    >
      <WorkflowDashboard reviews={reviews} />
    </ReviewShell>
  );
});

export const ReviewTemplatesWorkspace = memo(function ReviewTemplatesWorkspace() {
  const [title, setTitle] = useState("");
  return (
    <ReviewShell title="Review Templates" description="Initial Consultation → Custom">
      <label className="block text-sm">
        Optional title
        <input
          className="mt-1 min-h-11 w-full max-w-md rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>
      <div className="grid gap-3 md:grid-cols-2">
        {reviewTemplates.map((t) => (
          <ReviewTemplateCard
            key={t.id}
            name={t.name}
            blurb={t.blurb}
            onUse={() => {
              createSessionReview(t.id, title || undefined);
              setTitle("");
            }}
          />
        ))}
      </div>
    </ReviewShell>
  );
});
