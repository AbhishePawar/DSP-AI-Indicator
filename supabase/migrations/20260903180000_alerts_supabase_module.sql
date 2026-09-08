-- Alerts module: user alert rules, metric thresholds, saved searches, watchlist
-- Backs the /alerts dashboard: active rules, recent triggers, performance summary

-- 1. Types
DROP TYPE IF EXISTS public.alert_type CASCADE;
CREATE TYPE public.alert_type AS ENUM ('saved_search', 'metric_threshold', 'watchlist');

DROP TYPE IF EXISTS public.threshold_direction CASCADE;
CREATE TYPE public.threshold_direction AS ENUM ('above', 'below');

-- 2. Core tables
CREATE TABLE IF NOT EXISTS public.user_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    alert_type public.alert_type NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.saved_searches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES public.user_alerts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    search_params JSONB DEFAULT '{}',
    last_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.metric_thresholds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES public.user_alerts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_label TEXT NOT NULL,
    threshold_value NUMERIC NOT NULL,
    direction public.threshold_direction NOT NULL DEFAULT 'above',
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.watchlist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    company_name TEXT,
    notes TEXT,
    added_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.alert_triggers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES public.user_alerts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    metric_label TEXT,
    threshold_value NUMERIC,
    direction public.threshold_direction,
    triggered_value NUMERIC,
    triggered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'fired'
);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_user_alerts_user_id ON public.user_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_alerts_is_active ON public.user_alerts(is_active);
CREATE INDEX IF NOT EXISTS idx_saved_searches_user_id ON public.saved_searches(user_id);
CREATE INDEX IF NOT EXISTS idx_metric_thresholds_user_id ON public.metric_thresholds(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_items_user_id ON public.watchlist_items(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_triggers_user_id ON public.alert_triggers(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_triggers_triggered_at ON public.alert_triggers(triggered_at DESC);

-- 4. Updated_at trigger function
CREATE OR REPLACE FUNCTION public.set_alerts_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

-- 5. Enable RLS
ALTER TABLE public.user_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.metric_thresholds ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlist_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alert_triggers ENABLE ROW LEVEL SECURITY;

-- 6. RLS Policies
DROP POLICY IF EXISTS "users_manage_own_user_alerts" ON public.user_alerts;
CREATE POLICY "users_manage_own_user_alerts"
ON public.user_alerts FOR ALL TO authenticated
USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "users_manage_own_saved_searches" ON public.saved_searches;
CREATE POLICY "users_manage_own_saved_searches"
ON public.saved_searches FOR ALL TO authenticated
USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "users_manage_own_metric_thresholds" ON public.metric_thresholds;
CREATE POLICY "users_manage_own_metric_thresholds"
ON public.metric_thresholds FOR ALL TO authenticated
USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "users_manage_own_watchlist_items" ON public.watchlist_items;
CREATE POLICY "users_manage_own_watchlist_items"
ON public.watchlist_items FOR ALL TO authenticated
USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "users_manage_own_alert_triggers" ON public.alert_triggers;
CREATE POLICY "users_manage_own_alert_triggers"
ON public.alert_triggers FOR ALL TO authenticated
USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- 7. Triggers
DROP TRIGGER IF EXISTS set_user_alerts_updated_at ON public.user_alerts;
CREATE TRIGGER set_user_alerts_updated_at
    BEFORE UPDATE ON public.user_alerts
    FOR EACH ROW EXECUTE FUNCTION public.set_alerts_updated_at();

-- 8. Seed demo data for existing users
DO $$
DECLARE
    existing_user_id UUID;
    alert_id_1 UUID := gen_random_uuid();
    alert_id_2 UUID := gen_random_uuid();
    alert_id_3 UUID := gen_random_uuid();
    alert_id_4 UUID := gen_random_uuid();
    alert_id_5 UUID := gen_random_uuid();
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'auth' AND table_name = 'users'
    ) THEN
        SELECT id INTO existing_user_id FROM auth.users LIMIT 1;

        IF existing_user_id IS NOT NULL THEN
            INSERT INTO public.user_alerts (id, user_id, alert_type, name, description, is_active, created_at)
            VALUES
                (alert_id_1, existing_user_id, 'metric_threshold', 'AAPL P/E Alert', 'Alert when Apple P/E crosses 30', true, now() - interval '10 days'),
                (alert_id_2, existing_user_id, 'metric_threshold', 'MSFT Margin of Safety', 'Alert when MSFT margin of safety drops below 15%', true, now() - interval '8 days'),
                (alert_id_3, existing_user_id, 'saved_search', 'GOOGL Deep Dive', 'Saved search for Alphabet analysis', true, now() - interval '6 days'),
                (alert_id_4, existing_user_id, 'metric_threshold', 'NVDA Revenue Growth', 'Alert when NVDA revenue growth falls below 20%', false, now() - interval '4 days'),
                (alert_id_5, existing_user_id, 'watchlist', 'TSLA Watchlist', 'Tesla watchlist monitor', true, now() - interval '2 days')
            ON CONFLICT (id) DO NOTHING;

            INSERT INTO public.metric_thresholds (id, alert_id, user_id, ticker, metric_name, metric_label, threshold_value, direction, last_triggered_at, created_at)
            VALUES
                (gen_random_uuid(), alert_id_1, existing_user_id, 'AAPL', 'pe_ratio', 'P/E Ratio', 30, 'above', now() - interval '3 days', now() - interval '10 days'),
                (gen_random_uuid(), alert_id_2, existing_user_id, 'MSFT', 'margin_of_safety', 'Margin of Safety (%)', 15, 'below', null, now() - interval '8 days'),
                (gen_random_uuid(), alert_id_4, existing_user_id, 'NVDA', 'revenue_growth', 'Revenue Growth (%)', 20, 'below', now() - interval '1 day', now() - interval '4 days')
            ON CONFLICT (id) DO NOTHING;

            INSERT INTO public.saved_searches (id, alert_id, user_id, ticker, search_params, last_run_at, created_at)
            VALUES
                (gen_random_uuid(), alert_id_3, existing_user_id, 'GOOGL', '{"name": "GOOGL Deep Dive"}'::jsonb, now() - interval '1 day', now() - interval '6 days')
            ON CONFLICT (id) DO NOTHING;

            INSERT INTO public.watchlist_items (id, user_id, ticker, company_name, added_at)
            VALUES
                (gen_random_uuid(), existing_user_id, 'TSLA', 'Tesla Inc.', now() - interval '2 days'),
                (gen_random_uuid(), existing_user_id, 'AMZN', 'Amazon.com Inc.', now() - interval '5 days')
            ON CONFLICT (id) DO NOTHING;

            INSERT INTO public.alert_triggers (id, alert_id, user_id, ticker, metric_label, threshold_value, direction, triggered_value, triggered_at, status)
            VALUES
                (gen_random_uuid(), alert_id_1, existing_user_id, 'AAPL', 'P/E Ratio', 30, 'above', 31.4, now() - interval '3 days', 'fired'),
                (gen_random_uuid(), alert_id_1, existing_user_id, 'AAPL', 'P/E Ratio', 30, 'above', 30.8, now() - interval '7 days', 'fired'),
                (gen_random_uuid(), alert_id_4, existing_user_id, 'NVDA', 'Revenue Growth (%)', 20, 'below', 18.2, now() - interval '1 day', 'fired'),
                (gen_random_uuid(), alert_id_2, existing_user_id, 'MSFT', 'Margin of Safety (%)', 15, 'below', 14.1, now() - interval '12 days', 'fired')
            ON CONFLICT (id) DO NOTHING;
        ELSE
            RAISE NOTICE 'No existing users found. Skipping seed data.';
        END IF;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Seed data insertion failed: %', SQLERRM;
END $$;
