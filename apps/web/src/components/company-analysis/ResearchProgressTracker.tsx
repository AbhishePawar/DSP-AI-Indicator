"use client";

import React from "react";
import { Badge } from "@/components/ds";
import type { ResearchView } from "@/lib/research/mapResearchView";
import { cn } from "@/lib/utils";

export const CANONICAL_RESEARCH_STAGES = [
  ["identity", "Identifying security", "Company and exchange confirmed"],
  ["evidence", "Collecting financial evidence", "Authoritative data collection"],
  ["business_quality", "Analysing business quality", "Durability, reinvestment and operating discipline"],
  ["economic_moat", "Evaluating economic moat", "Competitive position and long-term advantages"],
  ["management", "Evaluating management", "Capital allocation discipline and governance"],
  ["growth", "Analysing earnings & growth", "Revenue durability and reinvestment economics"],
  ["valuation", "Evaluating valuation", "Intrinsic value and margin of safety"],
  ["peer_intelligence", "Checking peer intelligence", "Deterministic peer discovery and metric comparison"],
  ["validation", "Validating research", "Evidence integrity and P1-09 compliance check"],
  ["report", "Preparing analysis report", "Synthesising final research dossier"],
] as const;

export function ResearchProgressTracker({
  view,
  analysing = false,
  ticker,
  currentStepIndex,
}: {
  view?: ResearchView | null;
  analysing?: boolean;
  ticker?: string;
  currentStepIndex?: number;
}) {
  const returnedStages = new Set(view?.stages.map((stage) => stage.stage) ?? []);
  const hasResult = Boolean(view && (view.ok || returnedStages.size > 0));

  return (
    <section className="rounded-xl border border-border/80 bg-card/60 p-5 shadow-xs backdrop-blur-xs">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b border-border/50 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
              DSP Methodology Engine
            </span>
            <Badge variant="outline" className="text-[10px] font-mono py-0 h-5">
              10-Stage Pipeline
            </Badge>
          </div>
          <h2 className="text-base font-semibold text-foreground mt-0.5">
            Deterministic Research Execution
          </h2>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {analysing ? (
            <span className="inline-flex items-center gap-1.5 text-primary font-medium">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
              </span>
              Pipeline running {ticker ? `for ${ticker}` : ""}
            </span>
          ) : hasResult ? (
            <span className="text-emerald-500 font-medium flex items-center gap-1">
              ✓ Research dossier ready
            </span>
          ) : (
            <span className="text-muted-foreground font-medium flex items-center gap-1">
              Awaiting company selection
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-5">
        {CANONICAL_RESEARCH_STAGES.map(([id, label, detail], index) => {
          let isFinished = false;
          let isCurrent = false;

          if (analysing) {
            if (currentStepIndex !== undefined) {
              isFinished = index < currentStepIndex;
              isCurrent = index === currentStepIndex;
            } else {
              isFinished = false;
              isCurrent = index === 0;
            }
          } else if (hasResult) {
            // Stage is finished if view confirmed it, or if full dossier is ok
            isFinished = view?.ok || returnedStages.has(id as never) || index === 0;
          }

          const statusLabel = isFinished
            ? "DONE"
            : isCurrent
            ? "ACTIVE"
            : analysing
            ? "QUEUED"
            : "PENDING";

          return (
            <div
              key={id}
              className={cn(
                "rounded-lg border p-3 text-xs transition-colors",
                isCurrent
                  ? "border-primary/50 bg-primary/5 shadow-xs ring-1 ring-primary/20"
                  : isFinished
                  ? "border-border/60 bg-muted/20"
                  : "border-border/40 bg-muted/5 opacity-60"
              )}
            >
              <div className="flex items-center justify-between font-medium text-foreground">
                <span className="truncate">
                  {index + 1}. {label}
                </span>
                <span
                  className={cn(
                    "text-[10px] font-mono shrink-0 ml-1",
                    isFinished
                      ? "text-emerald-500 font-medium"
                      : isCurrent
                      ? "text-primary font-bold animate-pulse"
                      : "text-muted-foreground"
                  )}
                >
                  {statusLabel}
                </span>
              </div>
              <p className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">
                {detail}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
