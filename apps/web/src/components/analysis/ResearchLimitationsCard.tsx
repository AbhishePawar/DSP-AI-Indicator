"use client";

import { memo } from "react";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { ResearchLimitationsView } from "@/lib/analysis/types";
import { TraceLink } from "@/components/analysis/TraceLink";

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h3 className="text-sm font-medium">{title}</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export const ResearchLimitationsCard = memo(function ResearchLimitationsCard({
  limitations,
}: {
  limitations: ResearchLimitationsView;
}) {
  return (
    <Card>
      <CardHeader
        title="Research Limitations"
        description="Professional honesty — what DSP cannot yet claim"
      />
      <CardBody className="grid gap-4 sm:grid-cols-2">
        <ListBlock title="Unavailable data" items={limitations.unavailableData} />
        <ListBlock title="Unknown factors" items={limitations.unknownFactors} />
        <ListBlock title="Assumptions" items={limitations.assumptions} />
        <ListBlock title="External dependencies" items={limitations.externalDependencies} />
        <div className="sm:col-span-2">
          <ListBlock title="Pending improvements" items={limitations.pendingImprovements} />
        </div>
        <p className="text-xs text-[var(--muted)] sm:col-span-2">
          Trace: <TraceLink href="#transparency_panel">Transparency Panel</TraceLink>
          {" · "}
          <TraceLink href="#assumption_explorer">Assumption Explorer</TraceLink>
        </p>
      </CardBody>
    </Card>
  );
});
