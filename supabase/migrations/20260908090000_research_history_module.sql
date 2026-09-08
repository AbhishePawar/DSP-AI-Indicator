-- Research History Module
-- Stores saved company analyses per user for the /research/history page

CREATE TABLE IF NOT EXISTS public.research_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  company TEXT NOT NULL DEFAULT '',
  exchange TEXT NOT NULL DEFAULT '',
  recommendation TEXT NOT NULL DEFAULT '',
  analysed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  saved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  label TEXT,
  key_findings TEXT,
  request JSONB,
  response JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_research_history_user_id ON public.research_history(user_id);
CREATE INDEX IF NOT EXISTS idx_research_history_ticker ON public.research_history(ticker);
CREATE INDEX IF NOT EXISTS idx_research_history_saved_at ON public.research_history(saved_at DESC);

ALTER TABLE public.research_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_manage_own_research_history" ON public.research_history;
CREATE POLICY "users_manage_own_research_history"
  ON public.research_history
  FOR ALL
  TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());
