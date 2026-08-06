import type { ReactNode } from "react";

type Tone = "info" | "success" | "warning" | "danger";

const tones: Record<Tone, string> = {
  info: "border-[var(--border)] bg-[var(--surface-2)] text-[var(--fg)]",
  success:
    "border-[var(--accent)]/30 bg-[var(--accent-soft)] text-[var(--accent)]",
  warning:
    "border-[var(--warning-border)] bg-[var(--warning-bg)] text-[var(--warning-fg)]",
  danger:
    "border-[var(--danger-border)] bg-[var(--danger-bg)] text-[var(--danger-fg)]",
};

export function Alert({
  title,
  children,
  tone = "info",
}: {
  title?: string;
  children: ReactNode;
  tone?: Tone;
}) {
  return (
    <div
      role="alert"
      className={`rounded-md border px-3 py-2 text-sm ${tones[tone]}`}
    >
      {title ? <p className="font-medium">{title}</p> : null}
      <div className={title ? "mt-1 opacity-90" : ""}>{children}</div>
    </div>
  );
}
