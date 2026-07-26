"use client";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type { StageSummary } from "@/lib/api/compositionTypes";

function statusTone(
  status: string,
): "success" | "danger" | "warning" | "neutral" | "accent" {
  const s = status.toLowerCase();
  if (s === "succeeded") return "success";
  if (s === "failed") return "danger";
  if (s === "degraded" || s === "skipped") return "warning";
  if (s === "running") return "accent";
  return "neutral";
}

export function PipelineTimeline({ stages }: { stages: StageSummary[] }) {
  return (
    <Card>
      <CardHeader
        title="Pipeline Status"
        description="Deterministic execution order from the API"
      />
      <CardBody>
        {stages.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">
            Run analyse to populate the pipeline timeline.
          </p>
        ) : (
          <ol className="space-y-3" aria-label="Pipeline stages">
            {stages.map((stage, index) => (
              <li
                key={stage.stage}
                className="flex flex-wrap items-start gap-3 border-b border-[var(--border)] pb-3 last:border-0 last:pb-0"
              >
                <span
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--surface-2)] text-xs font-medium"
                  aria-hidden
                >
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{stage.stage}</span>
                    <Badge tone={statusTone(stage.status)}>{stage.status}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    {[
                      stage.label ? `Label: ${stage.label}` : null,
                      stage.decision ? `Decision: ${stage.decision}` : null,
                      stage.score != null ? `Score: ${stage.score}` : null,
                      stage.confidence != null
                        ? `Confidence: ${(stage.confidence * 100).toFixed(0)}%`
                        : null,
                      stage.error ? `Error: ${stage.error}` : null,
                    ]
                      .filter(Boolean)
                      .join(" · ") || "No stage summary fields"}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </CardBody>
    </Card>
  );
}
