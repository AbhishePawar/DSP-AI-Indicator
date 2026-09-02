import { FieldRow } from "@/components/analysis/FieldRow";
import type { DisplayField, InvestmentThesisView } from "@/lib/analysis/types";

export function InvestmentThesisCard({ thesis }: { thesis: InvestmentThesisView }) {
  return (
    <section className="space-y-6">
      <FieldRow label="Why this company deserves attention" field={thesis.whyAttention} />

      <div className="grid gap-6 sm:grid-cols-2">
        <BulletListField label="Key strengths" field={thesis.keyStrengths} accentColor="var(--accent)" />
        <BulletListField label="Key concerns" field={thesis.keyConcerns} accentColor="var(--danger-fg)" />
      </div>

      <FieldRow label="Long-term thesis" field={thesis.longTermThesis} />

      <BulletListField label="Things to monitor" field={thesis.thingsToMonitor} accentColor="var(--muted)" />
    </section>
  );
}

function BulletListField({
  label,
  field,
  accentColor,
}: {
  label: string;
  field: DisplayField<string[]>;
  accentColor: string;
}) {
  const items =
    field.presence === "available" && Array.isArray(field.value) ? field.value : [];

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-2.5">
        {label}
      </p>
      {items.length > 0 ? (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item} className="flex gap-2.5 text-sm text-[var(--fg)]">
              <span
                className="mt-1.5 inline-block h-1 w-1 rounded-full shrink-0"
                style={{ backgroundColor: accentColor }}
                aria-hidden
              />
              <span className="leading-relaxed">{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-[var(--muted)]">None reported</p>
      )}
    </div>
  );
}
