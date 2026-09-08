"use client";

import { useState, useEffect, useCallback } from "react";
import React from "react";
import Link from "next/link";
import {
  Bell,
  TrendingUp,
  Clock,
  Activity,
  CheckCircle2,
  AlertCircle,
  ArrowUpRight,
  ArrowDownRight,
  Eye,
  Search,
  Zap,
} from "lucide-react";

import {
  getActiveAlertRules,
  getMetricThresholds,
  getRecentTriggers,
  getAlertsPerformanceSummary,
  type UserAlert,
  type MetricThreshold,
  type AlertTrigger,
  type AlertsPerformanceSummary,
} from "@/lib/alerts/alertsService";
import { useAuth } from "@/lib/auth/AuthProvider";

/* ─── Shared primitives ──────────────────────────────────────────────────── */

function SectionHeader({
  icon: Icon,
  title,
  count,
}: {
  icon: React.ElementType;
  title: string;
  count?: number;
}) {
  return (
    <div className="mb-5 flex items-center gap-3 border-b border-[var(--border)] pb-3">
      <Icon className="size-5 text-[var(--accent)] shrink-0" aria-hidden />
      <h2 className="font-[family-name:var(--font-display)] text-lg tracking-tight text-[var(--fg)]">
        {title}
      </h2>
      {count !== undefined && (
        <span className="ml-auto rounded-full bg-[var(--surface-2)] px-2 py-0.5 font-mono text-xs text-[var(--muted)]">
          {count}
        </span>
      )}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded border border-dashed border-[var(--border)] px-4 py-8 text-center">
      <p className="text-sm text-[var(--muted)]">{message}</p>
    </div>
  );
}

function SkeletonRows({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="h-14 animate-pulse rounded border border-[var(--border)] bg-[var(--surface-2)]"
        />
      ))}
    </div>
  );
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest",
        active
          ? "bg-emerald-500/10 text-emerald-400" :"bg-[var(--surface-2)] text-[var(--muted)]",
      ].join(" ")}
    >
      {active ? (
        <CheckCircle2 className="size-3" />
      ) : (
        <AlertCircle className="size-3" />
      )}
      {active ? "Active" : "Paused"}
    </span>
  );
}

function AlertTypeBadge({ type }: { type: UserAlert["alertType"] }) {
  const map: Record<UserAlert["alertType"], { label: string; icon: React.ElementType }> = {
    metric_threshold: { label: "Threshold", icon: TrendingUp },
    saved_search: { label: "Search", icon: Search },
    watchlist: { label: "Watchlist", icon: Eye },
  };
  const { label, icon: Icon } = map[type] ?? { label: type, icon: Bell };
  return (
    <span className="inline-flex items-center gap-1 rounded bg-[var(--surface)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--muted)]">
      <Icon className="size-3" aria-hidden />
      {label}
    </span>
  );
}

/* ─── Performance Summary ────────────────────────────────────────────────── */

function PerformanceSummarySection() {
  const [summary, setSummary] = useState<AlertsPerformanceSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAlertsPerformanceSummary()
      .then(setSummary)
      .finally(() => setLoading(false));
  }, []);

  const stats = summary
    ? [
        {
          label: "Active Rules",
          value: summary.totalActive,
          sub: `${summary.totalPaused} paused`,
          icon: CheckCircle2,
          accent: true,
        },
        {
          label: "Triggers (30d)",
          value: summary.totalTriggersLast30Days,
          sub: `${summary.totalTriggersLast7Days} this week`,
          icon: Zap,
          accent: false,
        },
        {
          label: "Top Ticker",
          value: summary.mostTriggeredTicker ?? "—",
          sub: "most triggered",
          icon: Activity,
          accent: false,
        },
        {
          label: "Watchlist",
          value: summary.watchlistCount,
          sub: "tickers tracked",
          icon: Eye,
          accent: false,
        },
      ]
    : [];

  return (
    <section>
      <SectionHeader icon={Activity} title="Performance Summary" />
      {loading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-20 animate-pulse rounded border border-[var(--border)] bg-[var(--surface-2)]"
            />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.label}
                className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3"
              >
                <div className="mb-1 flex items-center gap-1.5">
                  <Icon
                    className={[
                      "size-3.5 shrink-0",
                      stat.accent ? "text-[var(--accent)]" : "text-[var(--muted)]",
                    ].join(" ")}
                    aria-hidden
                  />
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                    {stat.label}
                  </span>
                </div>
                <p
                  className={[
                    "font-[family-name:var(--font-display)] text-2xl font-bold tracking-tight",
                    stat.accent ? "text-[var(--accent)]" : "text-[var(--fg)]",
                  ].join(" ")}
                >
                  {stat.value}
                </p>
                <p className="mt-0.5 text-[10px] text-[var(--muted)]">{stat.sub}</p>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

/* ─── Active Alert Rules ─────────────────────────────────────────────────── */

function ActiveAlertRulesSection() {
  const [alerts, setAlerts] = useState<UserAlert[]>([]);
  const [thresholds, setThresholds] = useState<MetricThreshold[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const [alertsData, thresholdsData] = await Promise.all([
      getActiveAlertRules(),
      getMetricThresholds(),
    ]);
    setAlerts(alertsData);
    setThresholds(thresholdsData);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const thresholdByAlertId = Object.fromEntries(
    thresholds.map((t) => [t.alertId, t])
  );

  return (
    <section>
      <SectionHeader
        icon={Bell}
        title="Active Alert Rules"
        count={alerts.filter((a) => a.isActive).length}
      />

      {loading ? (
        <SkeletonRows count={3} />
      ) : alerts.length === 0 ? (
        <EmptyState message="No alert rules configured. Create thresholds or saved searches to monitor tickers." />
      ) : (
        <ul className="space-y-2">
          {alerts.map((alert) => {
            const threshold = thresholdByAlertId[alert.id];
            return (
              <li
                key={alert.id}
                className="flex items-start gap-3 rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <AlertTypeBadge type={alert.alertType} />
                    <span className="text-sm font-medium text-[var(--fg)]">
                      {alert.name}
                    </span>
                    <StatusBadge active={alert.isActive} />
                  </div>

                  {threshold && (
                    <div className="mt-1.5 flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-[var(--accent)]">
                        {threshold.ticker}
                      </span>
                      <span className="text-xs text-[var(--muted)]">
                        {threshold.metricLabel}
                      </span>
                      <span
                        className={[
                          "inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold",
                          threshold.direction === "above" ?"bg-emerald-500/10 text-emerald-400" :"bg-red-500/10 text-red-400",
                        ].join(" ")}
                      >
                        {threshold.direction === "above" ? (
                          <ArrowUpRight className="size-3" aria-hidden />
                        ) : (
                          <ArrowDownRight className="size-3" aria-hidden />
                        )}
                        {threshold.direction === "above" ? "above" : "below"}{" "}
                        {threshold.thresholdValue}
                      </span>
                      {threshold.lastTriggeredAt && (
                        <span className="text-[10px] text-[var(--muted)]">
                          Last fired{" "}
                          {new Date(threshold.lastTriggeredAt).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  )}

                  {alert.description && !threshold && (
                    <p className="mt-1 text-xs text-[var(--muted)]">
                      {alert.description}
                    </p>
                  )}
                </div>

                <div className="shrink-0 text-[10px] text-[var(--muted)]">
                  {new Date(alert.createdAt).toLocaleDateString()}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

/* ─── Recent Triggers ────────────────────────────────────────────────────── */

function RecentTriggersSection() {
  const [triggers, setTriggers] = useState<AlertTrigger[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRecentTriggers(15)
      .then(setTriggers)
      .finally(() => setLoading(false));
  }, []);

  function formatRelative(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  }

  return (
    <section>
      <SectionHeader
        icon={Clock}
        title="Recent Triggers"
        count={triggers.length}
      />

      {loading ? (
        <SkeletonRows count={4} />
      ) : triggers.length === 0 ? (
        <EmptyState message="No triggers recorded yet. Alerts will appear here when thresholds are crossed." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="pb-2 pr-4 text-left text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                  Ticker
                </th>
                <th className="pb-2 pr-4 text-left text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                  Metric
                </th>
                <th className="pb-2 pr-4 text-left text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                  Threshold
                </th>
                <th className="pb-2 pr-4 text-left text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                  Triggered
                </th>
                <th className="pb-2 text-left text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                  When
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {triggers.map((trigger) => (
                <tr key={trigger.id} className="group">
                  <td className="py-2.5 pr-4">
                    <Link
                      href={`/analysis?symbol=${trigger.ticker}`}
                      className="font-mono text-sm font-bold text-[var(--accent)] hover:underline"
                    >
                      {trigger.ticker}
                    </Link>
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-[var(--fg)]">
                    {trigger.metricLabel ?? "—"}
                  </td>
                  <td className="py-2.5 pr-4">
                    {trigger.thresholdValue != null && trigger.direction ? (
                      <span
                        className={[
                          "inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold",
                          trigger.direction === "above" ?"bg-emerald-500/10 text-emerald-400" :"bg-red-500/10 text-red-400",
                        ].join(" ")}
                      >
                        {trigger.direction === "above" ? (
                          <ArrowUpRight className="size-3" aria-hidden />
                        ) : (
                          <ArrowDownRight className="size-3" aria-hidden />
                        )}
                        {trigger.direction} {trigger.thresholdValue}
                        {trigger.triggeredValue != null && (
                          <span className="ml-1 opacity-70">
                            → {trigger.triggeredValue}
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-xs text-[var(--muted)]">—</span>
                    )}
                  </td>
                  <td className="py-2.5 pr-4">
                    <span
                      className={[
                        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest",
                        trigger.status === "fired" ?"bg-amber-500/10 text-amber-400" :"bg-[var(--surface-2)] text-[var(--muted)]",
                      ].join(" ")}
                    >
                      <Zap className="size-3" aria-hidden />
                      {trigger.status}
                    </span>
                  </td>
                  <td className="py-2.5 text-xs text-[var(--muted)]">
                    {formatRelative(trigger.triggeredAt)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/* ─── Auth gate ──────────────────────────────────────────────────────────── */

function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, status } = useAuth();
  const loading =
    status === "restoring" || status === "loading" || status === "refreshing";

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-32 animate-pulse rounded border border-[var(--border)] bg-[var(--surface-2)]"
          />
        ))}
      </div>
    );
  }

  if (!user) {
    return (
      <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-6 py-10 text-center">
        <Bell className="mx-auto mb-3 size-8 text-[var(--muted)]" aria-hidden />
        <p className="text-sm text-[var(--fg)]">
          Sign in to view your alerts and monitoring rules.
        </p>
        <Link
          href="/login"
          className="mt-4 inline-block rounded bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
        >
          Sign in
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}

/* ─── Page ───────────────────────────────────────────────────────────────── */

export default function AlertsPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Page header */}
      <div className="mb-8 border-b border-[var(--border)] pb-6">
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">
          DSP AI Indicator
        </p>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Bell className="size-7 text-[var(--accent)] shrink-0" aria-hidden />
            <h1 className="font-[family-name:var(--font-display)] text-3xl tracking-tight text-[var(--fg)]">
              Alerts
            </h1>
          </div>
          <Link
            href="/alerts/manage"
            className="inline-flex items-center gap-1.5 rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-xs font-medium text-[var(--muted)] hover:text-[var(--fg)] hover:bg-[var(--surface)] transition-colors"
          >
            Manage rules
            <ArrowUpRight className="size-3.5" aria-hidden />
          </Link>
        </div>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-[var(--muted)]">
          Overview of your active monitoring rules, recent threshold triggers, and
          alert performance across all tracked tickers.
        </p>
      </div>

      <AuthGate>
        <div className="space-y-10">
          <PerformanceSummarySection />
          <ActiveAlertRulesSection />
          <RecentTriggersSection />
        </div>
      </AuthGate>
    </div>
  );
}
