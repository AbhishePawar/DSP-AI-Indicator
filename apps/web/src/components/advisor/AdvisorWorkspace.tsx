"use client";

import {
  AdvisorOverviewCard,
  AdvisorQuickActions,
  ClientProfileCard,
  TaskCard,
} from "@/components/advisor/AdvisorCards";
import { AdvisorSidebar } from "@/components/advisor/AdvisorSidebar";
import {
  ClientDashboardCards,
  ClientDirectory,
  MeetingTimeline,
  NotesCard,
  ResearchHistoryCard,
  ReviewStatusBadge,
  TaskBoard,
} from "@/components/advisor/ClientManagement";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { getAdvisorWorkspace } from "@/lib/advisor/advisorWorkspace";
import { buildClientProfile } from "@/lib/advisor/advisorViewModel";
import Link from "next/link";
import { memo, type ReactNode } from "react";
function TrustBanner({ text }: { text: string }) {
  return (
    <p
      role="note"
      className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm"
    >
      {text}
    </p>
  );
}

export function AdvisorShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  const ws = getAdvisorWorkspace();
  return (
    <div className="space-y-4">
      <TrustBanner text={ws.trustBanner} />
      <div className="flex flex-col gap-4 sm:flex-row">
        <AdvisorSidebar />
        <div className="min-w-0 flex-1 space-y-4">
          <header>
            <h1 className="font-[family-name:var(--font-display)] text-3xl tracking-tight">{title}</h1>
            {description ? (
              <p className="mt-1 text-[var(--muted)]">{description}</p>
            ) : null}
          </header>
          {children}
        </div>
      </div>
    </div>
  );
}

export const AdvisorWorkspace = memo(function AdvisorWorkspace() {
  const ws = getAdvisorWorkspace();
  return (
    <AdvisorShell
      title="Advisor Workspace"
      description="Client management foundation — demo data only, optional layer."
    >
      <AdvisorQuickActions />
      <AdvisorOverviewCard overview={ws.overview} />
    </AdvisorShell>
  );
});

/** Sprint 2 — searchable / filterable client directory */
export const ClientDirectoryWorkspace = memo(function ClientDirectoryWorkspace() {
  return (
    <AdvisorShell
      title="Client Directory"
      description="Search · filter · sort — demo aliases only, no personal information."
    >
      <ClientDirectory />
    </AdvisorShell>
  );
});

/** @deprecated alias — use ClientDirectoryWorkspace */
export const ClientsWorkspace = ClientDirectoryWorkspace;

export const ClientDetailWorkspace = memo(function ClientDetailWorkspace({
  clientId,
}: {
  clientId: string;
}) {
  const profile = buildClientProfile(clientId);
  if (!profile) {
    return (
      <AdvisorShell title="Client not found">
        <EmptyState title="Unknown demo client" description="Return to the clients list." />
        <Link
          href="/advisor/clients"
          className="inline-flex min-h-11 items-center text-[var(--accent)] underline"
        >
          Back to directory
        </Link>
      </AdvisorShell>
    );
  }

  const d = profile.dashboard;

  return (
    <AdvisorShell
      title={profile.client.alias}
      description="Client management workspace — presentation only"
    >
      <div className="flex flex-wrap items-center gap-2">
        <ReviewStatusBadge status={profile.client.reviewStatus} />
        <Badge tone="neutral">{profile.client.riskProfile}</Badge>
        <Link
          href="/advisor/clients"
          className="text-sm text-[var(--accent)] underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Back to directory
        </Link>
      </div>

      <section aria-labelledby="client-dash">
        <h2 id="client-dash" className="mb-3 font-[family-name:var(--font-display)] text-xl">
          Client dashboard
        </h2>
        <ClientDashboardCards
          client={d.client}
          portfolioHealth={d.portfolioHealth}
          meetingStatus={d.meetingStatus}
          outstandingTasks={d.outstandingTasks}
          recentResearch={d.recentResearch}
          riskLevel={d.riskLevel}
          nextReview={d.nextReview}
        />
      </section>

      <ClientProfileCard
        alias={profile.client.alias}
        objectives={profile.objectives}
        riskProfile={profile.riskProfile}
        portfolioSnapshot={profile.portfolioSnapshot}
        documentsPlaceholder={profile.documentsPlaceholder}
      />

      <section aria-labelledby="client-meetings" className="space-y-3">
        <h2 id="client-meetings" className="font-[family-name:var(--font-display)] text-xl">
          Meetings
        </h2>
        <MeetingTimeline meetings={profile.meetings} />
      </section>

      <section aria-labelledby="client-tasks" className="space-y-3">
        <h2 id="client-tasks" className="font-[family-name:var(--font-display)] text-xl">
          Tasks
        </h2>
        {profile.tasks.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No tasks</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {profile.tasks.map((t) => (
              <TaskCard key={t.id} task={t} />
            ))}
          </div>
        )}
      </section>

      <NotesCard notes={profile.notes} />
      <ResearchHistoryCard events={profile.researchHistory} />

      <Card>
        <CardHeader title="Meeting notes (rollup)" />
        <CardBody>
          <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
            {profile.meetingNotes.length === 0 ? (
              <li>None</li>
            ) : (
              profile.meetingNotes.map((n) => <li key={n}>{n}</li>)
            )}
          </ul>
        </CardBody>
      </Card>
    </AdvisorShell>
  );
});

export const MeetingsWorkspace = memo(function MeetingsWorkspace() {
  const meetings = getAdvisorWorkspace().meetings;
  return (
    <AdvisorShell
      title="Meeting Timeline"
      description="Upcoming · Completed · Cancelled — demo schedule, no calendar sync."
    >
      <MeetingTimeline meetings={meetings} />
    </AdvisorShell>
  );
});

export const TasksWorkspace = memo(function TasksWorkspace() {
  return (
    <AdvisorShell
      title="Task Board"
      description="Kanban — To Do · In Progress · Waiting · Completed. Demo only."
    >
      <TaskBoard />
    </AdvisorShell>
  );
});
