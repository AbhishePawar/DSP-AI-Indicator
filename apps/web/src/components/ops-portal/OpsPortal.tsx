"use client";

/**
 * EPS-002 — Operational Dashboard / Incident Center (thin client).
 * RC1 M10 — also surfaces ProductionOpsPanel over /api/v1/ops/*.
 */

import { Suspense, lazy, useEffect, useState } from "react";

import { fetchOpsDashboard } from "@/lib/enterprise/enterpriseClient";
import type { OpsDashboard } from "@/lib/enterprise/types";

const ProductionOpsPanel = lazy(() =>
  import("./ProductionOpsPanel").then((m) => ({
    default: m.ProductionOpsPanel,
  })),
);

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-sm text-[var(--dsp-text-muted)]" role="status">
      {children}
    </p>
  );
}

export function OpsPortal() {
  const [data, setData] = useState<OpsDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const dash = await fetchOpsDashboard();
        if (!cancelled) setData(dash);
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

  if (loading) return <Empty>Loading operations dashboard…</Empty>;
  if (error) {
    return (
      <p className="text-sm text-[var(--dsp-danger)]" role="alert">
        {error}
      </p>
    );
  }
  if (!data) return <Empty>Data unavailable.</Empty>;

  const components = data.enterprise_health?.components || {};

  return (
    <div className="space-y-4" data-testid="ops-portal">
      <Suspense
        fallback={
          <p className="text-sm text-[var(--dsp-text-muted)]">
            Loading production operations…
          </p>
        }
      >
        <ProductionOpsPanel />
      </Suspense>

      <section className="rounded-lg border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-4">
        <h2 className="mb-2 text-base font-semibold">Enterprise health</h2>
        <p className="text-sm">
          Overall:{" "}
          <span className="font-medium">{data.enterprise_health.overall}</span>
        </p>
        <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          {Object.entries(components).map(([name, c]) => (
            <li
              key={name}
              className="flex justify-between rounded border border-[var(--dsp-border)] px-3 py-2"
            >
              <span className="capitalize">{name}</span>
              <span className="text-[var(--dsp-text-muted)]">
                {c.status} — {c.detail}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-lg border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-4">
        <h2 className="mb-2 text-base font-semibold">Platform metrics</h2>
        <dl className="grid gap-2 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-[var(--dsp-text-muted)]">Organizations</dt>
            <dd>{data.organizations}</dd>
          </div>
          <div>
            <dt className="text-[var(--dsp-text-muted)]">Active sessions</dt>
            <dd>{data.active_sessions}</dd>
          </div>
          <div>
            <dt className="text-[var(--dsp-text-muted)]">Billing</dt>
            <dd>
              {data.billing_available
                ? data.billing_provider
                : "Billing unavailable."}
            </dd>
          </div>
        </dl>
      </section>

      <section className="rounded-lg border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-4">
        <h2 className="mb-2 text-base font-semibold">Services</h2>
        <ul className="text-sm">
          {data.services.map((s) => (
            <li key={s.name} className="flex justify-between py-1">
              <span>{s.name}</span>
              <span className="text-[var(--dsp-text-muted)]">{s.status}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-lg border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-4">
        <h2 className="mb-2 text-base font-semibold">Deployments</h2>
        <Empty>
          {data.deployments?.message || "Data unavailable."}
        </Empty>
      </section>

      <section className="rounded-lg border border-[var(--dsp-border)] bg-[var(--dsp-surface)] p-4">
        <h2 className="mb-2 text-base font-semibold">
          Collaboration architecture
        </h2>
        <p className="text-sm text-[var(--dsp-text-muted)]">
          Status: {data.collaboration.status}. Realtime:{" "}
          {data.collaboration.realtime ? "enabled" : "not implemented"}.
        </p>
        <ul className="mt-2 list-inside list-disc text-sm text-[var(--dsp-text-muted)]">
          {data.collaboration.capabilities_reserved.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
