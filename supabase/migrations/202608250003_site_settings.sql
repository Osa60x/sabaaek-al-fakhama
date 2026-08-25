create table if not exists public.site_settings (
  singleton boolean primary key default true check (singleton = true),
  theme text not null default 'emerald_classic' check (theme in ('emerald_classic', 'obsidian_glass', 'ivory_luxe')),
  contact_actions jsonb not null default '[{"kind":"whatsapp","label":"تواصل عبر واتساب","value":"966550441259"}]'::jsonb check (jsonb_typeof(contact_actions) = 'array'),
  updated_by uuid references auth.users(id) on delete set null,
  updated_at timestamptz not null default now()
);

insert into public.site_settings (singleton)
values (true)
on conflict (singleton) do nothing;

drop trigger if exists site_settings_touch_updated_at on public.site_settings;
create trigger site_settings_touch_updated_at
before update on public.site_settings
for each row execute procedure private.touch_updated_at();

alter table public.site_settings enable row level security;
create policy "deny direct site settings access"
on public.site_settings
for all to anon, authenticated
using (false)
with check (false);

revoke all on public.site_settings from anon, authenticated;
