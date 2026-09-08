-- ─── Audit Trail Module ───────────────────────────────────────────────────────
-- Tracks: user logins, data exports, watchlist shares, alert triggers, admin actions

CREATE TABLE IF NOT EXISTS public.audit_trail (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID        REFERENCES public.user_profiles(id) ON DELETE SET NULL,
  actor_email     TEXT,
  event_type      TEXT        NOT NULL,
  event_category  TEXT        NOT NULL,
  resource_type   TEXT,
  resource_id     TEXT,
  description     TEXT        NOT NULL,
  metadata        JSONB       DEFAULT '{}'::jsonb,
  ip_address      TEXT,
  user_agent      TEXT,
  severity        TEXT        NOT NULL DEFAULT 'info',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_audit_trail_user_id     ON public.audit_trail(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_trail_event_type  ON public.audit_trail(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_trail_category    ON public.audit_trail(event_category);
CREATE INDEX IF NOT EXISTS idx_audit_trail_created_at  ON public.audit_trail(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_trail_severity    ON public.audit_trail(severity);

-- RLS
ALTER TABLE public.audit_trail ENABLE ROW LEVEL SECURITY;

-- Admins (via auth metadata) can read all audit events
CREATE OR REPLACE FUNCTION public.is_admin_for_audit()
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
        OR au.raw_app_meta_data->>'role' = 'admin'
      )
  )
$$;

-- Authenticated users can read their own audit events
DROP POLICY IF EXISTS "users_read_own_audit_trail" ON public.audit_trail;
CREATE POLICY "users_read_own_audit_trail"
  ON public.audit_trail
  FOR SELECT
  TO authenticated
  USING (user_id = auth.uid() OR public.is_admin_for_audit());

-- Only service role / backend can insert audit events
-- (frontend reads only; writes come from server-side triggers)
DROP POLICY IF EXISTS "service_insert_audit_trail" ON public.audit_trail;
CREATE POLICY "service_insert_audit_trail"
  ON public.audit_trail
  FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid() OR public.is_admin_for_audit());

-- ─── Seed illustrative audit events ──────────────────────────────────────────
DO $$
DECLARE
  existing_user_id UUID;
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'user_profiles'
  ) THEN
    SELECT id INTO existing_user_id FROM public.user_profiles LIMIT 1;

    IF existing_user_id IS NOT NULL THEN
      INSERT INTO public.audit_trail
        (user_id, actor_email, event_type, event_category, resource_type, resource_id, description, severity, metadata)
      VALUES
        (existing_user_id, 'demo@example.com', 'user_login',       'auth',       'session',   NULL,          'User signed in via email/password',                  'info',    '{"provider":"email"}'::jsonb),
        (existing_user_id, 'demo@example.com', 'data_export',      'data',       'report',    'RPT-001',     'Exported research report for RELIANCE to PDF',       'info',    '{"ticker":"RELIANCE","format":"pdf"}'::jsonb),
        (existing_user_id, 'demo@example.com', 'watchlist_share',  'sharing',    'watchlist', 'WL-001',      'Shared watchlist "Top Picks" with analyst@firm.com', 'info',    '{"shared_with":"analyst@firm.com","permission":"read"}'::jsonb),
        (existing_user_id, 'demo@example.com', 'alert_triggered',  'alerts',     'alert_rule','AR-001',      'Price alert triggered: INFY crossed above 1800',     'warning', '{"ticker":"INFY","metric":"price","threshold":1800}'::jsonb),
        (existing_user_id, 'demo@example.com', 'admin_action',     'admin',      'user',      NULL,          'Admin updated user role to analyst',                 'warning', '{"target_user":"user@example.com","new_role":"analyst"}'::jsonb),
        (existing_user_id, 'demo@example.com', 'user_login',       'auth',       'session',   NULL,          'User signed in via Google OAuth',                    'info',    '{"provider":"google"}'::jsonb),
        (existing_user_id, 'demo@example.com', 'data_export',      'data',       'report',    'RPT-002',     'Exported portfolio snapshot to CSV',                 'info',    '{"format":"csv","holdings":12}'::jsonb),
        (existing_user_id, 'demo@example.com', 'alert_triggered',  'alerts',     'alert_rule','AR-002',      'Margin of safety alert: TCS below 15%',              'warning', '{"ticker":"TCS","metric":"margin_of_safety","threshold":15}'::jsonb),
        (existing_user_id, 'demo@example.com', 'admin_action',     'admin',      'integration',NULL,         'Admin enabled Resend email integration',             'info',    '{"integration":"resend","action":"enabled"}'::jsonb),
        (existing_user_id, 'demo@example.com', 'watchlist_share',  'sharing',    'watchlist', 'WL-002',      'Revoked watchlist share for "NIFTY50 Watch"',        'info',    '{"action":"revoked","watchlist":"NIFTY50 Watch"}'::jsonb)
      ON CONFLICT (id) DO NOTHING;
    END IF;
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE 'Audit trail seed failed: %', SQLERRM;
END $$;
