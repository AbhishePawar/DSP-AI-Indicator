import type { HTMLAttributes, ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export type ErrorStateProps = HTMLAttributes<HTMLDivElement> & {
  title?: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
};

export function ErrorState({
  title = "Something went wrong",
  description,
  action,
  icon,
  className,
  ...props
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center rounded-[var(--radius-md)] border border-[var(--danger-border)] bg-[var(--danger-bg)] px-4 py-8 text-center",
        className,
      )}
      {...props}
    >
      <span className="mb-3 text-[var(--danger-fg)]" aria-hidden>
        {icon ?? <AlertCircle className="size-8" />}
      </span>
      <p className="font-medium text-[var(--danger-fg)]">{title}</p>
      {description ? (
        <p className="mt-2 max-w-sm text-sm text-[var(--danger-fg)]/90">
          {description}
        </p>
      ) : null}
      {action ? (
        <div className="mt-4 flex justify-center">{action}</div>
      ) : null}
    </div>
  );
}
