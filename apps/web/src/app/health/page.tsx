"use client";

import { useQuery } from "@tanstack/react-query";

import { LoadingBlock } from "@/components/LoadingBlock";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";

export default function HealthPage() {
  const { session } = useAuth();
  const query = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health({ token: session?.accessToken }),
  });

  return (
    <div>
      <PageHeader
        title="Health Status"
        description="Operational readiness from the API platform. This page never runs analysis."
      />
      {query.isLoading ? <LoadingBlock /> : null}
      {query.isError ? (
        <p className="text-sm text-[var(--danger-fg)]">
          {(query.error as Error).message}
        </p>
      ) : null}
      {query.data ? (
        <div className="space-y-4">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
            <p className="text-sm text-[var(--muted)]">Overall</p>
            <p className="mt-1 font-[family-name:var(--font-display)] text-2xl">
              {query.data.status} · ready={String(query.data.ready)}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">
              API {query.data.api_version} · platform{" "}
              {query.data.platform_version ?? "n/a"}
            </p>
          </div>
          <ul className="space-y-2">
            {query.data.checks.map((check) => (
              <li
                key={check.name}
                className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm"
              >
                <span className="font-medium">{check.name}</span>{" "}
                <span className="text-[var(--muted)]">· {check.status}</span>
                <p className="mt-1 text-[var(--muted)]">{check.message}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
