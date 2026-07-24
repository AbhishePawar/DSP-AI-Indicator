"use client";

import {
  memo,
  useCallback,
  useMemo,
  useState,
  useSyncExternalStore,
  type DragEvent,
  type ReactNode,
} from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { CollaborationLayout } from "@/components/advisor/TeamCollaboration";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { WindowedList } from "@/lib/perf/WindowedList";
import type { ClientReview } from "@/lib/advisor/reviewTypes";
import {
  FILTER_CLIENTS,
  FILTER_MEETING_TYPES,
  FILTER_PORTFOLIOS,
  TEAM_REVIEW_TRUST,
} from "@/lib/advisor/teamReviewModels";
import {
  ASSIGNMENT_COLUMNS,
  buildReviewProgress,
  buildTeamReviewOverview,
  filterTeamReviews,
  getAssignment,
  getTeamReviewSnapshot,
  laneReviews,
  moveAssignment,
  openTeamReview,
  resetTeamReviewFilters,
  reviewsByColumn,
  setActiveDiscussionId,
  setAssignmentOwner,
  setAssignmentPriority,
  setTeamReviewFilters,
  subscribeTeamReview,
  updateReviewDiscussion,
} from "@/lib/advisor/teamReviewSession";
import {
  DEMO_OWNERS,
  TEAM_REVIEW_NAV,
  type AssignmentColumnId,
  type AssignmentPriority,
  type TeamReviewActivityItem,
} from "@/lib/advisor/teamReviewTypes";

function useTeamReview() {
  return useSyncExternalStore(
    subscribeTeamReview,
    getTeamReviewSnapshot,
    getTeamReviewSnapshot,
  );
}

/* ── Badges ─────────────────────────────────────────────────────── */

export function ReviewStatusBadge({ status }: { status: string }) {
  return <Badge>{status.replace(/_/g, " ")}</Badge>;
}

export function OwnerBadge({ owner }: { owner: string }) {
  return <Badge tone={owner === "Unassigned" ? "neutral" : "accent"}>{owner}</Badge>;
}

export function PriorityBadge({ priority }: { priority: AssignmentPriority }) {
  const tone =
    priority === "p0" ? "danger" : priority === "p1" ? "warning" : "neutral";
  return <Badge tone={tone}>{priority.toUpperCase()}</Badge>;
}

/* ── Shell ──────────────────────────────────────────────────────── */

function TeamReviewSidebar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Team review sections"
      className="sticky top-24 flex max-h-[calc(100vh-7rem)] w-full shrink-0 flex-col gap-1 overflow-y-auto rounded-lg border border-[var(--border)] bg-[var(--surface)] p-2 lg:w-48"
    >
      {TEAM_REVIEW_NAV.map((link) => {
        const active = link.exact
          ? pathname === link.href
          : pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            className={`min-h-11 rounded-md px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] ${
              active
                ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}

function TeamReviewShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <CollaborationLayout title={title} description={description}>
      <p
        role="note"
        className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm"
      >
        {TEAM_REVIEW_TRUST}
      </p>
      <div className="flex flex-col gap-4 lg:flex-row">
        <TeamReviewSidebar />
        <div className="min-w-0 flex-1 space-y-4">{children}</div>
      </div>
    </CollaborationLayout>
  );
}

/* ── Cards / panels ─────────────────────────────────────────────── */

export const AssignmentCard = memo(function AssignmentCard({
  review,
}: {
  review: ClientReview;
}) {
  const snap = useTeamReview();
  const meta = snap.assignments.find((a) => a.reviewId === review.id) ?? {
    reviewId: review.id,
    column: "unassigned" as AssignmentColumnId,
    owner: "Unassigned",
    priority: "p2" as AssignmentPriority,
  };

  return (
    <article
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/review-id", review.id);
        e.dataTransfer.effectAllowed = "move";
      }}
      className="cursor-grab rounded-md border border-[var(--border)] bg-[var(--bg)] p-3 text-sm active:cursor-grabbing"
      aria-label={`${review.title}, ${meta.owner}, ${meta.priority}`}
    >
      <p className="font-medium">{review.title}</p>
      <p className="mt-1 text-xs text-[var(--muted)]">{review.clientAlias}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        <ReviewStatusBadge status={review.status} />
        <OwnerBadge owner={meta.owner} />
        <PriorityBadge priority={meta.priority} />
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        <label className="sr-only" htmlFor={`move-${review.id}`}>
          Move {review.title} to column
        </label>
        <select
          id={`move-${review.id}`}
          value={meta.column}
          onChange={(e) =>
            moveAssignment(review.id, e.target.value as AssignmentColumnId)
          }
          className="min-h-9 max-w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-1 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          aria-label={`Move ${review.title} to column`}
        >
          {ASSIGNMENT_COLUMNS.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => openTeamReview(review.id)}
        >
          Open
        </Button>
      </div>
    </article>
  );
});

export const ReviewFilterPanel = memo(function ReviewFilterPanel() {
  const snap = useTeamReview();
  const f = snap.filters;
  const selectClass =
    "mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]";

  return (
    <Card>
      <CardHeader title="Review Filters" description="Presentation filters over demo reviews" />
      <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <label className="block text-xs text-[var(--muted)] sm:col-span-2 lg:col-span-3">
          Search
          <input
            type="search"
            value={f.query}
            onChange={(e) => setTeamReviewFilters({ query: e.target.value })}
            className={selectClass}
            aria-label="Search team reviews"
            placeholder="Title or client…"
          />
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Owner
          <select
            value={f.owner}
            onChange={(e) => setTeamReviewFilters({ owner: e.target.value })}
            className={selectClass}
            aria-label="Filter by owner"
          >
            <option value="">All</option>
            {DEMO_OWNERS.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Priority
          <select
            value={f.priority}
            onChange={(e) =>
              setTeamReviewFilters({
                priority: e.target.value as typeof f.priority,
              })
            }
            className={selectClass}
            aria-label="Filter by priority"
          >
            <option value="">All</option>
            <option value="p0">P0</option>
            <option value="p1">P1</option>
            <option value="p2">P2</option>
            <option value="p3">P3</option>
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Client
          <select
            value={f.client}
            onChange={(e) => setTeamReviewFilters({ client: e.target.value })}
            className={selectClass}
            aria-label="Filter by client"
          >
            <option value="">All</option>
            {FILTER_CLIENTS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Status
          <select
            value={f.status}
            onChange={(e) => setTeamReviewFilters({ status: e.target.value })}
            className={selectClass}
            aria-label="Filter by status"
          >
            <option value="">All</option>
            <option value="upcoming">Upcoming</option>
            <option value="in_progress">In progress</option>
            <option value="completed">Completed</option>
            <option value="archived">Archived</option>
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Meeting type
          <select
            value={f.meetingType}
            onChange={(e) => setTeamReviewFilters({ meetingType: e.target.value })}
            className={selectClass}
            aria-label="Filter by meeting type"
          >
            <option value="">All</option>
            {FILTER_MEETING_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Portfolio
          <select
            value={f.portfolio}
            onChange={(e) => setTeamReviewFilters({ portfolio: e.target.value })}
            className={selectClass}
            aria-label="Filter by portfolio"
          >
            <option value="">All</option>
            {FILTER_PORTFOLIOS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Research status
          <select
            value={f.researchStatus}
            onChange={(e) =>
              setTeamReviewFilters({
                researchStatus: e.target.value as typeof f.researchStatus,
              })
            }
            className={selectClass}
            aria-label="Filter by research status"
          >
            <option value="">All</option>
            <option value="linked">Linked</option>
            <option value="missing">Missing</option>
          </select>
        </label>
        <label className="block text-xs text-[var(--muted)]">
          Presentation status
          <select
            value={f.presentationStatus}
            onChange={(e) =>
              setTeamReviewFilters({
                presentationStatus: e.target.value as typeof f.presentationStatus,
              })
            }
            className={selectClass}
            aria-label="Filter by presentation status"
          >
            <option value="">All</option>
            <option value="ready">Linked</option>
            <option value="missing">Missing</option>
          </select>
        </label>
        <fieldset className="sm:col-span-2 lg:col-span-3">
          <legend className="text-xs text-[var(--muted)]">Quick flags</legend>
          <div className="mt-2 flex flex-wrap gap-3">
            <label className="flex min-h-11 items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={f.upcomingOnly}
                onChange={(e) =>
                  setTeamReviewFilters({ upcomingOnly: e.target.checked })
                }
              />
              Upcoming
            </label>
            <label className="flex min-h-11 items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={f.completedOnly}
                onChange={(e) =>
                  setTeamReviewFilters({ completedOnly: e.target.checked })
                }
              />
              Completed
            </label>
          </div>
        </fieldset>
        <div className="sm:col-span-2 lg:col-span-3">
          <Button type="button" variant="ghost" size="sm" onClick={() => resetTeamReviewFilters()}>
            Reset filters
          </Button>
        </div>
      </CardBody>
    </Card>
  );
});

export const ReviewOverviewDashboard = memo(function ReviewOverviewDashboard() {
  const snap = useTeamReview();
  const overview = useMemo(() => buildTeamReviewOverview(snap), [snap]);
  const cells = [
    ["Total reviews", String(overview.totalReviews)],
    ["Assigned reviews", String(overview.assignedReviews)],
    ["Completed reviews", String(overview.completedReviews)],
    ["Pending reviews", String(overview.pendingReviews)],
    ["Average completion", overview.averageCompletion],
    ["Outstanding assignments", String(overview.outstandingAssignments)],
    ["Upcoming meetings", String(overview.upcomingMeetings)],
    ["Overall team progress", overview.overallTeamProgress],
  ] as const;

  return (
    <Card>
      <CardHeader
        title="Review Overview Dashboard"
        description="Presentation metrics from existing client review demos"
      />
      <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {cells.map(([label, value]) => (
          <div
            key={label}
            className="rounded-md border border-[var(--border)] bg-[var(--surface-2)]/40 p-3"
          >
            <p className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</p>
            <p className="mt-1 text-sm font-medium">{value}</p>
          </div>
        ))}
      </CardBody>
    </Card>
  );
});

export const ReviewActivityFeed = memo(function ReviewActivityFeed({
  items,
}: {
  items: TeamReviewActivityItem[];
}) {
  return (
    <Card>
      <CardHeader title="Review Activity" description="Session feed — not live multi-user" />
      <CardBody>
        <WindowedList
          items={items}
          initial={8}
          step={8}
          className="grid gap-2"
          empty={<EmptyState title="No activity yet" />}
          renderItem={(item) => (
            <div
              key={item.id}
              className="flex min-h-11 flex-col gap-1 rounded-md border border-[var(--border)] px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between"
            >
              <span>{item.label}</span>
              <span className="flex items-center gap-2 text-xs text-[var(--muted)]">
                <Badge>{item.kind}</Badge>
                <time dateTime={item.at}>{item.at.slice(0, 16).replace("T", " ")}</time>
              </span>
            </div>
          )}
        />
      </CardBody>
    </Card>
  );
});

export const ReviewTimeline = memo(function ReviewTimeline() {
  const snap = useTeamReview();
  return (
    <Card>
      <CardHeader
        title="Activity Timeline"
        description="Assignments · status · opened · completed · presentations · research · portfolios"
      />
      <CardBody>
        <ol className="space-y-3" aria-label="Team review timeline">
          {snap.activity.map((item) => (
            <li
              key={item.id}
              className="relative border-l-2 border-[var(--border)] pl-4"
            >
              <span
                className="absolute -left-1.5 top-1.5 h-3 w-3 rounded-full bg-[var(--accent)]"
                aria-hidden
              />
              <p className="text-sm font-medium">{item.label}</p>
              <p className="text-xs text-[var(--muted)]">
                <Badge>{item.kind}</Badge>{" "}
                <time dateTime={item.at}>{item.at.slice(0, 19).replace("T", " ")}</time>
              </p>
            </li>
          ))}
        </ol>
      </CardBody>
    </Card>
  );
});

export const AssignmentBoard = memo(function AssignmentBoard() {
  const snap = useTeamReview();
  const [dragOver, setDragOver] = useState<AssignmentColumnId | null>(null);

  const onDrop = useCallback((column: AssignmentColumnId, e: DragEvent) => {
    e.preventDefault();
    const id = e.dataTransfer.getData("text/review-id");
    if (id) moveAssignment(id, column);
    setDragOver(null);
  }, []);

  return (
    <div className="space-y-4">
      <ReviewFilterPanel />
      <div
        className="flex gap-3 overflow-x-auto pb-2"
        role="region"
        aria-label="Assignment board"
      >
        {ASSIGNMENT_COLUMNS.map((col) => {
          const items = reviewsByColumn(col.id, snap);
          return (
            <section
              key={col.id}
              aria-label={`${col.label} column`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(col.id);
              }}
              onDragLeave={() => setDragOver((d) => (d === col.id ? null : d))}
              onDrop={(e) => onDrop(col.id, e)}
              className={`flex w-64 shrink-0 flex-col gap-2 rounded-lg border p-2 ${
                dragOver === col.id
                  ? "border-[var(--accent)] bg-[var(--accent-soft)]/30"
                  : "border-[var(--border)] bg-[var(--surface)]"
              }`}
            >
              <header className="flex items-center justify-between px-1 py-1">
                <h3 className="text-sm font-medium">{col.label}</h3>
                <Badge>{items.length}</Badge>
              </header>
              <div className="flex min-h-[12rem] flex-col gap-2">
                {items.length === 0 ? (
                  <p className="px-1 text-xs text-[var(--muted)]">Drop here</p>
                ) : (
                  items.map((r) => <AssignmentCard key={r.id} review={r} />)
                )}
              </div>
            </section>
          );
        })}
      </div>
      <p className="text-xs text-[var(--muted)]" role="note">
        Drag cards between columns or use the keyboard-accessible column selector on each card.
        Presentation only — not persisted.
      </p>
    </div>
  );
});

export const ReviewDiscussionPanel = memo(function ReviewDiscussionPanel() {
  const snap = useTeamReview();
  const review =
    snap.reviews.find((r) => r.id === snap.activeDiscussionId) ?? snap.reviews[0];
  const draft =
    (review && snap.discussions[review.id]) ||
    (review
      ? {
          reviewId: review.id,
          reviewNotes: review.advisorNotes,
          researchNotes: "",
          portfolioNotes: "",
          meetingNotes: "",
          questions: review.clientQuestions.join("\n"),
          followUpNotes: "",
          updatedAt: "",
        }
      : null);

  const fieldClass =
    "mt-1 min-h-[5rem] w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]";

  if (!review || !draft) {
    return <EmptyState title="No reviews available" />;
  }

  const meta = getAssignment(review.id);

  return (
    <Card>
      <CardHeader
        title="Review Discussion"
        description="Session thread — not chat or real-time collaboration"
      />
      <CardBody className="space-y-4">
        <label className="block text-xs text-[var(--muted)]">
          Review
          <select
            value={review.id}
            onChange={(e) => setActiveDiscussionId(e.target.value)}
            className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            aria-label="Select review for discussion"
          >
            {snap.reviews.map((r) => (
              <option key={r.id} value={r.id}>
                {r.title}
              </option>
            ))}
          </select>
        </label>
        <div className="flex flex-wrap gap-2">
          <ReviewStatusBadge status={review.status} />
          {meta ? <OwnerBadge owner={meta.owner} /> : null}
          {meta ? <PriorityBadge priority={meta.priority} /> : null}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-xs text-[var(--muted)]">
            Owner
            <select
              value={meta?.owner ?? "Unassigned"}
              onChange={(e) => setAssignmentOwner(review.id, e.target.value)}
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              aria-label="Assignment owner"
            >
              {DEMO_OWNERS.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs text-[var(--muted)]">
            Priority
            <select
              value={meta?.priority ?? "p2"}
              onChange={(e) =>
                setAssignmentPriority(review.id, e.target.value as AssignmentPriority)
              }
              className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              aria-label="Assignment priority"
            >
              <option value="p0">P0</option>
              <option value="p1">P1</option>
              <option value="p2">P2</option>
              <option value="p3">P3</option>
            </select>
          </label>
        </div>
        {(
          [
            ["reviewNotes", "Review Notes", draft.reviewNotes],
            ["researchNotes", "Research Notes", draft.researchNotes],
            ["portfolioNotes", "Portfolio Notes", draft.portfolioNotes],
            ["meetingNotes", "Meeting Notes", draft.meetingNotes],
            ["questions", "Questions", draft.questions],
            ["followUpNotes", "Follow-up Notes", draft.followUpNotes],
          ] as const
        ).map(([key, label, value]) => (
          <label key={key} className="block text-xs text-[var(--muted)]">
            {label}
            <textarea
              value={value}
              onChange={(e) =>
                updateReviewDiscussion(review.id, { [key]: e.target.value })
              }
              className={fieldClass}
              aria-label={label}
            />
          </label>
        ))}
        <div>
          <p className="mb-1 text-xs uppercase tracking-wide text-[var(--muted)]">
            Discussion thread (session)
          </p>
          <ul className="space-y-2 text-sm" aria-label="Discussion thread">
            <li className="rounded-md border border-[var(--border)] px-3 py-2">
              <span className="font-medium">System</span> — Review pack linked to existing DSP demos.
            </li>
            {draft.updatedAt ? (
              <li className="rounded-md border border-[var(--border)] px-3 py-2">
                <span className="font-medium">Advisor (demo)</span> — Notes updated{" "}
                {draft.updatedAt.slice(0, 19).replace("T", " ")}.
              </li>
            ) : null}
          </ul>
        </div>
      </CardBody>
    </Card>
  );
});

function ProgressCards() {
  const snap = useTeamReview();
  const list = useMemo(() => filterTeamReviews(snap), [snap]);

  return (
    <div className="grid gap-4">
      {list.map((r) => {
        const progress = buildReviewProgress(r);
        return (
          <Card key={r.id}>
            <CardHeader title={r.title} description={r.clientAlias} />
            <CardBody className="space-y-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <ReviewStatusBadge status={r.status} />
                <Badge>{progress.completionPct}% complete</Badge>
                <Badge>{progress.checklistProgress} checklist</Badge>
              </div>
              <div
                className="h-2 overflow-hidden rounded-full bg-[var(--surface-2)]"
                role="progressbar"
                aria-valuenow={progress.completionPct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${r.title} completion`}
              >
                <div
                  className="h-full bg-[var(--accent)]"
                  style={{ width: `${progress.completionPct}%` }}
                />
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <p>
                  <span className="text-[var(--muted)]">Meeting readiness:</span>{" "}
                  {progress.meetingReadiness}
                </p>
                <p>
                  <span className="text-[var(--muted)]">Presentation:</span>{" "}
                  {progress.presentationReadiness}
                </p>
                <p>
                  <span className="text-[var(--muted)]">Research currency:</span>{" "}
                  {progress.researchCurrency}
                </p>
                <p>
                  <span className="text-[var(--muted)]">Portfolio currency:</span>{" "}
                  {progress.portfolioCurrency}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-[var(--muted)]">
                  Outstanding tasks
                </p>
                <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
                  {progress.outstandingTasks.length === 0 ? (
                    <li>None</li>
                  ) : (
                    progress.outstandingTasks.map((t) => <li key={t}>{t}</li>)
                  )}
                </ul>
              </div>
            </CardBody>
          </Card>
        );
      })}
    </div>
  );
}

/* ── Pages ──────────────────────────────────────────────────────── */

export const SharedReviewWorkspace = memo(function SharedReviewWorkspace() {
  const snap = useTeamReview();
  const lanes = useMemo(() => laneReviews(snap), [snap]);

  return (
    <TeamReviewShell
      title="Shared Review Workspace"
      description="Coordinate client reviews, ownership, and progress — session only"
    >
      <Card>
        <CardHeader title="Quick actions" />
        <CardBody className="flex flex-wrap gap-2">
          <Link href="/advisor/team/shared-reviews/board">
            <Button variant="secondary">Assignment Board</Button>
          </Link>
          <Link href="/advisor/team/shared-reviews/discussion">
            <Button variant="secondary">Discussion</Button>
          </Link>
          <Link href="/advisor/team/shared-reviews/progress">
            <Button variant="secondary">Progress</Button>
          </Link>
          <Link href="/advisor/reviews">
            <Button variant="ghost">Client Review Workflow</Button>
          </Link>
        </CardBody>
      </Card>
      <ReviewOverviewDashboard />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(
          [
            ["Pending Reviews", lanes.pending],
            ["Assigned Reviews", lanes.assigned],
            ["In Progress", lanes.inProgress],
            ["Ready for Meeting", lanes.readyForMeeting],
            ["Completed", lanes.completed],
            ["Archived", lanes.archived],
          ] as const
        ).map(([title, items]) => (
          <Card key={title}>
            <CardHeader title={title} description={`${items.length} demos`} />
            <CardBody>
              <ul className="space-y-2 text-sm" aria-label={title}>
                {items.length === 0 ? (
                  <li className="text-[var(--muted)]">None</li>
                ) : (
                  items.map((r) => (
                    <li
                      key={r.id}
                      className="flex min-h-11 items-center justify-between gap-2 rounded-md border border-[var(--border)] px-2"
                    >
                      <span>{r.title}</span>
                      <ReviewStatusBadge status={r.status} />
                    </li>
                  ))
                )}
              </ul>
            </CardBody>
          </Card>
        ))}
      </div>
      <ReviewActivityFeed items={snap.activity.slice(0, 6)} />
    </TeamReviewShell>
  );
});

export const TeamReviewBoardPage = memo(function TeamReviewBoardPage() {
  return (
    <TeamReviewShell
      title="Assignment Board"
      description="Unassigned · Assigned · In Progress · Ready · Completed · Deferred"
    >
      <AssignmentBoard />
    </TeamReviewShell>
  );
});

export const TeamReviewDiscussionPage = memo(function TeamReviewDiscussionPage() {
  return (
    <TeamReviewShell
      title="Review Discussion"
      description="Notes · research · portfolio · meeting · questions · follow-ups"
    >
      <ReviewDiscussionPanel />
    </TeamReviewShell>
  );
});

export const TeamReviewTimelinePage = memo(function TeamReviewTimelinePage() {
  return (
    <TeamReviewShell
      title="Activity Timeline"
      description="Reuse existing DSP review, research, portfolio, and presentation events"
    >
      <ReviewTimeline />
    </TeamReviewShell>
  );
});

export const TeamReviewProgressPage = memo(function TeamReviewProgressPage() {
  return (
    <TeamReviewShell
      title="Review Progress"
      description="Completion · checklist · meeting & presentation readiness · research/portfolio currency"
    >
      <ReviewFilterPanel />
      <ProgressCards />
    </TeamReviewShell>
  );
});

export const TeamReviewActivityPage = memo(function TeamReviewActivityPage() {
  const snap = useTeamReview();
  return (
    <TeamReviewShell
      title="Review Activity"
      description="Assignments · status changes · opened · completed · presentations · research · portfolios"
    >
      <ReviewActivityFeed items={snap.activity} />
      <ReviewOverviewDashboard />
    </TeamReviewShell>
  );
});
