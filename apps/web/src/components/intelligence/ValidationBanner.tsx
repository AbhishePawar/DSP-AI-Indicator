"use client";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";

export function ValidationBanner({
  valid,
  errors,
  warnings,
  apiError,
  correlationId,
  onRetry,
}: {
  valid?: boolean | null;
  errors?: string[];
  warnings?: string[];
  apiError?: string | null;
  correlationId?: string | null;
  onRetry?: () => void;
}) {
  if (apiError) {
    return (
      <Alert tone="danger" title="API error">
        <p>{apiError}</p>
        {correlationId ? (
          <p className="mt-1 font-mono text-xs">Correlation ID: {correlationId}</p>
        ) : null}
        {onRetry ? (
          <div className="mt-2">
            <Button type="button" size="sm" variant="secondary" onClick={onRetry}>
              Retry
            </Button>
          </div>
        ) : null}
      </Alert>
    );
  }

  if (valid === false && errors?.length) {
    return (
      <Alert tone="danger" title="Validation failed">
        <ul className="list-inside list-disc">
          {errors.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      </Alert>
    );
  }

  if (valid === true) {
    return (
      <Alert tone="success" title="Validation passed">
        Request shape is valid. Ready to run analyse.
        {warnings?.length ? (
          <ul className="mt-2 list-inside list-disc opacity-90">
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        ) : null}
      </Alert>
    );
  }

  if (warnings?.length) {
    return (
      <Alert tone="warning" title="Warnings">
        <ul className="list-inside list-disc">
          {warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      </Alert>
    );
  }

  return null;
}
