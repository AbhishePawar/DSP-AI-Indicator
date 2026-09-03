import type { SupabaseClient } from "@supabase/supabase-js";

import type { SavedAnalysis, UserDataBundle, UserPreference } from "@/lib/persistence/types";
import type { WatchlistEntry } from "@/lib/portfolio-intelligence/prefsStore";

import { dspSubjectToProfileIdSync } from "./identity";
import { sanitizeForPersistence, toPublicSavedResearch } from "./sanitize";

export type CloudWatchlistItem = {
  symbol: string;
  exchange: string | null;
  companyName: string | null;
};

export type CloudPersistenceSnapshot = {
  profileId: string;
  dspUserId: string;
  preferences: UserPreference;
  savedResearch: SavedAnalysis[];
  watchlist: CloudWatchlistItem[];
  history: Array<{
    ticker: string;
    eventType: string;
    researchStatus: string | null;
    createdAt: string;
  }>;
  updatedAt: string;
};

export async function ensureProfile(
  admin: SupabaseClient,
  user: { subject: string; email: string | null; displayName: string | null },
): Promise<string> {
  const profileId = dspSubjectToProfileIdSync(user.subject);
  const now = new Date().toISOString();
  const { error } = await admin.from("profiles").upsert(
    {
      id: profileId,
      dsp_user_id: user.subject,
      display_name: user.displayName,
      email: user.email,
      updated_at: now,
    },
    { onConflict: "id" },
  );
  if (error) throw new Error("Unable to persist profile");
  return profileId;
}

export async function readCloudSnapshot(
  admin: SupabaseClient,
  profileId: string,
): Promise<CloudPersistenceSnapshot | null> {
  const { data: profile, error: profileError } = await admin
    .from("profiles")
    .select("id, dsp_user_id, updated_at")
    .eq("id", profileId)
    .maybeSingle();
  if (profileError) throw new Error("Unable to load profile");
  if (!profile) return null;

  const [prefs, research, watchlists, history] = await Promise.all([
    admin.from("user_preferences").select("*").eq("user_id", profileId).maybeSingle(),
    admin
      .from("saved_research")
      .select("*")
      .eq("user_id", profileId)
      .order("saved_at", { ascending: false }),
    admin.from("watchlists").select("id").eq("user_id", profileId).limit(1),
    admin
      .from("research_history")
      .select("ticker, event_type, research_status, created_at")
      .eq("user_id", profileId)
      .order("created_at", { ascending: false })
      .limit(50),
  ]);

  if (prefs.error || research.error || watchlists.error || history.error) {
    throw new Error("Unable to load application data");
  }

  let watchlist: CloudWatchlistItem[] = [];
  const watchlistId = watchlists.data?.[0]?.id as string | undefined;
  if (watchlistId) {
    const items = await admin
      .from("watchlist_items")
      .select("symbol, exchange, company_name")
      .eq("watchlist_id", watchlistId)
      .eq("user_id", profileId);
    if (items.error) throw new Error("Unable to load watchlist");
    watchlist = (items.data ?? []).map((row) => ({
      symbol: String(row.symbol),
      exchange: row.exchange ? String(row.exchange) : null,
      companyName: row.company_name ? String(row.company_name) : null,
    }));
  }

  const savedResearch: SavedAnalysis[] = (research.data ?? []).map((row) => {
    const report = (row.public_report ?? {}) as Record<string, unknown>;
    return {
      id: String(row.id),
      ticker: String(row.ticker),
      company: String(row.company ?? ""),
      exchange: String(row.exchange ?? ""),
      recommendation: String(row.recommendation_action ?? ""),
      analysedAt: String(row.analysed_at ?? row.saved_at),
      savedAt: String(row.saved_at),
      label: row.label ? String(row.label) : undefined,
      request: (report.request as SavedAnalysis["request"]) ?? undefined,
      response: (report.response as SavedAnalysis["response"]) ?? undefined,
    };
  });

  const preferences: UserPreference = {
    theme: (prefs.data?.theme as UserPreference["theme"]) || "system",
    defaultLandingPage: String(prefs.data?.default_landing_page ?? "/dashboard"),
    preferredWatchlistView: prefs.data?.preferred_watchlist_view
      ? String(prefs.data.preferred_watchlist_view)
      : null,
  };

  return {
    profileId,
    dspUserId: String(profile.dsp_user_id),
    preferences,
    savedResearch,
    watchlist,
    history: (history.data ?? []).map((row) => ({
      ticker: String(row.ticker),
      eventType: String(row.event_type),
      researchStatus: row.research_status ? String(row.research_status) : null,
      createdAt: String(row.created_at),
    })),
    updatedAt: String(profile.updated_at),
  };
}

export async function writeCloudSnapshot(
  admin: SupabaseClient,
  profileId: string,
  bundle: UserDataBundle,
  watchlist: WatchlistEntry[] = [],
): Promise<void> {
  const now = new Date().toISOString();
  const prefs = bundle.preferences;
  const { error: prefError } = await admin.from("user_preferences").upsert({
    user_id: profileId,
    theme: prefs.theme,
    default_landing_page: prefs.defaultLandingPage,
    preferred_watchlist_view: prefs.preferredWatchlistView,
    alert_preferences: {},
    updated_at: now,
  });
  if (prefError) throw new Error("Unable to save preferences");

  const { error: deleteResearchError } = await admin
    .from("saved_research")
    .delete()
    .eq("user_id", profileId);
  if (deleteResearchError) throw new Error("Unable to replace saved research");

  if (bundle.savedAnalyses.length > 0) {
    const rows = bundle.savedAnalyses.map((item) => {
      const publicItem = toPublicSavedResearch({
        id: item.id,
        ticker: item.ticker,
        company: item.company,
        exchange: item.exchange,
        label: item.label,
        recommendation: item.recommendation,
        analysedAt: item.analysedAt,
        savedAt: item.savedAt,
        request: item.request,
        response: item.response,
      });
      return {
        id: looksLikeUuid(item.id) ? item.id : undefined,
        user_id: profileId,
        ticker: publicItem.ticker,
        company: publicItem.company,
        exchange: publicItem.exchange || null,
        analysis_id: publicItem.analysisId,
        label: publicItem.label,
        research_status: publicItem.researchStatus,
        recommendation_action: publicItem.recommendationAction,
        analysed_at: publicItem.analysedAt,
        saved_at: publicItem.savedAt,
        public_report: sanitizeForPersistence(publicItem.publicReport),
      };
    });
    const { error } = await admin.from("saved_research").insert(rows);
    if (error) throw new Error("Unable to save research");
  }

  let watchlistId: string | null = null;
  const existing = await admin
    .from("watchlists")
    .select("id")
    .eq("user_id", profileId)
    .limit(1)
    .maybeSingle();
  if (existing.error) throw new Error("Unable to load watchlist");
  if (existing.data?.id) {
    watchlistId = String(existing.data.id);
  } else {
    const created = await admin
      .from("watchlists")
      .insert({ user_id: profileId, name: "Watchlist" })
      .select("id")
      .single();
    if (created.error) throw new Error("Unable to create watchlist");
    watchlistId = String(created.data.id);
  }

  const { error: clearItemsError } = await admin
    .from("watchlist_items")
    .delete()
    .eq("watchlist_id", watchlistId)
    .eq("user_id", profileId);
  if (clearItemsError) throw new Error("Unable to replace watchlist");

  if (watchlist.length > 0) {
    const { error } = await admin.from("watchlist_items").insert(
      watchlist.map((item) => ({
        watchlist_id: watchlistId,
        user_id: profileId,
        symbol: item.symbol.trim().toUpperCase(),
        exchange: null,
        company_name: item.label ?? null,
      })),
    );
    if (error) throw new Error("Unable to save watchlist");
  }

  await admin.from("profiles").update({ updated_at: now }).eq("id", profileId);
}

function looksLikeUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value,
  );
}
