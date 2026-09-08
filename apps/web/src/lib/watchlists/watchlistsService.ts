import { createClient } from "@/lib/supabase/client";

export interface Watchlist {
  id: string;
  userId: string;
  name: string;
  description: string | null;
  createdAt: string;
  updatedAt: string;
  tickers?: WatchlistTicker[];
}

export interface WatchlistTicker {
  id: string;
  watchlistId: string;
  userId: string;
  ticker: string;
  companyName: string | null;
  notes: string | null;
  addedAt: string;
}

// ── Watchlists CRUD ───────────────────────────────────────────────────────────

export async function getWatchlists(): Promise<Watchlist[]> {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return [];

  const { data, error } = await supabase
    .from("watchlists")
    .select("*, watchlist_tickers(*)")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  if (error) {
    console.log("getWatchlists error:", error.message);
    return [];
  }

  return (data ?? []).map(mapWatchlist);
}

export async function getWatchlistById(id: string): Promise<Watchlist | null> {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const { data, error } = await supabase
    .from("watchlists")
    .select("*, watchlist_tickers(*)")
    .eq("id", id)
    .eq("user_id", user.id)
    .single();

  if (error || !data) {
    console.log("getWatchlistById error:", error?.message);
    return null;
  }

  return mapWatchlist(data);
}

export async function createWatchlist(params: {
  name: string;
  description?: string;
}): Promise<Watchlist | null> {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const { data, error } = await supabase
    .from("watchlists")
    .insert({
      user_id: user.id,
      name: params.name.trim(),
      description: params.description?.trim() || null,
    })
    .select()
    .single();

  if (error || !data) {
    console.log("createWatchlist error:", error?.message);
    return null;
  }

  return mapWatchlist(data);
}

export async function updateWatchlist(
  id: string,
  params: { name?: string; description?: string }
): Promise<Watchlist | null> {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const updates: Record<string, unknown> = {};
  if (params.name !== undefined) updates.name = params.name.trim();
  if (params.description !== undefined)
    updates.description = params.description.trim() || null;

  const { data, error } = await supabase
    .from("watchlists")
    .update(updates)
    .eq("id", id)
    .eq("user_id", user.id)
    .select()
    .single();

  if (error || !data) {
    console.log("updateWatchlist error:", error?.message);
    return null;
  }

  return mapWatchlist(data);
}

export async function deleteWatchlist(id: string): Promise<boolean> {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return false;

  const { error } = await supabase
    .from("watchlists")
    .delete()
    .eq("id", id)
    .eq("user_id", user.id);

  if (error) {
    console.log("deleteWatchlist error:", error.message);
    return false;
  }
  return true;
}

// ── Watchlist Tickers CRUD ────────────────────────────────────────────────────

export async function addTickerToWatchlist(
  watchlistId: string,
  ticker: string,
  companyName?: string
): Promise<WatchlistTicker | null> {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const { data, error } = await supabase
    .from("watchlist_tickers")
    .insert({
      watchlist_id: watchlistId,
      user_id: user.id,
      ticker: ticker.toUpperCase().trim(),
      company_name: companyName?.trim() || null,
    })
    .select()
    .single();

  if (error || !data) {
    console.log("addTickerToWatchlist error:", error?.message);
    return null;
  }

  return mapTicker(data);
}

export async function removeTickerFromWatchlist(
  watchlistId: string,
  ticker: string
): Promise<boolean> {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return false;

  const { error } = await supabase
    .from("watchlist_tickers")
    .delete()
    .eq("watchlist_id", watchlistId)
    .eq("ticker", ticker.toUpperCase())
    .eq("user_id", user.id);

  if (error) {
    console.log("removeTickerFromWatchlist error:", error.message);
    return false;
  }
  return true;
}

// ── Mappers ───────────────────────────────────────────────────────────────────

function mapWatchlist(row: Record<string, unknown>): Watchlist {
  return {
    id: row.id as string,
    userId: row.user_id as string,
    name: row.name as string,
    description: (row.description as string | null) ?? null,
    createdAt: row.created_at as string,
    updatedAt: row.updated_at as string,
    tickers: Array.isArray(row.watchlist_tickers)
      ? (row.watchlist_tickers as Record<string, unknown>[]).map(mapTicker)
      : [],
  };
}

function mapTicker(row: Record<string, unknown>): WatchlistTicker {
  return {
    id: row.id as string,
    watchlistId: row.watchlist_id as string,
    userId: row.user_id as string,
    ticker: row.ticker as string,
    companyName: (row.company_name as string | null) ?? null,
    notes: (row.notes as string | null) ?? null,
    addedAt: row.added_at as string,
  };
}
