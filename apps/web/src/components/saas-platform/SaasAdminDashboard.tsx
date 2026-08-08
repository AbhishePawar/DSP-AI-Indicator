"use client";

export function SaasAdminDashboard({
  data,
  loading,
  error,
}: {
  data?: Record<string, unknown>;
  loading?: boolean;
  error?: boolean;
}) {
  if (loading) {
    return <p className="text-sm text-[var(--muted)]">Loading SaaS dashboard…</p>;
  }
  if (error) {
    return (
      <p className="text-sm text-[var(--muted)]" role="alert">
        Data unavailable.
      </p>
    );
  }

  const revenue = (data?.revenue || {}) as Record<string, unknown>;
  const overview = (data?.subscription_overview || {}) as Record<string, unknown>;
  const planDist = (data?.plan_distribution || {}) as Record<string, number>;
  const active = (data?.most_active_organizations || []) as Array<
    Record<string, unknown>
  >;
  const growth = (data?.growth_metrics || {}) as Record<string, unknown>;
  const storage = (data?.storage_usage || {}) as Record<string, unknown>;

  return (
    <div
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
      data-testid="saas-admin-dashboard"
    >
      <section className="rounded-md border border-[var(--border)] p-3">
        <h2 className="mb-2 text-xs font-medium uppercase text-[var(--muted)]">
          Subscription overview
        </h2>
        <ul className="space-y-1 text-sm">
          <li>Organizations: {String(overview.organizations ?? 0)}</li>
          <li>Subscriptions: {String(overview.subscriptions_tracked ?? 0)}</li>
          <li>Licenses active: {String(overview.licenses_active ?? 0)}</li>
        </ul>
      </section>

      <section className="rounded-md border border-[var(--border)] p-3">
        <h2 className="mb-2 text-xs font-medium uppercase text-[var(--muted)]">
          Revenue
        </h2>
        <p className="text-sm">
          {revenue.available
            ? `MRR ${String(revenue.mrr)}`
            : String(revenue.message || "Data unavailable.")}
        </p>
        <p className="mt-1 text-xs text-[var(--muted)]">
          {String(revenue.note || "")}
        </p>
      </section>

      <section className="rounded-md border border-[var(--border)] p-3">
        <h2 className="mb-2 text-xs font-medium uppercase text-[var(--muted)]">
          Plan distribution
        </h2>
        <ul className="space-y-1 text-sm">
          {Object.keys(planDist).length === 0 ? (
            <li className="text-xs text-[var(--muted)]">Data unavailable.</li>
          ) : (
            Object.entries(planDist).map(([k, v]) => (
              <li key={k}>
                {k}: {v}
              </li>
            ))
          )}
        </ul>
      </section>

      <section className="rounded-md border border-[var(--border)] p-3">
        <h2 className="mb-2 text-xs font-medium uppercase text-[var(--muted)]">
          Storage usage
        </h2>
        <p className="text-sm">
          {String(storage.storage_bytes ?? 0)} bytes (observed counters)
        </p>
      </section>

      <section className="rounded-md border border-[var(--border)] p-3">
        <h2 className="mb-2 text-xs font-medium uppercase text-[var(--muted)]">
          Growth metrics
        </h2>
        <ul className="space-y-1 text-sm">
          <li>Research: {String(growth.research ?? 0)}</li>
          <li>Exports: {String(growth.exports ?? 0)}</li>
          <li>API: {String(growth.api_usage ?? 0)}</li>
        </ul>
        <p className="mt-1 text-xs text-[var(--muted)]">
          {String(growth.note || "")}
        </p>
      </section>

      <section className="rounded-md border border-[var(--border)] p-3 sm:col-span-2 xl:col-span-1">
        <h2 className="mb-2 text-xs font-medium uppercase text-[var(--muted)]">
          Most active organizations
        </h2>
        <ul className="space-y-1 text-sm">
          {active.length === 0 ? (
            <li className="text-xs text-[var(--muted)]">Data unavailable.</li>
          ) : (
            active.slice(0, 5).map((o) => (
              <li key={String(o.org_id)}>
                {String(o.name || o.org_id)} · score{" "}
                {String(o.activity_score ?? 0)}
              </li>
            ))
          )}
        </ul>
      </section>
    </div>
  );
}
