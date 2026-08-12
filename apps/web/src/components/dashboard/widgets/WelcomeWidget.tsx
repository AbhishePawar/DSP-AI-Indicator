"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { Badge, Button } from "@/components/ds";
import { useAuth } from "@/lib/auth/AuthProvider";
import { rbacAuthApi } from "@/lib/api/rbacAuth";
import { env } from "@/lib/env";
import { useUiStore } from "@/lib/shell";
import { DashboardWidgetShell } from "../DashboardWidgetShell";

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "Data unavailable.";
  const ms = Date.parse(iso);
  if (Number.isNaN(ms)) return "Data unavailable.";
  return new Date(ms).toLocaleString();
}

export function WelcomeWidget() {
  const { user, session, status } = useAuth();
  const setCommandOpen = useUiStore((s) => s.setCommandPaletteOpen);
  const token = session?.accessToken;

  const meQuery = useQuery({
    queryKey: ["dashboard", "rbac-me"],
    queryFn: () => rbacAuthApi.me(token!),
    enabled: Boolean(token),
    retry: false,
    staleTime: 60_000,
  });

  const name = user?.displayName || session?.displayName || "Analyst";
  const lastLogin =
    meQuery.data?.ok && meQuery.data.result
      ? meQuery.data.result.last_login
      : null;
  const envLabel =
    env.environment === "production"
      ? "PROD"
      : env.environment === "test"
        ? "TEST"
        : "DEV";

  return (
    <DashboardWidgetShell
      title={`Welcome, ${name}`}
      description="Institutional overview — research tools, not investment advice."
      span={2}
      action={
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="accent" className="font-mono text-[10px]">
            v{env.foundationVersion}
          </Badge>
          <Badge variant="outline" className="font-mono text-[10px]">
            {envLabel}
          </Badge>
        </div>
      }
    >
      <dl className="grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-[var(--muted)]">Role</dt>
          <dd className="mt-0.5 font-medium">
            {user?.role || session?.role || "Data unavailable."}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-[var(--muted)]">Last login</dt>
          <dd className="mt-0.5 font-medium">
            {meQuery.isLoading
              ? "Loading…"
              : meQuery.isError
                ? "Data unavailable."
                : formatWhen(lastLogin)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-[var(--muted)]">Session</dt>
          <dd className="mt-0.5 font-medium">
            {status === "authenticated"
              ? `Issued ${formatWhen(session?.issuedAt)}`
              : status}
          </dd>
        </div>
      </dl>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="sm" onClick={() => setCommandOpen(true)}>
          Search (Ctrl+K)
        </Button>
        <Link href="/docs/quick-start">
          <Button size="sm" variant="secondary">
            Quick start
          </Button>
        </Link>
        <Link href="/docs/support">
          <Button size="sm" variant="secondary">
            Support
          </Button>
        </Link>
        <Link href="/profile">
          <Button size="sm" variant="secondary">
            Profile
          </Button>
        </Link>
        <Link href="/settings">
          <Button size="sm" variant="secondary">
            Settings
          </Button>
        </Link>
      </div>
    </DashboardWidgetShell>
  );
}
