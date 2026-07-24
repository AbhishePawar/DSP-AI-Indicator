import { InsightCard } from "@/components/analysis/InsightCard";
import { ManagementCard } from "@/components/analysis/ManagementCard";
import type { ManagementInsightView } from "@/lib/analysis/types";

export function ManagementSection({
  items,
}: {
  items: ManagementInsightView[];
}) {
  return (
    <InsightCard
      title="Management Quality"
      intro="Whether leadership deserves trust for capital, execution, and long-term stewardship."
      outro="Monitor capital allocation disclosures, guidance vs delivery, and governance changes."
    >
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((insight) => (
          <ManagementCard key={insight.id} insight={insight} />
        ))}
      </div>
    </InsightCard>
  );
}
