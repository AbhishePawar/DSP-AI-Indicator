"use client";

import { LegalNavLinks } from "@/components/legal/LegalNavLinks";
import { SyncStatusBadge } from "@/components/persistence/SyncStatusBadge";
import { Badge } from "@/components/ds";
import { api } from "@/lib/api/client";
import { env } from "@/lib/env";
import { useAuth } from "@/lib/auth/AuthProvider";
import { resolveShellAudience } from "@/lib/shell";
import { usePersistence } from "@/providers/PersistenceProvider";
import { useQuery } from "@tanstack/react-query";

const LEGAL_DISCLAIMER = "Research tools — not investment advice";

function OrdinaryFooter() {
  return (
    <footer
      className="border-t border-[var(--border)] bg-[var(--surface)] px-4 py-5 sm:px-6"
      role="contentinfo"
      aria-label="Site footer"
    >
      <div className="mx-auto flex max-w-3xl flex-col items-center gap-3 text-center">
        <p className="font-[family-name:var(--font-display)] text-sm tracking-tight text-[var(--fg)]">
          {env.appName}
        </p>
        <LegalNavLinks density="footer" className="justify-center text-xs" />
        <p className="text-xs text-[var(--muted)]">{LEGAL_DISCLAIMER}</p>
        <p className="text-xs text-[var(--muted)]">
          © {new Date().getFullYear()} {env.appName}
        </p>
      </div>
    </footer>
  );
}

/** Application footer. Ordinary clients get policy links only — no diagnostics. */
export function StatusBar() {
  const { session, status, user } = useAuth();
  const permissions = session?.permissions ?? user?.permissions ?? [];
  const roles = session?.roles ?? user?.roles ?? [];
  const audience = resolveShellAudience(permissions, roles);
  const ordinary = audience === "ordinary";
  const { syncStatus, lastSyncedAt } = usePersistence();
  const healthQuery = useQuery({
    queryKey: ["terminal", "health"],
    queryFn: () => api.health({ token: session?.accessToken }),
    retry: 1,
    staleTime: 30_000,
    enabled: !ordinary,
  });

  if (ordinary) {
    return <OrdinaryFooter />;
  }

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
          {LEGAL_DISCLAIMER}
        </span>
        <LegalNavLinks density="footer" />
        <span>© {new Date().getFullYear()} DSP AI Indicator</span>
      </div>
    </footer>
  );
}
