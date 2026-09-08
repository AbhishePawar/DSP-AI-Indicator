import { createClient } from '@/lib/supabase/client';

export interface AccountSettings {
  id: string;
  userId: string;
  bio: string | null;
  avatarUrl: string | null;
  timezone: string;
  notifyAlertTriggers: boolean;
  notifyWatchlistUpdates: boolean;
  notifyResearchPublished: boolean;
  notifyPortfolioChanges: boolean;
  notifySystemAnnouncements: boolean;
  emailDigestFrequency: 'realtime' | 'daily' | 'weekly' | 'never';
  resendWebhookEnabled: boolean;
  resendWebhookAlerts: boolean;
  resendWebhookDigest: boolean;
  resendWebhookResearch: boolean;
  resendWebhookUrl: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProfileData {
  displayName: string;
  email: string;
}

function toAccountSettings(row: Record<string, unknown>): AccountSettings {
  return {
    id: row.id as string,
    userId: row.user_id as string,
    bio: (row.bio as string | null) ?? null,
    avatarUrl: (row.avatar_url as string | null) ?? null,
    timezone: (row.timezone as string) ?? 'UTC',
    notifyAlertTriggers: Boolean(row.notify_alert_triggers),
    notifyWatchlistUpdates: Boolean(row.notify_watchlist_updates),
    notifyResearchPublished: Boolean(row.notify_research_published),
    notifyPortfolioChanges: Boolean(row.notify_portfolio_changes),
    notifySystemAnnouncements: Boolean(row.notify_system_announcements),
    emailDigestFrequency: (row.email_digest_frequency as AccountSettings['emailDigestFrequency']) ?? 'daily',
    resendWebhookEnabled: Boolean(row.resend_webhook_enabled),
    resendWebhookAlerts: Boolean(row.resend_webhook_alerts),
    resendWebhookDigest: Boolean(row.resend_webhook_digest),
    resendWebhookResearch: Boolean(row.resend_webhook_research),
    resendWebhookUrl: (row.resend_webhook_url as string | null) ?? null,
    createdAt: row.created_at as string,
    updatedAt: row.updated_at as string,
  };
}

export async function getAccountSettings(): Promise<AccountSettings | null> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;

  const { data, error } = await supabase
    .from('user_account_settings')
    .select('*')
    .eq('user_id', user.id)
    .maybeSingle();

  if (error) throw new Error(error.message);
  if (!data) return null;
  return toAccountSettings(data as Record<string, unknown>);
}

export async function upsertAccountSettings(
  updates: Partial<Omit<AccountSettings, 'id' | 'userId' | 'createdAt' | 'updatedAt'>>
): Promise<AccountSettings> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error('Not authenticated');

  const payload: Record<string, unknown> = { user_id: user.id };
  if (updates.bio !== undefined) payload.bio = updates.bio;
  if (updates.avatarUrl !== undefined) payload.avatar_url = updates.avatarUrl;
  if (updates.timezone !== undefined) payload.timezone = updates.timezone;
  if (updates.notifyAlertTriggers !== undefined) payload.notify_alert_triggers = updates.notifyAlertTriggers;
  if (updates.notifyWatchlistUpdates !== undefined) payload.notify_watchlist_updates = updates.notifyWatchlistUpdates;
  if (updates.notifyResearchPublished !== undefined) payload.notify_research_published = updates.notifyResearchPublished;
  if (updates.notifyPortfolioChanges !== undefined) payload.notify_portfolio_changes = updates.notifyPortfolioChanges;
  if (updates.notifySystemAnnouncements !== undefined) payload.notify_system_announcements = updates.notifySystemAnnouncements;
  if (updates.emailDigestFrequency !== undefined) payload.email_digest_frequency = updates.emailDigestFrequency;
  if (updates.resendWebhookEnabled !== undefined) payload.resend_webhook_enabled = updates.resendWebhookEnabled;
  if (updates.resendWebhookAlerts !== undefined) payload.resend_webhook_alerts = updates.resendWebhookAlerts;
  if (updates.resendWebhookDigest !== undefined) payload.resend_webhook_digest = updates.resendWebhookDigest;
  if (updates.resendWebhookResearch !== undefined) payload.resend_webhook_research = updates.resendWebhookResearch;
  if (updates.resendWebhookUrl !== undefined) payload.resend_webhook_url = updates.resendWebhookUrl;

  const { data, error } = await supabase
    .from('user_account_settings')
    .upsert(payload, { onConflict: 'user_id' })
    .select()
    .single();

  if (error) throw new Error(error.message);
  return toAccountSettings(data as Record<string, unknown>);
}

export async function getProfileData(): Promise<ProfileData | null> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;

  const { data } = await supabase
    .from('user_profiles')
    .select('display_name')
    .eq('id', user.id)
    .maybeSingle();

  return {
    displayName: (data as Record<string, unknown> | null)?.display_name as string ?? '',
    email: user.email ?? '',
  };
}

export async function updateDisplayName(displayName: string): Promise<void> {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error('Not authenticated');

  const { error } = await supabase
    .from('user_profiles')
    .update({ display_name: displayName, updated_at: new Date().toISOString() })
    .eq('id', user.id);

  if (error) throw new Error(error.message);
}
