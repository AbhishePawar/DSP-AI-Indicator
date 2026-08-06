"use client";

import { Badge } from "@/components/ds";
import type { ReportTransparencyView } from "@/lib/report-transparency";
import {
  FieldRow,
  SectionCard,
} from "@/components/company-analysis/WorkspacePrimitives";

export function ReportInformationCard({
  transparency,
}: {
  transparency: ReportTransparencyView;
}) {
  const v = transparency.analysisVersions;
  return (
    <SectionCard
      title="Report Information"
      description="Transparency metadata from existing analysis outputs — no recalculation"
    >
      <p className="mb-3 text-xs text-[var(--muted)]">{transparency.disclaimer}</p>

      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <h4 className="mb-2 font-[family-name:var(--font-display)] text-sm tracking-tight">
            Analysis
          </h4>
          <dl>
            <FieldRow label="Analysis Date" value={transparency.analysisDate} />
            <FieldRow label="Report ID" value={transparency.reportId} />
            <FieldRow label="Frontend version" value={v.frontend} />
            <FieldRow label="Backend version" value={v.backend} />
            <FieldRow label="Buffett Framework" value={v.buffettFramework} />
            <FieldRow
              label="Institutional Rating Framework"
              value={v.institutionalRatingFramework}
            />
            <FieldRow label="Overall confidence" value={transparency.confidence} />
          </dl>
        </div>

        <div>
          <h4 className="mb-2 font-[family-name:var(--font-display)] text-sm tracking-tight">
            Company
          </h4>
          <dl>
            <FieldRow label="Company" value={transparency.company.name} />
            <FieldRow label="Exchange" value={transparency.company.exchange} />
            <FieldRow label="Symbol" value={transparency.company.symbol} />
          </dl>
          <h4 className="mb-2 mt-4 font-[family-name:var(--font-display)] text-sm tracking-tight">
            Data Information
          </h4>
          <dl>
            <FieldRow
              label="Primary Data Source"
              value={transparency.dataInformation.primaryDataSource}
            />
            <FieldRow
              label="Financial Period Used"
              value={transparency.dataInformation.financialPeriodUsed}
            />
            <FieldRow
              label="Latest Available Data Date"
              value={transparency.dataInformation.latestAvailableDataDate}
            />
            <FieldRow
              label="Data Freshness"
              value={transparency.dataInformation.dataFreshness}
            />
          </dl>
        </div>
      </div>

      <div className="mt-4 border-t border-[var(--border)] pt-4">
        <h4 className="mb-2 font-[family-name:var(--font-display)] text-sm tracking-tight">
          Transparency
        </h4>
        <dl>
          <FieldRow
            label="Analysis Type"
            value={transparency.transparency.analysisType}
          />
          <FieldRow
            label="Methodology"
            value={transparency.transparency.methodology}
          />
          <FieldRow
            label="Pipeline Version"
            value={transparency.transparency.pipelineVersion}
          />
          <FieldRow
            label="Recommendation Engine Version"
            value={transparency.transparency.recommendationEngineVersion}
          />
        </dl>
      </div>

      <div className="mt-4 border-t border-[var(--border)] pt-4">
        <h4 className="mb-2 font-[family-name:var(--font-display)] text-sm tracking-tight">
          Quality Indicators
        </h4>
        <ul className="flex flex-wrap gap-2" aria-label="Quality indicators">
          {transparency.qualityBadges.map((badge) => (
            <li key={badge.id}>
              <Badge variant="outline">{badge.label}</Badge>
            </li>
          ))}
        </ul>
      </div>
    </SectionCard>
  );
}
