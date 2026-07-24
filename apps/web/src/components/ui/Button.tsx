"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const variants: Record<Variant, string> = {
  primary:
    "bg-[var(--accent)] text-[var(--accent-fg)] hover:opacity-90 focus-visible:ring-[var(--accent)]",
  secondary:
    "border border-[var(--border)] bg-[var(--surface)] text-[var(--fg)] hover:bg-[var(--surface-2)] focus-visible:ring-[var(--accent)]",
  ghost:
    "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)] focus-visible:ring-[var(--accent)]",
  danger:
    "bg-[var(--danger-bg)] text-[var(--danger-fg)] border border-[var(--danger-border)] focus-visible:ring-[var(--danger-fg)]",
};

const sizes: Record<Size, string> = {
  sm: "min-h-9 px-2.5 py-1.5 text-xs",
  md: "min-h-11 px-3 py-2 text-sm",
  lg: "min-h-12 px-4 py-2.5 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
}) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-md font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg)] disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
      type={type}
    >
      {children}
    </button>
  );
}
