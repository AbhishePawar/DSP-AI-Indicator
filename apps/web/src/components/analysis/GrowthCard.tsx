import { ConceptTooltip } from "@/components/analysis/ConceptTooltip";
import { EvidencePanel } from "@/components/analysis/EvidencePanel";
import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import type { GrowthInsightView } from "@/lib/analysis/types";

function ratingColour(rating: string): string {
  const r = rating.toLowerCase();
  if (r.includes("strong") || r.includes("high") || r.includes("good") || r.includes("positive")) return "text-emerald-700";
  if (r.includes("moderate") || r.includes("medium") || r.includes("fair")) return "text-amber-700";
  if (r.includes("weak") || r.includes("low") || r.includes("poor") || r.includes("negative")) return "text-red-700";
  return "text-[var(--fg)]";
}

export function GrowthCard({ insight }: { insight: GrowthInsightView }) {
  const conceptKey = insight.learnMore.replace("term:", "");

  return (
    <div className="space-y-4 border-b border-[var(--border)] pb-6 last:border-0 last:pb-0">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <h4 className="font-[family-name:var(--font-display)] text-base font-semibold leading-snug text-[var(--fg)]">
          {insight.title}
        </h4>
        <span className={["shrink-0 text-sm font-semibold", ratingColour(insight.rating)].join(" ")}>
          {insight.rating}
        </span>
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-2">
        <ValueCategoryBadge category={insight.category} />
        <SourceBadge source={insight.source} />
      </div>

      {/* Content blocks */}
      <div className="space-y-3 text-sm">
        <Block label="Meaning">{insight.meaning}</Block>
        <Block label="Why it matters">{insight.whyItMatters}</Block>
        <Block label="Investor takeaway">{insight.investorTakeaway}</Block>
        <Block label="AI explanation">{insight.aiExplanation}</Block>
      </div>

      <ConceptTooltip conceptId={conceptKey}>
        <span className="text-xs text-[var(--muted)] underline decoration-dotted underline-offset-2 cursor-help">
          Concept help
        </span>
      </ConceptTooltip>

      <EvidencePanel evidence={insight.evidence} compact />
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
