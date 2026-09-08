-- ─── User Management Module ───────────────────────────────────────────────────
-- Adds:
--   1. public.user_profiles  — extended profile + tenant-admin permission flags
--   2. public.user_activity_log — lightweight per-user activity events
--   3. View: public.user_management_view — joins auth.users + profiles + activity

-- ─── 1. user_profiles ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.user_profiles (
  id                  uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name        text,
  role                text NOT NULL DEFAULT 'user',          -- 'user' | 'analyst' | 'admin'
  is_tenant_admin     boolean NOT NULL DEFAULT false,
  is_suspended        boolean NOT NULL DEFAULT false,
  can_access_research boolean NOT NULL DEFAULT true,
  can_access_portfolio boolean NOT NULL DEFAULT true,
  can_access_advisor  boolean NOT NULL DEFAULT false,
  can_export_reports  boolean NOT NULL DEFAULT false,
  notes               text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON public.user_profiles(role);
CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant_admin ON public.user_profiles(is_tenant_admin);

-- Updated-at trigger
CREATE OR REPLACE FUNCTION public.set_user_profiles_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_user_profiles_updated_at ON public.user_profiles;
CREATE TRIGGER trg_user_profiles_updated_at
  BEFORE UPDATE ON public.user_profiles
  FOR EACH ROW EXECUTE FUNCTION public.set_user_profiles_updated_at();

-- Auto-create profile on new auth user
CREATE OR REPLACE FUNCTION public.handle_new_user_profile()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO public.user_profiles (id, display_name)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email)
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_on_auth_user_created ON auth.users;
CREATE TRIGGER trg_on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user_profile();

-- ─── 2. user_activity_log ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.user_activity_log (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  event_type  text NOT NULL,   -- 'login' | 'research' | 'export' | 'alert' | 'portfolio'
  description text,
  metadata    jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_activity_log_user_id ON public.user_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_created_at ON public.user_activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_event_type ON public.user_activity_log(event_type);

-- ─── 3. RLS ───────────────────────────────────────────────────────────────────

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_activity_log ENABLE ROW LEVEL SECURITY;

-- user_profiles: users can read/update their own; tenant admins can read all
DROP POLICY IF EXISTS "user_profiles_own_read" ON public.user_profiles;
CREATE POLICY "user_profiles_own_read"
  ON public.user_profiles FOR SELECT
  USING (
    id = auth.uid()
    OR EXISTS (
      SELECT 1 FROM public.user_profiles p2
      WHERE p2.id = auth.uid() AND p2.is_tenant_admin = true
    )
  );

DROP POLICY IF EXISTS "user_profiles_own_update" ON public.user_profiles;
CREATE POLICY "user_profiles_own_update"
  ON public.user_profiles FOR UPDATE
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

DROP POLICY IF EXISTS "user_profiles_admin_update" ON public.user_profiles;
CREATE POLICY "user_profiles_admin_update"
  ON public.user_profiles FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles p2
      WHERE p2.id = auth.uid() AND p2.is_tenant_admin = true
    )
  );

DROP POLICY IF EXISTS "user_profiles_insert" ON public.user_profiles;
CREATE POLICY "user_profiles_insert"
  ON public.user_profiles FOR INSERT
  WITH CHECK (id = auth.uid());

-- user_activity_log: users can read their own; tenant admins can read all
DROP POLICY IF EXISTS "user_activity_log_own_read" ON public.user_activity_log;
CREATE POLICY "user_activity_log_own_read"
  ON public.user_activity_log FOR SELECT
  USING (
    user_id = auth.uid()
    OR EXISTS (
      SELECT 1 FROM public.user_profiles p2
      WHERE p2.id = auth.uid() AND p2.is_tenant_admin = true
    )
  );

DROP POLICY IF EXISTS "user_activity_log_own_insert" ON public.user_activity_log;
CREATE POLICY "user_activity_log_own_insert"
  ON public.user_activity_log FOR INSERT
  WITH CHECK (user_id = auth.uid());
