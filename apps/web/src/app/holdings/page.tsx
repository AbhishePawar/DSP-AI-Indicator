"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  TrendingUp,
  TrendingDown,
  Plus,
  Trash2,
  BarChart2,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { PageHeader } from "@/components/layout/PageHeader";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Holding {
  id: string;
  ticker: string;
  companyName: string;
  buyPrice: number;
  quantity: number;
  notes?: string;
  createdAt: string;
}

interface HoldingWithMetrics extends Holding {
  currentPrice: number;
  currentValue: number;
  costBasis: number;
  pnl: number;
  pnlPct: number;
  allocationPct: number;
  sparkline: number[];
}

// ─── Sparkline helpers ────────────────────────────────────────────────────────

/** Deterministic pseudo-random walk seeded by ticker string */
function seededRandom(seed: string, index: number): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (Math.imul(31, h) + seed.charCodeAt(i)) | 0;
  h = (Math.imul(h, index + 1) ^ (h >>> 16)) | 0;
  return ((h >>> 0) / 0xffffffff);
}

function generateSparkline(ticker: string, buyPrice: number): number[] {
  const points: number[] = [buyPrice];
  for (let i = 1; i < 30; i++) {
    const prev = points[i - 1];
    const delta = (seededRandom(ticker, i) - 0.48) * prev * 0.025;
    points.push(Math.max(prev + delta, prev * 0.7));
  }
  return points;
}

/** Simulated current price: last point of sparkline */
function simulatedCurrentPrice(ticker: string, buyPrice: number): number {
  const sparkline = generateSparkline(ticker, buyPrice);
  return sparkline[sparkline.length - 1];
}

// ─── SVG Sparkline ────────────────────────────────────────────────────────────

function Sparkline({ data, positive }: { data: number[]; positive: boolean }) {
  if (!data.length) return null;
  const w = 80;
  const h = 28;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - ((v - min) / range) * (h - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");
  const color = positive ? "#22c55e" : "#ef4444";
  const fillPts = `0,${h} ${pts} ${w},${h}`;
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polygon points={fillPts} fill={color} fillOpacity={0.12} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
}

// ─── Add Holding Form ─────────────────────────────────────────────────────────

interface AddHoldingFormProps {
  onAdd: (ticker: string, companyName: string, buyPrice: number, quantity: number) => Promise<void>;
  loading: boolean;
}

function AddHoldingForm({ onAdd, loading }: AddHoldingFormProps) {
  const [ticker, setTicker] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [buyPrice, setBuyPrice] = useState("");
  const [quantity, setQuantity] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const bp = parseFloat(buyPrice);
    const qty = parseFloat(quantity);
    if (!ticker.trim()) return setError("Ticker is required.");
    if (isNaN(bp) || bp <= 0) return setError("Buy price must be a positive number.");
    if (isNaN(qty) || qty <= 0) return setError("Quantity must be a positive number.");
    try {
      await onAdd(ticker.trim().toUpperCase(), companyName.trim(), bp, qty);
      setTicker("");
      setCompanyName("");
      setBuyPrice("");
      setQuantity("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add holding.");
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"
    >
      <h2 className="mb-4 text-sm font-semibold text-[var(--fg)]">Add Holding</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--muted)]">Ticker *</label>
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="AAPL"
            className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--muted)]">Company Name</label>
          <input
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="Apple Inc."
            className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--muted)]">Buy Price *</label>
          <input
            value={buyPrice}
            onChange={(e) => setBuyPrice(e.target.value)}
            placeholder="150.00"
            type="number"
            min="0"
            step="any"
            className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--muted)]">Quantity *</label>
          <input
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="10"
            type="number"
            min="0"
            step="any"
            className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--fg)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
          />
        </div>
      </div>
      {error && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-red-500">
          <AlertCircle className="size-3.5 shrink-0" />
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={loading}
        className="mt-4 inline-flex items-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
      >
        {loading ? (
          <RefreshCw className="size-4 animate-spin" />
        ) : (
          <Plus className="size-4" />
        )}
        Add Holding
      </button>
    </form>
  );
}

// ─── Summary Cards ────────────────────────────────────────────────────────────

function SummaryCards({ holdings }: { holdings: HoldingWithMetrics[] }) {
  const totalValue = holdings.reduce((s, h) => s + h.currentValue, 0);
  const totalCost = holdings.reduce((s, h) => s + h.costBasis, 0);
  const totalPnl = totalValue - totalCost;
  const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;
  const positive = totalPnl >= 0;

  const cards = [
    {
      label: "Portfolio Value",
      value: `$${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      sub: `${holdings.length} position${holdings.length !== 1 ? "s" : ""}`,
      accent: false,
    },
    {
      label: "Total Cost Basis",
      value: `$${totalCost.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      sub: "invested capital",
      accent: false,
    },
    {
      label: "Total P&L",
      value: `${positive ? "+" : ""}$${totalPnl.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
      sub: `${positive ? "+" : ""}${totalPnlPct.toFixed(2)}%`,
      accent: true,
      positive,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {cards.map((c) => (
        <div
          key={c.label}
          className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5"
        >
          <p className="text-xs text-[var(--muted)]">{c.label}</p>
          <p
            className={`mt-1 text-xl font-semibold ${
              c.accent
                ? c.positive
                  ? "text-green-500" :"text-red-500" :"text-[var(--fg)]"
            }`}
          >
            {c.value}
          </p>
          <p className="mt-0.5 text-xs text-[var(--muted)]">{c.sub}</p>
        </div>
      ))}
    </div>
  );
}

// ─── Holdings Table ───────────────────────────────────────────────────────────

interface HoldingsTableProps {
  holdings: HoldingWithMetrics[];
  onDelete: (id: string) => Promise<void>;
  deletingId: string | null;
}

function HoldingsTable({ holdings, onDelete, deletingId }: HoldingsTableProps) {
  if (!holdings.length) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[var(--border)] bg-[var(--surface)] py-16 text-center">
        <BarChart2 className="mb-3 size-10 text-[var(--muted)]" />
        <p className="text-sm font-medium text-[var(--fg)]">No holdings yet</p>
        <p className="mt-1 text-xs text-[var(--muted)]">Add your first position using the form above.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--surface)]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-xs text-[var(--muted)]">
            <th className="px-4 py-3 font-medium">Ticker</th>
            <th className="px-4 py-3 font-medium">Trend (30d)</th>
            <th className="px-4 py-3 text-right font-medium">Buy Price</th>
            <th className="px-4 py-3 text-right font-medium">Qty</th>
            <th className="px-4 py-3 text-right font-medium">Cost Basis</th>
            <th className="px-4 py-3 text-right font-medium">Current Value</th>
            <th className="px-4 py-3 text-right font-medium">P&amp;L</th>
            <th className="px-4 py-3 text-right font-medium">Allocation</th>
            <th className="px-4 py-3 text-right font-medium"></th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => {
            const positive = h.pnl >= 0;
            return (
              <tr
                key={h.id}
                className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface-2)] transition-colors"
              >
                <td className="px-4 py-3">
                  <p className="font-semibold text-[var(--fg)]">{h.ticker}</p>
                  {h.companyName && (
                    <p className="text-xs text-[var(--muted)] truncate max-w-[120px]">{h.companyName}</p>
                  )}
                </td>
                <td className="px-4 py-3">
                  <Sparkline data={h.sparkline} positive={positive} />
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--fg)]">
                  ${h.buyPrice.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--fg)]">
                  {h.quantity.toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--fg)]">
                  ${h.costBasis.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--fg)]">
                  ${h.currentValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  <span className={`inline-flex items-center gap-1 font-medium ${positive ? "text-green-500" : "text-red-500"}`}>
                    {positive ? <TrendingUp className="size-3.5" /> : <TrendingDown className="size-3.5" />}
                    {positive ? "+" : ""}
                    {h.pnlPct.toFixed(2)}%
                  </span>
                  <p className="text-xs text-[var(--muted)]">
                    {positive ? "+" : ""}${h.pnl.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </p>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-[var(--surface-2)]">
                      <div
                        className="h-full rounded-full bg-[var(--accent)]"
                        style={{ width: `${Math.min(h.allocationPct, 100)}%` }}
                      />
                    </div>
                    <span className="w-10 text-right text-xs tabular-nums text-[var(--muted)]">
                      {h.allocationPct.toFixed(1)}%
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => onDelete(h.id)}
                    disabled={deletingId === h.id}
                    className="inline-flex size-7 items-center justify-center rounded-lg text-[var(--muted)] transition hover:bg-red-500/10 hover:text-red-500 disabled:opacity-40"
                    aria-label={`Remove ${h.ticker}`}
                  >
                    {deletingId === h.id ? (
                      <RefreshCw className="size-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="size-3.5" />
                    )}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── Allocation Breakdown ─────────────────────────────────────────────────────

function AllocationBreakdown({ holdings }: { holdings: HoldingWithMetrics[] }) {
  if (!holdings.length) return null;
  const COLORS = [
    "bg-blue-500", "bg-violet-500", "bg-emerald-500", "bg-amber-500",
    "bg-rose-500", "bg-cyan-500", "bg-fuchsia-500", "bg-lime-500",
  ];
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
      <h2 className="mb-4 text-sm font-semibold text-[var(--fg)]">Allocation Breakdown</h2>
      <div className="mb-3 flex h-3 w-full overflow-hidden rounded-full">
        {holdings.map((h, i) => (
          <div
            key={h.id}
            className={`${COLORS[i % COLORS.length]} transition-all`}
            style={{ width: `${h.allocationPct}%` }}
            title={`${h.ticker}: ${h.allocationPct.toFixed(1)}%`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-3">
        {holdings.map((h, i) => (
          <div key={h.id} className="flex items-center gap-1.5">
            <span className={`size-2.5 rounded-full ${COLORS[i % COLORS.length]}`} />
            <span className="text-xs text-[var(--muted)]">
              {h.ticker} <span className="font-medium text-[var(--fg)]">{h.allocationPct.toFixed(1)}%</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

function HoldingsContent() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [loadingData, setLoadingData] = useState(true);
  const [addingHolding, setAddingHolding] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const supabase = useMemo(() => createClient(), []);
  const userIdRef = useRef<string | null>(null);

  const fetchHoldings = useCallback(async () => {
    setLoadingData(true);
    setFetchError(null);
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { setLoadingData(false); return; }
      userIdRef.current = user.id;

      const { data, error } = await supabase
        .from("holdings")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false });

      if (error) {
        setFetchError(error.message);
      } else {
        setHoldings(
          (data || []).map((row) => ({
            id: row.id,
            ticker: row.ticker,
            companyName: row.company_name ?? "",
            buyPrice: Number(row.buy_price),
            quantity: Number(row.quantity),
            notes: row.notes ?? "",
            createdAt: row.created_at,
          })),
        );
      }
    } catch (err: unknown) {
      setFetchError(err instanceof Error ? err.message : "Failed to load holdings.");
    } finally {
      setLoadingData(false);
    }
  }, [supabase]);

  // Initial fetch
  useEffect(() => { fetchHoldings(); }, [fetchHoldings]);

  // Real-time subscription — auto-refresh portfolio total, daily gains, and position values
  useEffect(() => {
    let channel: ReturnType<typeof supabase.channel> | null = null;

    async function subscribe() {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;
      userIdRef.current = user.id;

      channel = supabase
        .channel(`holdings_realtime_${user.id}`)
        .on(
          "postgres_changes",
          {
            event: "*",
            schema: "public",
            table: "holdings",
            filter: `user_id=eq.${user.id}`,
          },
          (payload) => {
            if (payload.eventType === "INSERT") {
              const row = payload.new as Record<string, unknown>;
              const newHolding: Holding = {
                id: row.id as string,
                ticker: row.ticker as string,
                companyName: (row.company_name as string) ?? "",
                buyPrice: Number(row.buy_price),
                quantity: Number(row.quantity),
                notes: (row.notes as string) ?? "",
                createdAt: row.created_at as string,
              };
              setHoldings((prev) => {
                // Avoid duplicates
                if (prev.some((h) => h.id === newHolding.id)) return prev;
                return [newHolding, ...prev];
              });
            } else if (payload.eventType === "UPDATE") {
              const row = payload.new as Record<string, unknown>;
              setHoldings((prev) =>
                prev.map((h) =>
                  h.id === (row.id as string)
                    ? {
                        ...h,
                        ticker: row.ticker as string,
                        companyName: (row.company_name as string) ?? "",
                        buyPrice: Number(row.buy_price),
                        quantity: Number(row.quantity),
                        notes: (row.notes as string) ?? "",
                      }
                    : h,
                ),
              );
            } else if (payload.eventType === "DELETE") {
              const row = payload.old as Record<string, unknown>;
              setHoldings((prev) => prev.filter((h) => h.id !== (row.id as string)));
            }
          },
        )
        .subscribe();
    }

    subscribe();

    return () => {
      if (channel) {
        supabase.removeChannel(channel);
      }
    };
  }, [supabase]);

  const holdingsWithMetrics = useMemo<HoldingWithMetrics[]>(() => {
    const enriched = holdings.map((h) => {
      const sparkline = generateSparkline(h.ticker, h.buyPrice);
      const currentPrice = simulatedCurrentPrice(h.ticker, h.buyPrice);
      const currentValue = currentPrice * h.quantity;
      const costBasis = h.buyPrice * h.quantity;
      const pnl = currentValue - costBasis;
      const pnlPct = costBasis > 0 ? (pnl / costBasis) * 100 : 0;
      return { ...h, sparkline, currentPrice, currentValue, costBasis, pnl, pnlPct, allocationPct: 0 };
    });
    const totalValue = enriched.reduce((s, h) => s + h.currentValue, 0);
    return enriched.map((h) => ({
      ...h,
      allocationPct: totalValue > 0 ? (h.currentValue / totalValue) * 100 : 0,
    }));
  }, [holdings]);

  async function handleAdd(ticker: string, companyName: string, buyPrice: number, quantity: number) {
    setAddingHolding(true);
    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) throw new Error("Not authenticated.");

      const { error } = await supabase.from("holdings").upsert(
        {
          user_id: user.id,
          ticker,
          company_name: companyName || null,
          buy_price: buyPrice,
          quantity,
        },
        { onConflict: "user_id,ticker" },
      );

      if (error) throw new Error(error.message);
      // Real-time subscription will handle the state update via INSERT/UPDATE event
    } finally {
      setAddingHolding(false);
    }
  }

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      const { error } = await supabase.from("holdings").delete().eq("id", id);
      if (error) throw new Error(error.message);
      // Real-time subscription will handle the state update via DELETE event
      // Optimistic removal as fallback
      setHoldings((prev) => prev.filter((h) => h.id !== id));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Holdings"
        description="Track positions with buy price and quantity. View current value, P&L, and portfolio allocation per ticker."
      />

      <AddHoldingForm onAdd={handleAdd} loading={addingHolding} />

      {fetchError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-500">
          <AlertCircle className="size-4 shrink-0" />
          {fetchError}
        </div>
      )}

      {loadingData ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-[var(--surface)]" />
          ))}
        </div>
      ) : (
        <>
          {holdingsWithMetrics.length > 0 && <SummaryCards holdings={holdingsWithMetrics} />}
          <HoldingsTable
            holdings={holdingsWithMetrics}
            onDelete={handleDelete}
            deletingId={deletingId}
          />
          <AllocationBreakdown holdings={holdingsWithMetrics} />
        </>
      )}
    </div>
  );
}

export default function HoldingsPage() {
  return (
    <ProtectedRoute>
      <HoldingsContent />
    </ProtectedRoute>
  );
}
