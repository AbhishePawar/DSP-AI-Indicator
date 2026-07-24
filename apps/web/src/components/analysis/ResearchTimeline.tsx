"use client";

import { useMemo } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { ResearchTimelineView, TimelineEvent } from "@/lib/analysis/types";

const STATUS_TONE: Record<
  TimelineEvent["status"],
  "success" | "accent" | "warning" | "neutral"
> = {
  done: "success",
  current: "accent",
  future: "warning",
  placeholder: "neutral",
};

export function TimelineCard({ event }: { event: TimelineEvent }) {
  return (
    <li className="relative flex gap-3 pb-6 last:pb-0">
      <span
        className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-[var(--accent)]"
        aria-hidden
      />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium">{event.label}</p>
          <Badge tone={STATUS_TONE[event.status]}>{event.status}</Badge>
        </div>
        <p className="text-xs text-[var(--muted)]">
          {event.at ?? "Unavailable"}
        </p>
        <p className="mt-1 text-sm text-[var(--muted)]">{event.detail}</p>
      </div>
    </li>
  );
}

/** Lightweight list timeline — virtualize when history grows large. */
export function ResearchTimeline({
  timeline,
}: {
  timeline: ResearchTimelineView;
}) {
  const events = useMemo(() => timeline.events, [timeline.events]);

  return (
    <Card id="research_timeline">
      <CardHeader
        title="Research timeline"
        description="When analysis was created/updated — placeholders for future research events"
      />
      <CardBody>
        <ol className="max-h-80 overflow-y-auto border-l border-[var(--border)] pl-1">
          {events.map((event) => (
            <TimelineCard key={event.id} event={event} />
          ))}
        </ol>
      </CardBody>
    </Card>
  );
}
