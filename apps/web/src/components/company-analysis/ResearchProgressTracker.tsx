"use client";

import { Badge } from "@/components/ds";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { cn } from "@/lib/utils";

const stages = [
  ["financial", "Financials"],
  ["business_quality_aggregator", "Quality"],
  ["economic_moat", "Moat"],
  ["valuation", "Valuation"],
  ["investment_committee", "Committee"],
] as const;

export function ResearchProgressTracker({
  view,
  analysing = false,
}: {
  view?: ResearchView | null;
  analysing?: boolean;
}) {
  const returnedStages = new Set(view?.stages.map((stage) => stage.stage) ?? []);
  const completeCount = stages.filter(([stage]) => returnedStages.has(stage)).length;
  return (
    <section
      aria-label="Research progression"
      className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
            Research progression
          </p>
          <p className="mt-1 text-sm">
            {analysing
              ? "Refreshing certified research stages…"
              : view
                ? `${completeCount} of ${stages.length} headline stages returned`
                : "Awaiting an explicit company selection"}
          </p>
        </div>
        <Badge variant={analysing ? "outline" : view?.ok ? "accent" : "outline"}>
          {analysing ? "In progress" : view?.ok ? "Returned" : "Pending"}
        </Badge>
      </div>
      <ol className="grid gap-2 sm:grid-cols-5">
        {stages.map(([stage, label], index) => {
          const returned = returnedStages.has(stage);
          return (
            <li key={stage} className="flex items-center gap-2 text-xs sm:block">
              <span
                className={cn(
                  "flex size-6 shrink-0 items-center justify-center rounded-full border text-[10px] font-semibold",
                  returned
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                    : "border-[var(--border)] text-[var(--muted)]",
                )}
              >
                {returned ? "✓" : index + 1}
              </span>
              <span
                className={cn(
                  "font-medium",
                  returned ? "text-[var(--fg)]" : "text-[var(--muted)]",
                )}
              >
                {label}
              </span>
              {index < stages.length - 1 ? (
                <span
                  className="hidden h-px bg-[var(--border)] sm:mt-3 sm:block"
                  aria-hidden="true"
                />
              ) : null}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
