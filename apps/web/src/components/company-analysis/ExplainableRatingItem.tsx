"use client";

/**
 * P2.2 — Expandable explainability card for one institutional rating.
 * Collapsed: score / grade / confidence / one-line summary.
 * Expanded: evidence, strengths, weaknesses, explanation, traceability.
 */

import {
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
  Badge,
} from "@/components/ds";
import type { ModuleExplainability } from "@/lib/explainability";

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-[var(--border)] py-2 text-sm last:border-0">
      <dt className="text-[var(--muted)]">{label}</dt>
      <dd className="text-right font-medium text-[var(--fg)]">
        {value.trim() && value !== "Unavailable"
          ? value
          : "Data unavailable."}
      </dd>
    </div>
  );
}

export function ExplainableRatingItem({
  item,
}: {
  item: ModuleExplainability;
}) {
  return (
    <AccordionItem
      value={item.moduleId}
      className="rounded-[var(--radius-md)] border border-[var(--border)] px-3"
    >
      <AccordionTrigger className="hover:no-underline">
        <div className="flex w-full flex-col gap-1 pr-2 text-left sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="font-[family-name:var(--font-display)] text-sm tracking-tight text-[var(--fg)]">
              {item.title}
            </p>
            <p className="truncate text-xs text-[var(--muted)]">
              {item.oneLineSummary}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Badge variant="outline" aria-label={`Score ${item.scoreOutOf10}`}>
              {item.scoreOutOf10}
            </Badge>
            <Badge variant="accent" aria-label={`Grade ${item.grade}`}>
              {item.grade}
            </Badge>
            <span
              className="text-[var(--muted)]"
              aria-label={`Confidence ${item.confidence}`}
            >
              {item.confidence}
            </span>
          </div>
        </div>
      </AccordionTrigger>
      <AccordionContent>
        <div className="space-y-4 pb-3">
          <section aria-label={`${item.title} evidence`}>
            <h5 className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              Evidence
            </h5>
            <dl>
              {item.evidence.map((e) => (
                <MetricRow
                  key={`${e.label}-${e.sourceField}-${e.value}`}
                  label={e.label}
                  value={e.value}
                />
              ))}
            </dl>
          </section>

          <div className="grid gap-4 sm:grid-cols-2">
            <section aria-label={`${item.title} strengths`}>
              <h5 className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
                Strengths
              </h5>
              <ul className="list-disc space-y-1 pl-4 text-sm text-[var(--fg)]">
                {item.strengths.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </section>
            <section aria-label={`${item.title} weaknesses`}>
              <h5 className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
                Weaknesses
              </h5>
              <ul className="list-disc space-y-1 pl-4 text-sm text-[var(--fg)]">
                {item.weaknesses.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </section>
          </div>

          <section aria-label={`${item.title} explanation`}>
            <h5 className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              Explanation
            </h5>
            <p className="text-sm leading-relaxed text-[var(--fg)]">
              {item.explanation}
            </p>
          </section>

          <section aria-label={`${item.title} traceability`}>
            <h5 className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              Traceability
            </h5>
            <ul className="space-y-1 text-xs text-[var(--muted)]">
              {item.traceability.map((t) => (
                <li key={`${t.label}-${t.sourceField}-${t.value}`}>
                  <span className="text-[var(--fg)]">{t.label}</span>
                  {": "}
                  {t.value}
                  {" · source: "}
                  {t.sourceField}
                </li>
              ))}
            </ul>
          </section>
        </div>
      </AccordionContent>
    </AccordionItem>
  );
}
