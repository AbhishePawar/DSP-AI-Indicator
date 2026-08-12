"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
  Badge,
} from "@/components/ds";
import type { BuffettReportView, BuffettMatrixState } from "@/lib/buffett-indicator";
import {
  FieldRow,
  SectionCard,
} from "@/components/company-analysis/WorkspacePrimitives";

function matrixLabel(state: BuffettMatrixState): string {
  if (state === "met") return "Met";
  if (state === "not_met") return "Not met";
  return "Unavailable";
}

function SubsectionBlock({
  title,
  bullets,
  verdict,
  evidenceSources,
}: {
  title: string;
  bullets: string[];
  verdict: string;
  evidenceSources: string[];
}) {
  return (
    <div className="space-y-2 border-b border-[var(--border)] pb-4 last:border-0">
      <h4 className="font-[family-name:var(--font-display)] text-sm tracking-tight text-[var(--fg)]">
        {title}
      </h4>
      <ul className="list-disc space-y-1 pl-4 text-sm text-[var(--fg)]">
        {bullets.map((b) => (
          <li key={b}>{b}</li>
        ))}
      </ul>
      <p className="text-sm">
        <span className="text-[var(--muted)]">Verdict: </span>
        {verdict}
      </p>
      <p className="text-xs text-[var(--muted)]">
        Evidence sources: {evidenceSources.join(", ")}
      </p>
    </div>
  );
}

export function BuffettIndicatorSection({
  report,
}: {
  report: BuffettReportView;
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Buffett Indicator Analysis"
        description="Presentation synthesis of existing /api/v1/analyse outputs — no recalculation"
        action={
          <Badge variant="outline">Overall {report.overallRating}</Badge>
        }
      >
        <p className="mb-3 text-xs text-[var(--muted)]">{report.disclaimer}</p>
        <dl className="mb-4">
          <FieldRow label="Overall Buffett Rating" value={report.overallRating} />
          <FieldRow label="Buffett Action" value={report.recommendation.action} />
          <FieldRow label="Confidence (existing)" value={report.confidence} />
        </dl>

        <Accordion type="multiple" defaultValue={["scorecard", "verdict", "action"]}>
          <AccordionItem value="pillars">
            <AccordionTrigger>1–8 · Pillars & valuation</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4">
                <SubsectionBlock {...report.circleOfCompetence} />
                <SubsectionBlock {...report.economicMoat} />
                <SubsectionBlock {...report.managementQuality} />
                <SubsectionBlock {...report.financialFortress} />
                <SubsectionBlock {...report.earningsPredictability} />
                <SubsectionBlock {...report.capitalAllocation} />
                <div className="space-y-2 border-b border-[var(--border)] pb-4">
                  <h4 className="font-[family-name:var(--font-display)] text-sm tracking-tight">
                    Intrinsic Value & Margin of Safety
                  </h4>
                  <dl>
                    <FieldRow
                      label="Current Price"
                      value={report.intrinsicValue.currentPrice}
                    />
                    <FieldRow
                      label="Intrinsic Value"
                      value={report.intrinsicValue.intrinsicValue}
                    />
                    <FieldRow
                      label="Margin of Safety"
                      value={report.intrinsicValue.marginOfSafety}
                    />
                  </dl>
                  <p className="text-sm">
                    <span className="text-[var(--muted)]">Verdict: </span>
                    {report.intrinsicValue.verdict}
                  </p>
                </div>
                <SubsectionBlock {...report.longTermRisks} />
              </div>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="matrix">
            <AccordionTrigger>9 · Buffett Decision Matrix</AccordionTrigger>
            <AccordionContent>
              <ul className="space-y-2 text-sm">
                {report.decisionMatrix.map((item) => (
                  <li
                    key={item.criterion}
                    className="flex flex-col gap-0.5 rounded-[var(--radius-md)] border border-[var(--border)] px-3 py-2"
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span>{item.criterion}</span>
                      <Badge
                        variant={
                          item.state === "met"
                            ? "accent"
                            : item.state === "not_met"
                              ? "danger"
                              : "outline"
                        }
                      >
                        {item.state === "met" ? "✓" : "·"} {matrixLabel(item.state)}
                      </Badge>
                    </span>
                    <span className="text-xs text-[var(--muted)]">{item.evidence}</span>
                  </li>
                ))}
              </ul>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="scorecard">
            <AccordionTrigger>10 · Buffett Scorecard</AccordionTrigger>
            <AccordionContent>
              <dl>
                {report.scorecard.map((row) => (
                  <FieldRow
                    key={row.dimension}
                    label={row.dimension}
                    value={row.grade}
                  />
                ))}
              </dl>
              <ul className="mt-3 space-y-1 text-xs text-[var(--muted)]">
                {report.scorecard.map((row) => (
                  <li key={`${row.dimension}-ev`}>
                    {row.dimension}: {row.evidence}
                  </li>
                ))}
              </ul>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="verdict">
            <AccordionTrigger>11 · Buffett Verdict</AccordionTrigger>
            <AccordionContent>
              <p className="text-sm leading-relaxed">{report.verdict}</p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <h4 className="mb-1 text-xs font-medium text-[var(--muted)]">
                    Key Strengths
                  </h4>
                  <ul className="list-disc space-y-1 pl-4 text-sm">
                    {report.keyStrengths.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="mb-1 text-xs font-medium text-[var(--muted)]">
                    Key Weaknesses
                  </h4>
                  <ul className="list-disc space-y-1 pl-4 text-sm">
                    {report.keyWeaknesses.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="action">
            <AccordionTrigger>12 · Buffett Recommendation</AccordionTrigger>
            <AccordionContent>
              <dl>
                <FieldRow
                  label="Business Quality"
                  value={report.recommendation.businessQuality}
                />
                <FieldRow
                  label="Investment Quality"
                  value={report.recommendation.investmentQuality}
                />
                <FieldRow
                  label="Current Valuation"
                  value={report.recommendation.currentValuation}
                />
                <FieldRow
                  label="Margin of Safety"
                  value={report.recommendation.marginOfSafety}
                />
                <FieldRow label="Buffett Action" value={report.recommendation.action} />
              </dl>
              <p className="mt-2 text-xs text-[var(--muted)]">
                {report.recommendation.actionEvidence}
              </p>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </SectionCard>
    </div>
  );
}
