import type { HTMLAttributes, ReactNode } from "react";
import { CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type SuccessStateProps = HTMLAttributes<HTMLDivElement> & {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
};

export function SuccessState({
  title,
  description,
  action,
  icon,
  className,
  ...props
}: SuccessStateProps) {
  return (
    <div
      role="status"
      className={cn(
        "flex flex-col items-center justify-center rounded-[var(--radius-md)] border border-[color-mix(in_srgb,var(--accent)_35%,var(--border))] bg-[var(--accent-soft)]/50 px-4 py-8 text-center",
        className,
      )}
      {...props}
    >
      <span className="mb-3 text-[var(--accent)]" aria-hidden>
        {icon ?? <CheckCircle2 className="size-8" />}
      </span>
      <p className="font-[family-name:var(--font-display)] text-lg tracking-tight text-[var(--fg)]">
        {title}
      </p>
      {description ? (
        <p className="mt-2 max-w-sm text-sm text-[var(--muted)]">{description}</p>
      ) : null}
      {action ? (
        <div className="mt-4 flex justify-center">{action}</div>
      ) : null}
    </div>
  );
}
