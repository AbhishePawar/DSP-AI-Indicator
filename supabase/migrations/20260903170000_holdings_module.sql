-- Holdings module: portfolio holdings with buy price, quantity, P&L, allocation

-- 1. Core table
CREATE TABLE IF NOT EXISTS public.holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    company_name TEXT,
    buy_price NUMERIC(18, 4) NOT NULL,
    quantity NUMERIC(18, 4) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, ticker)
);

-- 2. Indexes
CREATE INDEX IF NOT EXISTS idx_holdings_user_id ON public.holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_ticker ON public.holdings(ticker);

-- 3. Updated-at trigger function
CREATE OR REPLACE FUNCTION public.holdings_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

-- 4. Enable RLS
ALTER TABLE public.holdings ENABLE ROW LEVEL SECURITY;

-- 5. RLS policies
DROP POLICY IF EXISTS "users_manage_own_holdings" ON public.holdings;
CREATE POLICY "users_manage_own_holdings"
ON public.holdings
FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

-- 6. Trigger
DROP TRIGGER IF EXISTS holdings_updated_at ON public.holdings;
CREATE TRIGGER holdings_updated_at
    BEFORE UPDATE ON public.holdings
    FOR EACH ROW
    EXECUTE FUNCTION public.holdings_set_updated_at();
