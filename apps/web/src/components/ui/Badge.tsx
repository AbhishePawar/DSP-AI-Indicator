import type { ReactNode } from "react";

type Tone = "neutral" | "success" | "warning" | "danger" | "accent";

const tones: Record<Tone, string> = {
  neutral: "bg-[var(--surface-2)] text-[var(--muted)]",
  success: "bg-[var(--accent-soft)] text-[var(--accent)]",
  warning: "bg-[#f5e6c8] text-[#7a5a12] dark:bg-[#3a3218] dark:text-[#e6d29a]",
  danger: "bg-[var(--danger-bg)] text-[var(--danger-fg)]",
  accent: "bg-[var(--accent-soft)] text-[var(--accent)]",
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
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
