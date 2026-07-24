"use client";

import { memo, useId, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { ReasoningFlowNode, ReasoningFlowView } from "@/lib/analysis/types";
import { TraceLink } from "@/components/analysis/TraceLink";

const STATUS_TONE = {
  complete: "success" as const,
  partial: "warning" as const,
  unavailable: "neutral" as const,
};

export const ReasoningNode = memo(function ReasoningNode({
  node,
}: {
  node: ReasoningFlowNode;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--surface)]">
      <button
        type="button"
        className="flex min-h-11 w-full items-center justify-between gap-3 px-3 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        <span>
          <span className="font-medium">{node.label}</span>
          <span className="mt-1 block text-sm text-[var(--muted)]">{node.summary}</span>
        </span>
        <span className="flex shrink-0 items-center gap-2">
          <Badge tone={STATUS_TONE[node.status]}>{node.status}</Badge>
          <span aria-hidden className="text-[var(--muted)]">
            {open ? "−" : "+"}
          </span>
        </span>
      </button>
      {open ? (
        <ul
          id={panelId}
          className="list-disc space-y-1 border-t border-[var(--border)] px-3 py-3 pl-8 text-sm"
        >
          {node.details.map((d) => (
            <li key={d}>{d}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
});

export const ReasoningFlow = memo(function ReasoningFlow({
  flow,
}: {
  flow: ReasoningFlowView;
}) {
  return (
    <Card>
      <CardHeader
        title="Reasoning Flow"
        description="Visual decision pipeline — every step expandable"
      />
      <CardBody>
        <ol className="space-y-0" aria-label="Reasoning pipeline">
          {flow.nodes.map((node, i) => (
            <li key={node.id}>
              <ReasoningNode node={node} />
              {i < flow.nodes.length - 1 ? (
                <div
                  className="flex justify-center py-1 text-[var(--muted)] motion-reduce:transform-none"
                  aria-hidden
                >
                  ↓
                </div>
              ) : null}
            </li>
          ))}
        </ol>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Trace: <TraceLink href="#decision_trace">Decision Trace</TraceLink>
        </p>
      </CardBody>
    </Card>
  );
});

export function ReasoningFlowSection({ flow }: { flow: ReasoningFlowView }) {
  return <ReasoningFlow flow={flow} />;
}
