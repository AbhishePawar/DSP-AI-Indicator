"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-[var(--radius-md,0.5rem)] px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "bg-[var(--surface-2)] text-[var(--fg)]",
        accent: "bg-[var(--accent-soft)] text-[var(--accent)]",
        danger: "bg-[var(--danger-bg)] text-[var(--danger-fg)] border border-[var(--danger-border)]",
        warning:
          "bg-[var(--warning-bg,#f7ecd2)] text-[var(--warning-fg,#7a5a12)]",
        outline: "border border-[var(--border)] bg-transparent text-[var(--muted)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
