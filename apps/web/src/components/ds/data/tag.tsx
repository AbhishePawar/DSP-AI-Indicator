"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const tagVariants = cva(
  "inline-flex items-center gap-1 rounded-[var(--radius-md,0.5rem)] px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default: "bg-[var(--surface-2)] text-[var(--fg)]",
        accent: "bg-[var(--accent-soft)] text-[var(--accent)]",
        muted: "bg-transparent text-[var(--muted)] border border-[var(--border)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface TagProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof tagVariants> {}

function Tag({ className, variant, ...props }: TagProps) {
  return <span className={cn(tagVariants({ variant }), className)} {...props} />;
}

export { Tag, tagVariants };
