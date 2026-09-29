"use client";

/**
 * Figma `Diagnostics.tsx` — overall status banner · "Service Status" rows ·
 * "System Logs" console with Refresh.
 *
 * Data: `GET /api/v1/health` (platform checks, components, limitations) for
 * service status; the log console shows this browser session's client log
 * buffer (`logger.getRecentLogs`) — labelled as such. Server logs are not
 * exposed to the browser. Latencies shown are measured round-trips of the
 * health probe, never invented.
 */

import { useQuery } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { FigmaPage, Panel, PanelEmpty } from "@/components/pages/PagePrimitives";
import { api } from "@/lib/api/client";
import type { HealthResponse } from "@/lib/api/types";
import { logger, type LogEntry } from "@/lib/observability";

const QUERY_KEY = ["health", "diagnostics"] as const;

type Tone = "pass" | "warn" | "fail" | "unknown";

export function toneOf(status: string | undefined): Tone {
  const s = (status ?? "").toLowerCase();
  if (["pass", "ok", "ready", "healthy", "up", "available", "operational"].includes(s)) return "pass";
  if (["warn", "degraded", "skip", "fallback", "partial", "startup"].includes(s)) return "warn";
  if (["fail", "error", "unhealthy", "down", "unavailable"].includes(s)) return "fail";
  return "unknown";
}

const TONE_COLOR: Record<Tone, string> = {
  pass: "var(--c-profit)",
  warn: "var(--c-risk)",
  fail: "var(--danger-fg)",
  unknown: "var(--muted)",
};
const TONE_LABEL: Record<Tone, string> = {
  pass: "Operational",
  warn: "Degraded",
  fail: "Failing",
  unknown: "Unknown",
};

type ServiceRow = { name: string; status: string; message: string };

export function serviceRows(health: HealthResponse | undefined): ServiceRow[] {
  if (!health) return [];
  const rows: ServiceRow[] = health.checks.map((c) => ({ name: c.name, status: c.status, message: c.message }));
  const components = health.components ?? {};
  for (const [name, raw] of Object.entries(components)) {
    if (rows.some((r) => r.name === name)) continue;
    if (raw && typeof raw === "object") {
      const obj = raw as Record<string, unknown>;
      rows.push({
        name,
        status: String(obj.status ?? obj.state ?? "unknown"),
        message: String(obj.message ?? obj.detail ?? obj.reason ?? ""),
      });
    } else {
      rows.push({ name, status: String(raw ?? "unknown"), message: "" });
    }
  }
  return rows;
}

function humanise(name: string): string {
  return name.replace(/[_-]+/g, " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function levelColor(level: LogEntry["level"]): string {
  if (level === "error") return "var(--danger-fg)";
  if (level === "warn") return "var(--c-risk)";
  return "var(--c-profit)";
}

export function DiagnosticsStatus() {
  const [logs, setLogs] = useState<LogEntry[]>(() => logger.getRecentLogs(50));
  const refreshLogs = useCallback(() => setLogs(logger.getRecentLogs(50)), []);

  const healthQuery = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const started = performance.now();
      const data = await api.health();
      return { data, latencyMs: Math.round(performance.now() - started), at: new Date() };
    },
    retry: false,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  const health = healthQuery.data?.data;
  const rows = serviceRows(health);
  const overall: Tone = healthQuery.isError
    ? "fail"
    : health
      ? toneOf(health.platform_status ?? (health.ready ? "ready" : "fail"))
      : "unknown";
  const failing = rows.filter((r) => toneOf(r.status) === "fail").map((r) => humanise(r.name));
  const degraded = rows.filter((r) => toneOf(r.status) === "warn").map((r) => humanise(r.name));

  const overallText = healthQuery.isPending
    ? "Checking platform health…"
    : healthQuery.isError
      ? `API unreachable — ${healthQuery.error instanceof Error ? healthQuery.error.message : "health probe failed"}.`
      : overall === "pass"
        ? "All checked services operational."
        : failing.length
          ? `Service failure — ${failing.join(", ")}.`
          : degraded.length
            ? `Partial degradation — ${degraded.join(", ")}.`
            : `Platform status: ${health?.platform_status ?? health?.status ?? "unknown"}.`;

  return (
    <FigmaPage
      title="Diagnostics"
      subtitle="System health · Service status · Logs"
      actions={
        <button
          type="button"
          onClick={() => {
            void healthQuery.refetch();
            refreshLogs();
          }}
          disabled={healthQuery.isFetching}
          className="min-h-9 rounded-lg border border-[var(--border)] px-3.5 font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)] hover:text-[var(--fg)] disabled:opacity-50"
        >
          {healthQuery.isFetching ? "Refreshing…" : "Refresh"}
        </button>
      }
    >
      <div
        role="status"
        aria-live="polite"
        className="flex flex-wrap items-center gap-3 rounded-xl border px-5 py-4"
        style={{
          borderColor: `color-mix(in srgb, ${TONE_COLOR[overall]} 20%, transparent)`,
          background: `color-mix(in srgb, ${TONE_COLOR[overall]} 6%, transparent)`,
        }}
      >
        <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: TONE_COLOR[overall] }} aria-hidden="true" />
        <span className="text-sm text-[var(--fg)]">{overallText}</span>
        <span className="ml-auto font-[family-name:var(--font-mono)] text-xs text-[var(--muted)]">
          {healthQuery.data
            ? `${healthQuery.data.at.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })} · probe ${healthQuery.data.latencyMs}ms`
            : "—"}
        </span>
      </div>

      <Panel title="Service Status">
        {healthQuery.isPending ? (
          <PanelEmpty title="Loading service checks…" />
        ) : healthQuery.isError ? (
          <PanelEmpty title="Service status unavailable." description="The health endpoint did not respond. Check the API base URL and backend process." />
        ) : rows.length === 0 ? (
          <PanelEmpty title="No service checks reported." />
        ) : (
          <ul>
            {rows.map((r, i) => {
              const tone = toneOf(r.status);
              return (
                <li key={r.name} className={`flex flex-wrap items-center gap-3.5 px-5 py-3.5 ${i < rows.length - 1 ? "border-b border-[var(--border)]" : ""}`}>
                  <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: TONE_COLOR[tone] }} aria-hidden="true" />
                  <span className="min-w-[160px] flex-1 text-[13px] text-[var(--fg)]">{humanise(r.name)}</span>
                  <span className="w-[100px] font-[family-name:var(--font-mono)] text-xs" style={{ color: TONE_COLOR[tone] }}>
                    {TONE_LABEL[tone]}
                    <span className="sr-only"> ({r.status})</span>
                  </span>
                  <span className="basis-full truncate font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)] sm:basis-auto sm:max-w-[40%]" title={r.message}>
                    {r.message || r.status}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
        {health?.limitations?.length ? (
          <div className="border-t border-[var(--border)] px-5 py-3">
            <p className="mb-1 font-[family-name:var(--font-mono)] text-[10px] uppercase tracking-[0.06em] text-[var(--muted)]">Limitations</p>
            <ul className="list-disc space-y-0.5 pl-4 text-xs text-[var(--muted)]">
              {health.limitations.map((l) => <li key={l}>{l}</li>)}
            </ul>
          </div>
        ) : null}
        {health ? (
          <p className="border-t border-[var(--border)] px-5 py-2.5 font-[family-name:var(--font-mono)] text-[10px] text-[var(--muted)]">
            API {health.api_version} · platform {health.platform_version ?? "—"} · pipeline {health.pipeline_version ?? "—"}
          </p>
        ) : null}
      </Panel>

      <Panel
        title="System Logs (this browser session)"
        action={
          <button type="button" onClick={refreshLogs} className="rounded-md border border-[var(--border)] px-2.5 py-1 font-[family-name:var(--font-mono)] text-[11px] text-[var(--muted)] hover:text-[var(--fg)]">
            Refresh
          </button>
        }
      >
        <div className="bg-[#06080e] px-5 py-4 font-[family-name:var(--font-mono)] text-xs" role="log" aria-label="Client session logs">
          {logs.length === 0 ? (
            <p className="text-[var(--muted)]">No client log entries recorded in this session yet.</p>
          ) : (
            logs.map((entry) => (
              <div key={entry.id} className="mb-2 flex gap-3 leading-relaxed">
                <span className="shrink-0 text-[var(--muted)]">{new Date(entry.timestamp).toLocaleTimeString("en-IN", { hour12: false })}</span>
                <span className="w-11 shrink-0 uppercase" style={{ color: levelColor(entry.level) }}>{entry.level}</span>
                <span className="break-words text-[var(--fg)]">{entry.message}</span>
              </div>
            ))
          )}
        </div>
        <p className="border-t border-[var(--border)] px-5 py-2.5 text-[11px] text-[var(--muted)]">
          Server-side logs are available to operators through the ops console; they are not exposed to the browser.
        </p>
      </Panel>
    </FigmaPage>
  );
}
