import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import type { DisplayField } from "@/lib/analysis/types";

export function FieldRow({
  label,
  field,
  emphasize = false,
}: {
  label: string;
  field: DisplayField<string | string[] | number>;
  emphasize?: boolean;
}) {
  const display =
    field.presence === "unavailable" || field.value == null
      ? "Unavailable"
      : Array.isArray(field.value)
        ? field.value.join(" · ")
        : String(field.value);

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </p>
      <p className={emphasize ? "text-lg font-medium" : "text-sm"}>
        {display}
      </p>
      <div className="flex flex-wrap gap-2">
        <ValueCategoryBadge category={field.category} />
        <SourceBadge source={field.source} />
      </div>
    </div>
  );
}
