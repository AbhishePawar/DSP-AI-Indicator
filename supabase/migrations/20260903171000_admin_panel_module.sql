-- =============================================================
-- Admin Panel Module
-- Tables: alert_rules, threshold_logs, watchlist_shares, integration_settings
-- =============================================================

-- ---------------------------------------------------------------
-- 1. ENUM TYPES
-- ---------------------------------------------------------------
DROP TYPE IF EXISTS public.alert_rule_status CASCADE;
CREATE TYPE public.alert_rule_status AS ENUM ('active', 'paused', 'deleted');

DROP TYPE IF EXISTS public.alert_condition CASCADE;
CREATE TYPE public.alert_condition AS ENUM ('above', 'below', 'equals', 'crosses_above', 'crosses_below');

DROP TYPE IF EXISTS public.watchlist_share_permission CASCADE;
CREATE TYPE public.watchlist_share_permission AS ENUM ('view', 'edit', 'admin');

-- ---------------------------------------------------------------
-- 2. TABLES
-- ---------------------------------------------------------------

-- Alert Rules: per-user metric threshold alert configurations
CREATE TABLE IF NOT EXISTS public.alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    metric TEXT NOT NULL,
    condition public.alert_condition NOT NULL DEFAULT 'above'::public.alert_condition,
    threshold_value NUMERIC NOT NULL,
    alert_status public.alert_rule_status NOT NULL DEFAULT 'active'::public.alert_rule_status,
    notification_channel TEXT NOT NULL DEFAULT 'email',
    last_triggered_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Threshold Logs: immutable audit log of triggered alerts
CREATE TABLE IF NOT EXISTS public.threshold_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_rule_id UUID REFERENCES public.alert_rules(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    metric TEXT NOT NULL,
    condition public.alert_condition NOT NULL,
    threshold_value NUMERIC NOT NULL,
    actual_value NUMERIC NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivery_status TEXT NOT NULL DEFAULT 'pending',
    delivery_error TEXT,
    metadata JSONB
);

-- Watchlist Shares: sharing watchlists between users
CREATE TABLE IF NOT EXISTS public.watchlist_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    shared_with_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    shared_with_email TEXT,
    watchlist_name TEXT NOT NULL,
    tickers TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    permission public.watchlist_share_permission NOT NULL DEFAULT 'view'::public.watchlist_share_permission,
    is_public BOOLEAN NOT NULL DEFAULT false,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Integration Settings: per-user integration configuration (Resend, webhooks, etc.)
CREATE TABLE IF NOT EXISTS public.integration_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    integration_key TEXT NOT NULL,
    display_name TEXT NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT false,
    config JSONB NOT NULL DEFAULT '{}'::JSONB,
    last_tested_at TIMESTAMPTZ,
    last_test_status TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT integration_settings_user_key_unique UNIQUE (user_id, integration_key)
);

-- ---------------------------------------------------------------
-- 3. INDEXES
-- ---------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_alert_rules_user_id ON public.alert_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_rules_ticker ON public.alert_rules(ticker);
CREATE INDEX IF NOT EXISTS idx_alert_rules_status ON public.alert_rules(alert_status);

CREATE INDEX IF NOT EXISTS idx_threshold_logs_user_id ON public.threshold_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_threshold_logs_alert_rule_id ON public.threshold_logs(alert_rule_id);
CREATE INDEX IF NOT EXISTS idx_threshold_logs_triggered_at ON public.threshold_logs(triggered_at DESC);

CREATE INDEX IF NOT EXISTS idx_watchlist_shares_owner_id ON public.watchlist_shares(owner_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_shares_shared_with_id ON public.watchlist_shares(shared_with_id);

CREATE INDEX IF NOT EXISTS idx_integration_settings_user_id ON public.integration_settings(user_id);

-- ---------------------------------------------------------------
-- 4. UPDATED_AT TRIGGER FUNCTION
-- ---------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

-- ---------------------------------------------------------------
-- 5. ENABLE RLS
-- ---------------------------------------------------------------
ALTER TABLE public.alert_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.threshold_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlist_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integration_settings ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------
-- 6. RLS POLICIES
-- ---------------------------------------------------------------

-- alert_rules: users manage their own rules
DROP POLICY IF EXISTS "users_manage_own_alert_rules" ON public.alert_rules;
CREATE POLICY "users_manage_own_alert_rules"
ON public.alert_rules
FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

-- threshold_logs: users view their own logs (read-only from client)
DROP POLICY IF EXISTS "users_view_own_threshold_logs" ON public.threshold_logs;
CREATE POLICY "users_view_own_threshold_logs"
ON public.threshold_logs
FOR SELECT
TO authenticated
USING (user_id = auth.uid());

DROP POLICY IF EXISTS "users_insert_own_threshold_logs" ON public.threshold_logs;
CREATE POLICY "users_insert_own_threshold_logs"
ON public.threshold_logs
FOR INSERT
TO authenticated
WITH CHECK (user_id = auth.uid());

-- watchlist_shares: owners manage; shared_with can view
DROP POLICY IF EXISTS "owners_manage_watchlist_shares" ON public.watchlist_shares;
CREATE POLICY "owners_manage_watchlist_shares"
ON public.watchlist_shares
FOR ALL
TO authenticated
USING (owner_id = auth.uid())
WITH CHECK (owner_id = auth.uid());

DROP POLICY IF EXISTS "shared_users_view_watchlist_shares" ON public.watchlist_shares;
CREATE POLICY "shared_users_view_watchlist_shares"
ON public.watchlist_shares
FOR SELECT
TO authenticated
USING (shared_with_id = auth.uid() OR is_public = true);

-- integration_settings: users manage their own
DROP POLICY IF EXISTS "users_manage_own_integration_settings" ON public.integration_settings;
CREATE POLICY "users_manage_own_integration_settings"
ON public.integration_settings
FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

-- ---------------------------------------------------------------
-- 7. TRIGGERS
-- ---------------------------------------------------------------
DROP TRIGGER IF EXISTS set_alert_rules_updated_at ON public.alert_rules;
CREATE TRIGGER set_alert_rules_updated_at
    BEFORE UPDATE ON public.alert_rules
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS set_watchlist_shares_updated_at ON public.watchlist_shares;
CREATE TRIGGER set_watchlist_shares_updated_at
    BEFORE UPDATE ON public.watchlist_shares
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS set_integration_settings_updated_at ON public.integration_settings;
CREATE TRIGGER set_integration_settings_updated_at
    BEFORE UPDATE ON public.integration_settings
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
