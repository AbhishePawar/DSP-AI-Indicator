import { ConceptTooltip } from "@/components/analysis/ConceptTooltip";
import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import type { ManagementInsightView } from "@/lib/analysis/types";

export function ManagementCard({ insight }: { insight: ManagementInsightView }) {
  const conceptKey = insight.learnMore.replace("term:", "");

  return (
    <div className="space-y-4 border-b border-[var(--border)] pb-6 last:border-0 last:pb-0">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <h4 className="font-[family-name:var(--font-display)] text-base font-semibold leading-snug text-[var(--fg)]">
          {insight.title}
        </h4>
        <ConfidenceBadge level={insight.confidence} />
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-2">
        <ValueCategoryBadge category={insight.category} />
        <SourceBadge source={insight.source} />
      </div>

      {/* Content blocks */}
      <div className="space-y-3 text-sm">
        <Block label="Meaning">{insight.meaning}</Block>
        <Block label="Importance">{insight.importance}</Block>
        <Block label="Evidence">{insight.evidence}</Block>
        <Block label="AI interpretation">{insight.aiInterpretation}</Block>
      </div>

      <ConceptTooltip conceptId={conceptKey}>
        <span className="text-xs text-[var(--muted)] underline decoration-dotted underline-offset-2 cursor-help">
          Concept help
        </span>
      </ConceptTooltip>
    </div>
  );
}

function Block({ label, children }: { label: string; children: string }) {
  return (
    <div className="border-l-2 border-[var(--border)] pl-3">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
        {label}
      </p>
      <p className="mt-1 leading-relaxed text-[var(--fg)]">{children}</p>
    </div>
  );
}
