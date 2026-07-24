import { Badge } from "@/components/ui/Badge";
import {
  CONFIDENCE_LABELS,
  type ConfidenceLevel,
} from "@/lib/trust/labels";

const TONE: Record<ConfidenceLevel, "success" | "accent" | "neutral" | "warning" | "danger"> = {
  very_high: "success",
  high: "accent",
  moderate: "neutral",
  low: "warning",
  insufficient_evidence: "danger",
};

export function ConfidenceBadge({
  level,
}: {
  level: ConfidenceLevel | string;
}) {
  const key = (
    typeof level === "string" ? level.toLowerCase().replace(/\s+/g, "_") : level
  ) as ConfidenceLevel;
  const label = CONFIDENCE_LABELS[key] ?? String(level);
  const tone = TONE[key] ?? "neutral";
  return (
    <Badge tone={tone} className="font-normal">
      Confidence: {label}
    </Badge>
  );
}
