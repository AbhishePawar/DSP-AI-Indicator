"use client";

import { memo } from "react";

import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { ConfidenceBreakdownView } from "@/lib/analysis/types";
import { CONFIDENCE_LABELS } from "@/lib/trust/labels";
import { TraceLink } from "@/components/analysis/TraceLink";

export const ConfidenceBreakdown = memo(function ConfidenceBreakdown({
  breakdown,
}: {
  breakdown: ConfidenceBreakdownView;
}) {
  return (
    <Card>
      <CardHeader
        title="Confidence Breakdown"
        description="Why confidence differs across domains — Insufficient Evidence when metrics are missing"
        action={<ConfidenceBadge level={breakdown.overall} />}
      />
      <CardBody>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[28rem] text-left text-sm">
            <caption className="sr-only">
              Confidence by domain with explanation
            </caption>
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                <th scope="col" className="px-2 py-2 font-medium">
                  Domain
                </th>
                <th scope="col" className="px-2 py-2 font-medium">
                  Level
                </th>
                <th scope="col" className="px-2 py-2 font-medium">
                  Why it differs
                </th>
              </tr>
            </thead>
            <tbody>
              {breakdown.rows.map((row) => (
                <tr key={row.id} className="border-b border-[var(--border)] last:border-0 align-top">
                  <td className="px-2 py-2">{row.label}</td>
                  <td className="px-2 py-2">
                    <ConfidenceBadge level={row.level} />
                    <span className="sr-only">{CONFIDENCE_LABELS[row.level]}</span>
                  </td>
                  <td className="px-2 py-2 text-[var(--muted)]">{row.whyDifferent}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Also see <TraceLink href="#confidence_matrix">Confidence Matrix</TraceLink>
          {" · "}
          <TraceLink href="#decision_trace">Decision Trace</TraceLink>
        </p>
      </CardBody>
    </Card>
  );
});
