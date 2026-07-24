import { SourceBadge } from "@/components/trust/SourceBadge";
import { ValueCategoryBadge } from "@/components/trust/ValueCategoryBadge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import type { ExecutiveSummaryView } from "@/lib/analysis/types";
import { SCREEN_QUESTIONS } from "@/lib/product";

export function ExecutiveSummaryCard({
  summary,
}: {
  summary: ExecutiveSummaryView;
}) {
  return (
    <Card>
      <CardHeader
        title="Executive Summary"
        description="Understand the company in minutes — Four Question Rule"
        action={
          <div className="flex flex-wrap gap-2">
            <ValueCategoryBadge category={summary.category} />
            <SourceBadge source={summary.source} />
          </div>
        }
      />
      <CardBody className="space-y-4">
        <ol className="grid gap-2 text-xs text-[var(--muted)] sm:grid-cols-2">
          {SCREEN_QUESTIONS.map((q, i) => (
            <li key={q}>
              <span className="font-medium text-[var(--fg)]">{i + 1}.</span> {q}
            </li>
          ))}
        </ol>
        {summary.available ? (
          <div className="space-y-3 text-sm leading-relaxed">
            {summary.paragraphs.map((p) => (
              <p key={p.slice(0, 32)}>{p}</p>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No executive narrative yet"
            description="Run Analyze via API. When the envelope includes rationale or summary text, it appears here with source labels — never fabricated prose."
          />
        )}
      </CardBody>
    </Card>
  );
}
