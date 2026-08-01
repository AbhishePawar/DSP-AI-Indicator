"use client";

import type { ReactNode } from "react";

import {
  Badge,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  Skeleton,
} from "@/components/ds";
import type { StageSectionView } from "@/lib/research/mapResearchView";
import { cn } from "@/lib/utils";

export function FieldRow({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  const display =
    value === null || value === undefined || value === "" || value === "Unavailable"
      ? "Data unavailable."
      : value;
  return (
    <div className="flex justify-between gap-4 border-b border-[var(--border)] py-2 text-sm last:border-0">
      <dt className="text-[var(--muted)]">{label}</dt>
      <dd className="text-right font-medium text-[var(--fg)]">{display}</dd>
    </div>
  );
}

export function SectionCard({
  title,
  description,
  action,
  children,
  className,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn(className)} id={undefined}>
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <div>
          <CardTitle className="text-base">{title}</CardTitle>
          {description ? (
            <CardDescription className="mt-1">{description}</CardDescription>
          ) : null}
        </div>
        {action}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function StageSectionCard({
  title,
  section,
}: {
  title: string;
  section: StageSectionView;
}) {
  return (
    <SectionCard
      title={title}
      description={`Stage: ${section.stage} · status ${section.status}`}
      action={
        <Badge variant={section.status === "succeeded" ? "accent" : "outline"}>
          {section.status}
        </Badge>
      }
    >
      <dl>
        <FieldRow label="Label" value={section.label} />
        <FieldRow label="Decision" value={section.decision} />
        <FieldRow label="Score" value={section.score} />
        <FieldRow label="Confidence" value={section.confidence} />
      </dl>
      {section.metrics.length ? (
        <ul className="mt-3 space-y-1 text-sm">
          {section.metrics.map((m) => (
            <li key={m.label} className="flex justify-between gap-3">
              <span className="text-[var(--muted)]">{m.label}</span>
              <span>{m.value === "Unavailable" ? "Data unavailable." : m.value}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {section.error ? (
        <p className="mt-3 text-sm text-[var(--danger-fg)]">{section.error}</p>
      ) : null}
      {section.warnings.length ? (
        <ul className="mt-2 list-disc pl-4 text-xs text-[var(--muted)]">
          {section.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      ) : null}
    </SectionCard>
  );
}

export function WorkspaceSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading analysis">
      <Skeleton className="h-8 w-1/3" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

export function WorkspaceEmpty({
  title = "Data unavailable.",
  description,
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <EmptyState title={title} description={description} action={action} />
  );
}
