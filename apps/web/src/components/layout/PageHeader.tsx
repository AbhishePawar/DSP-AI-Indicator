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
    <div className="page-header -mx-4 mb-2 sm:-mx-6">
      <div className="min-w-0">
        <h1 className="break-words font-[family-name:var(--font-display)] text-base font-medium tracking-tight text-[var(--fg)] sm:text-lg">
          {title}
        </h1>
        {description ? (
          <p className="mt-1 max-w-2xl font-mono text-[11px] text-[var(--muted)]">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </div>
  );
}
