-- ─── Analytics Module ────────────────────────────────────────────────────────
-- Tables: company_views, metric_drilldowns, portfolio_activity
-- Used by: /admin/analytics screen

-- 1. company_views — tracks which companies users research
CREATE TABLE IF NOT EXISTS public.company_views (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  ticker        TEXT NOT NULL,
  company_name  TEXT,
  viewed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  session_id    TEXT,
  duration_secs INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_company_views_user_id   ON public.company_views(user_id);
CREATE INDEX IF NOT EXISTS idx_company_views_ticker    ON public.company_views(ticker);
CREATE INDEX IF NOT EXISTS idx_company_views_viewed_at ON public.company_views(viewed_at);

-- 2. metric_drilldowns — tracks which metrics users drill into per company
CREATE TABLE IF NOT EXISTS public.metric_drilldowns (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  ticker      TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  section     TEXT,
  drilled_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_metric_drilldowns_user_id   ON public.metric_drilldowns(user_id);
CREATE INDEX IF NOT EXISTS idx_metric_drilldowns_ticker    ON public.metric_drilldowns(ticker);
CREATE INDEX IF NOT EXISTS idx_metric_drilldowns_metric    ON public.metric_drilldowns(metric_name);

-- 3. portfolio_activity — tracks portfolio add/remove/view events
CREATE TABLE IF NOT EXISTS public.portfolio_activity (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  ticker      TEXT NOT NULL,
  action      TEXT NOT NULL CHECK (action IN ('add', 'remove', 'view', 'rebalance')),
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata    JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_portfolio_activity_user_id     ON public.portfolio_activity(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_activity_occurred_at ON public.portfolio_activity(occurred_at);

-- ─── Helper: admin check (reuse pattern from audit_trail module) ──────────────
CREATE OR REPLACE FUNCTION public.is_admin_for_analytics()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
  SELECT EXISTS (
    SELECT 1 FROM auth.users au
    WHERE au.id = auth.uid()
      AND (
        au.raw_user_meta_data->>'role' = 'admin'
        OR au.raw_app_meta_data->>'role'  = 'admin'
      )
  )
$$;

-- ─── RLS ─────────────────────────────────────────────────────────────────────
ALTER TABLE public.company_views      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.metric_drilldowns  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portfolio_activity ENABLE ROW LEVEL SECURITY;

-- company_views
DROP POLICY IF EXISTS "users_manage_own_company_views" ON public.company_views;
CREATE POLICY "users_manage_own_company_views"
  ON public.company_views FOR ALL TO authenticated
  USING  (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "admin_read_all_company_views" ON public.company_views;
CREATE POLICY "admin_read_all_company_views"
  ON public.company_views FOR SELECT TO authenticated
  USING (public.is_admin_for_analytics());

-- metric_drilldowns
DROP POLICY IF EXISTS "users_manage_own_metric_drilldowns" ON public.metric_drilldowns;
CREATE POLICY "users_manage_own_metric_drilldowns"
  ON public.metric_drilldowns FOR ALL TO authenticated
  USING  (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "admin_read_all_metric_drilldowns" ON public.metric_drilldowns;
CREATE POLICY "admin_read_all_metric_drilldowns"
  ON public.metric_drilldowns FOR SELECT TO authenticated
  USING (public.is_admin_for_analytics());

-- portfolio_activity
DROP POLICY IF EXISTS "users_manage_own_portfolio_activity" ON public.portfolio_activity;
CREATE POLICY "users_manage_own_portfolio_activity"
  ON public.portfolio_activity FOR ALL TO authenticated
  USING  (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "admin_read_all_portfolio_activity" ON public.portfolio_activity;
CREATE POLICY "admin_read_all_portfolio_activity"
  ON public.portfolio_activity FOR SELECT TO authenticated
  USING (public.is_admin_for_analytics());

-- ─── Seed data ────────────────────────────────────────────────────────────────
DO $$
DECLARE
  u1 UUID;
  u2 UUID;
  u3 UUID;
  base TIMESTAMPTZ := now() - INTERVAL '30 days';
BEGIN
  -- Grab up to 3 existing user_profiles
  SELECT id INTO u1 FROM public.user_profiles ORDER BY created_at LIMIT 1;
  SELECT id INTO u2 FROM public.user_profiles ORDER BY created_at OFFSET 1 LIMIT 1;
  SELECT id INTO u3 FROM public.user_profiles ORDER BY created_at OFFSET 2 LIMIT 1;

  IF u1 IS NULL THEN
    RAISE NOTICE 'No user_profiles found — skipping analytics seed data.';
    RETURN;
  END IF;

  -- Use u1 as fallback for missing users
  IF u2 IS NULL THEN u2 := u1; END IF;
  IF u3 IS NULL THEN u3 := u1; END IF;

  -- company_views seed (30 rows spread over 30 days)
  INSERT INTO public.company_views (user_id, ticker, company_name, viewed_at, duration_secs) VALUES
    (u1, 'AAPL', 'Apple Inc.',            base + INTERVAL '0 days',  120),
    (u2, 'AAPL', 'Apple Inc.',            base + INTERVAL '1 days',   95),
    (u3, 'AAPL', 'Apple Inc.',            base + INTERVAL '2 days',  200),
    (u1, 'MSFT', 'Microsoft Corp.',       base + INTERVAL '1 days',  180),
    (u2, 'MSFT', 'Microsoft Corp.',       base + INTERVAL '3 days',  145),
    (u1, 'GOOGL','Alphabet Inc.',         base + INTERVAL '2 days',  300),
    (u3, 'GOOGL','Alphabet Inc.',         base + INTERVAL '4 days',  210),
    (u1, 'AMZN', 'Amazon.com Inc.',       base + INTERVAL '5 days',   90),
    (u2, 'AMZN', 'Amazon.com Inc.',       base + INTERVAL '6 days',  160),
    (u1, 'NVDA', 'NVIDIA Corp.',          base + INTERVAL '7 days',  240),
    (u2, 'NVDA', 'NVIDIA Corp.',          base + INTERVAL '8 days',  190),
    (u3, 'NVDA', 'NVIDIA Corp.',          base + INTERVAL '9 days',  310),
    (u1, 'TSLA', 'Tesla Inc.',            base + INTERVAL '10 days', 130),
    (u2, 'META', 'Meta Platforms Inc.',   base + INTERVAL '11 days', 175),
    (u3, 'META', 'Meta Platforms Inc.',   base + INTERVAL '12 days', 220),
    (u1, 'BRK.B','Berkshire Hathaway',    base + INTERVAL '13 days', 400),
    (u2, 'JPM',  'JPMorgan Chase',        base + INTERVAL '14 days', 155),
    (u3, 'JPM',  'JPMorgan Chase',        base + INTERVAL '15 days', 100),
    (u1, 'V',    'Visa Inc.',             base + INTERVAL '16 days',  80),
    (u2, 'JNJ',  'Johnson & Johnson',     base + INTERVAL '17 days', 195),
    (u1, 'AAPL', 'Apple Inc.',            base + INTERVAL '18 days', 110),
    (u3, 'MSFT', 'Microsoft Corp.',       base + INTERVAL '19 days', 230),
    (u1, 'NVDA', 'NVIDIA Corp.',          base + INTERVAL '20 days', 280),
    (u2, 'GOOGL','Alphabet Inc.',         base + INTERVAL '21 days', 165),
    (u1, 'AMZN', 'Amazon.com Inc.',       base + INTERVAL '22 days', 140),
    (u3, 'TSLA', 'Tesla Inc.',            base + INTERVAL '23 days', 200),
    (u1, 'META', 'Meta Platforms Inc.',   base + INTERVAL '24 days', 185),
    (u2, 'BRK.B','Berkshire Hathaway',    base + INTERVAL '25 days', 350),
    (u1, 'AAPL', 'Apple Inc.',            base + INTERVAL '26 days',  75),
    (u3, 'NVDA', 'NVIDIA Corp.',          base + INTERVAL '27 days', 260)
  ON CONFLICT (id) DO NOTHING;

  -- metric_drilldowns seed
  INSERT INTO public.metric_drilldowns (user_id, ticker, metric_name, section, drilled_at) VALUES
    (u1, 'AAPL', 'P/E Ratio',          'Valuation',       base + INTERVAL '0 days'),
    (u1, 'AAPL', 'Revenue Growth',     'Fundamentals',    base + INTERVAL '1 days'),
    (u2, 'MSFT', 'Free Cash Flow',     'Financials',      base + INTERVAL '2 days'),
    (u2, 'MSFT', 'Gross Margin',       'Fundamentals',    base + INTERVAL '3 days'),
    (u3, 'NVDA', 'EPS Growth',         'Earnings',        base + INTERVAL '4 days'),
    (u3, 'NVDA', 'Debt/Equity',        'Balance Sheet',   base + INTERVAL '5 days'),
    (u1, 'GOOGL','DCF Valuation',      'Valuation',       base + INTERVAL '6 days'),
    (u2, 'AMZN', 'Operating Margin',   'Fundamentals',    base + INTERVAL '7 days'),
    (u1, 'TSLA', 'P/E Ratio',          'Valuation',       base + INTERVAL '8 days'),
    (u3, 'META', 'Revenue Growth',     'Fundamentals',    base + INTERVAL '9 days'),
    (u1, 'AAPL', 'DCF Valuation',      'Valuation',       base + INTERVAL '10 days'),
    (u2, 'NVDA', 'P/E Ratio',          'Valuation',       base + INTERVAL '11 days'),
    (u1, 'MSFT', 'Free Cash Flow',     'Financials',      base + INTERVAL '12 days'),
    (u3, 'GOOGL','Gross Margin',       'Fundamentals',    base + INTERVAL '13 days'),
    (u2, 'AAPL', 'EPS Growth',         'Earnings',        base + INTERVAL '14 days'),
    (u1, 'NVDA', 'Revenue Growth',     'Fundamentals',    base + INTERVAL '15 days'),
    (u3, 'AMZN', 'DCF Valuation',      'Valuation',       base + INTERVAL '16 days'),
    (u1, 'JPM',  'Debt/Equity',        'Balance Sheet',   base + INTERVAL '17 days'),
    (u2, 'META', 'Operating Margin',   'Fundamentals',    base + INTERVAL '18 days'),
    (u1, 'AAPL', 'Gross Margin',       'Fundamentals',    base + INTERVAL '19 days')
  ON CONFLICT (id) DO NOTHING;

  -- portfolio_activity seed
  INSERT INTO public.portfolio_activity (user_id, ticker, action, occurred_at) VALUES
    (u1, 'AAPL', 'add',       base + INTERVAL '0 days'),
    (u1, 'MSFT', 'add',       base + INTERVAL '1 days'),
    (u2, 'NVDA', 'add',       base + INTERVAL '2 days'),
    (u3, 'GOOGL','add',       base + INTERVAL '3 days'),
    (u1, 'TSLA', 'add',       base + INTERVAL '4 days'),
    (u2, 'AAPL', 'view',      base + INTERVAL '5 days'),
    (u1, 'AMZN', 'add',       base + INTERVAL '6 days'),
    (u3, 'META', 'add',       base + INTERVAL '7 days'),
    (u1, 'AAPL', 'view',      base + INTERVAL '8 days'),
    (u2, 'MSFT', 'view',      base + INTERVAL '9 days'),
    (u1, 'TSLA', 'remove',    base + INTERVAL '10 days'),
    (u3, 'NVDA', 'add',       base + INTERVAL '11 days'),
    (u2, 'AMZN', 'add',       base + INTERVAL '12 days'),
    (u1, 'BRK.B','add',       base + INTERVAL '13 days'),
    (u3, 'AAPL', 'view',      base + INTERVAL '14 days'),
    (u1, 'NVDA', 'view',      base + INTERVAL '15 days'),
    (u2, 'META', 'view',      base + INTERVAL '16 days'),
    (u1, 'MSFT', 'rebalance', base + INTERVAL '17 days'),
    (u3, 'JPM',  'add',       base + INTERVAL '18 days'),
    (u2, 'GOOGL','view',      base + INTERVAL '19 days'),
    (u1, 'AAPL', 'add',       base + INTERVAL '20 days'),
    (u3, 'AMZN', 'remove',    base + INTERVAL '21 days'),
    (u1, 'NVDA', 'add',       base + INTERVAL '22 days'),
    (u2, 'BRK.B','add',       base + INTERVAL '23 days'),
    (u1, 'META', 'view',      base + INTERVAL '24 days'),
    (u3, 'MSFT', 'add',       base + INTERVAL '25 days'),
    (u1, 'GOOGL','view',      base + INTERVAL '26 days'),
    (u2, 'NVDA', 'rebalance', base + INTERVAL '27 days'),
    (u1, 'TSLA', 'add',       base + INTERVAL '28 days'),
    (u3, 'V',    'add',       base + INTERVAL '29 days')
  ON CONFLICT (id) DO NOTHING;

EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE 'Analytics seed data failed: %', SQLERRM;
END $$;
