import { createClient } from "@/lib/supabase/client";

export interface UserAlert {
  id: string;
  userId: string;
  alertType: "saved_search" | "metric_threshold" | "watchlist";
  name: string;
  description: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface MetricThreshold {
  id: string;
  alertId: string;
  userId: string;
  ticker: string;
  metricName: string;
  metricLabel: string;
  thresholdValue: number;
  direction: "above" | "below";
  lastTriggeredAt: string | null;
  createdAt: string;
}

export interface SavedSearch {
  id: string;
  alertId: string;
  userId: string;
  ticker: string;
  searchParams: Record<string, unknown>;
  lastRunAt: string | null;
  createdAt: string;
}

export interface WatchlistItem {
  id: string;
  userId: string;
  ticker: string;
  companyName: string | null;
  notes: string | null;
  addedAt: string;
}

export interface AlertTrigger {
  id: string;
  alertId: string;
  userId: string;
  ticker: string;
  metricLabel: string | null;
  thresholdValue: number | null;
  direction: "above" | "below" | null;
  triggeredValue: number | null;
  triggeredAt: string;
  status: string;
}

export interface AlertsPerformanceSummary {
  totalActive: number;
  totalPaused: number;
  totalTriggersLast30Days: number;
  totalTriggersLast7Days: number;
  mostTriggeredTicker: string | null;
  watchlistCount: number;
}

// ── Active Alert Rules ────────────────────────────────────────────────────────

export async function getActiveAlertRules(): Promise<UserAlert[]> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return [];

  const { data, error } = await supabase
    .from("user_alerts")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  if (error) {
    console.log("getActiveAlertRules error:", error.message);
    return [];
  }

  return (data ?? []).map((row) => ({
    id: row.id,
    userId: row.user_id,
    alertType: row.alert_type,
    name: row.name,
    description: row.description,
    isActive: row.is_active,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }));
}

// ── Metric Thresholds ─────────────────────────────────────────────────────────

export async function getMetricThresholds(): Promise<MetricThreshold[]> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return [];

  const { data, error } = await supabase
    .from("metric_thresholds")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  if (error) {
    console.log("getMetricThresholds error:", error.message);
    return [];
  }

  return (data ?? []).map((row) => ({
    id: row.id,
    alertId: row.alert_id,
    userId: row.user_id,
    ticker: row.ticker,
    metricName: row.metric_name,
    metricLabel: row.metric_label,
    thresholdValue: Number(row.threshold_value),
    direction: row.direction,
    lastTriggeredAt: row.last_triggered_at,
    createdAt: row.created_at,
  }));
}

export async function createMetricThreshold(params: {
  ticker: string;
  metricName: string;
  metricLabel: string;
  thresholdValue: number;
  direction: "above" | "below";
}): Promise<MetricThreshold | null> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;

  const { data: alertData, error: alertError } = await supabase
    .from("user_alerts")
    .insert({
      user_id: user.id,
      alert_type: "metric_threshold",
      name: `${params.ticker} ${params.metricLabel}`,
      is_active: true,
    })
    .select()
    .single();

  if (alertError || !alertData) {
    console.log("createMetricThreshold alert error:", alertError?.message);
    return null;
  }

  const { data, error } = await supabase
    .from("metric_thresholds")
    .insert({
      alert_id: alertData.id,
      user_id: user.id,
      ticker: params.ticker.toUpperCase(),
      metric_name: params.metricName,
      metric_label: params.metricLabel,
      threshold_value: params.thresholdValue,
      direction: params.direction,
    })
    .select()
    .single();

  if (error || !data) {
    console.log("createMetricThreshold error:", error?.message);
    return null;
  }

  return {
    id: data.id,
    alertId: data.alert_id,
    userId: data.user_id,
    ticker: data.ticker,
    metricName: data.metric_name,
    metricLabel: data.metric_label,
    thresholdValue: Number(data.threshold_value),
    direction: data.direction,
    lastTriggeredAt: data.last_triggered_at,
    createdAt: data.created_at,
  };
}

export async function deleteMetricThreshold(alertId: string): Promise<void> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return;

  await supabase
    .from("metric_thresholds")
    .delete()
    .eq("alert_id", alertId)
    .eq("user_id", user.id);

  await supabase
    .from("user_alerts")
    .delete()
    .eq("id", alertId)
    .eq("user_id", user.id);
}

// ── Saved Searches ────────────────────────────────────────────────────────────

export async function getSavedSearches(): Promise<SavedSearch[]> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return [];

  const { data, error } = await supabase
    .from("saved_searches")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  if (error) {
    console.log("getSavedSearches error:", error.message);
    return [];
  }

  return (data ?? []).map((row) => ({
    id: row.id,
    alertId: row.alert_id,
    userId: row.user_id,
    ticker: row.ticker,
    searchParams: row.search_params ?? {},
    lastRunAt: row.last_run_at,
    createdAt: row.created_at,
  }));
}

export async function createSavedSearch(ticker: string, name: string): Promise<SavedSearch | null> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;

  const { data: alertData, error: alertError } = await supabase
    .from("user_alerts")
    .insert({
      user_id: user.id,
      alert_type: "saved_search",
      name,
      is_active: true,
    })
    .select()
    .single();

  if (alertError || !alertData) {
    console.log("createSavedSearch alert error:", alertError?.message);
    return null;
  }

  const { data, error } = await supabase
    .from("saved_searches")
    .insert({
      alert_id: alertData.id,
      user_id: user.id,
      ticker: ticker.toUpperCase(),
      search_params: { name },
    })
    .select()
    .single();

  if (error || !data) {
    console.log("createSavedSearch error:", error?.message);
    return null;
  }

  return {
    id: data.id,
    alertId: data.alert_id,
    userId: data.user_id,
    ticker: data.ticker,
    searchParams: data.search_params ?? {},
    lastRunAt: data.last_run_at,
    createdAt: data.created_at,
  };
}

export async function deleteSavedSearch(alertId: string): Promise<void> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return;

  await supabase
    .from("saved_searches")
    .delete()
    .eq("alert_id", alertId)
    .eq("user_id", user.id);

  await supabase
    .from("user_alerts")
    .delete()
    .eq("id", alertId)
    .eq("user_id", user.id);
}

// ── Watchlist ─────────────────────────────────────────────────────────────────

export async function getWatchlistItems(): Promise<WatchlistItem[]> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return [];

  const { data, error } = await supabase
    .from("watchlist_items")
    .select("*")
    .eq("user_id", user.id)
    .order("added_at", { ascending: false });

  if (error) {
    console.log("getWatchlistItems error:", error.message);
    return [];
  }

  return (data ?? []).map((row) => ({
    id: row.id,
    userId: row.user_id,
    ticker: row.ticker,
    companyName: row.company_name,
    notes: row.notes,
    addedAt: row.added_at,
  }));
}

export async function addToWatchlist(ticker: string, companyName?: string): Promise<WatchlistItem | null> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;

  const { data, error } = await supabase
    .from("watchlist_items")
    .upsert(
      { user_id: user.id, ticker: ticker.toUpperCase(), company_name: companyName ?? null },
      { onConflict: "user_id,ticker" }
    )
    .select()
    .single();

  if (error || !data) {
    console.log("addToWatchlist error:", error?.message);
    return null;
  }

  return {
    id: data.id,
    userId: data.user_id,
    ticker: data.ticker,
    companyName: data.company_name,
    notes: data.notes,
    addedAt: data.added_at,
  };
}

export async function removeFromWatchlist(id: string): Promise<void> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return;

  await supabase.from("watchlist_items").delete().eq("id", id).eq("user_id", user.id);
}

export async function updateWatchlistNotes(id: string, notes: string): Promise<void> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return;

  await supabase.from("watchlist_items").update({ notes }).eq("id", id).eq("user_id", user.id);
}

// ── Recent Triggers ───────────────────────────────────────────────────────────

export async function getRecentTriggers(limit = 20): Promise<AlertTrigger[]> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return [];

  const { data, error } = await supabase
    .from("alert_triggers")
    .select("*")
    .eq("user_id", user.id)
    .order("triggered_at", { ascending: false })
    .limit(limit);

  if (error) {
    console.log("getRecentTriggers error:", error.message);
    return [];
  }

  return (data ?? []).map((row) => ({
    id: row.id,
    alertId: row.alert_id,
    userId: row.user_id,
    ticker: row.ticker,
    metricLabel: row.metric_label,
    thresholdValue: row.threshold_value != null ? Number(row.threshold_value) : null,
    direction: row.direction,
    triggeredValue: row.triggered_value != null ? Number(row.triggered_value) : null,
    triggeredAt: row.triggered_at,
    status: row.status,
  }));
}

// ── Performance Summary ───────────────────────────────────────────────────────

export async function getAlertsPerformanceSummary(): Promise<AlertsPerformanceSummary> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) {
    return { totalActive: 0, totalPaused: 0, totalTriggersLast30Days: 0, totalTriggersLast7Days: 0, mostTriggeredTicker: null, watchlistCount: 0 };
  }

  const [alertsRes, triggersRes, watchlistRes] = await Promise.all([
    supabase.from("user_alerts").select("is_active").eq("user_id", user.id),
    supabase
      .from("alert_triggers")
      .select("ticker, triggered_at")
      .eq("user_id", user.id)
      .gte("triggered_at", new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()),
    supabase.from("watchlist_items").select("id").eq("user_id", user.id),
  ]);

  const alerts = alertsRes.data ?? [];
  const triggers = triggersRes.data ?? [];
  const now = Date.now();
  const sevenDaysAgo = now - 7 * 24 * 60 * 60 * 1000;

  const totalActive = alerts.filter((a) => a.is_active).length;
  const totalPaused = alerts.filter((a) => !a.is_active).length;
  const totalTriggersLast30Days = triggers.length;
  const totalTriggersLast7Days = triggers.filter(
    (t) => new Date(t.triggered_at).getTime() >= sevenDaysAgo
  ).length;

  const tickerCounts: Record<string, number> = {};
  for (const t of triggers) {
    tickerCounts[t.ticker] = (tickerCounts[t.ticker] ?? 0) + 1;
  }
  const mostTriggeredTicker = Object.keys(tickerCounts).length > 0
    ? Object.entries(tickerCounts).sort((a, b) => b[1] - a[1])[0][0]
    : null;

  return {
    totalActive,
    totalPaused,
    totalTriggersLast30Days,
    totalTriggersLast7Days,
    mostTriggeredTicker,
    watchlistCount: (watchlistRes.data ?? []).length,
  };
}
