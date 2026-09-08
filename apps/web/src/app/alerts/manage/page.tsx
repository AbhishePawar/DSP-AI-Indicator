"use client";

import { useState, useEffect, useCallback, FormEvent } from "react";
import React from "react";
import Link from "next/link";
import {
  Bell,
  Search,
  TrendingUp,
  Eye,
  Plus,
  Trash2,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle2,
  ArrowLeft,
} from "lucide-react";

import {
  getSavedSearches,
  createSavedSearch,
  deleteSavedSearch,
  getMetricThresholds,
  createMetricThreshold,
  deleteMetricThreshold,
  getWatchlistItems,
  addToWatchlist,
  removeFromWatchlist,
  updateWatchlistNotes,
  type SavedSearch,
  type MetricThreshold,
  type WatchlistItem,
} from "@/lib/alerts/alertsService";
import { useAuth } from "@/lib/auth/AuthProvider";

/* ─── Shared UI primitives ───────────────────────────────────────────────── */

function SectionHeader({ icon: Icon, title, count }: { icon: React.ElementType; title: string; count?: number }) {
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

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest",
        active
          ? "bg-emerald-500/10 text-emerald-400" :"bg-[var(--surface-2)] text-[var(--muted)]",
      ].join(" ")}
    >
      {active ? <CheckCircle2 className="size-3" /> : <AlertCircle className="size-3" />}
      {active ? "Active" : "Paused"}
    </span>
  );
}

/* ─── Saved Searches Section ─────────────────────────────────────────────── */

function SavedSearchesSection() {
  const [items, setItems] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [ticker, setTicker] = useState("");
  const [name, setName] = useState("");
  const [adding, setAdding] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getSavedSearches();
      setItems(data);
    } catch {
      setError("Failed to load saved searches.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!ticker.trim() || !name.trim()) return;
    setAdding(true);
    setError(null);
    try {
      const result = await createSavedSearch(ticker.trim(), name.trim());
      if (result) {
        setItems((prev) => [result, ...prev]);
        setTicker("");
        setName("");
        setShowForm(false);
      }
    } catch {
      setError("Failed to save search.");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(alertId: string) {
    await deleteSavedSearch(alertId);
    setItems((prev) => prev.filter((i) => i.alertId !== alertId));
  }

  return (
    <section>
      <SectionHeader icon={Search} title="Saved Searches" count={items.length} />
      {error && (
        <p className="mb-3 rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">{error}</p>
      )}
      <div className="mb-4">
        <button type="button" onClick={() => setShowForm((v) => !v)}
          className="inline-flex items-center gap-1.5 rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-xs font-medium text-[var(--fg)] hover:bg-[var(--surface)] transition-colors">
          <Plus className="size-3.5" aria-hidden />
          Save new search
          {showForm ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
        </button>
      </div>
      {showForm && (
        <form onSubmit={handleAdd}
          className="mb-5 grid gap-3 rounded border border-[var(--border)] bg-[var(--surface-2)] p-4 sm:grid-cols-3">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">Ticker</label>
            <input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} placeholder="e.g. AAPL" required
              className="min-h-9 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
          </div>
          <div className="flex flex-col gap-1 sm:col-span-2">
            <label className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">Label</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Apple Q4 deep-dive" required
              className="min-h-9 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
          </div>
          <div className="sm:col-span-3 flex gap-2">
            <button type="submit" disabled={adding}
              className="rounded bg-[var(--accent)] px-4 py-1.5 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50 transition-opacity">
              {adding ? "Saving…" : "Save"}
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              className="rounded border border-[var(--border)] px-4 py-1.5 text-xs text-[var(--muted)] hover:text-[var(--fg)] transition-colors">
              Cancel
            </button>
          </div>
        </form>
      )}
      {loading ? (
        <div className="space-y-2">{[1, 2].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded border border-[var(--border)] bg-[var(--surface-2)]" />
        ))}</div>
      ) : items.length === 0 ? (
        <EmptyState message="No saved searches yet. Save a ticker search to monitor it." />
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id} className="flex items-center gap-3 rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2.5">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-[var(--accent)]">{item.ticker}</span>
                  <StatusBadge active />
                </div>
                <p className="mt-0.5 truncate text-xs text-[var(--muted)]">{new Date(item.createdAt).toLocaleDateString()}</p>
              </div>
              <Link href={`/analysis?symbol=${item.ticker}`}
                className="rounded border border-[var(--border)] px-2.5 py-1 text-xs text-[var(--muted)] hover:text-[var(--fg)] hover:bg-[var(--surface)] transition-colors">
                Run
              </Link>
              <button type="button" onClick={() => handleDelete(item.alertId)} aria-label={`Delete saved search for ${item.ticker}`}
                className="rounded p-1 text-[var(--muted)] hover:text-red-400 transition-colors">
                <Trash2 className="size-4" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ─── Metric Thresholds Section ──────────────────────────────────────────── */

const COMMON_METRICS = [
  { name: "pe_ratio", label: "P/E Ratio" },
  { name: "margin_of_safety", label: "Margin of Safety (%)" },
  { name: "revenue_growth", label: "Revenue Growth (%)" },
  { name: "roe", label: "Return on Equity (%)" },
  { name: "debt_to_equity", label: "Debt / Equity" },
  { name: "current_ratio", label: "Current Ratio" },
  { name: "free_cash_flow_yield", label: "FCF Yield (%)" },
];

function MetricThresholdsSection() {
  const [items, setItems] = useState<MetricThreshold[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    ticker: "",
    metricName: COMMON_METRICS[0].name,
    thresholdValue: "",
    direction: "above" as "above" | "below",
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getMetricThresholds();
      setItems(data);
    } catch {
      setError("Failed to load thresholds.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!form.ticker.trim() || !form.thresholdValue) return;
    const metric = COMMON_METRICS.find((m) => m.name === form.metricName);
    if (!metric) return;
    setAdding(true);
    setError(null);
    try {
      const result = await createMetricThreshold({
        ticker: form.ticker.trim(),
        metricName: form.metricName,
        metricLabel: metric.label,
        thresholdValue: parseFloat(form.thresholdValue),
        direction: form.direction,
      });
      if (result) {
        setItems((prev) => [result, ...prev]);
        setForm({ ticker: "", metricName: COMMON_METRICS[0].name, thresholdValue: "", direction: "above" });
        setShowForm(false);
      }
    } catch {
      setError("Failed to create threshold.");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(alertId: string) {
    await deleteMetricThreshold(alertId);
    setItems((prev) => prev.filter((i) => i.alertId !== alertId));
  }

  return (
    <section>
      <SectionHeader icon={TrendingUp} title="Metric Thresholds" count={items.length} />
      {error && (
        <p className="mb-3 rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">{error}</p>
      )}
      <div className="mb-4">
        <button type="button" onClick={() => setShowForm((v) => !v)}
          className="inline-flex items-center gap-1.5 rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-xs font-medium text-[var(--fg)] hover:bg-[var(--surface)] transition-colors">
          <Plus className="size-3.5" aria-hidden />
          Add threshold
          {showForm ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
        </button>
      </div>
      {showForm && (
        <form onSubmit={handleAdd}
          className="mb-5 grid gap-3 rounded border border-[var(--border)] bg-[var(--surface-2)] p-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">Ticker</label>
            <input value={form.ticker} onChange={(e) => setForm((f) => ({ ...f, ticker: e.target.value.toUpperCase() }))} placeholder="e.g. MSFT" required
              className="min-h-9 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">Metric</label>
            <select value={form.metricName} onChange={(e) => setForm((f) => ({ ...f, metricName: e.target.value }))}
              className="min-h-9 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 text-sm text-[var(--fg)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]">
              {COMMON_METRICS.map((m) => <option key={m.name} value={m.name}>{m.label}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">Direction</label>
            <select value={form.direction} onChange={(e) => setForm((f) => ({ ...f, direction: e.target.value as "above" | "below" }))}
              className="min-h-9 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 text-sm text-[var(--fg)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]">
              <option value="above">Goes above</option>
              <option value="below">Falls below</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">Value</label>
            <input type="number" step="any" value={form.thresholdValue} onChange={(e) => setForm((f) => ({ ...f, thresholdValue: e.target.value }))} placeholder="e.g. 25" required
              className="min-h-9 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
          </div>
          <div className="sm:col-span-2 flex gap-2">
            <button type="submit" disabled={adding}
              className="rounded bg-[var(--accent)] px-4 py-1.5 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50 transition-opacity">
              {adding ? "Adding…" : "Add"}
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              className="rounded border border-[var(--border)] px-4 py-1.5 text-xs text-[var(--muted)] hover:text-[var(--fg)] transition-colors">
              Cancel
            </button>
          </div>
        </form>
      )}
      {loading ? (
        <div className="space-y-2">{[1, 2].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded border border-[var(--border)] bg-[var(--surface-2)]" />
        ))}</div>
      ) : items.length === 0 ? (
        <EmptyState message="No metric thresholds set. Add one to get notified when a metric crosses a value." />
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id} className="flex items-center gap-3 rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2.5">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-bold text-[var(--accent)]">{item.ticker}</span>
                  <span className="text-xs text-[var(--fg)]">{item.metricLabel}</span>
                  <span className={["rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold",
                    item.direction === "above" ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"].join(" ")}>
                    {item.direction === "above" ? "▲" : "▼"} {item.thresholdValue}
                  </span>
                  <StatusBadge active />
                </div>
                {item.lastTriggeredAt && (
                  <p className="mt-0.5 text-[10px] text-[var(--muted)]">
                    Last triggered: {new Date(item.lastTriggeredAt).toLocaleDateString()}
                  </p>
                )}
              </div>
              <button type="button" onClick={() => handleDelete(item.alertId)} aria-label={`Delete threshold for ${item.ticker} ${item.metricLabel}`}
                className="rounded p-1 text-[var(--muted)] hover:text-red-400 transition-colors">
                <Trash2 className="size-4" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ─── Watchlist Section ──────────────────────────────────────────────────── */

function WatchlistSection() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingNotes, setEditingNotes] = useState<string | null>(null);
  const [notesValue, setNotesValue] = useState("");
  const [ticker, setTicker] = useState("");
  const [companyName, setCompanyName] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getWatchlistItems();
      setItems(data);
    } catch {
      setError("Failed to load watchlist.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!ticker.trim()) return;
    setAdding(true);
    setError(null);
    try {
      const result = await addToWatchlist(ticker.trim(), companyName.trim() || undefined);
      if (result) {
        setItems((prev) => {
          const exists = prev.find((i) => i.id === result.id);
          return exists ? prev.map((i) => (i.id === result.id ? result : i)) : [result, ...prev];
        });
        setTicker("");
        setCompanyName("");
        setShowForm(false);
      }
    } catch {
      setError("Failed to add to watchlist.");
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(id: string) {
    await removeFromWatchlist(id);
    setItems((prev) => prev.filter((i) => i.id !== id));
  }

  async function handleSaveNotes(id: string) {
    await updateWatchlistNotes(id, notesValue);
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, notes: notesValue } : i)));
    setEditingNotes(null);
  }

  return (
    <section>
      <SectionHeader icon={Eye} title="Watchlist" count={items.length} />
      {error && (
        <p className="mb-3 rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">{error}</p>
      )}
      <div className="mb-4">
        <button type="button" onClick={() => setShowForm((v) => !v)}
          className="inline-flex items-center gap-1.5 rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-1.5 text-xs font-medium text-[var(--fg)] hover:bg-[var(--surface)] transition-colors">
          <Plus className="size-3.5" aria-hidden />
          Add to watchlist
          {showForm ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
        </button>
      </div>
      {showForm && (
        <form onSubmit={handleAdd}
          className="mb-5 grid gap-3 rounded border border-[var(--border)] bg-[var(--surface-2)] p-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">Ticker</label>
            <input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} placeholder="e.g. GOOGL" required
              className="min-h-9 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">Company name (optional)</label>
            <input value={companyName} onChange={(e) => setCompanyName(e.target.value)} placeholder="e.g. Alphabet Inc."
              className="min-h-9 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
          </div>
          <div className="sm:col-span-2 flex gap-2">
            <button type="submit" disabled={adding}
              className="rounded bg-[var(--accent)] px-4 py-1.5 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50 transition-opacity">
              {adding ? "Adding…" : "Add"}
            </button>
            <button type="button" onClick={() => setShowForm(false)}
              className="rounded border border-[var(--border)] px-4 py-1.5 text-xs text-[var(--muted)] hover:text-[var(--fg)] transition-colors">
              Cancel
            </button>
          </div>
        </form>
      )}
      {loading ? (
        <div className="space-y-2">{[1, 2, 3].map((i) => (
          <div key={i} className="h-16 animate-pulse rounded border border-[var(--border)] bg-[var(--surface-2)]" />
        ))}</div>
      ) : items.length === 0 ? (
        <EmptyState message="Your watchlist is empty. Add tickers to monitor them without running a full analysis." />
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id} className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2.5">
              <div className="flex items-center gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-bold text-[var(--accent)]">{item.ticker}</span>
                    {item.companyName && <span className="text-xs text-[var(--fg)]">{item.companyName}</span>}
                    <span className="text-[10px] text-[var(--muted)]">Added {new Date(item.addedAt).toLocaleDateString()}</span>
                  </div>
                  {item.notes && editingNotes !== item.id && (
                    <p className="mt-1 text-xs text-[var(--muted)]">{item.notes}</p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Link href={`/analysis?symbol=${item.ticker}`}
                    className="rounded border border-[var(--border)] px-2.5 py-1 text-xs text-[var(--muted)] hover:text-[var(--fg)] hover:bg-[var(--surface)] transition-colors">
                    Analyse
                  </Link>
                  <button type="button" onClick={() => { setEditingNotes(item.id); setNotesValue(item.notes ?? ""); }}
                    aria-label="Edit notes" className="rounded p-1 text-[var(--muted)] hover:text-[var(--fg)] transition-colors text-xs">
                    Notes
                  </button>
                  <button type="button" onClick={() => handleRemove(item.id)} aria-label={`Remove ${item.ticker} from watchlist`}
                    className="rounded p-1 text-[var(--muted)] hover:text-red-400 transition-colors">
                    <Trash2 className="size-4" aria-hidden />
                  </button>
                </div>
              </div>
              {editingNotes === item.id && (
                <div className="mt-2 flex gap-2">
                  <input value={notesValue} onChange={(e) => setNotesValue(e.target.value)} placeholder="Add notes…"
                    className="min-h-8 flex-1 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 text-xs text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
                  <button type="button" onClick={() => handleSaveNotes(item.id)}
                    className="rounded bg-[var(--accent)] px-3 py-1 text-xs font-semibold text-white hover:opacity-90 transition-opacity">
                    Save
                  </button>
                  <button type="button" onClick={() => setEditingNotes(null)}
                    className="rounded border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)] hover:text-[var(--fg)] transition-colors">
                    Cancel
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ─── Auth gate ──────────────────────────────────────────────────────────── */

function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, status } = useAuth();
  const loading = status === "restoring" || status === "loading" || status === "refreshing";

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 animate-pulse rounded border border-[var(--border)] bg-[var(--surface-2)]" />
        ))}
      </div>
    );
  }

  if (!user) {
    return (
      <div className="rounded border border-[var(--border)] bg-[var(--surface-2)] px-6 py-10 text-center">
        <Bell className="mx-auto mb-3 size-8 text-[var(--muted)]" aria-hidden />
        <p className="text-sm text-[var(--fg)]">Sign in to manage your alerts and watchlist.</p>
        <Link href="/login"
          className="mt-4 inline-block rounded bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90 transition-opacity">
          Sign in
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}

/* ─── Page ───────────────────────────────────────────────────────────────── */

export default function AlertsManagePage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 border-b border-[var(--border)] pb-6">
        <Link href="/alerts"
          className="mb-4 inline-flex items-center gap-1.5 text-xs text-[var(--muted)] hover:text-[var(--fg)] transition-colors">
          <ArrowLeft className="size-3.5" aria-hidden />
          Back to Alerts
        </Link>
        <div className="flex items-center gap-3">
          <Bell className="size-7 text-[var(--accent)] shrink-0" aria-hidden />
          <h1 className="font-[family-name:var(--font-display)] text-3xl tracking-tight text-[var(--fg)]">
            Manage Alert Rules
          </h1>
        </div>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-[var(--muted)]">
          Create and manage saved searches, metric thresholds, and watchlist entries.
        </p>
      </div>

      <AuthGate>
        <div className="space-y-10">
          <SavedSearchesSection />
          <MetricThresholdsSection />
          <WatchlistSection />
        </div>
      </AuthGate>
    </div>
  );
}
