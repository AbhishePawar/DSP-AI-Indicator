"use client";

import Link from "next/link";

import { SyncStatusBadge } from "@/components/persistence/SyncStatusBadge";
import { LegalNavLinks } from "@/components/legal/LegalNavLinks";
import { Badge } from "@/components/ds";
import { api } from "@/lib/api/client";
import { env } from "@/lib/env";
import { LEGAL_ROUTES } from "@/lib/legal";
import { useAuth } from "@/lib/auth/AuthProvider";
import { usePersistence } from "@/providers/PersistenceProvider";
import { useQuery } from "@tanstack/react-query";

/** Application footer / status bar — F003 + P4.1 legal links. */
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
  const envLabel =
    env.environment === "production"
      ? "PROD"
      : env.environment === "test"
        ? "TEST"
        : "DEV";

  return (
    <footer
      className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--border)] bg-[var(--status-bg,var(--surface))] px-3 py-1.5 text-[10px] text-[var(--muted)] font-mono"
      role="contentinfo"
      aria-label="Status bar"
    >
      <div className="flex flex-wrap items-center gap-3">
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
        <Badge variant="outline" className="font-mono text-[10px]">
          FE v{env.frontendVersion}
        </Badge>
        <Badge variant="accent" className="font-mono text-[10px]">
          Foundation v{env.foundationVersion}
        </Badge>
        {platformVersion ? (
          <span>Backend v{platformVersion}</span>
        ) : null}
        <Badge variant="outline" className="font-mono text-[10px]">
          {envLabel}
        </Badge>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {status === "authenticated" ? (
          <SyncStatusBadge status={syncStatus} lastSyncedAt={lastSyncedAt} />
        ) : null}
        <span className="max-w-[14rem] truncate sm:max-w-none">
          Research tools — not investment advice
        </span>
        <LegalNavLinks density="footer" />
        <Link
          href={LEGAL_ROUTES.docsIndex}
          className="text-[10px] underline-offset-2 hover:underline hover:text-[var(--fg)]"
        >
          Docs
        </Link>
        <span>© {new Date().getFullYear()} DSP AI Indicator</span>
      </div>
    </footer>
  );
}
