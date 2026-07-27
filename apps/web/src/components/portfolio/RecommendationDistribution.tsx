"use client";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { RecommendationDistribution } from "@/lib/portfolio/analytics";

const ORDER = [
  "Strong Buy",
  "Buy",
  "Hold",
  "Sell",
  "Strong Sell",
] as const;

export function RecommendationDistribution({
  distribution,
}: {
  distribution: RecommendationDistribution;
}) {
  const total = ORDER.reduce((sum, key) => sum + distribution[key], 0);

  return (
    <Card>
      <CardHeader
        title="Recommendation Distribution"
        description="Counts from holding recommendation labels"
      />
      <CardBody className="space-y-3">
        {ORDER.map((label) => {
          const count = distribution[label];
          const percent = total > 0 ? (count / total) * 100 : 0;
          return (
            <div key={label}>
              <div className="flex justify-between text-sm">
                <span>{label}</span>
                <span className="font-mono text-[var(--muted)]">{count}</span>
              </div>
              <div
                className="mt-1.5 h-2 overflow-hidden rounded-full bg-[var(--surface-2)]"
                role="presentation"
              >
                <div
                  className="h-full rounded-full bg-[var(--accent)]"
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          );
        })}
      </CardBody>
    </Card>
  );
}
