"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { AllocationSegment } from "@/lib/portfolio/model";

export function AllocationCard({
  title,
  segments,
  description = "Placeholder allocation view",
}: {
  title: string;
  segments: AllocationSegment[];
  description?: string;
}) {
  return (
    <Card>
      <CardHeader title={title} description={description} />
      <CardBody className="space-y-3">
        {segments.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No allocation data.</p>
        ) : (
          segments.map((segment) => (
            <div key={segment.name}>
              <div className="flex justify-between text-sm">
                <span>{segment.name}</span>
                <span className="font-mono text-[var(--muted)]">
                  {segment.percent.toFixed(1)}%
                </span>
              </div>
              <div
                className="mt-1.5 h-2 overflow-hidden rounded-full bg-[var(--surface-2)]"
                role="presentation"
              >
                <div
                  className="h-full rounded-full bg-[var(--accent)]"
                  style={{ width: `${Math.min(segment.percent, 100)}%` }}
                />
              </div>
            </div>
          ))
        )}
      </CardBody>
    </Card>
  );
}
