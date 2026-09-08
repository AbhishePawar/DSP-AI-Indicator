/**
 * Production error reporter.
 * Sends unhandled errors to the observability pipeline.
 * Currently logs to console in production; extend with a real sink (Sentry, etc.) here.
 */

import { logger } from "@/lib/observability/logger";

export interface ErrorReport {
  message: string;
  stack?: string;
  source: string;
  url?: string;
  userAgent?: string;
  timestamp: string;
  digest?: string;
}

/**
 * Report an error to the observability pipeline.
 * In production, this is the single place to wire in Sentry / Datadog / etc.
 */
export function reportError(
  error: Error | string,
  source: string,
  options?: { digest?: string }
): void {
  const message = typeof error === "string" ? error : error.message;
  const stack = typeof error === "string" ? undefined : error.stack;

  const report: ErrorReport = {
    message,
    stack,
    source,
    url: typeof window !== "undefined" ? window.location.href : undefined,
    userAgent:
      typeof navigator !== "undefined" ? navigator.userAgent : undefined,
    timestamp: new Date().toISOString(),
    digest: options?.digest,
  };

  // Always record in the in-memory logger
  logger.recordClientError(
    typeof error === "string" ? new Error(error) : error,
    source as Parameters<typeof logger.recordClientError>[1],
    options
  );

  // Production: forward to external sink if configured
  if (process.env.NODE_ENV === "production") {
    // Extend here: Sentry.captureException(error, { extra: report });
    // For now, structured console output for log aggregators (Datadog, CloudWatch, etc.)
    console.error(
      JSON.stringify({
        level: "error",
        ...report,
      })
    );
  }
}

/**
 * Install global window error handlers.
 * Call once from a client component or layout.
 */
export function installGlobalErrorHandlers(): void {
  if (typeof window === "undefined") return;

  window.addEventListener("error", (event) => {
    reportError(event.error ?? new Error(event.message), "window-error");
  });

  window.addEventListener("unhandledrejection", (event) => {
    const error =
      event.reason instanceof Error
        ? event.reason
        : new Error(String(event.reason));
    reportError(error, "unhandled-promise-rejection");
  });
}
