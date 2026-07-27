"use client";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { PortfolioHealthAnalytics } from "@/lib/portfolio/analytics";

export function PortfolioHealth({ health }: { health: PortfolioHealthAnalytics }) {
  return (
    <Card>
      <CardHeader
        title="Portfolio Health"
        description="Deterministic frontend rules only — no live market signals"
      />
      <CardBody className="space-y-3">
        <p className="font-[family-name:var(--font-display)] text-2xl tracking-tight">
          {health.primary}
        </p>
        <div className="flex flex-wrap gap-2">
          {health.labels.map((label) => (
            <Badge
              key={label}
              tone={
                label.includes("Incomplete") || label === "Concentrated"
                  ? "warning"
                  : label === "Empty"
                    ? "neutral"
                    : "success"
              }
            >
              {label}
            </Badge>
          ))}
        </div>
        <p className="text-sm text-[var(--muted)]">{health.details}</p>
      </CardBody>
    </Card>
  );
}
