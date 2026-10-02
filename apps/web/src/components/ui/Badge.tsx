import type { ReactNode } from "react";

type Tone = "neutral" | "success" | "warning" | "danger" | "accent" | "info";

const tones: Record<Tone, string> = {
  neutral: "border border-[var(--border)] bg-[var(--surface-2,#181e2e)] text-[var(--muted-foreground)]",
  success: "border border-[var(--success-border,#1f4a38)] bg-[var(--success-bg,#10261f)] text-[var(--success-fg,#34d399)]",
  warning: "border border-[var(--warning-border,#4c3d12)] bg-[var(--warning-bg,#2a2412)] text-[var(--warning-fg,#fbbf24)]",
  danger: "border border-[var(--danger-border,#4c1d1d)] bg-[var(--danger-bg,#2a1215)] text-[var(--danger-fg,#f87171)]",
  accent: "border border-[var(--accent)]/30 bg-[var(--accent-soft)] text-[var(--accent)]",
  info: "border border-[var(--info-border,#1b3a4a)] bg-[var(--info-bg,#0f1a24)] text-[var(--info-fg,#38bdf8)]",
};

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-2.5 py-0.5 font-mono text-[11px] font-medium tracking-wide ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
