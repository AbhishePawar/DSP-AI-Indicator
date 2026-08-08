"use client";

export function SaasPlanMatrix({
  data,
}: {
  data?: Record<string, unknown>;
}) {
  const plans = (data?.plans || []) as Array<Record<string, unknown>>;
  const featureKeys = (data?.feature_keys || []) as string[];

  if (plans.length === 0) {
    return (
      <p className="text-sm text-[var(--muted)]">Data unavailable.</p>
    );
  }

  return (
    <div className="overflow-x-auto" data-testid="saas-plan-matrix">
      <p className="mb-2 text-xs text-[var(--muted)]">
        {String(data?.note || "Plan matrix — packaging only.")}
      </p>
      <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-[var(--border)]">
            <th className="p-2">Feature / Limit</th>
            {plans.map((p) => (
              <th key={String(p.plan_id)} className="p-2">
                {String(p.name)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-[var(--border)]">
            <td className="p-2 text-[var(--muted)]">Seats</td>
            {plans.map((p) => {
              const limits = (p.limits || {}) as Record<string, unknown>;
              return (
                <td key={`seat-${p.plan_id}`} className="p-2">
                  {String(limits.seat_limit ?? "Custom")}
                </td>
              );
            })}
          </tr>
          <tr className="border-b border-[var(--border)]">
            <td className="p-2 text-[var(--muted)]">Trial days</td>
            {plans.map((p) => (
              <td key={`trial-${p.plan_id}`} className="p-2">
                {String(p.trial_days ?? 0)}
              </td>
            ))}
          </tr>
          {featureKeys.map((fk) => (
            <tr key={fk} className="border-b border-[var(--border)]">
              <td className="p-2 text-[var(--muted)]">{fk}</td>
              {plans.map((p) => {
                const feats = (p.features || {}) as Record<string, boolean>;
                return (
                  <td key={`${fk}-${p.plan_id}`} className="p-2">
                    {feats[fk] ? "Yes" : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
