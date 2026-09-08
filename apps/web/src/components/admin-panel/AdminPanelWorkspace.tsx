"use client";

/**
 * Admin Panel — Supabase-backed management of:
 * - User Alert Rules
 * - Threshold Logs
 * - Watchlist Shares
 * - Integration Settings (Resend / webhooks)
 */

import { useCallback, useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useAuth } from "@/lib/auth/AuthProvider";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface AlertRule {
  id: string;
  ticker: string;
  metric: string;
  condition: string;
  threshold_value: number;
  alert_status: string;
  notification_channel: string;
  last_triggered_at: string | null;
  notes: string | null;
  created_at: string;
}

interface ThresholdLog {
  id: string;
  alert_rule_id: string | null;
  ticker: string;
  metric: string;
  condition: string;
  threshold_value: number;
  actual_value: number;
  triggered_at: string;
  delivery_status: string;
  delivery_error: string | null;
}

interface WatchlistShare {
  id: string;
  owner_id: string;
  shared_with_id: string | null;
  shared_with_email: string | null;
  watchlist_name: string;
  tickers: string[];
  permission: string;
  is_public: boolean;
  expires_at: string | null;
  created_at: string;
}

interface IntegrationSetting {
  id: string;
  integration_key: string;
  display_name: string;
  is_enabled: boolean;
  config: Record<string, unknown>;
  last_tested_at: string | null;
  last_test_status: string | null;
  created_at: string;
}

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
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
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

function StatusBadge({ value }: { value: string }) {
  const color =
    value === "active" || value === "delivered" || value === "enabled" ?"bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400"
      : value === "paused"|| value === "pending" ?"bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400" :"bg-[var(--surface-2)] text-[var(--muted)]";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        color,
      )}
    >
      {value}
    </span>
  );
}

function EmptyRow({ message }: { message: string }) {
  return (
    <tr>
      <td
        colSpan={99}
        className="py-8 text-center text-sm text-[var(--muted)]"
      >
        {message}
      </td>
    </tr>
  );
}

function TableShell({
  headers,
  children,
}: {
  headers: string[];
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)]">
            {headers.map((h) => (
              <th
                key={h}
                className="py-2 pr-4 text-left text-xs font-medium text-[var(--muted)]"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function LoadingRows() {
  return (
    <>
      {[1, 2, 3].map((i) => (
        <tr key={i} className="border-b border-[var(--border)]">
          {[1, 2, 3, 4].map((j) => (
            <td key={j} className="py-3 pr-4">
              <div className="h-3 w-24 animate-pulse rounded bg-[var(--surface-2)]" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

function ErrorRow({ message }: { message: string }) {
  return (
    <tr>
      <td
        colSpan={99}
        className="py-6 text-center text-sm text-red-500"
      >
        {message}
      </td>
    </tr>
  );
}

function fmt(ts: string | null) {
  if (!ts) return "—";
  return new Date(ts).toLocaleString(undefined, {
    dateStyle: "short",
    timeStyle: "short",
  });
}

// ─── Alert Rules Tab ──────────────────────────────────────────────────────────

function AlertRulesTab({ userId }: { userId: string }) {
  const supabase = createClient();
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    ticker: "",
    metric: "price",
    condition: "above",
    threshold_value: "",
    notification_channel: "email",
    notes: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const { data, error: err } = await supabase
      .from("alert_rules")
      .select("*")
      .eq("user_id", userId)
      .order("created_at", { ascending: false });
    if (err) setError(err.message);
    else setRules((data as AlertRule[]) ?? []);
    setLoading(false);
  }, [userId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async () => {
    if (!form.ticker.trim() || !form.threshold_value) return;
    setSaving(true);
    const { error: err } = await supabase.from("alert_rules").insert({
      user_id: userId,
      ticker: form.ticker.trim().toUpperCase(),
      metric: form.metric,
      condition: form.condition,
      threshold_value: parseFloat(form.threshold_value),
      notification_channel: form.notification_channel,
      notes: form.notes || null,
    });
    setSaving(false);
    if (err) {
      setError(err.message);
    } else {
      setShowForm(false);
      setForm({
        ticker: "",
        metric: "price",
        condition: "above",
        threshold_value: "",
        notification_channel: "email",
        notes: "",
      });
      void load();
    }
  };

  const handleToggle = async (rule: AlertRule) => {
    const next =
      rule.alert_status === "active" ? "paused" : "active";
    await supabase
      .from("alert_rules")
      .update({ alert_status: next })
      .eq("id", rule.id)
      .eq("user_id", userId);
    void load();
  };

  const handleDelete = async (id: string) => {
    await supabase
      .from("alert_rules")
      .update({ alert_status: "deleted" })
      .eq("id", id)
      .eq("user_id", userId);
    void load();
  };

  return (
    <div className="space-y-4">
      <SectionCard
        title="Alert Rules"
        description="Metric threshold alerts per ticker. Notifications delivered via configured channel."
        action={
          <button
            onClick={() => setShowForm((v) => !v)}
            className="rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-medium text-[var(--text)] hover:bg-[var(--surface-2)]"
          >
            {showForm ? "Cancel" : "+ New Rule"}
          </button>
        }
      >
        {showForm && (
          <div className="mb-4 grid grid-cols-2 gap-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs text-[var(--muted)]">
                Ticker
              </label>
              <input
                value={form.ticker}
                onChange={(e) =>
                  setForm((f) => ({ ...f, ticker: e.target.value }))
                }
                placeholder="AAPL"
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-[var(--muted)]">
                Metric
              </label>
              <select
                value={form.metric}
                onChange={(e) =>
                  setForm((f) => ({ ...f, metric: e.target.value }))
                }
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm text-[var(--text)] focus:outline-none"
              >
                <option value="price">Price</option>
                <option value="pe_ratio">P/E Ratio</option>
                <option value="margin_of_safety">Margin of Safety</option>
                <option value="revenue_growth">Revenue Growth</option>
                <option value="roe">ROE</option>
                <option value="debt_to_equity">Debt/Equity</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-[var(--muted)]">
                Condition
              </label>
              <select
                value={form.condition}
                onChange={(e) =>
                  setForm((f) => ({ ...f, condition: e.target.value }))
                }
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm text-[var(--text)] focus:outline-none"
              >
                <option value="above">Above</option>
                <option value="below">Below</option>
                <option value="equals">Equals</option>
                <option value="crosses_above">Crosses Above</option>
                <option value="crosses_below">Crosses Below</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-[var(--muted)]">
                Threshold
              </label>
              <input
                type="number"
                value={form.threshold_value}
                onChange={(e) =>
                  setForm((f) => ({ ...f, threshold_value: e.target.value }))
                }
                placeholder="0.00"
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-[var(--muted)]">
                Channel
              </label>
              <select
                value={form.notification_channel}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    notification_channel: e.target.value,
                  }))
                }
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm text-[var(--text)] focus:outline-none"
              >
                <option value="email">Email</option>
                <option value="webhook">Webhook</option>
                <option value="in_app">In-App</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-[var(--muted)]">
                Notes
              </label>
              <input
                value={form.notes}
                onChange={(e) =>
                  setForm((f) => ({ ...f, notes: e.target.value }))
                }
                placeholder="Optional"
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm text-[var(--text)] focus:outline-none"
              />
            </div>
            <div className="col-span-full flex justify-end gap-2">
              <button
                onClick={handleCreate}
                disabled={saving}
                className="rounded-[var(--radius-sm)] bg-[var(--accent)] px-4 py-1.5 text-xs font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save Rule"}
              </button>
            </div>
          </div>
        )}
        {error && (
          <p className="mb-2 text-xs text-red-500">{error}</p>
        )}
        <TableShell
          headers={[
            "Ticker",
            "Metric",
            "Condition",
            "Threshold",
            "Channel",
            "Status",
            "Last Triggered",
            "",
          ]}
        >
          {loading ? (
            <LoadingRows />
          ) : rules.filter((r) => r.alert_status !== "deleted").length === 0 ? (
            <EmptyRow message="No alert rules configured." />
          ) : (
            rules
              .filter((r) => r.alert_status !== "deleted")
              .map((rule) => (
                <tr
                  key={rule.id}
                  className="border-b border-[var(--border)] last:border-0"
                >
                  <td className="py-2.5 pr-4 font-mono text-xs font-semibold text-[var(--text)]">
                    {rule.ticker}
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-[var(--text)]">
                    {rule.metric}
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-[var(--muted)]">
                    {rule.condition.replace(/_/g, " ")}
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-[var(--text)]">
                    {rule.threshold_value}
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-[var(--muted)]">
                    {rule.notification_channel}
                  </td>
                  <td className="py-2.5 pr-4">
                    <StatusBadge value={rule.alert_status} />
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-[var(--muted)]">
                    {fmt(rule.last_triggered_at)}
                  </td>
                  <td className="py-2.5 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleToggle(rule)}
                        className="text-xs text-[var(--muted)] hover:text-[var(--text)]"
                      >
                        {rule.alert_status === "active" ? "Pause" : "Resume"}
                      </button>
                      <button
                        onClick={() => handleDelete(rule.id)}
                        className="text-xs text-red-500 hover:text-red-700"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))
          )}
        </TableShell>
      </SectionCard>
    </div>
  );
}

// ─── Threshold Logs Tab ───────────────────────────────────────────────────────

function ThresholdLogsTab({ userId }: { userId: string }) {
  const supabase = createClient();
  const [logs, setLogs] = useState<ThresholdLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tickerFilter, setTickerFilter] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const filter = tickerFilter.trim();
    const baseQuery = supabase
      .from("threshold_logs")
      .select("*")
      .eq("user_id", userId)
      .order("triggered_at", { ascending: false })
      .limit(100);
    const { data, error: err } = filter
      ? await baseQuery.ilike("ticker", `%${filter}%`)
      : await baseQuery;
    if (err) setError(err.message);
    else setLogs((data as ThresholdLog[]) ?? []);
    setLoading(false);
  }, [userId, tickerFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <SectionCard
        title="Threshold Logs"
        description="Immutable audit trail of triggered alert events. Last 100 entries."
        action={
          <input
            value={tickerFilter}
            onChange={(e) => setTickerFilter(e.target.value)}
            placeholder="Filter by ticker"
            className="rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-xs text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />
        }
      >
        {error && <p className="mb-2 text-xs text-red-500">{error}</p>}
        <TableShell
          headers={[
            "Triggered",
            "Ticker",
            "Metric",
            "Condition",
            "Threshold",
            "Actual",
            "Delivery",
          ]}
        >
          {loading ? (
            <LoadingRows />
          ) : logs.length === 0 ? (
            <EmptyRow message="No threshold events recorded." />
          ) : (
            logs.map((log) => (
              <tr
                key={log.id}
                className="border-b border-[var(--border)] last:border-0"
              >
                <td className="py-2.5 pr-4 text-xs text-[var(--muted)]">
                  {fmt(log.triggered_at)}
                </td>
                <td className="py-2.5 pr-4 font-mono text-xs font-semibold text-[var(--text)]">
                  {log.ticker}
                </td>
                <td className="py-2.5 pr-4 text-xs text-[var(--text)]">
                  {log.metric}
                </td>
                <td className="py-2.5 pr-4 text-xs text-[var(--muted)]">
                  {log.condition.replace(/_/g, " ")}
                </td>
                <td className="py-2.5 pr-4 text-xs text-[var(--text)]">
                  {log.threshold_value}
                </td>
                <td className="py-2.5 pr-4 text-xs font-medium text-[var(--text)]">
                  {log.actual_value}
                </td>
                <td className="py-2.5">
                  <StatusBadge value={log.delivery_status} />
                </td>
              </tr>
            ))
          )}
        </TableShell>
      </SectionCard>
    </div>
  );
}

// ─── Watchlist Shares Tab ─────────────────────────────────────────────────────

function WatchlistSharesTab({ userId }: { userId: string }) {
  const supabase = createClient();
  const [shares, setShares] = useState<WatchlistShare[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    watchlist_name: "",
    tickers: "",
    shared_with_email: "",
    permission: "view",
    is_public: false,
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const { data, error: err } = await supabase
      .from("watchlist_shares")
      .select("*")
      .eq("owner_id", userId)
      .order("created_at", { ascending: false });
    if (err) setError(err.message);
    else setShares((data as WatchlistShare[]) ?? []);
    setLoading(false);
  }, [userId]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async () => {
    if (!form.watchlist_name.trim()) return;
    setSaving(true);
    const tickers = form.tickers
      .split(",")
      .map((t) => t.trim().toUpperCase())
      .filter(Boolean);
    const { error: err } = await supabase.from("watchlist_shares").insert({
      owner_id: userId,
      watchlist_name: form.watchlist_name.trim(),
      tickers,
      shared_with_email: form.shared_with_email.trim() || null,
      permission: form.permission,
      is_public: form.is_public,
    });
    setSaving(false);
    if (err) {
      setError(err.message);
    } else {
      setShowForm(false);
      setForm({
        watchlist_name: "",
        tickers: "",
        shared_with_email: "",
        permission: "view",
        is_public: false,
      });
      void load();
    }
  };

  const handleRevoke = async (id: string) => {
    await supabase
      .from("watchlist_shares")
      .delete()
      .eq("id", id)
      .eq("owner_id", userId);
    void load();
  };

  return (
    <div className="space-y-4">
      <SectionCard
        title="Watchlist Shares"
        description="Share named watchlists with specific users or make them public."
        action={
          <button
            onClick={() => setShowForm((v) => !v)}
            className="rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-medium text-[var(--text)] hover:bg-[var(--surface-2)]"
          >
            {showForm ? "Cancel" : "+ Share Watchlist"}
          </button>
        }
      >
        {showForm && (
          <div className="mb-4 grid grid-cols-2 gap-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] p-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs text-[var(--muted)]">
                Watchlist Name
              </label>
              <input
                value={form.watchlist_name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, watchlist_name: e.target.value }))
                }
                placeholder="My Watchlist"
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-[var(--muted)]">
                Tickers (comma-separated)
              </label>
              <input
                value={form.tickers}
                onChange={(e) =>
                  setForm((f) => ({ ...f, tickers: e.target.value }))
                }
                placeholder="AAPL, MSFT, GOOGL"
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-[var(--muted)]">
                Share With (email)
              </label>
              <input
                value={form.shared_with_email}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    shared_with_email: e.target.value,
                  }))
                }
                placeholder="colleague@example.com"
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-[var(--muted)]">
                Permission
              </label>
              <select
                value={form.permission}
                onChange={(e) =>
                  setForm((f) => ({ ...f, permission: e.target.value }))
                }
                className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm text-[var(--text)] focus:outline-none"
              >
                <option value="view">View</option>
                <option value="edit">Edit</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div className="flex items-end gap-2">
              <label className="flex cursor-pointer items-center gap-2 text-xs text-[var(--text)]">
                <input
                  type="checkbox"
                  checked={form.is_public}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, is_public: e.target.checked }))
                  }
                  className="rounded"
                />
                Public watchlist
              </label>
            </div>
            <div className="flex items-end justify-end">
              <button
                onClick={handleCreate}
                disabled={saving}
                className="rounded-[var(--radius-sm)] bg-[var(--accent)] px-4 py-1.5 text-xs font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                {saving ? "Saving…" : "Create Share"}
              </button>
            </div>
          </div>
        )}
        {error && <p className="mb-2 text-xs text-red-500">{error}</p>}
        <TableShell
          headers={[
            "Watchlist",
            "Tickers",
            "Shared With",
            "Permission",
            "Public",
            "Created",
            "",
          ]}
        >
          {loading ? (
            <LoadingRows />
          ) : shares.length === 0 ? (
            <EmptyRow message="No watchlists shared yet." />
          ) : (
            shares.map((share) => (
              <tr
                key={share.id}
                className="border-b border-[var(--border)] last:border-0"
              >
                <td className="py-2.5 pr-4 text-xs font-medium text-[var(--text)]">
                  {share.watchlist_name}
                </td>
                <td className="py-2.5 pr-4 text-xs text-[var(--muted)]">
                  {share.tickers?.slice(0, 4).join(", ")}
                  {(share.tickers?.length ?? 0) > 4 &&
                    ` +${share.tickers.length - 4}`}
                </td>
                <td className="py-2.5 pr-4 text-xs text-[var(--muted)]">
                  {share.shared_with_email ?? "—"}
                </td>
                <td className="py-2.5 pr-4">
                  <StatusBadge value={share.permission} />
                </td>
                <td className="py-2.5 pr-4 text-xs text-[var(--muted)]">
                  {share.is_public ? "Yes" : "No"}
                </td>
                <td className="py-2.5 pr-4 text-xs text-[var(--muted)]">
                  {fmt(share.created_at)}
                </td>
                <td className="py-2.5 text-right">
                  <button
                    onClick={() => handleRevoke(share.id)}
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Revoke
                  </button>
                </td>
              </tr>
            ))
          )}
        </TableShell>
      </SectionCard>
    </div>
  );
}

// ─── Integration Settings Tab ─────────────────────────────────────────────────

const DEFAULT_INTEGRATIONS = [
  {
    integration_key: "resend_email",
    display_name: "Resend Email",
    description: "Transactional email delivery for alert notifications.",
  },
  {
    integration_key: "webhook_alerts",
    display_name: "Webhook Alerts",
    description: "POST threshold events to a custom HTTPS endpoint.",
  },
  {
    integration_key: "in_app_notifications",
    display_name: "In-App Notifications",
    description: "Show alert banners inside the DSP AI Indicator interface.",
  },
];

function IntegrationSettingsTab({ userId }: { userId: string }) {
  const supabase = createClient();
  const [settings, setSettings] = useState<IntegrationSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [editKey, setEditKey] = useState<string | null>(null);
  const [configDraft, setConfigDraft] = useState<string>("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const { data, error: err } = await supabase
      .from("integration_settings")
      .select("*")
      .eq("user_id", userId);
    if (err) setError(err.message);
    else setSettings((data as IntegrationSetting[]) ?? []);
    setLoading(false);
  }, [userId]);

  useEffect(() => {
    void load();
  }, [load]);

  const getOrCreate = async (key: string, displayName: string) => {
    const existing = settings.find((s) => s.integration_key === key);
    if (existing) return existing;
    const { data, error: err } = await supabase
      .from("integration_settings")
      .upsert(
        {
          user_id: userId,
          integration_key: key,
          display_name: displayName,
          is_enabled: false,
          config: {},
        },
        { onConflict: "user_id,integration_key" },
      )
      .select()
      .single();
    if (err) return null;
    return data as IntegrationSetting;
  };

  const handleToggle = async (key: string, displayName: string) => {
    setSaving(key);
    const row = await getOrCreate(key, displayName);
    if (!row) {
      setSaving(null);
      return;
    }
    await supabase
      .from("integration_settings")
      .update({ is_enabled: !row.is_enabled })
      .eq("id", row.id)
      .eq("user_id", userId);
    setSaving(null);
    void load();
  };

  const handleSaveConfig = async (key: string) => {
    setSaving(key);
    let parsed: Record<string, unknown> = {};
    try {
      parsed = JSON.parse(configDraft) as Record<string, unknown>;
    } catch {
      setError("Invalid JSON in configuration.");
      setSaving(null);
      return;
    }
    const row = settings.find((s) => s.integration_key === key);
    if (!row) {
      setSaving(null);
      return;
    }
    await supabase
      .from("integration_settings")
      .update({ config: parsed })
      .eq("id", row.id)
      .eq("user_id", userId);
    setSaving(null);
    setEditKey(null);
    void load();
  };

  const getSetting = (key: string) =>
    settings.find((s) => s.integration_key === key);

  return (
    <div className="space-y-4">
      {error && <p className="text-xs text-red-500">{error}</p>}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-20 animate-pulse rounded-[var(--radius-md)] bg-[var(--surface-2)]"
            />
          ))}
        </div>
      ) : (
        DEFAULT_INTEGRATIONS.map((intg) => {
          const row = getSetting(intg.integration_key);
          const isEnabled = row?.is_enabled ?? false;
          const isEditing = editKey === intg.integration_key;
          return (
            <SectionCard
              key={intg.integration_key}
              title={intg.display_name}
              description={intg.description}
              action={
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => {
                      if (isEditing) {
                        setEditKey(null);
                      } else {
                        setEditKey(intg.integration_key);
                        setConfigDraft(
                          JSON.stringify(row?.config ?? {}, null, 2),
                        );
                      }
                    }}
                    className="text-xs text-[var(--muted)] hover:text-[var(--text)]"
                  >
                    {isEditing ? "Cancel" : "Configure"}
                  </button>
                  <button
                    onClick={() =>
                      handleToggle(intg.integration_key, intg.display_name)
                    }
                    disabled={saving === intg.integration_key}
                    className={cn(
                      "relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none",
                      isEnabled
                        ? "bg-[var(--accent)]"
                        : "bg-[var(--surface-2)]",
                    )}
                    role="switch"
                    aria-checked={isEnabled}
                    aria-label={`Toggle ${intg.display_name}`}
                  >
                    <span
                      className={cn(
                        "inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform",
                        isEnabled ? "translate-x-4" : "translate-x-0.5",
                      )}
                    />
                  </button>
                </div>
              }
            >
              <div className="flex items-center gap-4 text-xs text-[var(--muted)]">
                <span>
                  Status:{" "}
                  <span
                    className={
                      isEnabled ? "text-emerald-500" : "text-[var(--muted)]"
                    }
                  >
                    {isEnabled ? "Enabled" : "Disabled"}
                  </span>
                </span>
                {row?.last_tested_at && (
                  <span>Last tested: {fmt(row.last_tested_at)}</span>
                )}
                {row?.last_test_status && (
                  <StatusBadge value={row.last_test_status} />
                )}
              </div>
              {isEditing && (
                <div className="mt-3">
                  <label className="mb-1 block text-xs text-[var(--muted)]">
                    Configuration (JSON)
                  </label>
                  <textarea
                    value={configDraft}
                    onChange={(e) => setConfigDraft(e.target.value)}
                    rows={6}
                    className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 font-mono text-xs text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                    placeholder='{"api_key": "re_...", "from": "alerts@yourdomain.com"}'
                  />
                  <div className="mt-2 flex justify-end">
                    <button
                      onClick={() =>
                        handleSaveConfig(intg.integration_key)
                      }
                      disabled={saving === intg.integration_key}
                      className="rounded-[var(--radius-sm)] bg-[var(--accent)] px-4 py-1.5 text-xs font-medium text-white hover:opacity-90 disabled:opacity-50"
                    >
                      {saving === intg.integration_key
                        ? "Saving…" :"Save Config"}
                    </button>
                  </div>
                </div>
              )}
            </SectionCard>
          );
        })
      )}
    </div>
  );
}

// ─── User Management Tab ─────────────────────────────────────────────────────

interface UserProfile {
  id: string;
  display_name: string | null;
  role: string;
  is_tenant_admin: boolean;
  is_suspended: boolean;
  can_access_research: boolean;
  can_access_portfolio: boolean;
  can_access_advisor: boolean;
  can_export_reports: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

interface UserRow {
  id: string;
  email: string | null;
  created_at: string;
  last_sign_in_at: string | null;
  profile: UserProfile | null;
  activity_count: number;
  last_event_type: string | null;
}

const PERMISSION_KEYS: { key: keyof UserProfile; label: string }[] = [
  { key: "can_access_research", label: "Research" },
  { key: "can_access_portfolio", label: "Portfolio" },
  { key: "can_access_advisor", label: "Advisor" },
  { key: "can_export_reports", label: "Export Reports" },
  { key: "is_tenant_admin", label: "Tenant Admin" },
];

function PermissionToggle({
  enabled,
  onChange,
  disabled,
}: {
  enabled: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={() => !disabled && onChange(!enabled)}
      disabled={disabled}
      className={cn(
        "relative inline-flex h-4 w-7 items-center rounded-full transition-colors focus:outline-none",
        enabled ? "bg-[var(--accent)]" : "bg-[var(--surface-2)]",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <span
        className={cn(
          "inline-block h-3 w-3 transform rounded-full bg-white shadow transition-transform",
          enabled ? "translate-x-3.5" : "translate-x-0.5",
        )}
      />
    </button>
  );
}

function UserDetailPanel({
  row,
  onClose,
  onSave,
}: {
  row: UserRow;
  onClose: () => void;
  onSave: (id: string, patch: Partial<UserProfile>) => Promise<void>;
}) {
  const [patch, setPatch] = useState<Partial<UserProfile>>(
    row.profile ?? {},
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await onSave(row.id, patch);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const toggle = (key: keyof UserProfile) => {
    setPatch((p) => ({ ...p, [key]: !p[key] }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-5 shadow-xl">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h3 className="text-sm font-semibold text-[var(--text)]">
              {row.profile?.display_name ?? row.email ?? row.id}
            </h3>
            <p className="mt-0.5 text-xs text-[var(--muted)]">{row.email}</p>
          </div>
          <button
            onClick={onClose}
            className="text-[var(--muted)] hover:text-[var(--text)]"
          >
            ✕
          </button>
        </div>

        {/* Role */}
        <div className="mb-4">
          <label className="mb-1 block text-xs font-medium text-[var(--muted)]">
            Role
          </label>
          <select
            value={patch.role ?? row.profile?.role ?? "user"}
            onChange={(e) => setPatch((p) => ({ ...p, role: e.target.value }))}
            className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm text-[var(--text)] focus:outline-none"
          >
            <option value="user">User</option>
            <option value="analyst">Analyst</option>
            <option value="admin">Admin</option>
          </select>
        </div>

        {/* Permissions */}
        <div className="mb-4 space-y-2">
          <p className="text-xs font-medium text-[var(--muted)]">Permissions</p>
          {PERMISSION_KEYS.map(({ key, label }) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-xs text-[var(--text)]">{label}</span>
              <PermissionToggle
                enabled={
                  patch[key] !== undefined
                    ? Boolean(patch[key])
                    : Boolean(row.profile?.[key])
                }
                onChange={() => toggle(key)}
              />
            </div>
          ))}
        </div>

        {/* Suspend */}
        <div className="mb-4 flex items-center justify-between rounded-[var(--radius-sm)] border border-red-200 bg-red-50 px-3 py-2 dark:border-red-900/30 dark:bg-red-900/10">
          <span className="text-xs font-medium text-red-700 dark:text-red-400">
            Suspend account
          </span>
          <PermissionToggle
            enabled={
              patch.is_suspended !== undefined
                ? Boolean(patch.is_suspended)
                : Boolean(row.profile?.is_suspended)
            }
            onChange={() => toggle("is_suspended")}
          />
        </div>

        {/* Notes */}
        <div className="mb-4">
          <label className="mb-1 block text-xs font-medium text-[var(--muted)]">
            Admin notes
          </label>
          <textarea
            rows={2}
            value={patch.notes ?? row.profile?.notes ?? ""}
            onChange={(e) => setPatch((p) => ({ ...p, notes: e.target.value }))}
            className="w-full resize-none rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm text-[var(--text)] focus:outline-none"
          />
        </div>

        {error && (
          <p className="mb-2 text-xs text-red-500">{error}</p>
        )}

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-[var(--radius-sm)] border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--muted)] hover:bg-[var(--surface-2)]"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-[var(--radius-sm)] bg-[var(--accent)] px-4 py-1.5 text-xs font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}

function UserManagementTab({ currentUserId }: { currentUserId: string }) {
  const supabase = createClient();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedUser, setSelectedUser] = useState<UserRow | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    // Fetch profiles (visible to tenant admins via RLS)
    const { data: profiles, error: profErr } = await supabase
      .from("user_profiles")
      .select("*")
      .order("created_at", { ascending: false });

    if (profErr) {
      setError(profErr.message);
      setLoading(false);
      return;
    }

    // Fetch activity summary per user
    const { data: activityRaw } = await supabase
      .from("user_activity_log")
      .select("user_id, event_type, created_at")
      .order("created_at", { ascending: false });

    // Build activity map
    const activityMap: Record<
      string,
      { count: number; last_event_type: string | null }
    > = {};
    for (const a of activityRaw ?? []) {
      if (!activityMap[a.user_id]) {
        activityMap[a.user_id] = { count: 0, last_event_type: a.event_type };
      }
      activityMap[a.user_id].count += 1;
    }

    const rows: UserRow[] = (profiles as UserProfile[]).map((p) => ({
      id: p.id,
      email: p.display_name ?? null,
      created_at: p.created_at,
      last_sign_in_at: null,
      profile: p,
      activity_count: activityMap[p.id]?.count ?? 0,
      last_event_type: activityMap[p.id]?.last_event_type ?? null,
    }));

    setUsers(rows);
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleSave = async (
    userId: string,
    patch: Partial<UserProfile>,
  ) => {
    const { error: err } = await supabase
      .from("user_profiles")
      .upsert({ id: userId, ...patch }, { onConflict: "id" });
    if (err) throw new Error(err.message);
    await load();
  };

  const filtered = users.filter((u) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      u.email?.toLowerCase().includes(q) ||
      u.id.toLowerCase().includes(q) ||
      u.profile?.role?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-4">
      {selectedUser && (
        <UserDetailPanel
          row={selectedUser}
          onClose={() => setSelectedUser(null)}
          onSave={handleSave}
        />
      )}

      <SectionCard
        title="All Users"
        description="Signup date, last login, activity summary, and permission controls for tenant admins."
        action={
          <button
            onClick={() => void load()}
            className="rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-medium text-[var(--text)] hover:bg-[var(--surface-2)]"
          >
            Refresh
          </button>
        }
      >
        {/* Search */}
        <div className="mb-3">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, email, or role…"
            className="w-full rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-3 py-1.5 text-sm text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />
        </div>

        {error && (
          <p className="mb-2 text-xs text-red-500">{error}</p>
        )}

        <TableShell
          headers={[
            "User",
            "Role",
            "Signed Up",
            "Last Login",
            "Activity",
            "Permissions",
            "Status",
            "",
          ]}
        >
          {loading ? (
            <LoadingRows />
          ) : filtered.length === 0 ? (
            <EmptyRow
              message={
                users.length === 0
                  ? "No user profiles found. Profiles are created automatically on first sign-in." :"No users match your search."
              }
            />
          ) : (
            filtered.map((u) => (
              <tr
                key={u.id}
                className="border-b border-[var(--border)] last:border-0"
              >
                {/* User */}
                <td className="py-2.5 pr-4">
                  <div className="flex flex-col">
                    <span className="text-xs font-medium text-[var(--text)]">
                      {u.profile?.display_name ?? "—"}
                    </span>
                    <span className="font-mono text-[10px] text-[var(--muted)]">
                      {u.id.slice(0, 8)}…
                    </span>
                  </div>
                </td>

                {/* Role */}
                <td className="py-2.5 pr-4">
                  <span
                    className={cn(
                      "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                      u.profile?.role === "admin" ?"bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400"
                        : u.profile?.role === "analyst" ?"bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400" :"bg-[var(--surface-2)] text-[var(--muted)]",
                    )}
                  >
                    {u.profile?.role ?? "user"}
                  </span>
                </td>

                {/* Signed Up */}
                <td className="py-2.5 pr-4 text-xs text-[var(--muted)]">
                  {fmt(u.created_at)}
                </td>

                {/* Last Login */}
                <td className="py-2.5 pr-4 text-xs text-[var(--muted)]">
                  {fmt(u.last_sign_in_at)}
                </td>

                {/* Activity */}
                <td className="py-2.5 pr-4">
                  <div className="flex flex-col">
                    <span className="text-xs text-[var(--text)]">
                      {u.activity_count} events
                    </span>
                    {u.last_event_type && (
                      <span className="text-[10px] text-[var(--muted)]">
                        last: {u.last_event_type}
                      </span>
                    )}
                  </div>
                </td>

                {/* Permissions summary */}
                <td className="py-2.5 pr-4">
                  <div className="flex flex-wrap gap-1">
                    {u.profile?.is_tenant_admin && (
                      <span className="rounded-full bg-purple-100 px-1.5 py-0.5 text-[10px] font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                        Admin
                      </span>
                    )}
                    {u.profile?.can_access_research && (
                      <span className="rounded-full bg-[var(--surface-2)] px-1.5 py-0.5 text-[10px] text-[var(--muted)]">
                        Research
                      </span>
                    )}
                    {u.profile?.can_access_portfolio && (
                      <span className="rounded-full bg-[var(--surface-2)] px-1.5 py-0.5 text-[10px] text-[var(--muted)]">
                        Portfolio
                      </span>
                    )}
                    {u.profile?.can_access_advisor && (
                      <span className="rounded-full bg-[var(--surface-2)] px-1.5 py-0.5 text-[10px] text-[var(--muted)]">
                        Advisor
                      </span>
                    )}
                    {u.profile?.can_export_reports && (
                      <span className="rounded-full bg-[var(--surface-2)] px-1.5 py-0.5 text-[10px] text-[var(--muted)]">
                        Export
                      </span>
                    )}
                  </div>
                </td>

                {/* Status */}
                <td className="py-2.5 pr-4">
                  <StatusBadge
                    value={u.profile?.is_suspended ? "suspended" : "active"}
                  />
                </td>

                {/* Actions */}
                <td className="py-2.5 text-right">
                  <button
                    onClick={() => setSelectedUser(u)}
                    disabled={u.id === currentUserId}
                    className="text-xs text-[var(--accent)] hover:underline disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {u.id === currentUserId ? "You" : "Edit"}
                  </button>
                </td>
              </tr>
            ))
          )}
        </TableShell>

        {/* Legend */}
        <p className="mt-3 text-[10px] text-[var(--muted)]">
          Profiles are auto-created on first sign-in. Last login is populated from Supabase Auth metadata when available.
        </p>
      </SectionCard>
    </div>
  );
}

// ─── Audit Trail Tab ──────────────────────────────────────────────────────────

interface AuditEvent {
  id: string;
  user_id: string | null;
  actor_email: string | null;
  event_type: string;
  event_category: string;
  resource_type: string | null;
  resource_id: string | null;
  description: string;
  metadata: Record<string, unknown>;
  ip_address: string | null;
  severity: string;
  created_at: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  auth: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  data: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  sharing: "bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400",
  alerts: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  admin: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
};

const SEVERITY_COLORS: Record<string, string> = {
  info: "bg-[var(--surface-2)] text-[var(--muted)]",
  warning: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
  error: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  critical: "bg-red-200 text-red-900 dark:bg-red-900/50 dark:text-red-300",
};

const EVENT_TYPE_LABELS: Record<string, string> = {
  user_login: "Login",
  data_export: "Export",
  watchlist_share: "Share",
  alert_triggered: "Alert",
  admin_action: "Admin",
};

function CategoryBadge({ category }: { category: string }) {
  const color = CATEGORY_COLORS[category] ?? "bg-[var(--surface-2)] text-[var(--muted)]";
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", color)}>
      {category}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const color = SEVERITY_COLORS[severity] ?? SEVERITY_COLORS.info;
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", color)}>
      {severity}
    </span>
  );
}

function AuditTrailTab({ userId }: { userId: string }) {
  const supabase = createClient();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    let query = supabase
      .from("audit_trail")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(200);

    if (categoryFilter !== "all") {
      query = query.eq("event_category", categoryFilter);
    }

    const { data, error: err } = await query;
    if (err) setError(err.message);
    else setEvents((data as AuditEvent[]) ?? []);
    setLoading(false);
  }, [categoryFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = searchQuery.trim()
    ? events.filter(
        (e) =>
          e.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (e.actor_email ?? "").toLowerCase().includes(searchQuery.toLowerCase()) ||
          e.event_type.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : events;

  const categories = ["all", "auth", "data", "sharing", "alerts", "admin"];

  return (
    <div className="space-y-4">
      <SectionCard
        title="Audit Trail"
        description="Comprehensive regulatory audit log of user logins, data exports, watchlist shares, alert triggers, and admin actions."
      >
        {/* Filters */}
        <div className="mb-4 flex flex-wrap items-center gap-2">
          {/* Category filter pills */}
          <div className="flex flex-wrap gap-1">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat)}
                className={cn(
                  "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                  categoryFilter === cat
                    ? "bg-[var(--accent)] text-white"
                    : "border border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]",
                )}
              >
                {cat === "all" ? "All Events" : cat.charAt(0).toUpperCase() + cat.slice(1)}
              </button>
            ))}
          </div>

          {/* Search */}
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search events…"
            className="ml-auto w-48 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] px-2.5 py-1.5 text-xs text-[var(--text)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />

          {/* Refresh */}
          <button
            onClick={() => void load()}
            disabled={loading}
            className="rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-medium text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)] disabled:opacity-50"
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>

        {/* Summary stats */}
        {!loading && !error && (
          <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-5">
            {[
              { label: "Total Events", value: events.length, color: "text-[var(--text)]" },
              { label: "Logins", value: events.filter((e) => e.event_type === "user_login").length, color: "text-blue-600 dark:text-blue-400" },
              { label: "Exports", value: events.filter((e) => e.event_type === "data_export").length, color: "text-purple-600 dark:text-purple-400" },
              { label: "Shares", value: events.filter((e) => e.event_type === "watchlist_share").length, color: "text-teal-600 dark:text-teal-400" },
              { label: "Alerts", value: events.filter((e) => e.event_type === "alert_triggered").length, color: "text-amber-600 dark:text-amber-400" },
            ].map((stat) => (
              <div
                key={stat.label}
                className="rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-center"
              >
                <p className={cn("text-lg font-bold tabular-nums", stat.color)}>{stat.value}</p>
                <p className="text-[10px] text-[var(--muted)]">{stat.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Table */}
        <TableShell
          headers={["Time", "Actor", "Event", "Category", "Description", "Severity", ""]}
        >
          {loading ? (
            <LoadingRows />
          ) : error ? (
            <ErrorRow message={error} />
          ) : filtered.length === 0 ? (
            <EmptyRow message="No audit events found." />
          ) : (
            filtered.map((event) => (
              <>
                <tr
                  key={event.id}
                  className="cursor-pointer border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface-2)]"
                  onClick={() =>
                    setExpandedId((prev) => (prev === event.id ? null : event.id))
                  }
                >
                  <td className="py-2.5 pr-4 text-xs text-[var(--muted)] whitespace-nowrap">
                    {fmt(event.created_at)}
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-[var(--text)] max-w-[140px] truncate">
                    {event.actor_email ?? "—"}
                  </td>
                  <td className="py-2.5 pr-4">
                    <span className="inline-flex items-center rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-xs font-mono text-[var(--text)]">
                      {EVENT_TYPE_LABELS[event.event_type] ?? event.event_type}
                    </span>
                  </td>
                  <td className="py-2.5 pr-4">
                    <CategoryBadge category={event.event_category} />
                  </td>
                  <td className="py-2.5 pr-4 text-xs text-[var(--text)] max-w-[280px] truncate">
                    {event.description}
                  </td>
                  <td className="py-2.5 pr-4">
                    <SeverityBadge severity={event.severity} />
                  </td>
                  <td className="py-2.5 text-right text-xs text-[var(--muted)]">
                    {expandedId === event.id ? "▲" : "▼"}
                  </td>
                </tr>
                {expandedId === event.id && (
                  <tr key={`${event.id}-detail`} className="border-b border-[var(--border)] bg-[var(--surface-2)]">
                    <td colSpan={7} className="px-4 py-3">
                      <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs sm:grid-cols-4">
                        <div>
                          <span className="text-[var(--muted)]">Event ID</span>
                          <p className="font-mono text-[var(--text)] truncate">{event.id}</p>
                        </div>
                        <div>
                          <span className="text-[var(--muted)]">Resource Type</span>
                          <p className="text-[var(--text)]">{event.resource_type ?? "—"}</p>
                        </div>
                        <div>
                          <span className="text-[var(--muted)]">Resource ID</span>
                          <p className="font-mono text-[var(--text)]">{event.resource_id ?? "—"}</p>
                        </div>
                        <div>
                          <span className="text-[var(--muted)]">IP Address</span>
                          <p className="font-mono text-[var(--text)]">{event.ip_address ?? "—"}</p>
                        </div>
                        {Object.keys(event.metadata ?? {}).length > 0 && (
                          <div className="col-span-full">
                            <span className="text-[var(--muted)]">Metadata</span>
                            <pre className="mt-0.5 overflow-x-auto rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--bg)] p-2 text-[10px] text-[var(--text)]">
                              {JSON.stringify(event.metadata, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))
          )}
        </TableShell>

        <p className="mt-3 text-[10px] text-[var(--muted)]">
          Showing up to 200 most recent events. Click a row to expand metadata. For regulatory export, use the Enterprise Console.
        </p>
      </SectionCard>
    </div>
  );
}

// ─── Tab Navigation ───────────────────────────────────────────────────────────

type TabId = "alert-rules" | "threshold-logs" | "watchlist-shares" | "integrations" | "users" | "audit-trail";

const TABS: { id: TabId; label: string }[] = [
  { id: "alert-rules", label: "Alert Rules" },
  { id: "threshold-logs", label: "Threshold Logs" },
  { id: "watchlist-shares", label: "Watchlist Shares" },
  { id: "integrations", label: "Integration Settings" },
  { id: "users", label: "User Management" },
  { id: "audit-trail", label: "Audit Trail" },
];

// ─── Main Export ──────────────────────────────────────────────────────────────

export function AdminPanelWorkspace() {
  const { user, session, status } = useAuth();
  const [activeTab, setActiveTab] = useState<TabId>("alert-rules");

  const userId = user?.subject ?? session?.subject ?? null;

  if (status === "loading") {
    return (
      <div className="flex items-center justify-center py-16 text-sm text-[var(--muted)]">
        Loading…
      </div>
    );
  }

  if (!userId) {
    return (
      <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-8 text-center text-sm text-[var(--muted)]">
        Sign in to access the admin panel.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Tab bar */}
      <div className="flex gap-1 overflow-x-auto rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-1">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "whitespace-nowrap rounded-[var(--radius-sm)] px-3 py-1.5 text-xs font-medium transition-colors",
              activeTab === tab.id
                ? "bg-[var(--accent)] text-white"
                : "text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--text)]",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "alert-rules" && <AlertRulesTab userId={userId} />}
      {activeTab === "threshold-logs" && (
        <ThresholdLogsTab userId={userId} />
      )}
      {activeTab === "watchlist-shares" && (
        <WatchlistSharesTab userId={userId} />
      )}
      {activeTab === "integrations" && (
        <IntegrationSettingsTab userId={userId} />
      )}
      {activeTab === "users" && (
        <UserManagementTab currentUserId={userId} />
      )}
      {activeTab === "audit-trail" && (
        <AuditTrailTab userId={userId} />
      )}
    </div>
  );
}
