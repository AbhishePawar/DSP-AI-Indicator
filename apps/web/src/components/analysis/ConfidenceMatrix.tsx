import { ConfidenceBadge } from "@/components/trust/ConfidenceBadge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { ConfidenceMatrixView } from "@/lib/analysis/types";
import { CONFIDENCE_LABELS } from "@/lib/trust/labels";

export function ConfidenceMatrix({ matrix }: { matrix: ConfidenceMatrixView }) {
  return (
    <Card id="confidence_matrix">
      <CardHeader
        title="Confidence matrix"
        description="Research confidence by domain — Insufficient Evidence when metrics are missing"
        action={<ConfidenceBadge level={matrix.overall} />}
      />
      <CardBody>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[20rem] text-left text-sm">
            <caption className="sr-only">Confidence by research domain</caption>
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                <th scope="col" className="px-2 py-2 font-medium">
                  Domain
                </th>
                <th scope="col" className="px-2 py-2 font-medium">
                  Level
                </th>
              </tr>
            </thead>
            <tbody>
              {matrix.rows.map((row) => (
                <tr key={row.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-2 py-2">{row.label}</td>
                  <td className="px-2 py-2">
                    <ConfidenceBadge level={row.level} />
                    <span className="sr-only">{CONFIDENCE_LABELS[row.level]}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardBody>
    </Card>
  );
}
