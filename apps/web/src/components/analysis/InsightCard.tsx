import type { ReactNode } from "react";

export function SectionDivider({ label }: { label?: string }) {
  return (
    <div className="pt-2 pb-1" role="separator" aria-label={label}>
      {label ? (
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
          {label}
        </p>
      ) : (
        <div className="h-px bg-[var(--border)]" />
      )}
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
    <div className="space-y-6">
      {/* Section heading + editorial intro — matches ResearchSection/AnalysisSectionShell hierarchy */}
      <div className="space-y-3">
        <h2 className="font-[family-name:var(--font-display)] text-lg sm:text-xl tracking-tight text-[var(--fg)]">
          {title}
        </h2>
        <p className="border-l-2 border-[var(--border)] pl-3 text-sm leading-relaxed text-[var(--muted)]">
          <span className="font-medium text-[var(--fg)]">What you should know — </span>
          {intro}
        </p>
      </div>

      {children}

      {/* Editorial outro */}
      <p className="border-t border-[var(--border)] pt-4 text-sm leading-relaxed text-[var(--muted)]">
        <span className="font-medium text-[var(--fg)]">What investors should monitor — </span>
        {outro}
      </p>
    </div>
  );
}
