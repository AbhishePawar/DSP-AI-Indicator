"use client";

import { useMemo } from "react";

import { Badge } from "@/components/ui/Badge";
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
    <li className="relative flex gap-3 pb-5 last:pb-0">
      <span
        className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[var(--accent)]"
        aria-hidden
      />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-[var(--fg)]">{event.label}</p>
          <Badge tone={STATUS_TONE[event.status]}>{event.status}</Badge>
        </div>
        <p className="text-xs text-[var(--muted)]">
          {event.at ?? "Unavailable"}
        </p>
        <p className="mt-0.5 text-sm text-[var(--muted)]">{event.detail}</p>
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
    <section id="research_timeline" className="space-y-4">
      <div className="border-b border-[var(--border)] pb-3">
        <h3 className="font-[family-name:var(--font-display)] text-base tracking-tight text-[var(--fg)]">
          Research Timeline
        </h3>
        <p className="mt-0.5 text-xs text-[var(--muted)]">
          When analysis was created/updated — placeholders for future research events
        </p>
      </div>
      <ol className="max-h-80 overflow-y-auto border-l border-[var(--border)] pl-4">
        {events.map((event) => (
          <TimelineCard key={event.id} event={event} />
        ))}
      </ol>
    </section>
  );
}
