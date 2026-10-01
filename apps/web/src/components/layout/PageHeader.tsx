import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div data-testid="page-header" className="flex flex-col gap-3 border-b border-[var(--border)] pb-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="break-words font-[family-name:var(--font-display)] text-base font-medium tracking-tight text-[var(--fg)]">
          {title}
        </h1>
        {description ? (
          <p className="mt-0.5 max-w-3xl font-mono text-[11px] leading-relaxed text-[var(--muted)]">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
