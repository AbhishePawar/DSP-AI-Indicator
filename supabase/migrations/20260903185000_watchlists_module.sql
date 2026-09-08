-- Watchlists module: named watchlists with ticker lists
-- Backs the /watchlists page: create, edit, view saved watchlists

-- 1. Core tables
CREATE TABLE IF NOT EXISTS public.watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.watchlist_tickers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    watchlist_id UUID NOT NULL REFERENCES public.watchlists(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    company_name TEXT,
    notes TEXT,
    added_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (watchlist_id, ticker)
);

-- 2. Indexes
CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON public.watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlists_created_at ON public.watchlists(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_watchlist_tickers_watchlist_id ON public.watchlist_tickers(watchlist_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_tickers_user_id ON public.watchlist_tickers(user_id);

-- 3. Updated_at trigger function
CREATE OR REPLACE FUNCTION public.set_watchlists_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

-- 4. Enable RLS
ALTER TABLE public.watchlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlist_tickers ENABLE ROW LEVEL SECURITY;

-- 5. RLS Policies
DROP POLICY IF EXISTS "users_manage_own_watchlists" ON public.watchlists;
CREATE POLICY "users_manage_own_watchlists"
ON public.watchlists FOR ALL TO authenticated
USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "users_manage_own_watchlist_tickers" ON public.watchlist_tickers;
CREATE POLICY "users_manage_own_watchlist_tickers"
ON public.watchlist_tickers FOR ALL TO authenticated
USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

-- 6. Triggers
DROP TRIGGER IF EXISTS set_watchlists_updated_at ON public.watchlists;
CREATE TRIGGER set_watchlists_updated_at
    BEFORE UPDATE ON public.watchlists
    FOR EACH ROW EXECUTE FUNCTION public.set_watchlists_updated_at();

-- 7. Seed demo data for existing users
DO $$
DECLARE
    existing_user_id UUID;
    wl_id_1 UUID := gen_random_uuid();
    wl_id_2 UUID := gen_random_uuid();
    wl_id_3 UUID := gen_random_uuid();
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'auth' AND table_name = 'users'
    ) THEN
        SELECT id INTO existing_user_id FROM auth.users LIMIT 1;

        IF existing_user_id IS NOT NULL THEN
            INSERT INTO public.watchlists (id, user_id, name, description, created_at)
            VALUES
                (wl_id_1, existing_user_id, 'Tech Giants', 'Large-cap technology companies', now() - interval '14 days'),
                (wl_id_2, existing_user_id, 'Value Picks', 'Undervalued companies with strong fundamentals', now() - interval '7 days'),
                (wl_id_3, existing_user_id, 'Dividend Income', 'High-yield dividend stocks', now() - interval '3 days')
            ON CONFLICT (id) DO NOTHING;

            INSERT INTO public.watchlist_tickers (id, watchlist_id, user_id, ticker, company_name, added_at)
            VALUES
                (gen_random_uuid(), wl_id_1, existing_user_id, 'AAPL', 'Apple Inc.', now() - interval '14 days'),
                (gen_random_uuid(), wl_id_1, existing_user_id, 'MSFT', 'Microsoft Corporation', now() - interval '14 days'),
                (gen_random_uuid(), wl_id_1, existing_user_id, 'GOOGL', 'Alphabet Inc.', now() - interval '13 days'),
                (gen_random_uuid(), wl_id_1, existing_user_id, 'NVDA', 'NVIDIA Corporation', now() - interval '12 days'),
                (gen_random_uuid(), wl_id_2, existing_user_id, 'BRK.B', 'Berkshire Hathaway', now() - interval '7 days'),
                (gen_random_uuid(), wl_id_2, existing_user_id, 'JPM', 'JPMorgan Chase', now() - interval '6 days'),
                (gen_random_uuid(), wl_id_2, existing_user_id, 'JNJ', 'Johnson & Johnson', now() - interval '5 days'),
                (gen_random_uuid(), wl_id_3, existing_user_id, 'KO', 'The Coca-Cola Company', now() - interval '3 days'),
                (gen_random_uuid(), wl_id_3, existing_user_id, 'PG', 'Procter & Gamble', now() - interval '2 days'),
                (gen_random_uuid(), wl_id_3, existing_user_id, 'T', 'AT&T Inc.', now() - interval '1 day')
            ON CONFLICT (watchlist_id, ticker) DO NOTHING;
        ELSE
            RAISE NOTICE 'No existing users found. Skipping seed data.';
        END IF;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Seed data insertion failed: %', SQLERRM;
END $$;
