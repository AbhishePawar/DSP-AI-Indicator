"use client";

/**
 * RC1 Milestone 10 — Production Operations panel.
 * Thin client over /api/v1/ops/* — no operational logic in the browser.
 */

import { useEffect, useState } from "react";

import { Alert } from "@/components/ds";
import { api } from "@/lib/api/client";
import { featureFlags } from "@/lib/featureFlags";

export function ProductionOpsPanel() {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!featureFlags.productionOps) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await api.opsDashboard();
        if (!cancelled) {
          if (!res.ok) {
            setError(res.message || "Data unavailable.");
          } else {
            setResult((res.result || {}) as Record<string, unknown>);
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Data unavailable.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!featureFlags.productionOps) {
    return (
      <Alert variant="warning" title="Production ops UI disabled.">
        Set NEXT_PUBLIC_PRODUCTION_OPS=true to enable.
      </Alert>
    );
  }

  if (loading) {
    return (
      <p className="text-sm text-[var(--dsp-text-muted)]">
        Loading production operations…
      </p>
    );
  }

  if (error || !result) {
    return (
      <p className="text-sm text-[var(--dsp-danger)]" role="alert">
        {error || "Data unavailable."}
      </p>
    );
  }

  const version = (result.version || {}) as Record<string, unknown>;
  const health = (result.health || {}) as Record<string, unknown>;
  const ready = (health.ready || {}) as Record<string, unknown>;
  const live = (health.live || {}) as Record<string, unknown>;
  const deps = (health.dependencies || {}) as {
    components?: Array<{ name?: string; status?: string; message?: string }>;
  };
  const metrics = (result.metrics || {}) as Record<string, unknown>;
  const backup = (result.backup || {}) as Record<string, unknown>;
  const obs = (result.observability || {}) as Record<string, unknown>;
  const otel = (obs.opentelemetry || {}) as Record<string, unknown>;

  return (
    <div className="space-y-4" data-testid="production-ops-panel">
      <section className="rounded-lg border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-4">
        <h2 className="mb-2 text-base font-semibold">Production operations</h2>
        <p className="mb-3 text-xs text-[var(--dsp-text-muted)]">
          Aggregated from /api/v1/ops — reuses existing health, metrics, and audit
          infrastructure.
        </p>
        <h3 className="mb-2 text-sm font-medium">Build / version</h3>
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-[var(--dsp-text-muted)]">Application</dt>
            <dd>{String(version.application_version ?? "Data unavailable.")}</dd>
          </div>
          <div>
            <dt className="text-[var(--dsp-text-muted)]">Git SHA</dt>
            <dd className="font-mono text-xs">
              {String(version.git_sha ?? "unknown")}
            </dd>
          </div>
          <div>
            <dt className="text-[var(--dsp-text-muted)]">Environment</dt>
            <dd>{String(version.environment ?? "unknown")}</dd>
          </div>
          <div>
            <dt className="text-[var(--dsp-text-muted)]">Channel</dt>
            <dd>{String(version.release_channel ?? "unknown")}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-lg border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-4">
        <h2 className="mb-2 text-base font-semibold">System health</h2>
        <p className="text-sm">
          Live: {String(live.status ?? "Data unavailable.")} · Ready:{" "}
          {ready.ready ? "pass" : "fail"} · Status:{" "}
          {String(ready.status ?? "Data unavailable.")}
        </p>
        <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          {(deps.components || []).map((c) => (
            <li
              key={c.name}
              className="flex justify-between rounded border border-[var(--dsp-border)] px-3 py-2"
            >
              <span className="capitalize">{c.name}</span>
              <span className="text-[var(--dsp-text-muted)]">
                {c.status} — {c.message}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-lg border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-4">
        <h2 className="mb-2 text-base font-semibold">Metrics</h2>
        <p className="text-sm">
          Scrape: {String(metrics.scrape_path ?? "/metrics")} · Series sample:{" "}
          {String(metrics.sample_series_count ?? "Data unavailable.")}
        </p>
        <p className="mt-1 text-xs text-[var(--dsp-text-muted)]">
          {String(metrics.note ?? "")}
        </p>
      </section>

      <section className="rounded-lg border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-4">
        <h2 className="mb-2 text-base font-semibold">Observability</h2>
        <p className="text-sm">
          OpenTelemetry:{" "}
          {otel.available
            ? String(otel.endpoint || "configured")
            : String(otel.message || "Data unavailable.")}
        </p>
        <p className="mt-1 text-xs text-[var(--dsp-text-muted)]">
          Structured JSON logging + correlation IDs reused from
          production_platform.
        </p>
      </section>

      <section className="rounded-lg border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-4">
        <h2 className="mb-2 text-base font-semibold">Backup</h2>
        <p className="text-sm" role="status">
          {backup.available
            ? "Backup provider available."
            : String(backup.message || "Data unavailable.")}
        </p>
        <p className="mt-1 text-xs text-[var(--dsp-text-muted)]">
          {String(backup.note || "")}
        </p>
      </section>
    </div>
  );
}
