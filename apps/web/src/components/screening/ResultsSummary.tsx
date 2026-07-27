"use client";

import { Card, CardBody } from "@/components/ui/Card";

export function ResultsSummary({
  matched,
  filtersApplied,
  availableResearch,
}: {
  matched: number;
  filtersApplied: number;
  availableResearch: number;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <SummaryCard label="Companies Matched" value={matched} />
      <SummaryCard label="Filters Applied" value={filtersApplied} />
      <SummaryCard label="Available Research" value={availableResearch} />
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardBody>
        <p className="text-xs text-[var(--muted)]">{label}</p>
        <p className="mt-1 font-[family-name:var(--font-display)] text-2xl tracking-tight">
          {value}
        </p>
      </CardBody>
    </Card>
  );
}
