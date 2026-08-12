import type { ReactNode } from "react";

type SectionProps = {
  id?: string;
  eyebrow?: string;
  title: string;
  lead?: string;
  children?: ReactNode;
  className?: string;
};

export function Section({
  id,
  eyebrow,
  title,
  lead,
  children,
  className = "",
}: SectionProps) {
  return (
    <section
      id={id}
      className={`scroll-mt-24 border-t border-[var(--border)] px-4 py-16 sm:px-6 sm:py-20 ${className}`}
      aria-labelledby={id ? `${id}-title` : undefined}
    >
      <div className="mx-auto max-w-[72rem]">
        {eyebrow ? (
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            {eyebrow}
          </p>
        ) : null}
        <h2
          id={id ? `${id}-title` : undefined}
          className="mt-2 max-w-[28ch] font-[family-name:var(--font-display)] text-3xl font-medium tracking-tight text-[var(--fg)] sm:text-4xl"
        >
          {title}
        </h2>
        {lead ? (
          <p className="mt-4 max-w-[62ch] text-base leading-relaxed text-[var(--muted)]">
            {lead}
          </p>
        ) : null}
        {children ? <div className="mt-10">{children}</div> : null}
      </div>
    </section>
  );
}
