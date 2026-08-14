import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

export type SectionProps = HTMLAttributes<HTMLElement> & {
  title?: string;
  description?: string;
  actions?: ReactNode;
};

export function Section({
  title,
  description,
  actions,
  className,
  children,
  ...props
}: SectionProps) {
  const headingId = title
    ? `section-${title.toLowerCase().replace(/\s+/g, "-")}`
    : undefined;

  return (
    <section
      aria-labelledby={headingId}
      className={cn("py-6", className)}
      {...props}
    >
      {(title || description || actions) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            {title ? (
              <h2
                id={headingId}
                className="font-[family-name:var(--font-display)] text-xl tracking-tight text-[var(--fg)]"
              >
                {title}
              </h2>
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
      {children}
    </section>
  );
}
