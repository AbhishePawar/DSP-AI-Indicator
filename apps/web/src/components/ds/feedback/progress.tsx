"use client";

import * as ProgressPrimitive from "@radix-ui/react-progress";
import type { ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/utils";

export type ProgressProps = ComponentPropsWithoutRef<
  typeof ProgressPrimitive.Root
> & {
  value?: number | null;
  indeterminate?: boolean;
};

export function Progress({
  className,
  value = 0,
  indeterminate = false,
  ...props
}: ProgressProps) {
  const clamped =
    value == null ? 0 : Math.min(100, Math.max(0, Number(value)));

  return (
    <ProgressPrimitive.Root
      value={indeterminate ? null : clamped}
      className={cn(
        "relative h-2 w-full overflow-hidden rounded-full bg-[var(--surface-2)]",
        className,
      )}
      {...props}
    >
      <ProgressPrimitive.Indicator
        className={cn(
          "h-full w-full flex-1 rounded-full bg-[var(--accent)] transition-transform duration-300 ease-out",
          indeterminate && "animate-pulse",
        )}
        style={
          indeterminate
            ? { transform: "translateX(-35%)" }
            : { transform: `translateX(-${100 - clamped}%)` }
        }
      />
    </ProgressPrimitive.Root>
  );
}
