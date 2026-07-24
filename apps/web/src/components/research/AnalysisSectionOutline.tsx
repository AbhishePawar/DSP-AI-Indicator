import { ANALYSIS_PAGE_ORDER } from "@/lib/product";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

/** Architecture preview of L1.2 analysis IA — no business logic. */
export function AnalysisSectionOutline() {
  return (
    <Card className="mt-6">
      <CardHeader
        title="Analysis workspace outline"
        description="Canonical section order for L1.2 — Research Mode terminology"
      />
      <CardBody>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-[var(--muted)]">
          {ANALYSIS_PAGE_ORDER.map((section) => (
            <li key={section.id}>
              <span className="text-[var(--fg)]">{section.title}</span>
            </li>
          ))}
        </ol>
      </CardBody>
    </Card>
  );
}
