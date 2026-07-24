"use client";

import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

export function RetryCard({
  detail,
  onRetry,
}: {
  detail?: string;
  onRetry: () => void;
}) {
  return (
    <Card>
      <CardHeader title="Retry" description="Recover without reloading the whole application" />
      <CardBody className="space-y-3">
        {detail ? <p className="text-sm text-[var(--muted)]">{detail}</p> : null}
        <Button onClick={onRetry}>Try again</Button>
      </CardBody>
    </Card>
  );
}

export function GracefulDegradationCard({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <Card className="border-[var(--danger-border)]">
      <CardHeader title={title} description="Graceful degradation" />
      <CardBody>
        <p className="text-sm">{message}</p>
        <p className="mt-2 text-xs text-[var(--muted)]">
          DSP Research Mode, evidence, confidence, and methodology remain authoritative when
          available elsewhere in the workspace.
        </p>
      </CardBody>
    </Card>
  );
}

export function UnexpectedStateHandler({
  stateLabel,
  guidance,
}: {
  stateLabel: string;
  guidance: string;
}) {
  return (
    <div
      role="status"
      className="rounded-md border border-dashed border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm"
    >
      <p className="font-medium">Unexpected state: {stateLabel}</p>
      <p className="mt-1 text-[var(--muted)]">{guidance}</p>
    </div>
  );
}
