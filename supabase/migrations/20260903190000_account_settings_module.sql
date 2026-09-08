-- Account Settings Module
-- Adds user_account_settings table for notification preferences,
-- email digest frequency, and Resend webhook integration toggles.
-- user_profiles already exists; this is an additive module.

-- 1. Create user_account_settings table
CREATE TABLE IF NOT EXISTS public.user_account_settings (
  id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Profile extras (display name lives in user_profiles; bio/avatar_url here)
  bio                        TEXT,
  avatar_url                 TEXT,
  timezone                   TEXT DEFAULT 'UTC',

  -- Notification preferences
  notify_alert_triggers      BOOLEAN NOT NULL DEFAULT true,
  notify_watchlist_updates   BOOLEAN NOT NULL DEFAULT true,
  notify_research_published  BOOLEAN NOT NULL DEFAULT false,
  notify_portfolio_changes   BOOLEAN NOT NULL DEFAULT true,
  notify_system_announcements BOOLEAN NOT NULL DEFAULT true,

  -- Email digest frequency: 'realtime' | 'daily' | 'weekly' | 'never'
  email_digest_frequency     TEXT NOT NULL DEFAULT 'daily'
    CHECK (email_digest_frequency IN ('realtime', 'daily', 'weekly', 'never')),

  -- Resend webhook integration toggles
  resend_webhook_enabled     BOOLEAN NOT NULL DEFAULT false,
  resend_webhook_alerts      BOOLEAN NOT NULL DEFAULT false,
  resend_webhook_digest      BOOLEAN NOT NULL DEFAULT false,
  resend_webhook_research    BOOLEAN NOT NULL DEFAULT false,
  resend_webhook_url         TEXT,

  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Unique constraint: one settings row per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_account_settings_user_id
  ON public.user_account_settings (user_id);

-- 3. Index for lookups
CREATE INDEX IF NOT EXISTS idx_user_account_settings_user_id_lookup
  ON public.user_account_settings (user_id);

-- 4. Updated_at trigger function
CREATE OR REPLACE FUNCTION public.set_account_settings_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- 5. Enable RLS
ALTER TABLE public.user_account_settings ENABLE ROW LEVEL SECURITY;

-- 6. RLS policies
DROP POLICY IF EXISTS "users_manage_own_account_settings" ON public.user_account_settings;
CREATE POLICY "users_manage_own_account_settings"
  ON public.user_account_settings
  FOR ALL
  TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- 7. Trigger
DROP TRIGGER IF EXISTS trg_account_settings_updated_at ON public.user_account_settings;
CREATE TRIGGER trg_account_settings_updated_at
  BEFORE UPDATE ON public.user_account_settings
  FOR EACH ROW
  EXECUTE FUNCTION public.set_account_settings_updated_at();
