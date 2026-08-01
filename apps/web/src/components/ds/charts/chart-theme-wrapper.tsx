import type { CSSProperties, HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

export type ChartThemeWrapperProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
};

/**
 * Sets CSS variables commonly consumed by chart libraries (ECharts theme adapters, etc.).
 * Pure presentational — no chart engine imports.
 */
export function ChartThemeWrapper({
  className,
  style,
  children,
  ...props
}: ChartThemeWrapperProps) {
  const chartVars = {
    "--chart-bg": "var(--surface)",
    "--chart-fg": "var(--fg)",
    "--chart-muted": "var(--muted)",
    "--chart-border": "var(--border)",
    "--chart-accent": "var(--accent)",
    "--chart-accent-fg": "var(--accent-fg)",
    "--chart-surface": "var(--surface)",
    "--chart-surface-2": "var(--surface-2)",
    "--chart-grid": "color-mix(in srgb, var(--border) 80%, transparent)",
    "--chart-tooltip-bg": "var(--surface)",
    "--chart-tooltip-fg": "var(--fg)",
  } as CSSProperties;

  return (
    <div
      className={cn("text-[var(--chart-fg)]", className)}
      style={{ ...chartVars, ...style }}
      {...props}
    >
      {children}
    </div>
  );
}
