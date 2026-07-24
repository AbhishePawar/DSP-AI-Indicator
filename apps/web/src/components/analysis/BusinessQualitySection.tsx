import { MetricCard } from "@/components/analysis/MetricCard";
import type { MetricView } from "@/lib/analysis/types";

export function BusinessQualitySection({ metrics }: { metrics: MetricView[] }) {
  return (
    <section aria-labelledby="business-quality-heading" className="space-y-4">
      <div>
        <h2
          id="business-quality-heading"
          className="font-[family-name:var(--font-display)] text-2xl tracking-tight"
        >
          Business Quality
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Educational metric cards. Values stay Unavailable until calculated
          metrics appear in the API envelope — never fabricated.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {metrics.map((m) => (
          <MetricCard key={m.id} metric={m} />
        ))}
      </div>
    </section>
  );
}

export function FinancialStrengthSection({ metrics }: { metrics: MetricView[] }) {
  return (
    <section aria-labelledby="financial-strength-heading" className="space-y-4">
      <div>
        <h2
          id="financial-strength-heading"
          className="font-[family-name:var(--font-display)] text-2xl tracking-tight"
        >
          Financial Strength
        </h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          What is happening financially? Why care? What to investigate next.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {metrics.map((m) => (
          <MetricCard key={m.id} metric={m} />
        ))}
      </div>
    </section>
  );
}
