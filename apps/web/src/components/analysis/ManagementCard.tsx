import { ConceptTooltip } from "@/components/analysis/ConceptTooltip";
import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { ManagementInsightView } from "@/lib/analysis/types";

export function ManagementCard({ insight }: { insight: ManagementInsightView }) {
  const conceptKey = insight.learnMore.replace("term:", "");

  return (
    <Card>
      <CardHeader
        title={insight.title}
        action={<ConfidenceBadge level={insight.confidence} />}
      />
      <CardBody className="space-y-3 text-sm">
        <div className="flex flex-wrap gap-2">
          <ValueCategoryBadge category={insight.category} />
          <SourceBadge source={insight.source} />
        </div>
        <Block label="Meaning">{insight.meaning}</Block>
        <Block label="Importance">{insight.importance}</Block>
        <Block label="Evidence">{insight.evidence}</Block>
        <Block label="AI interpretation">{insight.aiInterpretation}</Block>
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
