import type { HTMLAttributes, ReactNode } from "react";

type CardVariant = "default" | "elevated" | "subtle" | "ghost";

const cardVariants: Record<CardVariant, string> = {
  default: "border border-[var(--border)] bg-[var(--card,#111520)] shadow-[var(--shadow-card)]",
  elevated: "border border-[var(--border)] bg-[var(--surface-2,#181e2e)] shadow-[var(--shadow-lg)]",
  subtle: "border border-[var(--border)]/50 bg-[var(--surface,#111520)]/60 backdrop-blur-sm",
  ghost: "border-0 bg-transparent shadow-none",
};

export function Card({
  children,
  variant = "default",
  className = "",
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  variant?: CardVariant;
}) {
  return (
    <div
      className={`rounded-[var(--card-radius,14px)] transition-colors ${cardVariants[variant]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  description,
  action,
  className = "",
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex items-start justify-between gap-3 border-b border-[var(--border)] px-5 py-4 ${className}`}>
      <div>
        <h3 className="font-[family-name:var(--font-display)] text-lg font-medium tracking-tight text-[var(--fg)]">
          {title}
        </h3>
        {description ? (
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function CardBody({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}
