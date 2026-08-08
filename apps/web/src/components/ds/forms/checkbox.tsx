"use client";

import * as React from "react";
import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

const Checkbox = React.forwardRef<
  React.ElementRef<typeof CheckboxPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>
>(({ className, ...props }, ref) => (
  <CheckboxPrimitive.Root
    ref={ref}
    className={cn(
      // Visual box 20px; expanded hit target ≥44px via absolute pseudo-area.
      "peer relative h-5 w-5 shrink-0 rounded-[calc(var(--radius-md,0.5rem)-2px)]",
      "before:absolute before:left-1/2 before:top-1/2 before:h-11 before:w-11",
      "before:-translate-x-1/2 before:-translate-y-1/2 before:content-['']",
      "border border-[var(--border)] bg-[var(--surface)]",
      "shadow-[var(--shadow-sm,0_1px_2px_rgba(0,0,0,0.04))]",
      "disabled:cursor-not-allowed disabled:opacity-50",
      "data-[state=checked]:border-[var(--accent)] data-[state=checked]:bg-[var(--accent)]",
      "data-[state=checked]:text-[var(--accent-fg)]",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
      "focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)]",
      className,
    )}
    {...props}
  >
    <CheckboxPrimitive.Indicator className={cn("flex items-center justify-center text-current")}>
      <Check className="h-3 w-3" aria-hidden />
    </CheckboxPrimitive.Indicator>
  </CheckboxPrimitive.Root>
));
Checkbox.displayName = CheckboxPrimitive.Root.displayName;

export type CheckboxProps = React.ComponentPropsWithoutRef<
  typeof CheckboxPrimitive.Root
>;
export { Checkbox };
