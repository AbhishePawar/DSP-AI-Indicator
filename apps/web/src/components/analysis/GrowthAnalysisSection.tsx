import { GrowthCard } from "@/components/analysis/GrowthCard";
import { InsightCard } from "@/components/analysis/InsightCard";
import { EmptyState } from "@/components/ui/EmptyState";
import type { GrowthInsightView } from "@/lib/analysis/types";

export function GrowthAnalysisSection({ items }: { items: GrowthInsightView[] }) {
  return (
    <InsightCard
      title="Growth Analysis"
      intro="Growth is about whether this business can expand value over a decade — not a single percentage rate."
      outro="Monitor revenue quality, operating leverage, and constraints each reporting cycle. Prefer evidence over slogans."
    >
      {items.length === 0 ? (
        <EmptyState
          title="Growth insights unavailable"
          description="Why: no growth artifacts in the API envelope. How to improve: wire fundamentals/growth series. When: later data integrations."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((insight) => (
            <GrowthCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}
    </InsightCard>
  );
}
