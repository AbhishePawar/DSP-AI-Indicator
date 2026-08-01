"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ds";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { env } from "@/lib/env";
import { featureFlags } from "@/lib/featureFlags";
import {
  DashboardWidgetShell,
  WidgetError,
  WidgetLoading,
  WidgetUnavailable,
} from "../DashboardWidgetShell";

export function PlatformHealthWidget() {
  const { session } = useAuth();
  const token = session?.accessToken;

  const health = useQuery({
    queryKey: ["dashboard", "health"],
    queryFn: () => api.health({ token }),
    retry: 1,
    staleTime: 30_000,
  });
  const market = useQuery({
    queryKey: ["dashboard", "market-health"],
    queryFn: () => api.marketHealth({ token }),
    retry: 1,
    staleTime: 30_000,
    enabled: Boolean(token),
  });
  const data = useQuery({
    queryKey: ["dashboard", "data-health"],
    queryFn: () => api.dataHealth({ token }),
    retry: 1,
    staleTime: 30_000,
    enabled: Boolean(token),
  });

  return (
    <DashboardWidgetShell
      title="Platform Health"
      description="GET /api/v1/health · market/data health"
      action={
        <Link
          href="/health"
          className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Details
        </Link>
      }
    >
      {health.isLoading ? <WidgetLoading label="Loading platform health" /> : null}
      {health.isError ? (
        <WidgetError
          description={(health.error as Error).message || "Data unavailable."}
          onRetry={() => void health.refetch()}
        />
      ) : null}
      {health.data ? (
        <div className="space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={health.data.ready ? "accent" : "warning"}>
              {health.data.status}
            </Badge>
            <span className="text-[var(--muted)]">
              ready={String(health.data.ready)}
            </span>
          </div>
          <p className="text-[var(--muted)]">
            API {health.data.api_version} · platform{" "}
            {health.data.platform_version ?? "Data unavailable."}
          </p>
          <ul className="space-y-1 text-xs text-[var(--muted)]">
            <li>
              Market:{" "}
              {market.isLoading
                ? "Checking…"
                : market.isError
                  ? "Data unavailable."
                  : market.data?.ok
                    ? "OK"
                    : "Unavailable"}
            </li>
            <li>
              Data bundle:{" "}
              {data.isLoading
                ? "Checking…"
                : data.isError
                  ? "Data unavailable."
                  : data.data?.ok
                    ? "OK"
                    : "Unavailable"}
            </li>
          </ul>
        </div>
      ) : null}
    </DashboardWidgetShell>
  );
}

export function ApiStatusWidget() {
  const { session } = useAuth();
  const token = session?.accessToken;

  const health = useQuery({
    queryKey: ["dashboard", "api-health"],
    queryFn: () => api.health({ token }),
    retry: 1,
    staleTime: 30_000,
  });
  const version = useQuery({
    queryKey: ["dashboard", "version"],
    queryFn: () => api.version({ token }),
    retry: 1,
    staleTime: 60_000,
  });
  const capabilities = useQuery({
    queryKey: ["dashboard", "capabilities"],
    queryFn: () => api.capabilities({ token }),
    retry: 1,
    staleTime: 60_000,
  });

  const ready = health.data?.ready;
  const envLabel =
    env.environment === "production"
      ? "PROD"
      : env.environment === "test"
        ? "TEST"
        : "DEV";

  return (
    <DashboardWidgetShell
      title="API Status"
      description="UI status strip over frozen /api/v1 probes"
    >
      {health.isLoading || version.isLoading ? (
        <WidgetLoading label="Loading API status" />
      ) : null}
      {health.isError ? (
        <WidgetError
          description="Data unavailable."
          onRetry={() => void health.refetch()}
        />
      ) : (
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between gap-3">
            <dt className="text-[var(--muted)]">Connection</dt>
            <dd className="flex items-center gap-2 font-medium">
              <span
                className={`terminal-dot${ready === false ? " terminal-dot--danger" : ready === undefined ? " terminal-dot--warn" : ""}`}
                aria-hidden
              />
              {ready === undefined
                ? "Checking…"
                : ready
                  ? "Connected"
                  : "Unavailable"}
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-[var(--muted)]">Environment</dt>
            <dd>
              <Badge variant="outline" className="font-mono text-[10px]">
                {envLabel}
              </Badge>
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-[var(--muted)]">Foundation</dt>
            <dd className="font-mono text-xs">v{env.foundationVersion}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-[var(--muted)]">Platform</dt>
            <dd className="font-mono text-xs">
              {version.data?.platform_version ?? "Data unavailable."}
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-[var(--muted)]">Pipeline</dt>
            <dd className="font-mono text-xs">
              {version.data?.pipeline_version ?? "Data unavailable."}
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-[var(--muted)]">Capabilities</dt>
            <dd className="font-mono text-xs">
              {capabilities.isError
                ? "Data unavailable."
                : capabilities.data
                  ? "Loaded"
                  : capabilities.isLoading
                    ? "Loading…"
                    : "Data unavailable."}
            </dd>
          </div>
        </dl>
      )}
    </DashboardWidgetShell>
  );
}

export function BackgroundJobsWidget() {
  return (
    <DashboardWidgetShell
      title="Background Jobs"
      description="UI only — no jobs status endpoint in frozen client"
    >
      <WidgetUnavailable description="Data unavailable. Job status will appear when a certified jobs API is exposed." />
    </DashboardWidgetShell>
  );
}

export function CommitteeActivityWidget() {
  return (
    <DashboardWidgetShell
      title="Recent AI Committee Decisions"
      description="No AI committee list API in thin client"
    >
      <WidgetUnavailable
        description="Data unavailable. Open Copilot or Research for explainability surfaces."
        href="/copilot"
        actionLabel="Open Copilot"
      />
    </DashboardWidgetShell>
  );
}

export function ComplianceSummaryWidget() {
  return (
    <DashboardWidgetShell
      title="Compliance Summary"
      description="Feature-flag presentation only — not a compliance engine"
    >
      <ul className="space-y-2 text-sm">
        <li className="flex justify-between gap-2">
          <span className="text-[var(--muted)]">Research Mode</span>
          <Badge variant={featureFlags.researchMode ? "accent" : "outline"}>
            {featureFlags.researchMode ? "On" : "Off"}
          </Badge>
        </li>
        <li className="flex justify-between gap-2">
          <span className="text-[var(--muted)]">Recommendation Mode</span>
          <Badge variant="outline">
            {featureFlags.recommendationMode ? "On" : "Off"}
          </Badge>
        </li>
        <li className="flex justify-between gap-2">
          <span className="text-[var(--muted)]">SEBI Mode</span>
          <Badge variant="outline">
            {featureFlags.sebiMode ? "On" : "Off"}
          </Badge>
        </li>
      </ul>
      <p className="mt-3 text-xs text-[var(--muted)]">
        Enforcement remains on the backend. This widget does not invent compliance
        outcomes.
      </p>
    </DashboardWidgetShell>
  );
}

export function WorkflowSummaryWidget() {
  return (
    <DashboardWidgetShell
      title="Workflow Summary"
      description="No workflow list endpoint in frozen /api/v1 client"
    >
      <WidgetUnavailable
        description="Data unavailable. Workflow queues will surface when admin workflow APIs are consumed in a later epic."
        href="/admin"
        actionLabel="Administration"
      />
    </DashboardWidgetShell>
  );
}

export function CopilotActivityWidget() {
  const { session } = useAuth();
  const token = session?.accessToken;

  const providers = useQuery({
    queryKey: ["dashboard", "copilot-providers"],
    queryFn: () => api.copilotProviders({ token }),
    retry: 1,
    staleTime: 60_000,
    enabled: Boolean(token),
  });

  return (
    <DashboardWidgetShell
      title="Copilot Activity"
      description="GET /api/v1/copilot/providers"
      action={
        <Link
          href="/copilot"
          className="text-xs text-[var(--accent)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          Copilot
        </Link>
      }
    >
      {!token ? (
        <WidgetUnavailable
          description="Sign in to load Copilot providers."
          href="/login"
          actionLabel="Sign in"
        />
      ) : null}
      {token && providers.isLoading ? (
        <WidgetLoading label="Loading Copilot providers" />
      ) : null}
      {token && providers.isError ? (
        <WidgetError
          description="Data unavailable."
          onRetry={() => void providers.refetch()}
        />
      ) : null}
      {token && providers.data ? (
        <div className="space-y-2 text-sm">
          <p>
            Providers:{" "}
            <span className="font-medium">
              {Array.isArray(providers.data.providers)
                ? providers.data.providers.length
                : "Data unavailable."}
            </span>
          </p>
          <p className="text-xs text-[var(--muted)]">
            Session activity history is not exposed by this endpoint.
          </p>
        </div>
      ) : null}
    </DashboardWidgetShell>
  );
}
