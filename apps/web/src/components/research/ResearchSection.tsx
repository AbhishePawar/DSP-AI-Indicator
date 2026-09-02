"use client";

import type { ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import type { StageSectionView } from "@/lib/research/mapResearchView";

/**
 * MetricGrid — document-style metric presentation.
 * Avoids turning every metric into a floating card.
 * Uses a table-like row layout for easy scanning.
 */
export function MetricGrid({
  metrics,
}: {
  metrics: { label: string; value: string }[];
}) {
  if (!metrics.length) return null;

  return (
    <div className="divide-y divide-[var(--border)]">
      {metrics.map((m) => (
        <div
          key={m.label}
          className="flex items-baseline justify-between gap-4 py-2.5 first:pt-0 last:pb-0"
        >
          <p className="shrink-0 text-sm text-[var(--muted)]">{m.label}</p>
          <p className="min-w-0 text-right text-sm font-medium text-[var(--fg)] tabular-nums break-words">
            {m.value}
          </p>
        </div>
      ))}
    </div>
  );
}

/**
 * ResearchSection — document-like section wrapper.
 * Uses a horizontal rule + heading rather than a card header,
 * to evoke an institutional research report rather than a dashboard.
 */
export function ResearchSection({
  id,
  title,
  description,
  section,
  children,
}: {
  id: string;
  title: string;
  description?: string;
  section?: StageSectionView;
  children?: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24">
      {/* Section heading — document style */}
      <div className="mb-5 flex items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-lg sm:text-xl tracking-tight text-[var(--fg)]">
            {title}
          </h2>
          {description ? (
            <p className="mt-0.5 text-sm text-[var(--muted)]">{description}</p>
          ) : null}
        </div>
        {section ? (
          <Badge
            tone={
              section.status === "succeeded" ? "success"
                : section.status === "failed" ? "danger" : "neutral"
            }
            className="shrink-0 mt-0.5"
          >
            {section.status}
          </Badge>
        ) : null}
      </div>

      {/* Section content */}
      <div className="space-y-6">
        {section ? <MetricGrid metrics={section.metrics} /> : null}
        {children}
        {section?.error ? (
          <p className="text-sm text-[var(--danger-fg)] border-l-2 border-[var(--danger-border)] pl-3">
            {section.error}
          </p>
        ) : null}
        {section?.warnings?.length ? (
          <ul className="space-y-1 border-l-2 border-[var(--warning-border)] pl-3">
            {section.warnings.map((w) => (
              <li key={w} className="text-sm text-[var(--warning-fg)]">
                {w}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}
