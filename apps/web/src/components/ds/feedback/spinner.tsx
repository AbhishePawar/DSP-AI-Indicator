import type { HTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type SpinnerProps = HTMLAttributes<HTMLDivElement> & {
  label?: string;
  size?: "sm" | "md" | "lg";
};

const sizeClass = {
  sm: "size-3.5",
  md: "size-4",
  lg: "size-6",
} as const;

export function Spinner({
  label = "Loading",
  size = "md",
  className,
  ...props
}: SpinnerProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "inline-flex items-center gap-2 text-sm text-[var(--muted)]",
        className,
      )}
      {...props}
    >
      <Loader2
        className={cn("animate-spin text-[var(--accent)]", sizeClass[size])}
        aria-hidden
      />
      <span className="sr-only">{label}</span>
      {label !== "Loading" ? <span>{label}</span> : null}
    </div>
  );
}
