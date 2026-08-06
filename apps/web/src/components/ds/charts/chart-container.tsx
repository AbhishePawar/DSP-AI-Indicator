import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

export type ChartContainerProps = HTMLAttributes<HTMLDivElement> & {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function ChartContainer({
  title,
  description,
  actions,
  className,
  children,
  ...props
}: ChartContainerProps) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] text-[var(--fg)] shadow-[var(--shadow-md)]",
        className,
      )}
      {...props}
    >
      {(title || description || actions) && (
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] px-4 py-3">
          <div className="min-w-0">
            {title ? (
              <h3 className="font-[family-name:var(--font-display)] text-base tracking-tight">
                {title}
              </h3>
            ) : null}
            {description ? (
              <p className="mt-1 text-sm text-[var(--muted)]">{description}</p>
            ) : null}
          </div>
          {actions ? (
            <div className="flex shrink-0 items-center gap-2">{actions}</div>
          ) : null}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}
