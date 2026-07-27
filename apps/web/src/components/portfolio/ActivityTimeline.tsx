"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { PortfolioActivity } from "@/lib/portfolio/model";

export function ActivityTimeline({
  activities,
}: {
  activities: PortfolioActivity[];
}) {
  return (
    <Card>
      <CardHeader title="Recent Activity" description="Placeholder timeline" />
      <CardBody>
        {activities.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No recent activity.</p>
        ) : (
          <ol className="space-y-4" aria-label="Portfolio activity timeline">
            {activities.map((activity, index) => (
              <li key={activity.id} className="flex gap-3">
                <span
                  className="mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full bg-[var(--accent)]"
                  aria-hidden
                />
                <div className="min-w-0 flex-1 border-b border-[var(--border)] pb-3 last:border-0 last:pb-0">
                  <p className="text-sm font-medium">{activity.label}</p>
                  <p className="mt-0.5 font-mono text-xs text-[var(--muted)]">
                    {new Date(activity.timestamp).toLocaleString()}
                  </p>
                  {index < activities.length - 1 ? (
                    <span className="sr-only">Earlier activity below</span>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
        )}
      </CardBody>
    </Card>
  );
}
