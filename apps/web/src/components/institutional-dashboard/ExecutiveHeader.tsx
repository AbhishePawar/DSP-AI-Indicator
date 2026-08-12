import { MetricCell } from "@/components/institutional-dashboard/MetricCell";
import { SectionShell } from "@/components/institutional-dashboard/SectionShell";
import type { ExecutiveHeaderView } from "@/lib/institutional-dashboard/types";

export function ExecutiveHeader({ view }: { view: ExecutiveHeaderView }) {
  return (
    <SectionShell
      id="rs-001-executive"
      title="Executive Summary"
      description="RS-001 — mandatory research header"
      prominent
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <MetricCell label="Company name" field={view.companyName} emphasize />
        <MetricCell label="Ticker" field={view.ticker} emphasize />
        <MetricCell label="Exchange" field={view.exchange} />
        <MetricCell label="Sector" field={view.sector} />
        <MetricCell label="Industry" field={view.industry} />
        <MetricCell
          label="Current market price"
          field={view.currentMarketPrice}
          emphasize
        />
        <MetricCell
          label="Intrinsic value"
          field={view.intrinsicValue}
          emphasize
        />
        <MetricCell
          label="Margin of safety"
          field={view.marginOfSafety}
          emphasize
        />
        <MetricCell label="Fair value range" field={view.fairValueRange} />
        <MetricCell label="Expected CAGR" field={view.expectedCagr} />
        <MetricCell label="Overall score" field={view.overallScore} emphasize />
        <MetricCell label="Confidence" field={view.confidence} />
        <MetricCell label="Research status" field={view.researchStatus} />
        <MetricCell label="Recommendation" field={view.recommendation} />
        <MetricCell label="Report timestamp" field={view.reportTimestamp} />
        <MetricCell label="Research version" field={view.researchVersion} />
        <MetricCell label="Engine version" field={view.engineVersion} />
        <MetricCell label="Research mode" field={view.researchMode} />
        <MetricCell label="Report version" field={view.reportVersion} />
      </div>
    </SectionShell>
  );
}
