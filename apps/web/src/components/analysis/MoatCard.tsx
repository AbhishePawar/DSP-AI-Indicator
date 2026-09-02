import { ConceptTooltip } from "@/components/analysis/ConceptTooltip";
import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import type { MoatInsightView } from "@/lib/analysis/types";

export function MoatCard({ insight }: { insight: MoatInsightView }) {
  const conceptKey = insight.learnMore.replace("term:", "");

  return (
    <div className="border-b border-[var(--border)] pb-5 last:border-0 last:pb-0">
      {/* Header row */}
      <div className="flex flex-wrap items-start justify-between gap-2 mb-3">
        <h4 className="font-[family-name:var(--font-display)] text-base font-semibold text-[var(--fg)] leading-snug">
          {insight.title}
        </h4>
        <span className="shrink-0 rounded border border-[var(--border)] bg-[var(--surface-2)] px-2 py-0.5 font-mono text-xs font-semibold text-[var(--muted)]">
          {insight.rating}
        </span>
      </div>

      {/* Trust badges */}
      <div className="flex flex-wrap gap-2 mb-4">
        <ValueCategoryBadge category={insight.category} />
        <SourceBadge source={insight.source} />
      </div>

      {/* Content blocks */}
      <div className="space-y-3 text-sm">
        <Block label="Meaning">{insight.meaning}</Block>
        <Block label="Evidence">{insight.evidence}</Block>
        <Block label="Investor takeaway">{insight.investorTakeaway}</Block>
      </div>

      <ConceptTooltip conceptId={conceptKey}>
        <span className="mt-3 inline-block text-xs text-[var(--muted)] hover:text-[var(--fg)] transition-colors cursor-help">
          Concept help ↗
        </span>
      </ConceptTooltip>
    </div>
  );
}

function Block({ label, children }: { label: string; children: string }) {
  return (
    <div className="pl-3 border-l-2 border-[var(--border)]">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] mb-0.5">
        {label}
      </p>
      <p className="text-[var(--fg)] leading-relaxed">{children}</p>
    </div>
  );
}
