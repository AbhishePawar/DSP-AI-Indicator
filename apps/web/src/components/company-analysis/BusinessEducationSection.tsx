"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
  Badge,
} from "@/components/ds";
import type { BusinessEducationReportView } from "@/lib/business-education";
import {
  FieldRow,
  SectionCard,
} from "@/components/company-analysis/WorkspacePrimitives";

export function BusinessEducationSection({
  report,
}: {
  report: BusinessEducationReportView;
}) {
  return (
    <div className="space-y-4">
      <SectionCard
        title="Business & Buffett Analysis"
        description="Educational business understanding — separate from quantitative valuation"
        action={<Badge variant="outline">Educational</Badge>}
      >
        <p className="mb-3 text-xs text-[var(--muted)]">{report.disclaimer}</p>
        <dl className="mb-4">
          <FieldRow label="Company" value={report.company} />
          <FieldRow label="Symbol" value={report.symbol} />
          <FieldRow label="Business type lens" value={report.businessType} />
          <FieldRow
            label="Preferred metrics"
            value={report.preferredMetrics.join(", ")}
          />
        </dl>
        <p className="mb-4 text-xs text-[var(--muted)]">
          This layer cannot modify intrinsic value, margin of safety, Buffett
          score, or recommendations. Use Quantitative Research sections for
          those outputs.
        </p>

        <Accordion
          type="multiple"
          defaultValue={report.sections.slice(0, 3).map((s) => s.id)}
        >
          {report.sections.map((sec) => (
            <AccordionItem key={sec.id} value={sec.id}>
              <AccordionTrigger>{sec.title}</AccordionTrigger>
              <AccordionContent>
                <div className="space-y-3">
                  <p className="text-sm text-[var(--fg)]">{sec.summary}</p>
                  {sec.bullets.length > 0 ? (
                    <ul className="list-disc space-y-1 pl-4 text-sm text-[var(--fg)]">
                      {sec.bullets.map((b) => (
                        <li key={b}>{b}</li>
                      ))}
                    </ul>
                  ) : null}
                  {sec.checklist ? (
                    <div className="space-y-3">
                      {sec.checklist.map((item) => (
                        <div
                          key={item.id}
                          className="border-b border-[var(--border)] pb-3 last:border-0"
                        >
                          <h4 className="text-sm font-medium text-[var(--fg)]">
                            {item.id}. {item.title}
                          </h4>
                          <p className="mt-1 text-xs text-[var(--muted)]">
                            Evidence: {item.evidence}
                          </p>
                          <p className="text-sm">{item.strengthOrWeakness}</p>
                          <p className="text-xs text-[var(--muted)]">
                            Uncertainty: {item.uncertainty}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {sec.risks ? (
                    <div className="space-y-3">
                      {sec.risks.map((r) => (
                        <div
                          key={r.risk}
                          className="border-b border-[var(--border)] pb-3 last:border-0"
                        >
                          <h4 className="text-sm font-medium text-[var(--fg)]">
                            {r.risk}
                          </h4>
                          <p className="text-sm">Why it matters: {r.whyItMatters}</p>
                          <p className="text-sm">
                            Potential trigger: {r.potentialTrigger}
                          </p>
                          <p className="text-xs text-[var(--muted)]">
                            Metric to monitor: {r.metricToMonitor}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  <div className="space-y-1">
                    {sec.claims.map((c, idx) => (
                      <p key={`${sec.id}-${idx}`} className="text-xs text-[var(--muted)]">
                        [{c.kind}] {c.text}
                        {c.source ? ` · ${c.source}` : ""}
                      </p>
                    ))}
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </SectionCard>
    </div>
  );
}
