"use client";

import { useMemo } from "react";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  getBuildInfo,
  getEnabledModules,
  getFeatureFlagPlaceholders,
  getRecentTimings,
  logger,
} from "@/lib/observability";
import { loadResearchSession } from "@/lib/research/sessionStore";
import { useAuth } from "@/lib/auth/AuthProvider";
import { sessionStatusLabel } from "@/lib/auth/types";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:items-center sm:justify-between">
      <dt className="text-[var(--muted)]">{label}</dt>
      <dd className="font-mono text-sm break-all">{value}</dd>
    </div>
  );
}

export function DiagnosticsDashboard() {
  const { user, session, status } = useAuth();
  const build = useMemo(() => getBuildInfo(), []);
  const modules = useMemo(() => getEnabledModules(), []);
  const flags = useMemo(() => getFeatureFlagPlaceholders(), []);
  const errors = logger.getSessionErrors();
  const timings = getRecentTimings(10);
  const researchSession = typeof window !== "undefined" ? loadResearchSession() : null;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title="Version & Build" description="Application metadata" />
        <CardBody>
          <dl className="space-y-3 text-sm">
            <Row label="Application Version" value={build.applicationVersion} />
            <Row label="Frontend Version" value={build.frontendVersion} />
            <Row label="Environment" value={build.environment} />
            <Row label="Build Timestamp" value={build.buildTimestamp} />
            <Row label="API Base URL" value={build.apiBaseUrl} />
          </dl>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Session Status" description="Current browser session" />
        <CardBody>
          <dl className="space-y-3 text-sm">
            <Row
              label="Auth Session"
              value={
                status === "loading" || status === "refreshing"
                  ? sessionStatusLabel(status)
                  : session && user
                    ? `Active (${user.displayName} · ${user.role})`
                    : sessionStatusLabel(status)
              }
            />
            <Row
              label="Research Session"
              value={
                researchSession
                  ? `${researchSession.ticker} · ${researchSession.analysedAt}`
                  : "No research session loaded"
              }
            />
          </dl>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Enabled Modules" description="Primary navigation surface" />
        <CardBody>
          <ul className="space-y-2">
            {modules.map((mod) => (
              <li
                key={mod.id}
                className="flex items-center justify-between rounded-md border border-[var(--border)] px-3 py-2 text-sm"
              >
                <span>
                  {mod.label}{" "}
                  <span className="font-mono text-xs text-[var(--muted)]">
                    {mod.route}
                  </span>
                </span>
                <Badge tone="neutral">{mod.status}</Badge>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Feature Flags"
          description="Placeholder — no remote flag service"
        />
        <CardBody>
          <ul className="space-y-2">
            {flags.map((flag) => (
              <li
                key={flag.id}
                className="flex flex-col gap-1 rounded-md border border-[var(--border)] px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="font-medium">{flag.label}</p>
                  <p className="text-xs text-[var(--muted)]">{flag.note}</p>
                </div>
                <Badge tone={flag.enabled ? "success" : "neutral"}>
                  {flag.enabled ? "On" : "Off"}
                </Badge>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Recent Client Errors"
          description="Current browser session only"
        />
        <CardBody>
          {errors.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">
              No client errors recorded in this session.
            </p>
          ) : (
            <ul className="space-y-2">
              {errors.map((err) => (
                <li
                  key={err.id}
                  className="rounded-md border border-[var(--danger-border)] bg-[var(--danger-bg)] px-3 py-2 text-sm"
                >
                  <p className="font-medium text-[var(--danger-fg)]">
                    [{err.source}] {err.message}
                  </p>
                  <p className="mt-1 font-mono text-xs text-[var(--danger-fg)]/80">
                    {err.timestamp}
                    {err.digest ? ` · digest ${err.digest}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Performance Timings"
          description="Route transitions and measured operations"
        />
        <CardBody>
          {timings.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">
              No timings recorded yet. Navigate routes or run an analysis.
            </p>
          ) : (
            <ul className="space-y-1 font-mono text-xs">
              {timings.map((timing, index) => (
                <li key={`${timing.label}-${timing.endedAt}-${index}`}>
                  {timing.label}: {Math.round(timing.durationMs)} ms
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
