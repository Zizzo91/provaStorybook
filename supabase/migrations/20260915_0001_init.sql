-- provaStorybook: schema dedicato storybook su progetto gfglazxhxxplhoteaahr (gestione-conti)
-- Storie generate + impostazioni utente (chiave Groq), protette da RLS per user_id.

create schema if not exists storybook;

-- Storie
create table if not exists storybook.stories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  slug text not null,
  title text not null,
  audience text,
  tone text,
  idea text,
  short_version text,
  chapters jsonb not null default '[]',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, slug)
);

-- Impostazioni per utente (chiave Groq, mai nel repo)
create table if not exists storybook.settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  groq_api_key text not null default '',
  updated_at timestamptz not null default now()
);

alter table storybook.stories enable row level security;
alter table storybook.settings enable row level security;

drop policy if exists "stories read own" on storybook.stories;
create policy "stories read own"
  on storybook.stories for select
  to authenticated using (auth.uid() = user_id);

drop policy if exists "stories write own" on storybook.stories;
create policy "stories write own"
  on storybook.stories for all
  to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "settings read own" on storybook.settings;
create policy "settings read own"
  on storybook.settings for select
  to authenticated using (auth.uid() = user_id);

drop policy if exists "settings write own" on storybook.settings;
create policy "settings write own"
  on storybook.settings for all
  to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- trigger updated_at
create or replace function storybook.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end; $$;

drop trigger if exists trg_stories_updated_at on storybook.stories;
create trigger trg_stories_updated_at
  before update on storybook.stories
  for each row execute function storybook.set_updated_at();

drop trigger if exists trg_settings_updated_at on storybook.settings;
create trigger trg_settings_updated_at
  before update on storybook.settings
  for each row execute function storybook.set_updated_at();

-- grants (PostgREST + service_role per seed)
grant usage on schema storybook to authenticated, anon, service_role;
grant select, insert, update, delete on storybook.stories to authenticated, service_role;
grant select, insert, update, delete on storybook.settings to authenticated, service_role;

-- keepalive anon: solo la colonna non sensibile id, policy using(false) -> 200 senza dati
grant select (id) on storybook.stories to anon;
drop policy if exists "stories id for anon keepalive" on storybook.stories;
create policy "stories id for anon keepalive"
  on storybook.stories for select
  to anon using (false);