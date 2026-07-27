"use client";

import type { ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { StageSectionView } from "@/lib/research/mapResearchView";

export function MetricGrid({
  metrics,
}: {
  metrics: { label: string; value: string }[];
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {metrics.map((m) => (
        <div key={m.label}>
          <p className="text-xs text-[var(--muted)]">{m.label}</p>
          <p className="mt-1 text-lg font-medium">{m.value}</p>
        </div>
      ))}
    </div>
  );
}

export function ResearchSection({
  id,
  title,
  description,
  section,
  children,
}: {
  id: string;
  title: string;
  description?: string;
  section?: StageSectionView;
  children?: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24">
      <Card>
        <CardHeader
          title={title}
          description={description}
          action={
            section ? (
              <Badge
                tone={
                  section.status === "succeeded"
                    ? "success"
                    : section.status === "failed"
                      ? "danger"
                      : "neutral"
                }
              >
                {section.status}
              </Badge>
            ) : undefined
          }
        />
        <CardBody className="space-y-4">
          {section ? <MetricGrid metrics={section.metrics} /> : null}
          {children}
          {section?.error ? (
            <p className="text-sm text-[var(--danger-fg)]">Error: {section.error}</p>
          ) : null}
          {section?.warnings?.length ? (
            <ul className="list-inside list-disc text-sm text-[var(--muted)]">
              {section.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}
        </CardBody>
      </Card>
    </section>
  );
}
