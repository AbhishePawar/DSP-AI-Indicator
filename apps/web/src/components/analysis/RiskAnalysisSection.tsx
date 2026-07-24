import { InsightCard } from "@/components/analysis/InsightCard";
import { RiskCard } from "@/components/analysis/RiskCard";
import type { RiskInsightView } from "@/lib/analysis/types";

export function RiskAnalysisSection({ risks }: { risks: RiskInsightView[] }) {
  return (
    <InsightCard
      title="Risk Analysis"
      intro="What can go wrong over the next decade — categorized so nothing important is left as a vague worry."
      outro="Revisit severity once evidence arrives. Until then, use watchpoints as a filing checklist — never as fabricated scores."
    >
      <div className="grid gap-4 lg:grid-cols-2">
        {risks.map((risk) => (
          <RiskCard key={risk.id} risk={risk} />
        ))}
      </div>
    </InsightCard>
  );
}
