"use client";

import { memo } from "react";

import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type {
  AssumptionExplorerItem,
  AssumptionExplorerView,
} from "@/lib/analysis/types";
import { TraceLink } from "@/components/analysis/TraceLink";

/** Sprint 4 Assumption Explorer card (distinct from AI Challenge AssumptionCard). */
export const AssumptionCard = memo(function AssumptionCard({
  item,
}: {
  item: AssumptionExplorerItem;
}) {
  return (
    <Card>
      <CardHeader
        title="Core assumption"
        action={<ConfidenceBadge level={item.confidence} />}
      />
      <CardBody className="space-y-3 text-sm">
        <p className="font-medium">{item.statement}</p>
        <ValueCategoryBadge category={item.category} />
        <Field label="Sensitivity" text={item.sensitivity} />
        <Field label="Impact" text={item.impact} />
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Alternative assumptions
          </p>
          <ul className="mt-1 list-disc pl-5">
            {item.alternativeAssumptions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </div>
        <Field label="What changes if wrong" text={item.whatChangesIfWrong} />
      </CardBody>
    </Card>
  );
});

function Field({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="mt-1">{text}</p>
    </div>
  );
}

export function AssumptionExplorerSection({
  view,
}: {
  view: AssumptionExplorerView;
}) {
  return (
    <div className="space-y-4">
      <p className="rounded-md border border-[var(--border)] bg-[var(--accent-soft)]/40 px-3 py-2 text-sm">
        <span className="font-medium">What you should know — </span>
        Assumptions that matter most to the DSP View, with sensitivity, impact, and
        alternatives.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {view.items.map((item) => (
          <AssumptionCard key={item.id} item={item} />
        ))}
      </div>
      <p className="text-xs text-[var(--muted)]">
        Related: <TraceLink href="#ai_challenge">AI Challenge</TraceLink>
        {" · "}
        <TraceLink href="#research_limitations">Research Limitations</TraceLink>
      </p>
    </div>
  );
}
