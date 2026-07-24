"use client";

import { QUICK_ACTIONS, type CopilotAction } from "@/lib/analysis/sprint6Copilot";

export function QuickActionBar({
  onAction,
  disabled,
}: {
  onAction: (action: CopilotAction) => void;
  disabled?: boolean;
}) {
  return (
    <div
      className="flex flex-wrap gap-2"
      role="toolbar"
      aria-label="Copilot quick actions"
    >
      {QUICK_ACTIONS.map((a) => (
        <button
          key={a.id}
          type="button"
          disabled={disabled}
          className="min-h-11 rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 text-xs font-medium hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] disabled:opacity-50"
          onClick={() => onAction(a.id)}
        >
          {a.label}
        </button>
      ))}
    </div>
  );
}
