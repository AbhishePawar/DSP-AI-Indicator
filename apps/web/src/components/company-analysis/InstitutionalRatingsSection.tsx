"use client";

import { Accordion, Badge } from "@/components/ds";
import type { InstitutionalRatingFramework } from "@/lib/institutional-rating";
import type { InstitutionalExplainabilityFramework } from "@/lib/explainability";
import type { ReportTransparencyView } from "@/lib/report-transparency";
import {
  FieldRow,
  SectionCard,
} from "@/components/company-analysis/WorkspacePrimitives";
import { ReportInformationCard } from "./ReportInformationCard";
import { ExplainableRatingItem } from "./ExplainableRatingItem";

function Stars({ count }: { count: number }) {
  if (count <= 0) {
    return <span className="text-sm text-[var(--muted)]">Unavailable</span>;
  }
  return (
    <span aria-label={`${count} of 5 stars`} className="tracking-wider text-[var(--accent)]">
      {"★".repeat(count)}
      <span className="text-[var(--muted)]">{"★".repeat(Math.max(0, 5 - count))}</span>
    </span>
  );
}

export function InstitutionalRatingsSection({
  ratings,
  transparency,
  explainability,
}: {
  ratings: InstitutionalRatingFramework;
  transparency?: ReportTransparencyView;
  explainability?: InstitutionalExplainabilityFramework;
}) {
  const explain =
    explainability ??
    ({
      kind: "institutional_explainability_framework",
      version: "1.0.0",
      disclaimer: "",
      modules: [],
    } as InstitutionalExplainabilityFramework);

  return (
    <div className="space-y-4">
      {transparency ? (
        <ReportInformationCard transparency={transparency} />
      ) : null}
      <SectionCard
        title="Institutional Dashboard"
        description="One-page rating summary — remapped from existing /analyse outputs"
        action={<Badge variant="accent">{ratings.overall.recommendation}</Badge>}
      >
        <p className="mb-3 text-xs text-[var(--muted)]">{ratings.disclaimer}</p>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs text-[var(--muted)]">Overall Investment Rating</p>
            <p className="font-[family-name:var(--font-display)] text-2xl tracking-tight">
              {ratings.overall.grade}
            </p>
            <Stars count={ratings.overall.stars} />
          </div>
          <dl className="min-w-[12rem]">
            <FieldRow label="Score" value={ratings.overall.scoreOutOf10} />
            <FieldRow label="Confidence" value={ratings.overall.confidence} />
            <FieldRow label="Recommendation" value={ratings.overall.recommendation} />
          </dl>
        </div>
        <dl>
          <FieldRow label="Investment Quality" value={ratings.overall.investmentQuality} />
          <FieldRow label="Business Quality" value={ratings.overall.businessQuality} />
          <FieldRow label="Valuation Quality" value={ratings.overall.valuationQuality} />
          <FieldRow label="Risk Level" value={ratings.overall.riskLevel} />
          <FieldRow
            label="Expected Long-Term Quality"
            value={ratings.overall.expectedLongTermQuality}
          />
        </dl>
        <p className="mt-3 text-sm">{ratings.overall.explanation}</p>
        <p className="mt-1 text-xs text-[var(--muted)]">
          {ratings.overall.recommendationReasoning}
        </p>
      </SectionCard>

      <SectionCard title="Investment Scorecard">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[28rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="py-2 pr-3 font-medium">Module</th>
                <th className="py-2 pr-3 font-medium">Score</th>
                <th className="py-2 pr-3 font-medium">Grade</th>
                <th className="py-2 font-medium">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {ratings.scorecard.map((row) => (
                <tr
                  key={row.module}
                  className="border-b border-[var(--border)] last:border-0"
                >
                  <td className="py-2 pr-3">{row.module}</td>
                  <td className="py-2 pr-3 font-medium">{row.scoreOutOf10}</td>
                  <td className="py-2 pr-3">{row.grade}</td>
                  <td className="py-2">{row.confidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <SectionCard
        title="Module Ratings · Explainability"
        description="Expand any rating for evidence, strengths, weaknesses, explanation, and traceability"
      >
        {explain.disclaimer ? (
          <p className="mb-3 text-xs text-[var(--muted)]">{explain.disclaimer}</p>
        ) : null}
        <Accordion type="multiple" className="space-y-2" defaultValue={[]}>
          {explain.modules.map((item) => (
            <ExplainableRatingItem key={item.moduleId} item={item} />
          ))}
        </Accordion>
        {explain.modules.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">Unavailable</p>
        ) : null}
      </SectionCard>
    </div>
  );
}
