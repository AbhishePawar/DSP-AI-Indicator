import { Badge } from "@/components/ui/Badge";
import { CATEGORY_LABELS, type ValueCategory } from "@/lib/trust/labels";

const TONE: Record<
  ValueCategory,
  "neutral" | "success" | "warning" | "danger" | "accent"
> = {
  verified_fact: "success",
  calculated: "accent",
  estimated: "warning",
  ai_interpretation: "warning",
  external_consensus: "neutral",
  user_input: "neutral",
  unknown: "neutral",
  unavailable: "danger",
};

export function ValueCategoryBadge({ category }: { category: ValueCategory }) {
  return (
    <Badge tone={TONE[category]} className="font-normal">
      {CATEGORY_LABELS[category]}
    </Badge>
  );
}
