-- DSP application infrastructure (auth-adjacent persistence only).
-- Do not put valuation, share-count authority, Buffett, moat, or recommendation formulas here.
-- Canonical outstanding-share facts stay in the DSP evidence pipeline.

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

create table if not exists public.profiles (
  id uuid primary key,
  dsp_user_id text not null unique,
  display_name text,
  email text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint profiles_dsp_user_id_len check (char_length(dsp_user_id) between 1 and 128),
  constraint profiles_email_len check (email is null or char_length(email) <= 320)
);

create table if not exists public.user_preferences (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  theme text not null default 'system',
  default_landing_page text not null default '/dashboard',
  preferred_watchlist_view text,
  alert_preferences jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint user_preferences_theme_ok
    check (theme in ('light', 'dark', 'system')),
  constraint user_preferences_landing_ok
    check (char_length(default_landing_page) between 1 and 128)
);

create table if not exists public.watchlists (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  name text not null default 'Watchlist',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint watchlists_name_len check (char_length(name) between 1 and 120)
);

create table if not exists public.watchlist_items (
  id uuid primary key default gen_random_uuid(),
  watchlist_id uuid not null references public.watchlists (id) on delete cascade,
  user_id uuid not null references public.profiles (id) on delete cascade,
  symbol text not null,
  exchange text,
  company_name text,
  created_at timestamptz not null default now(),
  constraint watchlist_items_symbol_ok
    check (symbol = upper(btrim(symbol)) and char_length(symbol) between 1 and 32)
);

create unique index if not exists watchlist_items_unique
  on public.watchlist_items (watchlist_id, symbol, (coalesce(exchange, '')));

create table if not exists public.saved_research (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  ticker text not null,
  company text,
  exchange text,
  analysis_id text,
  label text,
  research_status text,
  recommendation_action text,
  analysed_at timestamptz,
  saved_at timestamptz not null default now(),
  public_report jsonb not null default '{}'::jsonb,
  constraint saved_research_ticker_ok
    check (char_length(ticker) between 1 and 32),
  constraint saved_research_no_private_keys check (
    not (public_report ? 'private_prompt')
    and not (public_report ? 'prompt_parts')
    and not (public_report ? 'chain_of_thought')
    and not (public_report ? 'api_key')
    and not (public_report ? 'service_role')
    and not (public_report ? 'provider_routing')
    and not (public_report ? 'token_count')
    and not (public_report ? 'cost_usd')
  )
);

create table if not exists public.research_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  ticker text not null,
  exchange text,
  analysis_id text,
  event_type text not null,
  research_status text,
  created_at timestamptz not null default now(),
  constraint research_history_event_ok
    check (event_type in ('saved', 'opened', 'status_changed', 'deleted')),
  constraint research_history_ticker_ok
    check (char_length(ticker) between 1 and 32)
);

create table if not exists public.alerts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  symbol text,
  exchange text,
  alert_kind text not null,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint alerts_kind_ok
    check (alert_kind in ('research_ready', 'watchlist_update', 'status_change'))
);

create table if not exists public.stored_documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  storage_path text not null unique,
  filename text not null,
  content_type text,
  byte_size integer,
  document_kind text not null default 'user_upload',
  created_at timestamptz not null default now(),
  constraint stored_documents_kind_ok
    check (document_kind in ('user_upload')),
  constraint stored_documents_path_ok
    check (storage_path like 'user-documents/%'),
  constraint stored_documents_size_ok
    check (byte_size is null or (byte_size >= 0 and byte_size <= 20971520))
);

create table if not exists public.research_document_metadata (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  document_id uuid references public.stored_documents (id) on delete set null,
  saved_research_id uuid references public.saved_research (id) on delete set null,
  title text,
  source_locator text,
  created_at timestamptz not null default now(),
  constraint research_document_metadata_no_fetch check (
    source_locator is null
    or source_locator like 'https://%'
    or source_locator like 'http://%'
  )
);

create index if not exists profiles_dsp_user_id_idx on public.profiles (dsp_user_id);
create index if not exists watchlists_user_id_idx on public.watchlists (user_id);
create index if not exists watchlist_items_user_id_idx on public.watchlist_items (user_id);
create index if not exists saved_research_user_saved_idx
  on public.saved_research (user_id, saved_at desc);
create index if not exists research_history_user_created_idx
  on public.research_history (user_id, created_at desc);
create index if not exists alerts_user_id_idx on public.alerts (user_id);
create index if not exists stored_documents_user_id_idx on public.stored_documents (user_id);

-- ---------------------------------------------------------------------------
-- Updated-at triggers
-- ---------------------------------------------------------------------------

create or replace function public.dsp_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.dsp_set_updated_at();

drop trigger if exists user_preferences_set_updated_at on public.user_preferences;
create trigger user_preferences_set_updated_at
  before update on public.user_preferences
  for each row execute function public.dsp_set_updated_at();

drop trigger if exists watchlists_set_updated_at on public.watchlists;
create trigger watchlists_set_updated_at
  before update on public.watchlists
  for each row execute function public.dsp_set_updated_at();

drop trigger if exists alerts_set_updated_at on public.alerts;
create trigger alerts_set_updated_at
  before update on public.alerts
  for each row execute function public.dsp_set_updated_at();

-- ---------------------------------------------------------------------------
-- Row Level Security — deny by default; owner-only for authenticated.
-- Service role (server BFF) bypasses RLS. Anon has no table grants.
-- ---------------------------------------------------------------------------

alter table public.profiles enable row level security;
alter table public.user_preferences enable row level security;
alter table public.watchlists enable row level security;
alter table public.watchlist_items enable row level security;
alter table public.saved_research enable row level security;
alter table public.research_history enable row level security;
alter table public.alerts enable row level security;
alter table public.stored_documents enable row level security;
alter table public.research_document_metadata enable row level security;

revoke all on public.profiles from anon, authenticated, public;
revoke all on public.user_preferences from anon, authenticated, public;
revoke all on public.watchlists from anon, authenticated, public;
revoke all on public.watchlist_items from anon, authenticated, public;
revoke all on public.saved_research from anon, authenticated, public;
revoke all on public.research_history from anon, authenticated, public;
revoke all on public.alerts from anon, authenticated, public;
revoke all on public.stored_documents from anon, authenticated, public;
revoke all on public.research_document_metadata from anon, authenticated, public;

grant select, insert, update, delete on public.profiles to authenticated;
grant select, insert, update, delete on public.user_preferences to authenticated;
grant select, insert, update, delete on public.watchlists to authenticated;
grant select, insert, update, delete on public.watchlist_items to authenticated;
grant select, insert, update, delete on public.saved_research to authenticated;
grant select, insert, update, delete on public.research_history to authenticated;
grant select, insert, update, delete on public.alerts to authenticated;
grant select, insert, update, delete on public.stored_documents to authenticated;
grant select, insert, update, delete on public.research_document_metadata to authenticated;

create policy profiles_own on public.profiles
  for all to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());

create policy user_preferences_own on public.user_preferences
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy watchlists_own on public.watchlists
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy watchlist_items_own on public.watchlist_items
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy saved_research_own on public.saved_research
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy research_history_own on public.research_history
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy alerts_own on public.alerts
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy stored_documents_own on public.stored_documents
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy research_document_metadata_own on public.research_document_metadata
  for all to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- Storage — private user documents. Paths must start with auth.uid().
-- ---------------------------------------------------------------------------

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'user-documents',
  'user-documents',
  false,
  20971520,
  array[
    'application/pdf',
    'text/plain',
    'image/png',
    'image/jpeg',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ]
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit;

drop policy if exists user_documents_select_own on storage.objects;
drop policy if exists user_documents_insert_own on storage.objects;
drop policy if exists user_documents_update_own on storage.objects;
drop policy if exists user_documents_delete_own on storage.objects;

create policy user_documents_select_own on storage.objects
  for select to authenticated
  using (
    bucket_id = 'user-documents'
    and split_part(name, '/', 1) = auth.uid()::text
  );

create policy user_documents_insert_own on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'user-documents'
    and split_part(name, '/', 1) = auth.uid()::text
  );

create policy user_documents_update_own on storage.objects
  for update to authenticated
  using (
    bucket_id = 'user-documents'
    and split_part(name, '/', 1) = auth.uid()::text
  )
  with check (
    bucket_id = 'user-documents'
    and split_part(name, '/', 1) = auth.uid()::text
  );

create policy user_documents_delete_own on storage.objects
  for delete to authenticated
  using (
    bucket_id = 'user-documents'
    and split_part(name, '/', 1) = auth.uid()::text
  );

-- Realtime is available for status/history; the UI does not subscribe yet.
alter table public.research_history replica identity full;
alter table public.alerts replica identity full;
