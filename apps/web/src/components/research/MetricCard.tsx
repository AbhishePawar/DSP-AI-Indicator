import type { ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";

/**
 * Canonical metric card — Title / Rating / Value / Explanation / Why / Takeaway.
 *
 * Refined to use the ResearchSection institutional pattern:
 * Fraunces heading + bottom-border rule, no floating card container.
 */

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
    <section className="space-y-3">
      {/* Heading row — document style matching ResearchSection */}
      <div className="flex items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
        <h3 className="font-[family-name:var(--font-display)] text-base tracking-tight text-[var(--fg)] leading-snug">
          {title}
        </h3>
        <Badge tone={ratingTone} className="shrink-0 mt-0.5">
          {rating}
        </Badge>
      </div>

      {/* Actual value — prominent */}
      <div className="border-b border-[var(--border)] pb-3">
        <p className="text-xs uppercase tracking-wider text-[var(--muted)] mb-0.5">
          Actual value
        </p>
        <p className="text-lg font-medium text-[var(--fg)] tabular-nums">
          {actualValue}
        </p>
      </div>

      {/* Explanatory content — compact */}
      <div className="space-y-2.5 text-sm">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)] mb-0.5">
            What this means
          </p>
          <p className="text-[var(--fg)] leading-relaxed">{plainEnglishExplanation}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)] mb-0.5">
            Why it matters
          </p>
          <p className="text-[var(--fg)] leading-relaxed">{whyItMatters}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)] mb-0.5">
            Investor takeaway
          </p>
          <p className="text-[var(--fg)] leading-relaxed">{investorTakeaway}</p>
        </div>
      </div>

      {footer ? <div className="pt-1">{footer}</div> : null}
    </section>
  );
}
