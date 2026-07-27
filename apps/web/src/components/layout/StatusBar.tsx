"use client";

import { SyncStatusBadge } from "@/components/persistence/SyncStatusBadge";
import { api } from "@/lib/api/client";
import { env } from "@/lib/env";
import { useAuth } from "@/lib/auth/AuthProvider";
import { usePersistence } from "@/providers/PersistenceProvider";
import { useQuery } from "@tanstack/react-query";
export function StatusBar() {
  const { session, status } = useAuth();
  const { syncStatus, lastSyncedAt } = usePersistence();
  const healthQuery = useQuery({
    queryKey: ["terminal", "health"],
    queryFn: () => api.health({ token: session?.accessToken }),
    retry: 1,
    staleTime: 30_000,
  });

  const ready = healthQuery.data?.ready;
  const platformVersion = healthQuery.data?.platform_version;

  return (
    <footer
      className="flex items-center justify-between border-t border-[var(--border)] bg-[var(--status-bg,var(--surface))] px-3 py-1.5 text-[10px] text-[var(--muted)] font-mono"
      role="contentinfo"
      aria-label="Status bar"
    >
      <div className="flex items-center gap-4">
        <span>
          <span
            className={`terminal-dot${ready === false ? " terminal-dot--danger" : ""}`}
            aria-hidden
          />{" "}
          {ready === undefined
            ? "Checking…"
            : ready
              ? "API Connected"
              : "API Unavailable"}
        </span>
        <span>Frontend v{env.frontendVersion}</span>
        {platformVersion ? <span>Backend v{platformVersion}</span> : null}
      </div>
      <div className="flex items-center gap-4">
        {status === "authenticated" ? (
          <SyncStatusBadge status={syncStatus} lastSyncedAt={lastSyncedAt} />
        ) : null}
        <span>© {new Date().getFullYear()} DSP AI Indicator</span>
      </div>
    </footer>
  );
}
