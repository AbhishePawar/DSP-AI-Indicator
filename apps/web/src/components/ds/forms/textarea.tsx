"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[5.5rem] w-full rounded-[var(--radius-md,0.5rem)] border border-[var(--border)]",
          "bg-[var(--surface)] px-3 py-2 text-sm text-[var(--fg)]",
          "placeholder:text-[var(--muted)]",
          "shadow-[var(--shadow-sm,0_1px_2px_rgba(0,0,0,0.04))]",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
          "focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]",
          "aria-[invalid=true]:border-[var(--danger-border)]",
          className,
        )}
        ref={ref}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";

export { Textarea };
