"use client";

import { useQuery } from "@tanstack/react-query";

import { LoadingBlock } from "@/components/LoadingBlock";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";

export default function PlatformPage() {
  const { session } = useAuth();
  const query = useQuery({
    queryKey: ["platform"],
    queryFn: () => api.platform({ token: session?.accessToken }),
  });

  return (
    <div>
      <PageHeader
        title="Platform Information"
        description="Immutable metadata and capability discovery from the DSP Platform façade via HTTP."
      />
      {query.isLoading ? <LoadingBlock /> : null}
      {query.isError ? (
        <p className="text-sm text-[var(--danger-fg)]">
          {(query.error as Error).message}
        </p>
      ) : null}
      {query.data ? (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
            <h2 className="font-[family-name:var(--font-display)] text-2xl">
              {query.data.name}
            </h2>
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--muted)]">Version</dt>
                <dd>{query.data.version}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--muted)]">Status</dt>
                <dd>{query.data.status}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--muted)]">Environment</dt>
                <dd>{query.data.environment}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--muted)]">Generated</dt>
                <dd>{new Date(query.data.generated_at).toLocaleString()}</dd>
              </div>
            </dl>
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
            <h3 className="text-sm font-medium text-[var(--muted)]">
              Capabilities
            </h3>
            <ul className="mt-3 flex flex-wrap gap-2">
              {query.data.capabilities.map((cap) => (
                <li
                  key={cap}
                  className="rounded-md bg-[var(--accent-soft)] px-2 py-1 text-xs text-[var(--accent)]"
                >
                  {cap}
                </li>
              ))}
            </ul>
            <h3 className="mt-6 text-sm font-medium text-[var(--muted)]">
              Services
            </h3>
            <ul className="mt-3 space-y-1 text-sm">
              {query.data.registered_services.map((svc) => (
                <li key={svc}>{svc}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}
    </div>
  );
}
