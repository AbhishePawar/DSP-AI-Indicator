"use client";

import type { ReactNode } from "react";
import { Button } from "./Button";

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
}: {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-4 py-10 text-center">
      <p className="font-[family-name:var(--font-display)] text-lg tracking-tight">
        {title}
      </p>
      {description ? (
        <p className="mt-2 max-w-sm text-sm text-[var(--muted)]">{description}</p>
      ) : null}
      {actionLabel && onAction ? (
        <Button className="mt-4" variant="secondary" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  description,
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div
      role="alert"
      className="rounded-md border border-[var(--danger-border)] bg-[var(--danger-bg)] px-4 py-6 text-center"
    >
      <p className="font-medium text-[var(--danger-fg)]">{title}</p>
      {description ? (
        <p className="mt-2 text-sm text-[var(--danger-fg)]/90">{description}</p>
      ) : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}

export function SuccessState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div
      role="status"
      className="rounded-md border border-[var(--accent)]/35 bg-[var(--accent-soft)]/50 px-4 py-6 text-center"
    >
      <p className="font-[family-name:var(--font-display)] text-lg tracking-tight text-[var(--fg)]">
        {title}
      </p>
      {description ? (
        <p className="mt-2 text-sm text-[var(--muted)]">{description}</p>
      ) : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}
