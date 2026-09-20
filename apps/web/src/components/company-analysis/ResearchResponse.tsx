"use client";

/**
 * Structured research-answer renderer for the conversational result page.
 *
 * Reads only fields already present on the mapped `ResearchView` (itself a
 * thin presentation layer over /api/v1/analyse). It never computes scores,
 * valuations, or recommendations — sections are simply omitted when the
 * backend did not provide the underlying data.
 */

import { lazy, Suspense, useState } from "react";

import type { ResearchView } from "@/lib/research/mapResearchView";

const BuffettIndicatorSection = lazy(() =>
  import("./BuffettIndicatorSection").then((m) => ({
    default: m.BuffettIndicatorSection,
  })),
);

function has(value: unknown): boolean {
  if (value == null) return false;
  if (typeof value === "string") {
    return !["", "unavailable", "data unavailable", "—"].includes(
      value.trim().toLowerCase(),
    );
  }
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return true;
}

function display(value: string | null | undefined): string {
  return has(value) ? (value as string) : "Data unavailable";
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b border-[var(--border)] px-4 py-4 last:border-b-0">
      <h3 className="mb-2 text-sm font-semibold text-[var(--ink)]">{title}</h3>
      {children}
    </section>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1.5 pl-5 text-sm leading-6 text-[var(--muted)]">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function FieldGrid({
  fields,
}: {
  fields: Array<{ label: string; value: string | null | undefined }>;
}) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2">
      {fields.map((field) => (
        <div key={field.label} className="min-w-0">
          <dt className="text-[11px] uppercase tracking-wide text-[var(--muted)]">
            {field.label}
          </dt>
          <dd className="truncate text-sm font-medium text-[var(--ink)]">
            {display(field.value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function ResearchResponse({ view }: { view: ResearchView }) {
  const [buffettExpanded, setBuffettExpanded] = useState(false);

  const strengths = view.strengths ?? [];
  const weaknesses = view.weaknesses ?? [];
  const risks = view.risks ?? [];
  const limitations = [...(view.limitations ?? []), ...(view.warnings ?? [])];
  const evidenceCounts = Object.entries(view.evidenceCounts ?? {}).filter(
    ([, count]) => typeof count === "number" && count > 0,
  );
  const financialMetrics = [
    ...(view.financial?.metrics ?? []),
    ...(view.businessQuality?.metrics ?? []),
  ].filter((metric) => has(metric.value));
  const buffett = view.buffett;
  const hasBuffett = has(buffett?.overallRating) || has(buffett?.verdict);

  return (
    <article className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow-sm)]">
      <Section title="Executive Summary">
        <p className="text-sm leading-6 text-[var(--ink)]">
          {display(view.company)} ({display(view.ticker)}) — {display(view.recommendation)}
          {has(view.recommendationConfidence)
            ? ` · Confidence ${Math.round((view.recommendationConfidence as number) * 100)}%`
            : ""}
          {has(view.valuation?.marginOfSafety)
            ? ` · Margin of safety ${view.valuation.marginOfSafety}`
            : ""}
          .
        </p>
      </Section>

      {strengths.length || weaknesses.length ? (
        <Section title="Key Findings">
          <div className="grid gap-4 sm:grid-cols-2">
            {strengths.length ? (
              <div>
                <p className="mb-1 text-xs font-medium text-[var(--muted)]">
                  Strengths
                </p>
                <BulletList items={strengths} />
              </div>
            ) : null}
            {weaknesses.length ? (
              <div>
                <p className="mb-1 text-xs font-medium text-[var(--muted)]">
                  Weaknesses
                </p>
                <BulletList items={weaknesses} />
              </div>
            ) : null}
          </div>
        </Section>
      ) : null}

      {financialMetrics.length ? (
        <Section title="Financial &amp; Business Analysis">
          <FieldGrid fields={financialMetrics} />
        </Section>
      ) : null}

      <Section title="Valuation">
        <FieldGrid
          fields={[
            { label: "Current Price", value: view.valuation?.currentPrice },
            { label: "Intrinsic Value", value: view.valuation?.intrinsicValue },
            { label: "Margin of Safety", value: view.valuation?.marginOfSafety },
            { label: "Method", value: view.valuation?.method },
            { label: "Confidence", value: view.valuation?.confidence },
          ]}
        />
      </Section>

      {hasBuffett ? (
        <Section title="DSP Buffett-style Indicator">
          <FieldGrid
            fields={[
              { label: "Overall Rating", value: buffett?.overallRating },
              { label: "Buffett Action", value: buffett?.recommendation?.action },
            ]}
          />
          {has(buffett?.verdict) ? (
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              {buffett?.verdict}
            </p>
          ) : null}
          <button
            type="button"
            onClick={() => setBuffettExpanded((prev) => !prev)}
            className="mt-3 text-xs font-medium text-[var(--accent-strong)] hover:underline"
          >
            {buffettExpanded ? "Hide full Buffett analysis" : "View full Buffett analysis"}
          </button>
          {buffettExpanded ? (
            <div className="mt-3">
              <Suspense
                fallback={
                  <p className="text-xs text-[var(--muted)]">Loading full analysis…</p>
                }
              >
                <BuffettIndicatorSection report={buffett} />
              </Suspense>
            </div>
          ) : null}
        </Section>
      ) : null}

      {risks.length ? (
        <Section title="Risks">
          <BulletList items={risks} />
        </Section>
      ) : null}

      {evidenceCounts.length || view.analysisId ? (
        <Section title="Evidence &amp; Sources">
          <FieldGrid
            fields={[
              ...evidenceCounts.map(([label, count]) => ({
                label: label.replace(/_/g, " "),
                value: String(count),
              })),
              { label: "Analysis ID", value: view.analysisId },
            ]}
          />
        </Section>
      ) : null}

      {limitations.length ? (
        <Section title="Methodology &amp; Caveats">
          <BulletList items={limitations} />
        </Section>
      ) : null}
    </article>
  );
}

export default ResearchResponse;
