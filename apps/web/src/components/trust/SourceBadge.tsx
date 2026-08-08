import { Badge } from "@/components/ui/Badge";
import { SOURCE_LABELS, type SourceKind } from "@/lib/trust/labels";

const TONE: Record<SourceKind, "neutral" | "success" | "warning" | "accent"> = {
  verified_financial_statement: "success",
  authenticated_market_data: "success",
  calculated_metric: "accent",
  estimated_value: "warning",
  ai_interpretation: "warning",
  external_consensus: "neutral",
  user_input: "neutral",
  unavailable: "neutral",
};

export function SourceBadge({ source }: { source: SourceKind }) {
  return (
    <Badge tone={TONE[source]} className="font-normal">
      Source: {SOURCE_LABELS[source]}
    </Badge>
  );
}
