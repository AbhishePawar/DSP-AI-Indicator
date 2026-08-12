import type { HTMLAttributes, ReactNode } from "react";
import { Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

export type EmptyStateProps = HTMLAttributes<HTMLDivElement> & {
  title?: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
};

export function EmptyState({
  title = "Data unavailable.",
  description,
  action,
  icon,
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      role="status"
      className={cn(
        "flex flex-col items-center justify-center px-4 py-10 text-center",
        className,
      )}
      {...props}
    >
      <span className="mb-3 text-[var(--muted)]" aria-hidden>
        {icon ?? <Inbox className="size-8" />}
      </span>
      <p className="font-[family-name:var(--font-display)] text-lg tracking-tight text-[var(--fg)]">
        {title}
      </p>
      {description ? (
        <p className="mt-2 max-w-sm text-sm text-[var(--muted)]">{description}</p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
