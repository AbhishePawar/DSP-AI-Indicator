import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import type { DashboardField } from "@/lib/institutional-dashboard/types";

export function MetricCell({
  label,
  field,
  emphasize = false,
}: {
  label: string;
  field: DashboardField<string | number | string[]>;
  emphasize?: boolean;
}) {
  const display =
    Array.isArray(field.value) && field.presence === "available"
      ? field.value.join(" · ")
      : field.display;

  const muted =
    field.presence === "unavailable" ||
    field.presence === "unable_to_calculate";

  return (
    <div className="space-y-1">
      <p className="text-[0.65rem] font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </p>
      <p
        className={`${emphasize ? "text-lg font-semibold tracking-tight" : "text-sm font-medium"} ${
          muted ? "text-[var(--muted)]" : "text-[var(--fg)]"
        }`}
      >
        {display}
      </p>
      <div className="flex flex-wrap gap-1.5">
        <ValueCategoryBadge category={field.category} />
        <SourceBadge source={field.source} />
      </div>
    </div>
  );
}
