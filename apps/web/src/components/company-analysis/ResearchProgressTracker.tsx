"use client";

import { Badge } from "@/components/ds";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { cn } from "@/lib/utils";

const teamStages = [
  [
    "find",
    "Researching primary sources",
    "Candidate evidence from authoritative sources",
  ],
  ["verify", "Verifying evidence", "Checking provenance and source quality"],
  ["attack", "Testing the thesis", "Searching for disconfirming evidence"],
  ["review", "Independent review", "Reviewing contradictions and evidence sufficiency"],
] as const;

const stages = [
  ["identity", "Security identity", "Company and exchange confirmed"],
  ["evidence", "Finding evidence", "Collecting verified research inputs"],
  [
    "financial",
    "Financial performance",
    "Profitability, cash generation and balance sheet",
  ],
  [
    "business_quality_aggregator",
    "Business quality",
    "Durability, reinvestment and operating discipline",
  ],
  ["economic_moat", "Economic moat", "Competitive position and long-term advantages"],
  ["valuation", "Valuation", "Intrinsic value and margin of safety"],
  ["risk", "Risks", "Financial, business and valuation risks"],
  ["investment_committee", "DSP judgment", "Forming the investment view"],
] as const;

export function ResearchProgressTracker({
  view,
  analysing = false,
  ticker,
}: {
  view?: ResearchView | null;
  analysing?: boolean;
  ticker?: string;
}) {
  const returnedStages = new Set(view?.stages.map((stage) => stage.stage) ?? []);
  const researchTeam = view?.researchTeam;
  const teamByRole = new Map(
    researchTeam?.agents.map((agent) => [agent.role, agent]) ?? [],
  );
  const knownStages = new Set([
    "financial",
    "business_quality_aggregator",
    "economic_moat",
    "valuation",
    "investment_committee",
  ]);
  const completeCount = stages.filter(([stage]) =>
    stage === "identity"
      ? Boolean(ticker)
      : knownStages.has(stage) && returnedStages.has(stage),
  ).length;
  const activeIndex = analysing
    ? Math.min(completeCount, stages.length - 1)
    : completeCount;
  return (
    <section
      aria-label="Research progression"
      className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
            {ticker ? `Researching ${ticker}` : "Research progression"}
          </p>
          <p className="mt-1 text-sm">
            {analysing
              ? "DSP is building an evidence-backed investment view."
              : view
                ? `${completeCount} of ${stages.length} methodology stages represented`
                : "Awaiting an explicit company selection"}
          </p>
        </div>
        <Badge variant={analysing ? "outline" : view?.ok ? "accent" : "outline"}>
          {analysing ? "Researching" : view?.ok ? "Complete" : "Pending"}
        </Badge>
      </div>
      <ol className="flex flex-col gap-3" aria-live="polite">
        {teamStages.map(([role, label, description], index) => {
          const agent = teamByRole.get(role);
          const complete = agent?.status === "research_complete";
          const active = analysing && !complete && Boolean(researchTeam);
          return (
            <li key={role} className="flex gap-3 text-sm">
              <span
                className={cn(
                  "mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border text-[10px] font-semibold",
                  complete
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                    : active
                      ? "border-[var(--accent)] text-[var(--accent)]"
                      : "border-[var(--border)] text-[var(--muted)]",
                )}
                aria-hidden="true"
              >
                {complete ? "✓" : active ? "●" : index + 1}
              </span>
              <span className="min-w-0">
                <span
                  className={cn(
                    "block font-medium",
                    complete || active ? "text-[var(--fg)]" : "text-[var(--muted)]",
                  )}
                >
                  {label}
                  {active ? (
                    <span className="ml-2 text-xs font-normal text-[var(--accent)]">
                      In progress
                    </span>
                  ) : null}
                </span>
                <span className="mt-0.5 block text-xs leading-5 text-[var(--muted)]">
                  {description}
                </span>
              </span>
            </li>
          );
        })}
        {stages.map(([stage, label, description], index) => {
          const returned =
            stage === "identity"
              ? Boolean(ticker)
              : knownStages.has(stage) && returnedStages.has(stage);
          const active = analysing && index === activeIndex;
          return (
            <li key={stage} className="flex gap-3 text-sm">
              <span
                className={cn(
                  "mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full border text-[10px] font-semibold",
                  returned
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                    : active
                      ? "border-[var(--accent)] text-[var(--accent)]"
                      : "border-[var(--border)] text-[var(--muted)]",
                )}
                aria-hidden="true"
              >
                {returned ? "✓" : active ? "●" : index + 1}
              </span>
              <span className="min-w-0">
                <span
                  className={cn(
                    "block font-medium",
                    returned || active ? "text-[var(--fg)]" : "text-[var(--muted)]",
                  )}
                >
                  {label}
                  {active ? (
                    <span className="ml-2 text-xs font-normal text-[var(--accent)]">
                      In progress
                    </span>
                  ) : null}
                </span>
                <span className="mt-0.5 block text-xs leading-5 text-[var(--muted)]">
                  {description}
                </span>
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
