import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import type { ConfidenceMatrixView } from "@/lib/analysis/types";
import { CONFIDENCE_LABELS } from "@/lib/trust/labels";

export function ConfidenceMatrix({ matrix }: { matrix: ConfidenceMatrixView }) {
  return (
    <section id="confidence_matrix" className="space-y-4">
      <div className="mb-4 flex items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
        <div>
          <h3 className="font-[family-name:var(--font-display)] text-base tracking-tight text-[var(--fg)]">
            Confidence Matrix
          </h3>
          <p className="mt-0.5 text-xs text-[var(--muted)]">
            Research confidence by domain — Insufficient Evidence when metrics are missing
          </p>
        </div>
        <ConfidenceBadge level={matrix.overall} />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[20rem] text-left text-sm">
          <caption className="sr-only">Confidence by research domain</caption>
          <thead>
            <tr className="border-b border-[var(--border)] text-[var(--muted)]">
              <th scope="col" className="py-2 pr-4 text-[10px] font-semibold uppercase tracking-widest">
                Domain
              </th>
              <th scope="col" className="py-2 text-[10px] font-semibold uppercase tracking-widest">
                Level
              </th>
            </tr>
          </thead>
          <tbody>
            {matrix.rows.map((row) => (
              <tr key={row.id} className="border-b border-[var(--border)] last:border-0">
                <td className="py-2 pr-4 text-xs text-[var(--muted)]">{row.label}</td>
                <td className="py-2">
                  <ConfidenceBadge level={row.level} />
                  <span className="sr-only">{CONFIDENCE_LABELS[row.level]}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
