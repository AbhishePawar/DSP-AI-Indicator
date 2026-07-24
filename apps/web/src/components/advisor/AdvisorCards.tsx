"use client";

import { memo } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type {
  ClientSummary,
  Meeting,
  ModelPortfolio,
  ResearchCollection,
  Task,
} from "@/lib/advisor/advisorTypes";
import type { AdvisorOverviewView } from "@/lib/advisor/advisorViewModel";
import { clientAlias } from "@/lib/advisor/advisorViewModel";

export function AdvisorOverviewCard({ overview }: { overview: AdvisorOverviewView }) {
  return (
    <Card className="border-[var(--accent)]/35">
      <CardHeader
        title="Advisor overview"
        description={`${overview.advisorName} · ${overview.organizationName}`}
        action={<Badge tone="accent">Demo</Badge>}
      />
      <CardBody className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 text-sm">
        <section aria-labelledby="adv-meetings">
          <h3 id="adv-meetings" className="font-medium">
            Today&apos;s meetings
          </h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-[var(--muted)]">
            {overview.todaysMeetings.length === 0 ? (
              <li>None scheduled (demo)</li>
            ) : (
              overview.todaysMeetings.map((m) => (
                <li key={m.id}>
                  {m.title} · {new Date(m.scheduledAt).toLocaleTimeString()}
                </li>
              ))
            )}
          </ul>
        </section>
        <section aria-labelledby="adv-tasks">
          <h3 id="adv-tasks" className="font-medium">
            Pending tasks
          </h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-[var(--muted)]">
            {overview.pendingTasks.slice(0, 4).map((t) => (
              <li key={t.id}>{t.title}</li>
            ))}
          </ul>
        </section>
        <section aria-labelledby="adv-research">
          <h3 id="adv-research" className="font-medium">
            Recent research
          </h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-[var(--muted)]">
            {overview.recentResearch.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
        <section aria-labelledby="adv-activity" className="sm:col-span-2 lg:col-span-2">
          <h3 id="adv-activity" className="font-medium">
            Client activity
          </h3>
          <ul className="mt-2 space-y-1 text-[var(--muted)]">
            {overview.clientActivity.map((c) => (
              <li key={c.alias}>
                <span className="font-medium text-[var(--fg)]">{c.alias}</span> — {c.segment} ·{" "}
                {new Date(c.lastTouchAt).toLocaleDateString()}
              </li>
            ))}
          </ul>
        </section>
        <section aria-labelledby="adv-reviews">
          <h3 id="adv-reviews" className="font-medium">
            Portfolio reviews
          </h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-[var(--muted)]">
            {overview.portfolioReviews.length === 0 ? (
              <li>None pending</li>
            ) : (
              overview.portfolioReviews.map((t) => <li key={t.id}>{t.title}</li>)
            )}
          </ul>
        </section>
      </CardBody>
    </Card>
  );
}

export const ClientCard = memo(function ClientCard({ client }: { client: ClientSummary }) {
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={client.alias}
        description={client.segment}
        action={<Badge tone="neutral">{client.riskProfile}</Badge>}
      />
      <CardBody className="space-y-2 text-sm">
        <p className="text-[var(--muted)]">{client.portfolioSnapshotLabel}</p>
        <p className="text-xs text-[var(--muted)]">
          Research history: {client.researchHistoryCount} · Last touch{" "}
          {new Date(client.lastTouchAt).toLocaleDateString()} · Review{" "}
          {client.reviewStatus.replace(/_/g, " ")}
        </p>
        <Link
          href={`/advisor/clients/${client.id}`}
          className="inline-flex min-h-11 items-center text-[var(--accent)] underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Open profile
        </Link>
      </CardBody>
    </Card>
  );
});

export function ClientProfileCard({
  alias,
  objectives,
  riskProfile,
  portfolioSnapshot,
  documentsPlaceholder,
}: {
  alias: string;
  objectives: string[];
  riskProfile: string;
  portfolioSnapshot: string;
  documentsPlaceholder?: string[];
}) {
  return (
    <Card>
      <CardHeader
        title={`${alias} — Overview`}
        description="Demo client profile — no personal information"
        action={<Badge tone="accent">Demo</Badge>}
      />
      <CardBody className="grid gap-4 sm:grid-cols-2 text-sm">
        <section>
          <h3 className="font-medium">Investment objectives</h3>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {objectives.map((o) => (
              <li key={o}>{o}</li>
            ))}
          </ul>
        </section>
        <section>
          <h3 className="font-medium">Risk profile</h3>
          <p className="mt-1 text-[var(--muted)] capitalize">{riskProfile}</p>
        </section>
        <section>
          <h3 className="font-medium">Portfolio snapshot</h3>
          <p className="mt-1 text-[var(--muted)]">{portfolioSnapshot}</p>
        </section>
        <section>
          <h3 className="font-medium">Documents (placeholder)</h3>
          <ul className="mt-1 list-disc pl-5 text-[var(--muted)]">
            {(documentsPlaceholder ?? ["No documents"]).map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </section>
      </CardBody>
    </Card>
  );
}

export const MeetingCard = memo(function MeetingCard({ meeting }: { meeting: Meeting }) {
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={meeting.title}
        action={<Badge tone={meeting.status === "scheduled" ? "accent" : "neutral"}>{meeting.status}</Badge>}
      />
      <CardBody className="space-y-1 text-sm">
        <p className="text-[var(--muted)]">
          {new Date(meeting.scheduledAt).toLocaleString()} · {clientAlias(meeting.clientId)}
        </p>
        <p>{meeting.agenda}</p>
        <p className="text-xs text-[var(--muted)]">{meeting.notesPlaceholder}</p>
      </CardBody>
    </Card>
  );
});

export const TaskCard = memo(function TaskCard({ task }: { task: Task }) {
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={task.title}
        action={<Badge tone={task.status === "done" ? "success" : "warning"}>{task.status}</Badge>}
      />
      <CardBody className="space-y-1 text-sm">
        <div className="flex flex-wrap gap-1">
          <Badge tone="warning">{task.priority}</Badge>
          <Badge tone="neutral">{task.kind.replace(/_/g, " ")}</Badge>
        </div>
        <p className="text-[var(--muted)]">
          Due {new Date(task.dueAt).toLocaleDateString()} · Owner {task.owner}
        </p>
        <p className="text-xs text-[var(--muted)]">{clientAlias(task.clientId)}</p>
      </CardBody>
    </Card>
  );
});

export const ResearchCollectionCard = memo(function ResearchCollectionCard({
  collection,
}: {
  collection: ResearchCollection;
}) {
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={collection.name}
        action={<Badge tone="neutral">{collection.kind.replace(/_/g, " ")}</Badge>}
      />
      <CardBody>
        <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
          {collection.itemLabels.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-[var(--muted)]">
          Presentation bookmarks only — does not change research outputs.
        </p>
      </CardBody>
    </Card>
  );
});

export const ModelPortfolioCard = memo(function ModelPortfolioCard({
  portfolio,
}: {
  portfolio: ModelPortfolio;
}) {
  return (
    <Card className="dsp-interactive">
      <CardHeader
        title={portfolio.name}
        description={portfolio.description}
        action={<Badge tone="accent">Demo allocation</Badge>}
      />
      <CardBody className="space-y-2 text-sm">
        <ul className="space-y-1">
          {portfolio.allocations.map((a) => (
            <li key={a.label} className="flex justify-between gap-2">
              <span>{a.label}</span>
              <span className="tabular-nums text-[var(--muted)]">{a.weightPct}%</span>
            </li>
          ))}
        </ul>
        <p className="text-xs text-[var(--muted)]">Not live investments · not advice</p>
      </CardBody>
    </Card>
  );
});

export function AdvisorQuickActions() {
  const actions = [
    { href: "/advisor/clients", label: "Clients" },
    { href: "/advisor/meetings", label: "Meetings" },
    { href: "/advisor/tasks", label: "Tasks" },
    { href: "/advisor/research", label: "Research Library" },
    { href: "/advisor/research/compare", label: "Compare" },
    { href: "/advisor/portfolios", label: "Model Portfolios" },
    { href: "/advisor/portfolios/builder", label: "Portfolio Builder" },
    { href: "/advisor/presentations", label: "Presentations" },
    { href: "/advisor/reviews", label: "Client Reviews" },
    { href: "/advisor/team", label: "Team Collaboration" },
    { href: "/advisor/team/dashboard", label: "Collab Dashboard" },
    { href: "/analysis", label: "Open Research Platform" },
  ] as const;
  return (
    <Card>
      <CardHeader title="Advisor quick actions" description="Demo navigation" />
      <CardBody className="flex flex-wrap gap-2">
        {actions.map((a) => (
          <Link key={a.href} href={a.href}>
            <Button variant="secondary" size="md">
              {a.label}
            </Button>
          </Link>
        ))}
      </CardBody>
    </Card>
  );
}
