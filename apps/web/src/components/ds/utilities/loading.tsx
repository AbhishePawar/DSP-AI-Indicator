import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Spinner } from "../feedback/spinner";
import { Skeleton } from "../feedback/skeleton";

export type LoadingBlockProps = HTMLAttributes<HTMLDivElement> & {
  label?: string;
  /** Prefer skeleton placeholders when laying out known structure. */
  variant?: "spinner" | "skeleton";
  rows?: number;
  children?: ReactNode;
};

export function LoadingBlock({
  label = "Loading",
  variant = "spinner",
  rows = 3,
  className,
  children,
  ...props
}: LoadingBlockProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={cn("w-full", className)}
      {...props}
    >
      {variant === "spinner" ? (
        <div className="flex flex-col items-center justify-center gap-3 py-8">
          <Spinner label={label} />
          <span className="text-sm text-[var(--muted)]">{label}</span>
          {children}
        </div>
      ) : (
        <div className="flex flex-col gap-3 py-2" aria-label={label}>
          {Array.from({ length: rows }, (_, i) => (
            <Skeleton
              key={i}
              className={cn("h-4 w-full", i === rows - 1 && "w-2/3")}
            />
          ))}
          {children}
        </div>
      )}
    </div>
  );
}
