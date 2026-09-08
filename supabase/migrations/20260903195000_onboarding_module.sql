-- Onboarding module: tracks first-time login walkthrough completion per user
-- Migration: 20260903195000_onboarding_module.sql

CREATE TABLE IF NOT EXISTS public.user_onboarding_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    completed BOOLEAN NOT NULL DEFAULT false,
    completed_at TIMESTAMPTZ,
    skipped BOOLEAN NOT NULL DEFAULT false,
    skipped_at TIMESTAMPTZ,
    last_step_seen INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_onboarding_state_user_id
    ON public.user_onboarding_state (user_id);

CREATE INDEX IF NOT EXISTS idx_user_onboarding_state_completed
    ON public.user_onboarding_state (user_id, completed);

-- updated_at trigger function (reuse pattern from other modules)
CREATE OR REPLACE FUNCTION public.set_onboarding_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

ALTER TABLE public.user_onboarding_state ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_manage_own_onboarding_state" ON public.user_onboarding_state;
CREATE POLICY "users_manage_own_onboarding_state"
ON public.user_onboarding_state
FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

DROP TRIGGER IF EXISTS trg_onboarding_updated_at ON public.user_onboarding_state;
CREATE TRIGGER trg_onboarding_updated_at
    BEFORE UPDATE ON public.user_onboarding_state
    FOR EACH ROW
    EXECUTE FUNCTION public.set_onboarding_updated_at();
