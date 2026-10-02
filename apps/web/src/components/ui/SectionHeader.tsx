import type { ReactNode } from "react";

export function SectionHeader({
  eyebrow,
  title,
  description,
  action,
  as: Component = "h2",
  className = "",
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  as?: "h1" | "h2" | "h3" | "h4";
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between ${className}`}>
      <div className="max-w-2xl">
        {eyebrow ? (
          <p className="font-mono text-[10px] uppercase tracking-wider text-[var(--accent)]">
            {eyebrow}
          </p>
        ) : null}
        <Component className="mt-1 font-[family-name:var(--font-display)] text-xl font-medium tracking-tight text-[var(--fg)] sm:text-2xl">
          {title}
        </Component>
        {description ? (
          <p className="mt-1.5 text-sm text-[var(--muted-foreground)] leading-relaxed">
            {description}
          </p>
        ) : null}
      </div>
      {action ? <div className="mt-2 shrink-0 sm:mt-0">{action}</div> : null}
    </div>
  );
}
