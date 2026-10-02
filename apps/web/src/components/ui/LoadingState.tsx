import type { ReactNode } from "react";
import { Spinner } from "./Spinner";

export function LoadingState({
  title = "Loading data",
  description,
  steps,
  currentStepIndex,
  className = "",
}: {
  title?: string;
  description?: string;
  steps?: string[];
  currentStepIndex?: number;
  className?: string;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex flex-col items-center justify-center rounded-[var(--card-radius,14px)] border border-[var(--border)] bg-[var(--card,#111520)] px-6 py-12 text-center ${className}`}
    >
      <Spinner label={title} />
      <p className="mt-3 font-[family-name:var(--font-display)] text-base font-medium text-[var(--fg)]">
        {title}
      </p>
      {description ? (
        <p className="mt-1.5 max-w-sm text-xs text-[var(--muted-foreground)]">
          {description}
        </p>
      ) : null}
      {steps && steps.length > 0 ? (
        <ul className="mt-5 space-y-1 text-left font-mono text-[11px] text-[var(--muted)]" aria-label="Loading progress">
          {steps.map((step, idx) => {
            const isCompleted = typeof currentStepIndex === "number" && idx < currentStepIndex;
            const isCurrent = typeof currentStepIndex === "number" && idx === currentStepIndex;
            return (
              <li
                key={step}
                className={`flex items-center gap-2 ${
                  isCurrent ? "font-semibold text-[var(--accent)]" : isCompleted ? "text-[var(--fg)]/70" : "opacity-40"
                }`}
              >
                <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
                <span>{step}</span>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
