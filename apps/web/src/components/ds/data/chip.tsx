"use client";

import * as React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  onDismiss?: () => void;
  dismissLabel?: string;
}

function Chip({
  className,
  children,
  onDismiss,
  dismissLabel = "Remove",
  ...props
}: ChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-[var(--radius-md,0.5rem)]",
        "border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-xs text-[var(--fg)]",
        "shadow-[var(--shadow-sm,0_1px_2px_rgba(0,0,0,0.04))]",
        className,
      )}
      {...props}
    >
      {children}
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          aria-label={dismissLabel}
          className={cn(
            "ml-0.5 inline-flex h-4 w-4 items-center justify-center rounded-sm text-[var(--muted)]",
            "hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
            "focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]",
          )}
        >
          <X className="h-3 w-3" aria-hidden />
        </button>
      ) : null}
    </span>
  );
}

export { Chip };
