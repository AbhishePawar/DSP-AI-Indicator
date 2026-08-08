import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type FlexProps = HTMLAttributes<HTMLDivElement> & {
  direction?: "row" | "col" | "row-reverse" | "col-reverse";
  align?: "start" | "center" | "end" | "stretch" | "baseline";
  justify?: "start" | "center" | "end" | "between" | "around" | "evenly";
  wrap?: boolean;
  gap?: 0 | 1 | 2 | 3 | 4 | 5 | 6 | 8;
};

const directionClass = {
  row: "flex-row",
  col: "flex-col",
  "row-reverse": "flex-row-reverse",
  "col-reverse": "flex-col-reverse",
} as const;

const alignClass = {
  start: "items-start",
  center: "items-center",
  end: "items-end",
  stretch: "items-stretch",
  baseline: "items-baseline",
} as const;

const justifyClass = {
  start: "justify-start",
  center: "justify-center",
  end: "justify-end",
  between: "justify-between",
  around: "justify-around",
  evenly: "justify-evenly",
} as const;

const gapClass = {
  0: "gap-0",
  1: "gap-1",
  2: "gap-2",
  3: "gap-3",
  4: "gap-4",
  5: "gap-5",
  6: "gap-6",
  8: "gap-8",
} as const;

export function Flex({
  direction = "row",
  align,
  justify,
  wrap = false,
  gap,
  className,
  children,
  ...props
}: FlexProps) {
  return (
    <div
      className={cn(
        "flex",
        directionClass[direction],
        align ? alignClass[align] : null,
        justify ? justifyClass[justify] : null,
        wrap ? "flex-wrap" : null,
        gap !== undefined ? gapClass[gap] : null,
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
