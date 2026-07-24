import type { ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

/** Canonical metric card — Title / Rating / Value / Explanation / Why / Takeaway. */

export type MetricCardProps = {
  title: string;
  rating: string;
  actualValue: string;
  plainEnglishExplanation: string;
  whyItMatters: string;
  investorTakeaway: string;
  ratingTone?: "neutral" | "success" | "warning" | "danger" | "accent";
  footer?: ReactNode;
};

export function MetricCard({
  title,
  rating,
  actualValue,
  plainEnglishExplanation,
  whyItMatters,
  investorTakeaway,
  ratingTone = "neutral",
  footer,
}: MetricCardProps) {
  return (
    <Card>
      <CardHeader
        title={title}
        action={<Badge tone={ratingTone}>{rating}</Badge>}
      />
      <CardBody className="space-y-3 text-sm">
        <p>
          <span className="text-[var(--muted)]">Actual value</span>
          <br />
          <span className="font-medium">{actualValue}</span>
        </p>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            What this means
          </p>
          <p className="mt-1">{plainEnglishExplanation}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Why it matters
          </p>
          <p className="mt-1">{whyItMatters}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Investor takeaway
          </p>
          <p className="mt-1">{investorTakeaway}</p>
        </div>
        {footer}
      </CardBody>
    </Card>
  );
}
