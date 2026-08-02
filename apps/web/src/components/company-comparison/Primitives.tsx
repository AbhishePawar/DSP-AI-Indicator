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
import { DATA_UNAVAILABLE } from "@/lib/company-comparison";
import type { Medal } from "@/lib/company-comparison";
import { cn } from "@/lib/utils";

export function FieldRow({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  const display =
    value === null ||
    value === undefined ||
    value === "" ||
    value === "Unavailable" ||
    value === "—"
      ? DATA_UNAVAILABLE
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
    <Card className={cn(className)}>
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

export function WorkspaceEmpty({
  title = "No comparison yet",
  description = "Add 2–5 company tickers and run Compare. This workspace assists decisions — it never makes investment decisions for users.",
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return <EmptyState title={title} description={description} action={action} />;
}

export function WorkspaceSkeleton() {
  return (
    <div
      className="space-y-4 p-4"
      aria-busy="true"
      aria-label="Loading company comparison"
    >
      <Skeleton className="h-10 w-full max-w-xl" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

export function MedalBadge({ medal }: { medal: Medal }) {
  if (!medal) return null;
  const label =
    medal === "gold" ? "1st" : medal === "silver" ? "2nd" : "3rd";
  const tone =
    medal === "gold" ? "accent" : medal === "silver" ? "default" : "outline";
  return (
    <Badge variant={tone} className="ml-1">
      {label}
    </Badge>
  );
}

export function AlignmentBadge({
  alignment,
}: {
  alignment: "aligned" | "partial" | "not_aligned" | "unavailable";
}) {
  const map = {
    aligned: { label: "Aligned", variant: "accent" as const },
    partial: { label: "Partial", variant: "default" as const },
    not_aligned: { label: "Not aligned", variant: "outline" as const },
    unavailable: { label: DATA_UNAVAILABLE, variant: "outline" as const },
  };
  const m = map[alignment];
  return <Badge variant={m.variant}>{m.label}</Badge>;
}

export function HeatCell({
  intensity,
  display,
}: {
  intensity: "high" | "medium" | "low" | "unavailable";
  display: string;
}) {
  const bg =
    intensity === "high"
      ? "bg-[var(--accent)]/25"
      : intensity === "medium"
        ? "bg-[var(--accent)]/12"
        : intensity === "low"
          ? "bg-[var(--muted)]/20"
          : "bg-transparent";
  return (
    <div
      className={cn(
        "rounded-md border border-[var(--border)] px-2 py-2 text-center text-xs motion-safe:transition-colors",
        bg,
      )}
    >
      {display}
    </div>
  );
}
