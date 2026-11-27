import type { InputHTMLAttributes } from "react";

export function Input({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`h-10 w-full rounded-[var(--radius-md,8px)] border border-[var(--border)] bg-[var(--bg,#080b12)] px-3.5 py-2 text-sm text-[var(--fg)] outline-none transition placeholder:text-[var(--muted-foreground,#6b7a99)] focus-visible:border-[var(--accent)] focus-visible:ring-2 focus-visible:ring-[var(--accent)]/30 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    />
  );
}
