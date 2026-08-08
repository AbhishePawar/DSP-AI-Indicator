"use client";

import { useId, useState } from "react";

import { MetricCell } from "@/components/institutional-dashboard/MetricCell";
import { Badge, Button } from "@/components/ds";
import type { ScoreCard } from "@/lib/institutional-dashboard/types";

export function ExplainableScore({ score }: { score: ScoreCard }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            {score.title}
          </p>
          <p className="mt-1 text-base font-semibold">{score.score.display}</p>
          <p className="text-xs text-[var(--muted)]">{score.label.display}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant={
              score.score.presence === "available" ? "accent" : "default"
            }
          >
            {score.score.presence === "available" ? "Scored" : "Pending"}
          </Badge>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            aria-expanded={open}
            aria-controls={panelId}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? "Hide explainability" : "Explain"}
          </Button>
        </div>
      </div>
      {open ? (
        <div
          id={panelId}
          className="mt-3 grid gap-3 border-t border-[var(--border)] pt-3 sm:grid-cols-2"
        >
          <MetricCell label="Formula" field={score.explainability.formula} />
          <MetricCell label="Inputs" field={score.explainability.inputs} />
          <MetricCell label="Weights" field={score.explainability.weights} />
          <MetricCell
            label="Calculation"
            field={score.explainability.calculation}
          />
          <MetricCell
            label="Contributing engines"
            field={score.explainability.engines}
          />
          <MetricCell
            label="Confidence"
            field={score.explainability.confidence}
          />
          <MetricCell
            label="Supporting data"
            field={score.explainability.supportingData}
          />
          <MetricCell label="Reasoning" field={score.explainability.reasoning} />
          <MetricCell
            label="Contribution"
            field={score.explainability.contribution}
          />
        </div>
      ) : null}
    </div>
  );
}
