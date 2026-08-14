import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const gapClass = {
  0: "gap-0",
  1: "gap-1",
  2: "gap-2",
  3: "gap-3",
  4: "gap-4",
  5: "gap-5",
  6: "gap-6",
  8: "gap-8",
  10: "gap-10",
  12: "gap-12",
} as const;

export type StackGap = keyof typeof gapClass;
export type StackDirection = "vertical" | "horizontal";

export type StackProps = HTMLAttributes<HTMLDivElement> & {
  gap?: StackGap;
  direction?: StackDirection;
};

export function Stack({
  gap = 4,
  direction = "vertical",
  className,
  children,
  ...props
}: StackProps) {
  return (
    <div
      className={cn(
        "flex",
        direction === "vertical" ? "flex-col" : "flex-row",
        gapClass[gap],
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
