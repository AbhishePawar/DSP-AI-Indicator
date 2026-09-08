"use client";

/**
 * Admin Analytics Workspace
 * Panels:
 *  1. Most-Viewed Companies (bar chart + table)
 *  2. Metric Drill-Downs by User (table with user breakdown)
 *  3. Portfolio Activity Heatmap (calendar-style grid)
 *  4. Signups / Logins Time-Series (line chart)
 */

import { useCallback, useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";

// ─── Shared primitives ────────────────────────────────────────────────────────

function SectionCard({
  title,
  description,
  action,
  children,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-[var(--text)]">{title}</h3>
          {description && (
            <p className="mt-0.5 text-xs text-[var(--muted)]">{description}</p>
          )}
        </div>
        {action && <div>{action}</div>}
      </div>
      {children}
    </div>
  );
}

function StatPill({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex flex-col rounded-[var(--radius-sm)] border px-3 py-2",
        accent
          ? "border-[var(--accent)]/30 bg-[var(--accent)]/5"
          : "border-[var(--border)] bg-[var(--surface-2)]",
      )}
    >
      <span className="text-[10px] font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </span>
      <span
        className={cn(
          "mt-0.5 text-lg font-bold",
          accent ? "text-[var(--accent)]" : "text-[var(--text)]",
        )}
      >
        {value}
      </span>
    </div>
  );
}

function SkeletonBlock({ className }: { className?: string }) {
  return (
    <div className={cn("animate-pulse rounded bg-[var(--surface-2)]", className)} />
  );
}

function ErrorMsg({ message }: { message: string }) {
  return <p className="py-6 text-center text-sm text-red-500">{message}</p>;
}

function fmt(ts: string) {
  return new Date(ts).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

// ─── Panel 1: Most-Viewed Companies ──────────────────────────────────────────

interface CompanyViewRow {
  ticker: string;
  company_name: string | null;
  view_count: number;
  unique_users: number;
  avg_duration: number;
}

function MostViewedCompaniesPanel() {
  const supabase = createClient();
  const [rows, setRows] = useState<CompanyViewRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const { data, error: err } = await supabase
      .from("company_views")
      .select("ticker, company_name, duration_secs, user_id");
    if (err) {
      setError(err.message);
      setLoading(false);
      return;
    }
    const map = new Map<string, CompanyViewRow>();
    const userMap = new Map<string, Set<string>>();
    const durationMap = new Map<string, number[]>();
    for (const row of data ?? []) {
      const key = row.ticker as string;
      if (!map.has(key)) {
        map.set(key, {
          ticker: key,
          company_name: row.company_name ?? key,
          view_count: 0,
          unique_users: 0,
          avg_duration: 0,
        });
        userMap.set(key, new Set());
        durationMap.set(key, []);
      }
      map.get(key)!.view_count += 1;
      userMap.get(key)!.add(row.user_id as string);
      durationMap.get(key)!.push(row.duration_secs ?? 0);
    }
    const result = Array.from(map.values())
      .map((r) => {
        const durations = durationMap.get(r.ticker) ?? [];
        return {
          ...r,
          unique_users: userMap.get(r.ticker)?.size ?? 1,
          avg_duration:
            durations.length > 0
              ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length)
              : 0,
        };
      })
      .sort((a, b) => b.view_count - a.view_count)
      .slice(0, 10);
    setRows(result);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const chartOption = {
    tooltip: { trigger: "axis" as const },
    grid: { left: 40, right: 8, top: 8, bottom: 24 },
    xAxis: {
      type: "category" as const,
      data: rows.slice(0, 8).map((r) => r.ticker),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 10, color: "#94a3b8" },
    },
    yAxis: {
      type: "value" as const,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
      axisLabel: { fontSize: 10, color: "#94a3b8" },
    },
    series: [
      {
        name: "Views",
        type: "bar" as const,
        data: rows.slice(0, 8).map((r) => r.view_count),
        itemStyle: { color: "#6366f1", borderRadius: [3, 3, 0, 0] },
        barMaxWidth: 32,
      },
      {
        name: "Unique Users",
        type: "bar" as const,
        data: rows.slice(0, 8).map((r) => r.unique_users),
        itemStyle: { color: "#94a3b8", borderRadius: [3, 3, 0, 0] },
        barMaxWidth: 32,
      },
    ],
  };

  return (
    <SectionCard
      title="Most-Viewed Companies"
      description="Top 10 companies by research views in the last 30 days"
      action={
        <button
          onClick={load}
          className="rounded-[var(--radius-sm)] border border-[var(--border)] px-2 py-1 text-xs text-[var(--muted)] hover:bg-[var(--surface-2)]"
        >
          Refresh
        </button>
      }
    >
      {loading ? (
        <div className="space-y-2">
          <SkeletonBlock className="h-40 w-full" />
          <SkeletonBlock className="h-24 w-full" />
        </div>
      ) : error ? (
        <ErrorMsg message={error} />
      ) : (
        <div className="space-y-4">
          <ReactECharts option={chartOption} style={{ height: 176 }} />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  {["Ticker", "Company", "Views", "Unique Users", "Avg Duration"].map(
                    (h) => (
                      <th
                        key={h}
                        className="py-2 pr-4 text-left font-medium text-[var(--muted)]"
                      >
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr
                    key={r.ticker}
                    className="border-b border-[var(--border)] last:border-0"
                  >
                    <td className="py-2 pr-4 font-mono font-semibold text-[var(--accent)]">
                      {r.ticker}
                    </td>
                    <td className="py-2 pr-4 text-[var(--text)]">
                      {r.company_name ?? r.ticker}
                    </td>
                    <td className="py-2 pr-4 text-[var(--text)]">{r.view_count}</td>
                    <td className="py-2 pr-4 text-[var(--text)]">{r.unique_users}</td>
                    <td className="py-2 pr-4 text-[var(--muted)]">{r.avg_duration}s</td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-[var(--muted)]">
                      No view data yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </SectionCard>
  );
}

// ─── Panel 2: Metric Drill-Downs by User ─────────────────────────────────────

interface DrilldownRow {
  user_id: string;
  ticker: string;
  metric_name: string;
  section: string | null;
  drilled_at: string;
}

interface UserDrillSummary {
  userId: string;
  totalDrills: number;
  metrics: { name: string; count: number }[];
}

function MetricDrilldownsPanel() {
  const supabase = createClient();
  const [rows, setRows] = useState<DrilldownRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const { data, error: err } = await supabase
      .from("metric_drilldowns")
      .select("user_id, ticker, metric_name, section, drilled_at")
      .order("drilled_at", { ascending: false })
      .limit(200);
    if (err) {
      setError(err.message);
    } else {
      setRows((data as DrilldownRow[]) ?? []);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const userMap = new Map<string, UserDrillSummary>();
  for (const r of rows) {
    const uid = r.user_id;
    if (!userMap.has(uid)) {
      userMap.set(uid, { userId: uid, totalDrills: 0, metrics: [] });
    }
    const u = userMap.get(uid)!;
    u.totalDrills += 1;
    const m = u.metrics.find((x) => x.name === r.metric_name);
    if (m) m.count += 1;
    else u.metrics.push({ name: r.metric_name, count: 1 });
  }
  const users = Array.from(userMap.values()).map((u) => ({
    ...u,
    metrics: [...u.metrics].sort((a, b) => b.count - a.count).slice(0, 5),
  }));

  const filteredRows = selectedUser
    ? rows.filter((r) => r.user_id === selectedUser)
    : rows.slice(0, 30);

  return (
    <SectionCard
      title="Metric Drill-Downs by User"
      description="Which metrics users explore most, broken down per user"
    >
      {loading ? (
        <SkeletonBlock className="h-48 w-full" />
      ) : error ? (
        <ErrorMsg message={error} />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedUser(null)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                selectedUser === null
                  ? "border-[var(--accent)] bg-[var(--accent)] text-white"
                  : "border-[var(--border)] text-[var(--muted)] hover:bg-[var(--surface-2)]",
              )}
            >
              All Users
            </button>
            {users.map((u) => (
              <button
                key={u.userId}
                onClick={() =>
                  setSelectedUser(u.userId === selectedUser ? null : u.userId)
                }
                className={cn(
                  "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                  selectedUser === u.userId
                    ? "border-[var(--accent)] bg-[var(--accent)] text-white"
                    : "border-[var(--border)] text-[var(--muted)] hover:bg-[var(--surface-2)]",
                )}
              >
                {u.userId.slice(0, 8)}…
                <span className="ml-1 opacity-60">({u.totalDrills})</span>
              </button>
            ))}
          </div>

          {selectedUser && (
            <div className="flex flex-wrap gap-2">
              {(userMap.get(selectedUser)?.metrics ?? []).map((m) => (
                <span
                  key={m.name}
                  className="inline-flex items-center gap-1 rounded-full bg-[var(--surface-2)] px-2 py-0.5 text-xs text-[var(--text)]"
                >
                  {m.name}
                  <span className="font-semibold text-[var(--accent)]">×{m.count}</span>
                </span>
              ))}
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  {["User", "Ticker", "Metric", "Section", "When"].map((h) => (
                    <th
                      key={h}
                      className="py-2 pr-4 text-left font-medium text-[var(--muted)]"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((r, i) => (
                  <tr
                    key={i}
                    className="border-b border-[var(--border)] last:border-0"
                  >
                    <td className="py-2 pr-4 font-mono text-[var(--muted)]">
                      {r.user_id.slice(0, 8)}…
                    </td>
                    <td className="py-2 pr-4 font-semibold text-[var(--accent)]">
                      {r.ticker}
                    </td>
                    <td className="py-2 pr-4 text-[var(--text)]">{r.metric_name}</td>
                    <td className="py-2 pr-4 text-[var(--muted)]">{r.section ?? "—"}</td>
                    <td className="py-2 pr-4 text-[var(--muted)]">{fmt(r.drilled_at)}</td>
                  </tr>
                ))}
                {filteredRows.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-[var(--muted)]">
                      No drill-down data yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </SectionCard>
  );
}

// ─── Panel 3: Portfolio Activity Heatmap ─────────────────────────────────────

interface PortfolioActivityRow {
  occurred_at: string;
  action: string;
  ticker: string;
}

function PortfolioHeatmapPanel() {
  const supabase = createClient();
  const [rows, setRows] = useState<PortfolioActivityRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const since = new Date();
    since.setDate(since.getDate() - 30);
    const { data, error: err } = await supabase
      .from("portfolio_activity")
      .select("occurred_at, action, ticker")
      .gte("occurred_at", since.toISOString())
      .order("occurred_at", { ascending: true });
    if (err) {
      setError(err.message);
    } else {
      setRows((data as PortfolioActivityRow[]) ?? []);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const days: { date: string; label: string; events: PortfolioActivityRow[] }[] = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    days.push({
      date: dateStr,
      label: d.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
      events: rows.filter((r) => r.occurred_at.slice(0, 10) === dateStr),
    });
  }

  const maxEvents = Math.max(...days.map((d) => d.events.length), 1);
  const totalAdd = rows.filter((r) => r.action === "add").length;
  const totalRemove = rows.filter((r) => r.action === "remove").length;
  const totalView = rows.filter((r) => r.action === "view").length;
  const totalRebalance = rows.filter((r) => r.action === "rebalance").length;

  return (
    <SectionCard
      title="Portfolio Activity Heatmap"
      description="Daily portfolio events over the last 30 days"
    >
      {loading ? (
        <SkeletonBlock className="h-48 w-full" />
      ) : error ? (
        <ErrorMsg message={error} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <StatPill label="Adds" value={totalAdd} accent />
            <StatPill label="Removes" value={totalRemove} />
            <StatPill label="Views" value={totalView} />
            <StatPill label="Rebalances" value={totalRebalance} />
          </div>

          <div className="overflow-x-auto">
            <div className="flex min-w-max gap-1 pb-2">
              {days.map((day, idx) => {
                const intensity = day.events.length / maxEvents;
                return (
                  <div
                    key={day.date}
                    className="group relative flex flex-col items-center gap-1"
                  >
                    <div
                      className="h-8 w-8 cursor-default rounded-sm transition-transform group-hover:scale-110"
                      style={{
                        backgroundColor: `rgba(99, 102, 241, ${0.08 + intensity * 0.88})`,
                        border: "1px solid rgba(99,102,241,0.2)",
                      }}
                    />
                    {/* Tooltip */}
                    <div className="pointer-events-none absolute bottom-10 left-1/2 z-10 hidden min-w-[100px] -translate-x-1/2 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] p-2 text-xs shadow-lg group-hover:block">
                      <p className="font-semibold text-[var(--text)]">{day.label}</p>
                      <p className="text-[var(--muted)]">
                        {day.events.length} event{day.events.length !== 1 ? "s" : ""}
                      </p>
                      {day.events.slice(0, 3).map((e, i) => (
                        <p key={i} className="text-[var(--muted)]">
                          {e.action} {e.ticker}
                        </p>
                      ))}
                    </div>
                    {idx % 5 === 0 && (
                      <span className="text-[9px] text-[var(--muted)]">
                        {day.label.split(" ")[1]}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            {[
              { label: "Add", color: "bg-emerald-500" },
              { label: "Remove", color: "bg-red-400" },
              { label: "View", color: "bg-blue-400" },
              { label: "Rebalance", color: "bg-amber-400" },
            ].map(({ label, color }) => (
              <span
                key={label}
                className="flex items-center gap-1.5 text-xs text-[var(--muted)]"
              >
                <span className={cn("h-2.5 w-2.5 rounded-sm", color)} />
                {label}
              </span>
            ))}
          </div>
        </div>
      )}
    </SectionCard>
  );
}

// ─── Panel 4: Signups / Logins Time-Series ────────────────────────────────────

interface AuditRow {
  event_category: string;
  event_type: string;
  created_at: string;
}

interface TimeSeriesPoint {
  date: string;
  signups: number;
  logins: number;
}

function SignupsLoginsPanel() {
  const supabase = createClient();
  const [data, setData] = useState<TimeSeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<7 | 14 | 30>(30);

  const load = useCallback(async (days: number) => {
    setLoading(true);
    setError(null);
    const since = new Date();
    since.setDate(since.getDate() - days);
    const { data: rows, error: err } = await supabase
      .from("audit_trail")
      .select("event_category, event_type, created_at")
      .gte("created_at", since.toISOString())
      .order("created_at", { ascending: true });
    if (err) {
      setError(err.message);
      setLoading(false);
      return;
    }
    const buckets = new Map<string, TimeSeriesPoint>();
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      buckets.set(key, {
        date: d.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        signups: 0,
        logins: 0,
      });
    }
    for (const row of (rows as AuditRow[]) ?? []) {
      const key = row.created_at.slice(0, 10);
      const bucket = buckets.get(key);
      if (!bucket) continue;
      const et = (row.event_type ?? "").toLowerCase();
      if (et.includes("signup") || et.includes("register")) bucket.signups += 1;
      else if (et.includes("login") || et.includes("sign_in")) bucket.logins += 1;
    }
    setData(Array.from(buckets.values()));
    setLoading(false);
  }, []);

  useEffect(() => {
    void load(range);
  }, [load, range]);

  const totalSignups = data.reduce((s, d) => s + d.signups, 0);
  const totalLogins = data.reduce((s, d) => s + d.logins, 0);

  const chartOption = {
    tooltip: { trigger: "axis" as const },
    legend: { data: ["Signups", "Logins"], bottom: 0, textStyle: { fontSize: 11 } },
    grid: { left: 40, right: 8, top: 8, bottom: 32 },
    xAxis: {
      type: "category" as const,
      data: data.map((d) => d.date),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        fontSize: 10,
        color: "#94a3b8",
        interval: Math.floor(data.length / 6),
      },
    },
    yAxis: {
      type: "value" as const,
      minInterval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
      axisLabel: { fontSize: 10, color: "#94a3b8" },
    },
    series: [
      {
        name: "Signups",
        type: "line" as const,
        data: data.map((d) => d.signups),
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#6366f1", width: 2 },
        areaStyle: { color: "rgba(99,102,241,0.08)" },
      },
      {
        name: "Logins",
        type: "line" as const,
        data: data.map((d) => d.logins),
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#94a3b8", width: 2 },
        areaStyle: { color: "rgba(148,163,184,0.06)" },
      },
    ],
  };

  return (
    <SectionCard
      title="Signups & Logins Over Time"
      description="Daily authentication events from the audit trail"
      action={
        <div className="flex gap-1">
          {([7, 14, 30] as const).map((d) => (
            <button
              key={d}
              onClick={() => {
                setRange(d);
                void load(d);
              }}
              className={cn(
                "rounded-[var(--radius-sm)] px-2 py-1 text-xs font-medium transition-colors",
                range === d
                  ? "bg-[var(--accent)] text-white"
                  : "border border-[var(--border)] text-[var(--muted)] hover:bg-[var(--surface-2)]",
              )}
            >
              {d}d
            </button>
          ))}
        </div>
      }
    >
      {loading ? (
        <SkeletonBlock className="h-52 w-full" />
      ) : error ? (
        <ErrorMsg message={error} />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <StatPill label="Total Signups" value={totalSignups} accent />
            <StatPill label="Total Logins" value={totalLogins} />
            <StatPill
              label="Avg Signups/Day"
              value={(totalSignups / (data.length || 1)).toFixed(1)}
            />
            <StatPill
              label="Avg Logins/Day"
              value={(totalLogins / (data.length || 1)).toFixed(1)}
            />
          </div>
          <ReactECharts option={chartOption} style={{ height: 208 }} />
        </div>
      )}
    </SectionCard>
  );
}

// ─── Root export ──────────────────────────────────────────────────────────────

export function AnalyticsWorkspace() {
  return (
    <div className="space-y-4">
      <MostViewedCompaniesPanel />
      <MetricDrilldownsPanel />
      <PortfolioHeatmapPanel />
      <SignupsLoginsPanel />
    </div>
  );
}
