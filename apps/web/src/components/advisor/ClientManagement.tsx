"use client";

import { memo, useMemo, useState } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { WindowedList } from "@/lib/perf/WindowedList";
import {
  DEFAULT_CLIENT_FILTERS,
  filterAndSortClients,
} from "@/lib/advisor/clientDirectory";
import { clientAlias } from "@/lib/advisor/advisorViewModel";
import type {
  ClientDirectoryFilters,
  ClientNote,
  ClientSummary,
  Meeting,
  ResearchHistoryEvent,
  ReviewStatus,
  Task,
  TaskStatus,
} from "@/lib/advisor/advisorTypes";
import { listClients, listMeetings, listTasksByStatus } from "@/lib/advisor/advisorViewModel";

function reviewTone(status: ReviewStatus): "success" | "warning" | "danger" | "neutral" {
  if (status === "on_track" || status === "completed") return "success";
  if (status === "due_soon") return "warning";
  if (status === "overdue") return "danger";
  return "neutral";
}

export function ReviewStatusBadge({ status }: { status: ReviewStatus }) {
  return <Badge tone={reviewTone(status)}>{status.replace(/_/g, " ")}</Badge>;
}

export function PortfolioHealthCard({
  label,
  sizeLabel,
  snapshot,
}: {
  label: string;
  sizeLabel: string;
  snapshot: string;
}) {
  return (
    <Card>
      <CardHeader title="Portfolio health" action={<Badge tone="accent">Demo</Badge>} />
      <CardBody className="space-y-1 text-sm">
        <p className="font-medium">{label}</p>
        <p className="text-[var(--muted)]">{snapshot}</p>
        <p className="text-xs text-[var(--muted)]">Size band: {sizeLabel} (illustrative)</p>
      </CardBody>
    </Card>
  );
}

export function ClientSearch({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="font-medium">Search clients</span>
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Alias, segment, sleeve…"
        className="mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        aria-label="Search clients"
      />
    </label>
  );
}

export function ClientFilters({
  filters,
  onChange,
}: {
  filters: ClientDirectoryFilters;
  onChange: (next: ClientDirectoryFilters) => void;
}) {
  const selectClass =
    "mt-1 min-h-11 w-full rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]";
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" role="group" aria-label="Client filters">
      <label className="block text-sm">
        Risk profile
        <select
          className={selectClass}
          value={filters.riskProfile}
          onChange={(e) =>
            onChange({
              ...filters,
              riskProfile: e.target.value as ClientDirectoryFilters["riskProfile"],
            })
          }
        >
          <option value="all">All</option>
          <option value="conservative">Conservative</option>
          <option value="moderate">Moderate</option>
          <option value="growth">Growth</option>
          <option value="aggressive">Aggressive</option>
        </select>
      </label>
      <label className="block text-sm">
        Review status
        <select
          className={selectClass}
          value={filters.reviewStatus}
          onChange={(e) =>
            onChange({
              ...filters,
              reviewStatus: e.target.value as ClientDirectoryFilters["reviewStatus"],
            })
          }
        >
          <option value="all">All</option>
          <option value="on_track">On track</option>
          <option value="due_soon">Due soon</option>
          <option value="overdue">Overdue</option>
          <option value="completed">Completed</option>
        </select>
      </label>
      <label className="block text-sm">
        Portfolio size
        <select
          className={selectClass}
          value={filters.portfolioSize}
          onChange={(e) =>
            onChange({
              ...filters,
              portfolioSize: e.target.value as ClientDirectoryFilters["portfolioSize"],
            })
          }
        >
          <option value="all">All</option>
          <option value="small">Small</option>
          <option value="medium">Medium</option>
          <option value="large">Large</option>
          <option value="institutional">Institutional</option>
        </select>
      </label>
      <label className="block text-sm">
        Sort
        <select
          className={selectClass}
          value={filters.sort}
          onChange={(e) =>
            onChange({
              ...filters,
              sort: e.target.value as ClientDirectoryFilters["sort"],
            })
          }
        >
          <option value="alias_asc">Alphabet A–Z</option>
          <option value="alias_desc">Alphabet Z–A</option>
          <option value="risk">Risk profile</option>
          <option value="review_status">Review status</option>
          <option value="portfolio_size">Portfolio size</option>
          <option value="activity">Recent activity</option>
          <option value="meeting_due">Meeting due</option>
        </select>
      </label>
    </div>
  );
}

export const ClientDirectory = memo(function ClientDirectory() {
  const [filters, setFilters] = useState<ClientDirectoryFilters>(DEFAULT_CLIENT_FILTERS);
  const all = useMemo(() => listClients(), []);
  const visible = useMemo(() => filterAndSortClients(all, filters), [all, filters]);

  return (
    <div className="space-y-4">
      <ClientSearch
        value={filters.query}
        onChange={(query) => setFilters((f) => ({ ...f, query }))}
      />
      <ClientFilters filters={filters} onChange={setFilters} />
      <p className="text-xs text-[var(--muted)]" aria-live="polite">
        Showing {visible.length} of {all.length} demo clients
      </p>
      <WindowedList
        items={visible}
        initial={8}
        empty={
          <EmptyState
            title="No clients match"
            description="Adjust search or filters — demo directory only."
          />
        }
        renderItem={(c) => <DirectoryClientRow key={c.id} client={c} />}
      />
    </div>
  );
});

const DirectoryClientRow = memo(function DirectoryClientRow({
  client,
}: {
  client: ClientSummary;
}) {
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={client.alias}
        description={client.segment}
        action={<ReviewStatusBadge status={client.reviewStatus} />}
      />
      <CardBody className="space-y-2 text-sm">
        <div className="flex flex-wrap gap-2">
          <Badge tone="neutral">{client.riskProfile}</Badge>
          <Badge tone="neutral">{client.portfolioSizeLabel}</Badge>
        </div>
        <p className="text-[var(--muted)]">{client.portfolioSnapshotLabel}</p>
        <p className="text-xs text-[var(--muted)]">
          Activity {new Date(client.lastTouchAt).toLocaleDateString()}
          {client.meetingDueAt
            ? ` · Meeting due ${new Date(client.meetingDueAt).toLocaleString()}`
            : " · No meeting due"}
        </p>
        <Link
          href={`/advisor/clients/${client.id}`}
          className="inline-flex min-h-11 items-center text-[var(--accent)] underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Open client workspace
        </Link>
      </CardBody>
    </Card>
  );
});

export function MeetingTimeline({ meetings }: { meetings: Meeting[] }) {
  const groups: { status: Meeting["status"]; label: string }[] = [
    { status: "scheduled", label: "Upcoming" },
    { status: "completed", label: "Completed" },
    { status: "cancelled", label: "Cancelled" },
  ];
  return (
    <div className="space-y-6">
      {groups.map((g) => {
        const items = meetings.filter((m) => m.status === g.status);
        return (
          <section key={g.status} aria-labelledby={`mtg-${g.status}`}>
            <h2 id={`mtg-${g.status}`} className="font-[family-name:var(--font-display)] text-lg">
              {g.label}
            </h2>
            {items.length === 0 ? (
              <p className="mt-2 text-sm text-[var(--muted)]">None</p>
            ) : (
              <ol className="mt-3 space-y-3 border-l-2 border-[var(--border)] pl-4">
                {items.map((m) => (
                  <li key={m.id} className="relative">
                    <span
                      className="absolute -left-[1.35rem] top-1.5 h-2.5 w-2.5 rounded-full bg-[var(--accent)]"
                      aria-hidden
                    />
                    <Card>
                      <CardHeader
                        title={m.title}
                        description={`${new Date(m.scheduledAt).toLocaleString()} · ${clientAlias(m.clientId)}`}
                        action={<Badge tone="neutral">{m.status}</Badge>}
                      />
                      <CardBody className="space-y-2 text-sm">
                        <p>{m.agenda}</p>
                        <p>
                          <span className="font-medium">Review notes — </span>
                          {m.reviewNotes}
                        </p>
                        <div>
                          <p className="font-medium">Action items</p>
                          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
                            {m.actionItems.length === 0 ? (
                              <li>None</li>
                            ) : (
                              m.actionItems.map((a) => <li key={a}>{a}</li>)
                            )}
                          </ul>
                        </div>
                      </CardBody>
                    </Card>
                  </li>
                ))}
              </ol>
            )}
          </section>
        );
      })}
    </div>
  );
}

export function MeetingTimelineWorkspace() {
  const meetings = useMemo(() => listMeetings(), []);
  return <MeetingTimeline meetings={meetings} />;
}

const KANBAN_LANES: { status: TaskStatus; label: string }[] = [
  { status: "todo", label: "To Do" },
  { status: "in_progress", label: "In Progress" },
  { status: "waiting", label: "Waiting" },
  { status: "done", label: "Completed" },
];

export function TaskLane({
  label,
  status,
  tasks,
}: {
  label: string;
  status: TaskStatus;
  tasks: Task[];
}) {
  return (
    <section
      aria-labelledby={`lane-${status}`}
      className="min-w-[16rem] flex-1 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3"
    >
      <h3 id={`lane-${status}`} className="font-medium text-sm">
        {label}{" "}
        <span className="text-[var(--muted)]">({tasks.length})</span>
      </h3>
      <div className="mt-3 space-y-2">
        {tasks.length === 0 ? (
          <p className="text-xs text-[var(--muted)]">Empty</p>
        ) : (
          tasks.map((t) => (
            <Card key={t.id} className="dsp-interactive">
              <CardBody className="space-y-1 text-sm">
                <p className="font-medium">{t.title}</p>
                <div className="flex flex-wrap gap-1">
                  <Badge tone="warning">{t.priority}</Badge>
                  <Badge tone="neutral">{t.kind.replace(/_/g, " ")}</Badge>
                </div>
                <p className="text-xs text-[var(--muted)]">
                  Due {new Date(t.dueAt).toLocaleDateString()} · Owner {t.owner}
                </p>
                <p className="text-xs text-[var(--muted)]">{clientAlias(t.clientId)}</p>
              </CardBody>
            </Card>
          ))
        )}
      </div>
    </section>
  );
}

export function TaskBoard() {
  return (
    <div
      className="flex gap-3 overflow-x-auto pb-2"
      role="region"
      aria-label="Task board kanban"
    >
      {KANBAN_LANES.map((lane) => (
        <TaskLane
          key={lane.status}
          label={lane.label}
          status={lane.status}
          tasks={listTasksByStatus(lane.status)}
        />
      ))}
    </div>
  );
}

export function NotesCard({ notes }: { notes: ClientNote[] }) {
  return (
    <Card>
      <CardHeader title="Notes" description="Pinned · Meeting · Research · Advisor (demo)" />
      <CardBody className="space-y-3">
        {notes.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No demo notes</p>
        ) : (
          notes.map((n) => (
            <article
              key={n.id}
              className="rounded-md border border-[var(--border)] px-3 py-2 text-sm"
            >
              <div className="flex flex-wrap items-center gap-2">
                {n.pinned ? <Badge tone="accent">Pinned</Badge> : null}
                <Badge tone="neutral">{n.kind}</Badge>
                <h3 className="font-medium">{n.title}</h3>
              </div>
              <p className="mt-1 text-[var(--muted)] whitespace-pre-wrap">{n.body}</p>
              <p className="mt-1 text-xs text-[var(--muted)]">
                Updated {new Date(n.updatedAt).toLocaleString()}
              </p>
            </article>
          ))
        )}
      </CardBody>
    </Card>
  );
}

export function ResearchHistoryCard({ events }: { events: ResearchHistoryEvent[] }) {
  return (
    <Card>
      <CardHeader
        title="Research history"
        description="Companies · exports · portfolio reviews · saved — presentation only"
      />
      <CardBody>
        {events.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No history</p>
        ) : (
          <ol className="space-y-3 border-l-2 border-[var(--border)] pl-4">
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
        )}
        <p className="mt-3 text-xs text-[var(--muted)]">
          Does not change research engines, evidence, confidence, or methodology.
        </p>
      </CardBody>
    </Card>
  );
}

export function ClientDashboardCards({
  client,
  portfolioHealth,
  meetingStatus,
  outstandingTasks,
  recentResearch,
  riskLevel,
  nextReview,
}: {
  client: ClientSummary;
  portfolioHealth: string;
  meetingStatus: string;
  outstandingTasks: Task[];
  recentResearch: ResearchHistoryEvent[];
  riskLevel: string;
  nextReview: string;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <PortfolioHealthCard
        label={portfolioHealth}
        sizeLabel={client.portfolioSizeLabel}
        snapshot={client.portfolioSnapshotLabel}
      />
      <Card>
        <CardHeader title="Meeting status" />
        <CardBody className="text-sm text-[var(--muted)]">{meetingStatus}</CardBody>
      </Card>
      <Card>
        <CardHeader title="Outstanding tasks" action={<Badge tone="warning">{outstandingTasks.length}</Badge>} />
        <CardBody>
          <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
            {outstandingTasks.length === 0 ? (
              <li>None</li>
            ) : (
              outstandingTasks.map((t) => <li key={t.id}>{t.title}</li>)
            )}
          </ul>
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Recent research" />
        <CardBody>
          <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
            {recentResearch.length === 0 ? (
              <li>None</li>
            ) : (
              recentResearch.map((e) => <li key={e.id}>{e.label}</li>)
            )}
          </ul>
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Risk level" action={<Badge tone="neutral">{riskLevel}</Badge>} />
        <CardBody className="text-sm text-[var(--muted)]">
          <ReviewStatusBadge status={client.reviewStatus} />
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="Next review" />
        <CardBody className="text-sm text-[var(--muted)]">
          {new Date(nextReview).toLocaleString()}
        </CardBody>
      </Card>
    </div>
  );
}
