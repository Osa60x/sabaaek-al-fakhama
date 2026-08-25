alter table public.profiles
  add column if not exists must_change_password boolean not null default false;

create table if not exists public.password_setup_tokens (
  token_hash text primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  purpose text not null check (purpose in ('owner_initial_setup')),
  expires_at timestamptz not null,
  used_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.password_setup_tokens enable row level security;

create policy "deny direct setup token access"
  on public.password_setup_tokens
  for all to anon, authenticated
  using (false)
  with check (false);

revoke all on public.password_setup_tokens from anon, authenticated;

create index if not exists password_setup_tokens_user_expiry_idx
  on public.password_setup_tokens (user_id, expires_at desc);

update public.profiles
set must_change_password = false
where role = 'owner';

create or replace function private.touch_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- Password values are handled only by Supabase Auth in the Edge Function.
-- This schema stores neither passwords nor password hashes.
