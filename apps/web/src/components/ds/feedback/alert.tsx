import type { HTMLAttributes, ReactNode } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

const variants = {
  info: {
    className:
      "border-[var(--border)] bg-[var(--surface-2)] text-[var(--fg)]",
    Icon: Info,
  },
  success: {
    className:
      "border-[color-mix(in_srgb,var(--accent)_35%,var(--border))] bg-[var(--accent-soft)] text-[var(--accent)]",
    Icon: CheckCircle2,
  },
  warning: {
    className:
      "border-[color-mix(in_srgb,#d4b56a_60%,var(--border))] bg-[#f7ecd2] text-[#6b5210] dark:bg-[var(--warning-bg,#2a2412)] dark:text-[var(--warning-fg,#fbbf24)]",
    Icon: AlertTriangle,
  },
  error: {
    className:
      "border-[var(--danger-border)] bg-[var(--danger-bg)] text-[var(--danger-fg)]",
    Icon: AlertCircle,
  },
} as const;

export type AlertVariant = keyof typeof variants;

export type AlertProps = HTMLAttributes<HTMLDivElement> & {
  variant?: AlertVariant;
  title?: string;
  children?: ReactNode;
  icon?: ReactNode;
};

export function Alert({
  variant = "info",
  title,
  children,
  icon,
  className,
  ...props
}: AlertProps) {
  const { className: toneClass, Icon } = variants[variant];

  return (
    <div
      role="alert"
      className={cn(
        "flex gap-3 rounded-[var(--radius-md)] border px-3 py-2.5 text-sm",
        toneClass,
        className,
      )}
      {...props}
    >
      <span className="mt-0.5 shrink-0" aria-hidden>
        {icon ?? <Icon className="size-4" />}
      </span>
      <div className="min-w-0 flex-1">
        {title ? <p className="font-medium leading-tight">{title}</p> : null}
        {children ? (
          <div className={cn(title ? "mt-1 opacity-90" : null)}>{children}</div>
        ) : null}
      </div>
    </div>
  );
}
