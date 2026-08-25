create schema if not exists private;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  role text not null default 'user' check (role in ('owner', 'manager', 'user')),
  is_active boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.price_adjustments (
  carat text primary key check (carat in ('24', '21', '18')),
  adjustment_sar numeric(10,2) not null default 0 check (adjustment_sar between -5000 and 5000),
  updated_by uuid references auth.users(id) on delete set null,
  updated_at timestamptz not null default now()
);

insert into public.price_adjustments (carat, adjustment_sar) values
  ('24', 0), ('21', 0), ('18', 0)
on conflict (carat) do nothing;

create table if not exists public.manager_invites (
  id bigint generated always as identity primary key,
  email text not null unique check (email = lower(email)),
  invited_by uuid not null references auth.users(id) on delete restrict,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.audit_log (
  id bigint generated always as identity primary key,
  actor_id uuid references auth.users(id) on delete set null,
  actor_role text,
  action text not null,
  entity_type text not null,
  detail jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create or replace function private.touch_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create or replace function private.handle_new_sabaaek_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name, role, is_active)
  values (
    new.id,
    nullif(coalesce(new.raw_user_meta_data ->> 'display_name', split_part(coalesce(new.email, ''), '@', 1)), ''),
    case when lower(coalesce(new.email, '')) = 'osa60x@gmail.com' then 'owner' else 'user' end,
    case when lower(coalesce(new.email, '')) = 'osa60x@gmail.com' then true else false end
  )
  on conflict (id) do update set
    role = case when lower(coalesce(new.email, '')) = 'osa60x@gmail.com' then 'owner' else public.profiles.role end,
    is_active = case when lower(coalesce(new.email, '')) = 'osa60x@gmail.com' then true else public.profiles.is_active end,
    updated_at = now();
  return new;
end;
$$;

create or replace function private.is_active_admin(target_user uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.profiles
    where id = target_user and is_active = true and role in ('owner', 'manager')
  );
$$;

create or replace function private.is_owner(target_user uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.profiles
    where id = target_user and is_active = true and role = 'owner'
  );
$$;

drop trigger if exists profiles_touch_updated_at on public.profiles;
create trigger profiles_touch_updated_at before update on public.profiles for each row execute procedure private.touch_updated_at();
drop trigger if exists adjustments_touch_updated_at on public.price_adjustments;
create trigger adjustments_touch_updated_at before update on public.price_adjustments for each row execute procedure private.touch_updated_at();
drop trigger if exists invites_touch_updated_at on public.manager_invites;
create trigger invites_touch_updated_at before update on public.manager_invites for each row execute procedure private.touch_updated_at();
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users for each row execute procedure private.handle_new_sabaaek_user();

alter table public.profiles enable row level security;
alter table public.price_adjustments enable row level security;
alter table public.manager_invites enable row level security;
alter table public.audit_log enable row level security;

create policy "profile owner may read self" on public.profiles for select to authenticated using (id = auth.uid());
create policy "deny direct profile changes" on public.profiles for all to authenticated using (false) with check (false);
create policy "deny direct adjustment reads" on public.price_adjustments for select to anon, authenticated using (false);
create policy "deny direct adjustment writes" on public.price_adjustments for all to anon, authenticated using (false) with check (false);
create policy "deny direct invite access" on public.manager_invites for all to anon, authenticated using (false) with check (false);
create policy "deny direct audit access" on public.audit_log for all to anon, authenticated using (false) with check (false);

revoke all on public.profiles, public.price_adjustments, public.manager_invites, public.audit_log from anon, authenticated;
grant select on public.profiles to authenticated;

create or replace function public.apply_sabaaek_adjustments(p_updates jsonb, p_actor uuid)
returns table(carat text, adjustment_sar numeric, updated_at timestamptz)
language plpgsql
security definer
set search_path = ''
as $$
declare
  item jsonb;
  requested_carat text;
  requested_value numeric;
begin
  if not private.is_active_admin(p_actor) then
    raise exception 'not_authorized';
  end if;
  if jsonb_typeof(p_updates) <> 'array' or jsonb_array_length(p_updates) <> 3 then
    raise exception 'invalid_adjustments';
  end if;
  if (select count(distinct value ->> 'carat') from jsonb_array_elements(p_updates)) <> 3
    or not (p_updates @> '[{"carat":"24"},{"carat":"21"},{"carat":"18"}]'::jsonb) then
    raise exception 'invalid_carats';
  end if;
  for item in select value from jsonb_array_elements(p_updates) loop
    requested_carat := item ->> 'carat';
    requested_value := (item ->> 'adjustment_sar')::numeric;
    if requested_value is null or requested_value < -5000 or requested_value > 5000 then
      raise exception 'invalid_adjustment_value';
    end if;
    update public.price_adjustments
      set adjustment_sar = round(requested_value, 2), updated_by = p_actor, updated_at = now()
      where price_adjustments.carat = requested_carat;
  end loop;
  insert into public.audit_log (actor_id, actor_role, action, entity_type, detail)
  select p_actor, role, 'price_adjustments_updated', 'price_adjustments', p_updates
  from public.profiles where id = p_actor;
  return query select p.carat, p.adjustment_sar, p.updated_at from public.price_adjustments p order by p.carat desc;
end;
$$;

revoke all on function public.apply_sabaaek_adjustments(jsonb, uuid) from public, anon, authenticated;
grant execute on function public.apply_sabaaek_adjustments(jsonb, uuid) to service_role;
