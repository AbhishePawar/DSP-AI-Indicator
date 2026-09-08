"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme, type ThemeMode } from "@/providers/ThemeProvider";

const options: { mode: ThemeMode; label: string; Icon: typeof Sun }[] = [
  { mode: "light", label: "Light", Icon: Sun },
  { mode: "dark", label: "Dark", Icon: Moon },
  { mode: "system", label: "System", Icon: Monitor },
];

export type ThemeSwitcherProps = {
  className?: string;
  /** Single cycling control for compact headers. Theme engine unchanged. */
  compact?: boolean;
};

const CYCLE: ThemeMode[] = ["light", "dark", "system"];

export function ThemeSwitcher({ className, compact = false }: ThemeSwitcherProps) {
  const { mode, setMode } = useTheme();

  if (compact) {
    const current = options.find((o) => o.mode === mode) ?? options[0];
    const next = CYCLE[(CYCLE.indexOf(mode) + 1) % CYCLE.length]!;
    const Icon = current.Icon;
    return (
      <button
        type="button"
        aria-label={`Theme ${current.label}. Click to switch to ${next}.`}
        title={`Theme: ${current.label}`}
        onClick={() => setMode(next)}
        className={cn(
          "inline-flex min-h-9 min-w-9 items-center justify-center rounded-[var(--radius-md)] text-[var(--muted)] transition hover:bg-[var(--surface-2)] hover:text-[var(--fg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
          className,
        )}
      >
        <Icon className="size-4" aria-hidden />
      </button>
    );
  }

  return (
    <div
      role="group"
      aria-label="Theme"
      className={cn(
        "inline-flex rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-0.5",
        className,
      )}
    >
      {options.map(({ mode: option, label, Icon }) => {
        const active = mode === option;
        return (
          <button
            key={option}
            type="button"
            aria-pressed={active}
            aria-label={label}
            title={label}
            onClick={() => setMode(option)}
            className={cn(
              "inline-flex min-h-9 min-w-9 items-center justify-center rounded-[calc(var(--radius-md)-2px)] px-2 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
              active
                ? "bg-[var(--accent)] text-[var(--accent-fg)]"
                : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
            )}
          >
            <Icon className="size-4" aria-hidden />
            <span className="sr-only">{label}</span>
          </button>
        );
      })}
    </div>
  );
}
