import { InsightCard } from "@/components/analysis/InsightCard";
import { MoatCard } from "@/components/analysis/MoatCard";
import type { MoatInsightView } from "@/lib/analysis/types";

export function CompetitiveAdvantageSection({
  items,
}: {
  items: MoatInsightView[];
}) {
  return (
    <InsightCard
      title="Competitive Advantage"
      intro="Whether advantages look durable enough to matter over a decade — brand, networks, switching costs, scale, and more."
      outro="Ask what could erode each advantage. Moat sustainability matters more than a single rating badge."
    >
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((insight) => (
          <MoatCard key={insight.id} insight={insight} />
        ))}
      </div>
    </InsightCard>
  );
}
