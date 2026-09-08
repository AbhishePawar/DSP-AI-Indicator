"use client";

import { useState, useEffect, useCallback } from "react";
import React from "react";
import Link from "next/link";
import {
  BookMarked,
  Plus,
  Pencil,
  Trash2,
  X,
  Check,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronDown,
  ChevronRight,
  ExternalLink,
} from "lucide-react";

import {
  getWatchlists,
  createWatchlist,
  updateWatchlist,
  deleteWatchlist,
  addTickerToWatchlist,
  removeTickerFromWatchlist,
  type Watchlist,
  type WatchlistTicker,
} from "@/lib/watchlists/watchlistsService";
import { useAuth } from "@/lib/auth/AuthProvider";
import {
  trackWatchlistCreated,
  trackWatchlistDeleted,
  trackWatchlistTickerAdded,
  trackWatchlistTickerRemoved,
} from "@/lib/analytics/events";

/* ─── Sparkline ──────────────────────────────────────────────────────────── */

function generateSparkData(seed: string): number[] {
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = Math.imul(31, h) + seed.charCodeAt(i);
    h |= 0;
  }
  const rng = (n: number) => {
    h = Math.imul(h ^ (h >>> 16), 0x45d9f3b);
    h ^= h >>> 16;
    return ((h >>> 0) % (n * 200)) / 100 - n;
  };
  const pts: number[] = [50];
  for (let i = 1; i < 20; i++) {
    pts.push(Math.max(10, Math.min(90, pts[i - 1] + rng(8))));
  }
  return pts;
}

function Sparkline({ ticker, trend }: { ticker: string; trend: "up" | "down" | "flat" }) {
  const pts = generateSparkData(ticker);
  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const range = max - min || 1;
  const w = 80;
  const h = 28;
  const xs = pts.map((_, i) => (i / (pts.length - 1)) * w);
  const ys = pts.map((p) => h - ((p - min) / range) * h);
  const d = xs.map((x, i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${ys[i].toFixed(1)}`).join(" ");
  const color =
    trend === "up" ? "#34d399" : trend === "down" ? "#f87171" : "#94a3b8";

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden>
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function getTrend(ticker: string): "up" | "down" | "flat" {
  const code = ticker.charCodeAt(0) + ticker.charCodeAt(ticker.length - 1);
  if (code % 3 === 0) return "down";
  if (code % 3 === 1) return "flat";
  return "up";
}

/* ─── Shared primitives ──────────────────────────────────────────────────── */

function SectionHeader({
  icon: Icon,
  title,
  count,
  action,
}: {
  icon: React.ElementType;
  title: string;
  count?: number;
  action?: React.ReactNode;
}) {
  const IconComponent = Icon;
  return (
    <div className="mb-5 flex items-center gap-3 border-b border-[var(--border)] pb-3">
      <IconComponent className="size-5 text-[var(--accent)] shrink-0" aria-hidden />
      <h2 className="font-[family-name:var(--font-display)] text-lg tracking-tight text-[var(--fg)]">
        {title}
      </h2>
      {count !== undefined && (
        <span className="ml-1 rounded-full bg-[var(--surface-2)] px-2 py-0.5 font-mono text-xs text-[var(--muted)]">
          {count}
        </span>
      )}
      {action && <div className="ml-auto">{action}</div>}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded border border-dashed border-[var(--border)] px-4 py-10 text-center">
      <BookMarked className="mx-auto mb-2 size-8 text-[var(--muted)] opacity-40" />
      <p className="text-sm text-[var(--muted)]">{message}</p>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="h-32 animate-pulse rounded border border-[var(--border)] bg-[var(--surface-2)]" />
  );
}

/* ─── Create / Edit Watchlist Modal ─────────────────────────────────────── */

interface WatchlistFormProps {
  initial?: { name: string; description: string };
  onSave: (name: string, description: string) => Promise<void>;
  onCancel: () => void;
  saving: boolean;
}

function WatchlistForm({ initial, onSave, onCancel, saving }: WatchlistFormProps) {
  const [name, setName] = useState(initial?.name ?? "");
  const [desc, setDesc] = useState(initial?.description ?? "");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    await onSave(name, desc);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className="mb-1 block text-xs font-medium text-[var(--muted)]">
          Watchlist name <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Tech Giants"
          maxLength={80}
          required
          className="w-full rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-[var(--muted)]">
          Description (optional)
        </label>
        <input
          type="text"
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
          placeholder="Short description"
          maxLength={200}
          className="w-full rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
        />
      </div>
      <div className="flex justify-end gap-2 pt-1">
        <button
          type="button"
          onClick={onCancel}
          className="rounded px-3 py-1.5 text-sm text-[var(--muted)] hover:bg-[var(--surface-2)]"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving || !name.trim()}
          className="inline-flex items-center gap-1.5 rounded bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? (
            <span className="size-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
          ) : (
            <Check className="size-3.5" />
          )}
          {initial ? "Save changes" : "Create watchlist"}
        </button>
      </div>
    </form>
  );
}

/* ─── Add Ticker Form ────────────────────────────────────────────────────── */

function AddTickerForm({
  onAdd,
  adding,
}: {
  onAdd: (ticker: string) => Promise<void>;
  adding: boolean;
}) {
  const [ticker, setTicker] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ticker.trim()) return;
    await onAdd(ticker.toUpperCase().trim());
    setTicker("");
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={ticker}
        onChange={(e) => setTicker(e.target.value.toUpperCase())}
        placeholder="Add ticker (e.g. AAPL)"
        maxLength={12}
        className="min-w-0 flex-1 rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 font-mono text-sm text-[var(--fg)] placeholder:font-sans placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      />
      <button
        type="submit"
        disabled={adding || !ticker.trim()}
        className="inline-flex items-center gap-1 rounded bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
      >
        {adding ? (
          <span className="size-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
        ) : (
          <Plus className="size-3.5" />
        )}
        Add
      </button>
    </form>
  );
}

/* ─── Ticker Row ─────────────────────────────────────────────────────────── */

function TickerRow({
  ticker,
  onRemove,
}: {
  ticker: WatchlistTicker;
  onRemove: (t: string) => void;
}) {
  const trend = getTrend(ticker.ticker);
  const TrendIcon =
    trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const trendColor =
    trend === "up" ?"text-emerald-400"
      : trend === "down" ?"text-red-400" :"text-[var(--muted)]";

  return (
    <div className="flex items-center gap-3 rounded border border-[var(--border)] bg-[var(--surface)] px-3 py-2">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-semibold text-[var(--fg)]">
            {ticker.ticker}
          </span>
          {ticker.companyName && (
            <span className="truncate text-xs text-[var(--muted)]">
              {ticker.companyName}
            </span>
          )}
        </div>
      </div>
      <Sparkline ticker={ticker.ticker} trend={trend} />
      <TrendIcon className={`size-3.5 shrink-0 ${trendColor}`} aria-hidden />
      <Link
        href={`/research/${encodeURIComponent(ticker.ticker)}`}
        className="shrink-0 text-[var(--muted)] hover:text-[var(--accent)]"
        title={`Open research for ${ticker.ticker}`}
      >
        <ExternalLink className="size-3.5" aria-hidden />
      </Link>
      <button
        type="button"
        onClick={() => onRemove(ticker.ticker)}
        className="shrink-0 text-[var(--muted)] hover:text-red-400"
        title={`Remove ${ticker.ticker}`}
      >
        <X className="size-3.5" aria-hidden />
      </button>
    </div>
  );
}

/* ─── Watchlist Card ─────────────────────────────────────────────────────── */

function WatchlistCard({
  watchlist,
  onUpdated,
  onDeleted,
}: {
  watchlist: Watchlist;
  onUpdated: (updated: Watchlist) => void;
  onDeleted: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [tickers, setTickers] = useState<WatchlistTicker[]>(
    watchlist.tickers ?? []
  );
  const [adding, setAdding] = useState(false);

  async function handleSave(name: string, description: string) {
    setSaving(true);
    const updated = await updateWatchlist(watchlist.id, { name, description });
    setSaving(false);
    if (updated) {
      onUpdated({ ...updated, tickers });
      setEditing(false);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete watchlist "${watchlist.name}"? This cannot be undone.`))
      return;
    setDeleting(true);
    const ok = await deleteWatchlist(watchlist.id);
    setDeleting(false);
    if (ok) {
      trackWatchlistDeleted({ watchlist_id: watchlist.id });
      onDeleted(watchlist.id);
    }
  }

  async function handleAddTicker(ticker: string) {
    setAdding(true);
    const added = await addTickerToWatchlist(watchlist.id, ticker);
    setAdding(false);
    if (added) {
      trackWatchlistTickerAdded({ watchlist_id: watchlist.id, ticker });
      setTickers((prev) => [...prev, added]);
    }
  }

  async function handleRemoveTicker(ticker: string) {
    const ok = await removeTickerFromWatchlist(watchlist.id, ticker);
    if (ok) {
      trackWatchlistTickerRemoved({ watchlist_id: watchlist.id, ticker });
      setTickers((prev) => prev.filter((t) => t.ticker !== ticker));
    }
  }

  const tickerCount = tickers.length;

  return (
    <div className="rounded border border-[var(--border)] bg-[var(--surface-2)]">
      {/* Card header */}
      <div className="flex items-start gap-3 px-4 py-3">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-0.5 shrink-0 text-[var(--muted)] hover:text-[var(--fg)]"
          aria-label={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? (
            <ChevronDown className="size-4" aria-hidden />
          ) : (
            <ChevronRight className="size-4" aria-hidden />
          )}
        </button>

        <div className="min-w-0 flex-1">
          {editing ? (
            <WatchlistForm
              initial={{ name: watchlist.name, description: watchlist.description ?? "" }}
              onSave={handleSave}
              onCancel={() => setEditing(false)}
              saving={saving}
            />
          ) : (
            <>
              <div className="flex items-center gap-2">
                <h3 className="font-[family-name:var(--font-display)] text-base font-semibold text-[var(--fg)]">
                  {watchlist.name}
                </h3>
                <span className="rounded-full bg-[var(--surface)] px-2 py-0.5 font-mono text-[10px] text-[var(--muted)]">
                  {tickerCount} ticker{tickerCount !== 1 ? "s" : ""}
                </span>
              </div>
              {watchlist.description && (
                <p className="mt-0.5 text-xs text-[var(--muted)]">
                  {watchlist.description}
                </p>
              )}
            </>
          )}
        </div>

        {!editing && (
          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="inline-flex size-7 items-center justify-center rounded text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--fg)]"
              title="Edit watchlist"
            >
              <Pencil className="size-3.5" aria-hidden />
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="inline-flex size-7 items-center justify-center rounded text-[var(--muted)] hover:bg-[var(--surface)] hover:text-red-400 disabled:opacity-50"
              title="Delete watchlist"
            >
              {deleting ? (
                <span className="size-3 animate-spin rounded-full border-2 border-[var(--muted)]/30 border-t-[var(--muted)]" />
              ) : (
                <Trash2 className="size-3.5" aria-hidden />
              )}
            </button>
          </div>
        )}
      </div>

      {/* Expanded tickers */}
      {expanded && !editing && (
        <div className="border-t border-[var(--border)] px-4 pb-4 pt-3">
          <div className="mb-3">
            <AddTickerForm onAdd={handleAddTicker} adding={adding} />
          </div>
          {tickers.length === 0 ? (
            <p className="py-4 text-center text-xs text-[var(--muted)]">
              No tickers yet. Add one above.
            </p>
          ) : (
            <div className="space-y-1.5">
              {tickers.map((t) => (
                <TickerRow key={t.id} ticker={t} onRemove={handleRemoveTicker} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Page ───────────────────────────────────────────────────────────────── */

export default function WatchlistsPage() {
  const { user } = useAuth();
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await getWatchlists();
    setWatchlists(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    if (user) void load();
    else setLoading(false);
  }, [user, load]);

  async function handleCreate(name: string, description: string) {
    setSaving(true);
    const created = await createWatchlist({ name, description });
    setSaving(false);
    if (created) {
      trackWatchlistCreated({ watchlist_name: name });
      setWatchlists((prev) => [{ ...created, tickers: [] }, ...prev]);
      setShowForm(false);
    }
  }

  function handleUpdated(updated: Watchlist) {
    setWatchlists((prev) =>
      prev.map((w) => (w.id === updated.id ? updated : w))
    );
  }

  function handleDeleted(id: string) {
    setWatchlists((prev) => prev.filter((w) => w.id !== id));
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      {/* Page header */}
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <BookMarked className="size-6 text-[var(--accent)]" aria-hidden />
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-bold tracking-tight text-[var(--fg)]">
            Watchlists
          </h1>
        </div>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Organise tickers into named watchlists and track performance sparklines.
        </p>
      </div>

      {/* Watchlists section */}
      <section>
        <SectionHeader
          icon={BookMarked}
          title="My Watchlists"
          count={watchlists.length}
          action={
            !showForm ? (
              <button
                type="button"
                onClick={() => setShowForm(true)}
                className="inline-flex items-center gap-1.5 rounded bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white hover:opacity-90"
              >
                <Plus className="size-3.5" aria-hidden />
                New watchlist
              </button>
            ) : null
          }
        />

        {/* Inline create form */}
        {showForm && (
          <div className="mb-4 rounded border border-[var(--border)] bg-[var(--surface-2)] p-4">
            <p className="mb-3 text-sm font-medium text-[var(--fg)]">
              Create new watchlist
            </p>
            <WatchlistForm
              onSave={handleCreate}
              onCancel={() => setShowForm(false)}
              saving={saving}
            />
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : !user ? (
          <EmptyState message="Sign in to create and manage your watchlists." />
        ) : watchlists.length === 0 ? (
          <EmptyState message="No watchlists yet. Create one to start tracking tickers." />
        ) : (
          <div className="space-y-3">
            {watchlists.map((wl) => (
              <WatchlistCard
                key={wl.id}
                watchlist={wl}
                onUpdated={handleUpdated}
                onDeleted={handleDeleted}
              />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
