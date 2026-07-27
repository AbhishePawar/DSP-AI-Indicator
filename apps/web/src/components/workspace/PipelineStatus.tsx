"use client";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import type {
  PipelineStageView,
  PipelineUiStatus,
} from "@/lib/analysis/pipelineStages";

function toneFor(
  status: PipelineUiStatus,
): "neutral" | "accent" | "success" | "danger" | "warning" {
  if (status === "Completed") return "success";
  if (status === "Running") return "accent";
  if (status === "Failed") return "danger";
  return "neutral";
}

export function PipelineStatus({ stages }: { stages: PipelineStageView[] }) {
  return (
    <Card>
      <CardHeader
        title="Pipeline Progress"
        description="Composition execution stages"
      />
      <CardBody>
        <ol className="space-y-0" aria-label="Analysis pipeline">
          {stages.map((stage, index) => (
            <li key={stage.id} className="relative flex gap-3 pb-4 last:pb-0">
              {index < stages.length - 1 ? (
                <span
                  className="absolute left-[11px] top-6 h-[calc(100%-1.25rem)] w-px bg-[var(--border)]"
                  aria-hidden
                />
              ) : null}
              <span
                className={`mt-1 h-3 w-3 shrink-0 rounded-full ${
                  stage.status === "Completed"
                    ? "bg-[var(--accent)]"
                    : stage.status === "Running"
                      ? "bg-[var(--accent)] shadow-[0_0_0_3px_var(--accent-soft)]"
                      : stage.status === "Failed"
                        ? "bg-[var(--danger-fg)]"
                        : "bg-[var(--border)]"
                }`}
                aria-hidden
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">{stage.label}</span>
                  <Badge tone={toneFor(stage.status)}>{stage.status}</Badge>
                </div>
              </div>
            </li>
          ))}
        </ol>
      </CardBody>
    </Card>
  );
}
