import { Badge } from "@/components/ui/Badge";
import type { AgreementLevel } from "@/lib/analysis/types";

const LABELS: Record<AgreementLevel, string> = {
  aligned: "Aligned",
  different_view: "Different View",
  unavailable: "Unavailable",
};

const TONE: Record<AgreementLevel, "success" | "warning" | "neutral"> = {
  aligned: "success",
  different_view: "warning",
  unavailable: "neutral",
};

export function AgreementBadge({ level }: { level: AgreementLevel }) {
  return <Badge tone={TONE[level]}>{LABELS[level]}</Badge>;
}
