"use client";

import type { ReactNode } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  Skeleton,
} from "@/components/ds";
import { cn } from "@/lib/utils";

export function FieldRow({
  label,
  value,
}: {
  label: string;
  value: string | number | boolean | null | undefined;
}) {
  const display =
    value === null ||
    value === undefined ||
    value === "" ||
    value === "Unavailable"
      ? "Data unavailable."
      : String(value);
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
  title = "Data unavailable.",
  description,
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
      className="space-y-3"
      aria-busy="true"
      aria-label="Loading administration console"
    >
      <Skeleton className="h-8 w-1/3" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

export function QueryError({ message }: { message?: string | null }) {
  return (
    <WorkspaceEmpty
      title="Data unavailable."
      description={message || "Unable to load administration data from /api/v1/admin."}
    />
  );
}
