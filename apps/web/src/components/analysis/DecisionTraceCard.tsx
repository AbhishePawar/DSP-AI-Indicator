"use client";

import { memo, useId, useState } from "react";

import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { DecisionTraceStep, DecisionTraceView } from "@/lib/analysis/types";
import { TraceLink } from "@/components/analysis/TraceLink";

function TraceStep({ step }: { step: DecisionTraceStep }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--surface)]">
      <button
        type="button"
        className="flex min-h-11 w-full items-start justify-between gap-3 px-3 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        <span>
          <span className="font-medium">{step.title}</span>
          <span className="mt-1 block text-sm text-[var(--muted)]">{step.summary}</span>
        </span>
        <span aria-hidden className="shrink-0 text-[var(--muted)]">
          {open ? "−" : "+"}
        </span>
      </button>
      {open ? (
        <div
          id={panelId}
          className="space-y-3 border-t border-[var(--border)] px-3 py-3 text-sm motion-safe:animate-none"
        >
          <div className="flex flex-wrap gap-2">
            <ValueCategoryBadge category={step.category} />
            <SourceBadge source={step.source} />
          </div>
          <ul className="list-disc space-y-1 pl-5">
            {step.details.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export const DecisionTraceCard = memo(function DecisionTraceCard({
  trace,
}: {
  trace: DecisionTraceView;
}) {
  const steps = [
    trace.inputs,
    trace.calculations,
    trace.businessRules,
    trace.evidenceUsed,
    trace.confidence,
    trace.limitations,
    trace.reasoningChain,
    trace.output,
  ];

  return (
    <Card>
      <CardHeader
        title={`Decision Trace — ${trace.conclusionLabel}`}
        description="Every major conclusion step is expandable. Why DSP said this is documented here."
      />
      <CardBody className="space-y-3">
        {!trace.available ? (
          <p className="text-sm text-[var(--muted)]">
            Trace scaffold is ready — conclusion output is Unavailable until Analyze returns a DSP
            View.
          </p>
        ) : null}
        <ol className="space-y-2" aria-label="Decision trace steps">
          {steps.map((s, i) => (
            <li key={s.id}>
              <p className="mb-1 text-xs text-[var(--muted)]">
                Step {i + 1}
              </p>
              <TraceStep step={s} />
            </li>
          ))}
        </ol>
        <p className="text-xs text-[var(--muted)]">
          Related: <TraceLink href="#evidence_explorer">Evidence Explorer</TraceLink>
          {" · "}
          <TraceLink href="#reasoning_flow">Reasoning Flow</TraceLink>
          {" · "}
          <TraceLink href="#confidence_breakdown">Confidence Breakdown</TraceLink>
          {" · "}
          <TraceLink href="#research_limitations">Limitations</TraceLink>
        </p>
      </CardBody>
    </Card>
  );
});

export function DecisionTraceSection({ trace }: { trace: DecisionTraceView }) {
  return (
    <div className="space-y-4">
      <p className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm">
        <span className="font-medium">What you should know — </span>
        Decision Trace turns the research conclusion into Inputs → Calculations → Rules → Evidence →
        Confidence → Limitations → Reasoning → Output.
      </p>
      <DecisionTraceCard trace={trace} />
    </div>
  );
}
