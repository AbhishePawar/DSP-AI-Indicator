import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import type { ExecutiveSummaryView } from "@/lib/analysis/types";
import { SCREEN_QUESTIONS } from "@/lib/product";

export function ExecutiveSummaryCard({
  summary,
}: {
  summary: ExecutiveSummaryView;
}) {
  return (
    <section>
      {/* Trust badges — right-aligned, subdued */}
      <div className="flex flex-wrap gap-2 mb-5">
        <ValueCategoryBadge category={summary.category} />
        <SourceBadge source={summary.source} />
      </div>

      {/* Four Question Rule — document-style numbered list */}
      <div className="mb-6 border-l-2 border-[var(--border)] pl-4">
        <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)] mb-2">
          Four Question Rule
        </p>
        <ol className="space-y-1 text-xs text-[var(--muted)]">
          {SCREEN_QUESTIONS.map((q, i) => (
            <li key={q} className="flex gap-2">
              <span className="font-mono text-[var(--border)] shrink-0">{i + 1}.</span>
              <span>{q}</span>
            </li>
          ))}
        </ol>
      </div>

      {/* Summary content */}
      {summary.available ? (
        <div className="space-y-4 text-sm leading-relaxed text-[var(--fg)]">
          {summary.paragraphs.map((p) => (
            <p key={p.slice(0, 32)} className="leading-[1.75]">{p}</p>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No executive narrative yet"
          description="Run Analyze via API. When the envelope includes rationale or summary text, it appears here with source labels — never fabricated prose."
        />
      )}
    </section>
  );
}
