import type { ReactNode } from "react";

export function SectionDivider({ label }: { label?: string }) {
  return (
    <div className="my-6 flex items-center gap-3" role="separator" aria-label={label}>
      <div className="h-px flex-1 bg-[var(--border)]" />
      {label ? (
        <span className="text-xs uppercase tracking-wide text-[var(--muted)]">
          {label}
        </span>
      ) : null}
      <div className="h-px flex-1 bg-[var(--border)]" />
    </div>
  );
}

export function InsightCard({
  title,
  intro,
  outro,
  children,
}: {
  title: string;
  intro: string;
  outro: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-tight">
          {title}
        </h2>
        <p className="mt-2 rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm">
          <span className="font-medium">What you should know — </span>
          {intro}
        </p>
      </div>
      {children}
      <p className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm">
        <span className="font-medium">What investors should monitor — </span>
        {outro}
      </p>
    </div>
  );
}
