"use client";

import { Badge } from "@/components/ui/Badge";

export function HealthIndicator({
  ready,
  status,
  platformVersion,
  pipelineVersion,
  loading,
  error,
}: {
  ready?: boolean;
  status?: string;
  platformVersion?: string | null;
  pipelineVersion?: string | null;
  loading?: boolean;
  error?: string | null;
}) {
  const tone = error
    ? "danger"
    : loading
      ? "neutral"
      : ready
        ? "success"
        : "warning";

  return (
    <div
      className="flex flex-wrap items-center gap-2 text-sm"
      role="status"
      aria-live="polite"
      aria-label="API health"
    >
      <Badge tone={tone}>
        {error
          ? "API unavailable"
          : loading
            ? "Checking…"
            : ready
              ? "API ready"
              : status || "Not ready"}
      </Badge>
      {platformVersion ? (
        <span className="text-[var(--muted)]">Platform {platformVersion}</span>
      ) : null}
      {pipelineVersion ? (
        <span className="text-[var(--muted)]">Pipeline {pipelineVersion}</span>
      ) : null}
      {error ? <span className="text-[var(--danger-fg)]">{error}</span> : null}
    </div>
  );
}
