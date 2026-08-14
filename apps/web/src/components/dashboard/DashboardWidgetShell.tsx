"use client";

import type { ReactNode } from "react";
import Link from "next/link";

import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorState,
  Skeleton,
} from "@/components/ds";
import { cn } from "@/lib/utils";

export function DashboardWidgetShell({
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
  /** @deprecated Span is applied by the dashboard grid wrapper. */
  span?: 1 | 2;
}) {
  return (
    <Card className={cn("h-full", className)}>
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <div className="min-w-0">
          <CardTitle className="text-base">{title}</CardTitle>
          {description ? (
            <CardDescription className="mt-1">{description}</CardDescription>
          ) : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function WidgetLoading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="space-y-2" aria-busy="true" aria-label={label}>
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-16 w-full" />
    </div>
  );
}

export function WidgetUnavailable({
  title = "Data unavailable.",
  description,
  href,
  actionLabel,
}: {
  title?: string;
  description?: string;
  href?: string;
  actionLabel?: string;
}) {
  return (
    <EmptyState
      title={title}
      description={description}
      action={
        href && actionLabel ? (
          <Link href={href}>
            <Button size="sm" variant="secondary">
              {actionLabel}
            </Button>
          </Link>
        ) : undefined
      }
    />
  );
}

export function WidgetError({
  title = "Something went wrong",
  description = "Data unavailable.",
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <ErrorState
      title={title}
      description={description}
      action={
        onRetry ? (
          <Button size="sm" variant="secondary" onClick={onRetry}>
            Retry
          </Button>
        ) : undefined
      }
    />
  );
}
