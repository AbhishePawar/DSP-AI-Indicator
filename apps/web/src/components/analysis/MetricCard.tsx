"use client";

import { useState } from "react";

import { useCopilotOptional } from "@/components/analysis/copilot/CopilotContext";
import { TraceLink } from "@/components/analysis/TraceLink";
import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { MetricView } from "@/lib/analysis/types";

export function MetricCard({ metric }: { metric: MetricView }) {
  const [openLearn, setOpenLearn] = useState(false);
  const [showPrompts, setShowPrompts] = useState(false);
  const [showExplain, setShowExplain] = useState(false);
  const copilot = useCopilotOptional();
  const ratingTone = metric.available
    ? ("accent" as const)
    : ("neutral" as const);

  return (
    <Card>
      <CardHeader
        title={metric.title}
        action={<Badge tone={ratingTone}>{metric.rating}</Badge>}
      />
      <CardBody className="space-y-3 text-sm">
        <div className="flex flex-wrap gap-2">
          <ValueCategoryBadge category={metric.category} />
          <SourceBadge source={metric.source} />
        </div>
        <p>
          <span className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Actual value
          </span>
          <br />
          <span className="font-medium">{metric.actualValue}</span>
        </p>
        <Field label="What this means" text={metric.meaning} />
        <Field label="Why it matters" text={metric.whyItMatters} />
        <Field label="Investor takeaway" text={metric.investorTakeaway} />
        <div className="flex flex-wrap gap-2 pt-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowExplain((v) => !v)}
            aria-expanded={showExplain}
          >
            Explain
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setOpenLearn((v) => !v)}
            aria-expanded={openLearn}
          >
            Learn more
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              if (copilot) {
                copilot.ask({
                  action: "explain_metric",
                  text: `Explain this metric: ${metric.title}`,
                  metricId: metric.id,
                  metricTitle: metric.title,
                });
              } else {
                setShowPrompts((v) => !v);
              }
            }}
            aria-expanded={copilot ? undefined : showPrompts}
          >
            Ask AI
          </Button>
        </div>
        {showExplain ? (
          <div className="space-y-2 rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs">
            <p>
              <span className="font-medium">Where it came from — </span>
              {metric.available
                ? "Mapped from analyze envelope / calculated presentation fields."
                : "Unavailable in the current envelope — not invented client-side."}
            </p>
            <p>
              <span className="font-medium">How calculated — </span>
              Browser performs no investment math. Values appear only when the
              backend/envelope supplies them; otherwise educational template.
            </p>
            <p>
              <span className="font-medium">Confidence — </span>
              {metric.available
                ? "Tied to source category badges above."
                : "Insufficient Evidence"}
            </p>
            <p>
              <span className="font-medium">Evidence — </span>
              <TraceLink href="#evidence_explorer">Evidence Explorer</TraceLink>
              {" · "}
              <TraceLink href="#decision_trace">Decision Trace</TraceLink>
              {" · "}
              <TraceLink href="#methodology_panel">Methodology</TraceLink>
            </p>
          </div>
        ) : null}
        {openLearn ? (
          <p className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs text-[var(--muted)]">
            Terminology key: <code>{metric.learnMore}</code>. Full definitions
            ship with the terminology drawer in a later sprint.
          </p>
        ) : null}
        {showPrompts && !copilot ? (
          <ul className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-xs text-[var(--muted)]">
            <li className="mb-1 font-medium text-[var(--fg)]">Copilot prompts</li>
            {metric.aiPrompts.map((p) => (
              <li key={p}>• {p}</li>
            ))}
          </ul>
        ) : null}
      </CardBody>
    </Card>
  );
}

function Field({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </p>
      <p className="mt-1">{text}</p>
    </div>
  );
}
