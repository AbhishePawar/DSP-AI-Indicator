import { ConceptTooltip } from "@/components/analysis/ConceptTooltip";
import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { MoatInsightView } from "@/lib/analysis/types";

export function MoatCard({ insight }: { insight: MoatInsightView }) {
  const conceptKey = insight.learnMore.replace("term:", "");

  return (
    <Card>
      <CardHeader
        title={insight.title}
        action={<Badge tone="neutral">{insight.rating}</Badge>}
      />
      <CardBody className="space-y-3 text-sm">
        <div className="flex flex-wrap gap-2">
          <ValueCategoryBadge category={insight.category} />
          <SourceBadge source={insight.source} />
        </div>
        <Block label="Meaning">{insight.meaning}</Block>
        <Block label="Evidence">{insight.evidence}</Block>
        <Block label="Investor takeaway">{insight.investorTakeaway}</Block>
        <ConceptTooltip conceptId={conceptKey}>
          <span className="text-xs text-[var(--muted)]">Concept help</span>
        </ConceptTooltip>
      </CardBody>
    </Card>
  );
}

function Block({ label, children }: { label: string; children: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </p>
      <p className="mt-1">{children}</p>
    </div>
  );
}
