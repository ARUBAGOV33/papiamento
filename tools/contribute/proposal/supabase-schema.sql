-- PROPOSAL: the contribution tool's own database (Supabase / Postgres).
-- Not run anywhere. The repo stays the source of truth: this database only
-- holds work in progress (answers, ratings, board decisions) until a sync job
-- turns decisions into a pull request.
--
-- Access rules (row-level security) carry the quality design:
--   * a contributor sees an item's other answers only after the item is decided,
--     so every answer is independent;
--   * nobody rates their own sentence; nobody decides on an item they answered;
--   * only board members read all answers and write decisions;
--   * email addresses never leave auth.users and are never exported.

create table people (
  id            uuid primary key references auth.users (id) on delete cascade,
  handle        text unique not null check (handle ~ '^[a-z0-9-]+$'),
  credit_name   text,                          -- null = do not name me
  role          text not null default 'contributor' check (role in ('contributor', 'board', 'maintainer')),
  github        text,                          -- required for board members
  consent       jsonb not null,                -- {"words": "CC-BY-4.0", "sentences": "CC0-1.0", "version": "...", "at": "..."}
  created_at    timestamptz not null default now()
);

-- Words to check or translate, and prompts to translate. Loaded from the repo
-- by the sync job; `ref` is the repo id (pap-000123, prm-000045).
create table items (
  id            bigint generated always as identity primary key,
  kind          text not null check (kind in ('review', 'translate', 'prompt')),
  ref           text not null,
  payload       jsonb not null,                -- lemma, page, crop url, machine draft, prompt text ...
  priority      integer not null default 0,    -- frequency rank for 'translate'
  split         text check (split in ('train', 'eval')),  -- prompts only; fixed at creation
  repo_commit   text not null,
  unique (kind, ref)
);

-- One row per person per word item ('review' or 'translate').
create table answers (
  id            bigint generated always as identity primary key,
  item_id       bigint not null references items (id),
  person_id     uuid not null references people (id),
  body          jsonb not null,                -- review: {en: {verdict, fix}, ...}; translate: {en, nl, es, unknown}
  comment       text,
  created_at    timestamptz not null default now(),
  unique (item_id, person_id)
);

-- Papiamento sentences written for a prompt. Several per prompt are allowed.
create table translations (
  id            bigint generated always as identity primary key,
  item_id       bigint not null references items (id),
  person_id     uuid not null references people (id),
  text          text not null,
  flags_kept    jsonb not null default '[]',   -- checker findings kept on purpose
  fix_of        bigint references translations (id),
  created_at    timestamptz not null default now()
);

create table ratings (
  id              bigint generated always as identity primary key,
  translation_id  bigint not null references translations (id),
  person_id       uuid not null references people (id),
  verdict         text not null check (verdict in ('good', 'fix')),
  fix_translation bigint references translations (id),
  comment         text,
  created_at      timestamptz not null default now(),
  unique (translation_id, person_id)
);

create table decisions (
  id            bigint generated always as identity primary key,
  kind          text not null check (kind in ('review', 'translate', 'sentence')),
  target        bigint not null,               -- items.id, or translations.id for 'sentence'
  board_id      uuid not null references people (id),
  outcome       text not null check (outcome in ('reviewed', 'disputed')),
  value         jsonb,                         -- chosen en/nl/es values, or the chosen sentence
  note          text,
  created_at    timestamptz not null default now(),
  exported_in   text                           -- PR url once the sync job has written it
);

-- security definer: these must see rows the caller's own policies hide.
create function is_board() returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from people where id = auth.uid() and role in ('board', 'maintainer'))
$$;

create function answer_count(p_item bigint) returns bigint language sql stable security definer set search_path = public as $$
  select count(*) from answers where item_id = p_item
$$;

alter table people       enable row level security;
alter table items        enable row level security;
alter table answers      enable row level security;
alter table translations enable row level security;
alter table ratings      enable row level security;
alter table decisions    enable row level security;

create policy "own profile"        on people for select using (id = auth.uid() or is_board());
create policy "create own profile" on people for insert with check (id = auth.uid() and role = 'contributor');
create policy "items readable"     on items  for select using (auth.uid() is not null);

-- Answers: write your own; read your own; the board reads all.
create policy "write own answer" on answers for insert with check (
  person_id = auth.uid()
  and answer_count(item_id) < 2
);
create policy "read own answer or board" on answers for select using (person_id = auth.uid() or is_board());

-- Sentences: write your own; others may read them only to rate them.
create policy "write own translation" on translations for insert with check (person_id = auth.uid());
create policy "read translations" on translations for select using (auth.uid() is not null);

-- Ratings: never your own sentence; raters do not see each other's ratings.
create policy "rate others" on ratings for insert with check (
  person_id = auth.uid()
  and (select t.person_id from translations t where t.id = translation_id) <> auth.uid()
);
create policy "read own rating or board" on ratings for select using (person_id = auth.uid() or is_board());

-- Decisions: board only, and not on an item the board member answered.
create policy "board decides" on decisions for insert with check (
  board_id = auth.uid() and is_board()
  and not exists (select 1 from answers a where a.item_id = target and a.person_id = auth.uid() and kind <> 'sentence')
  and not exists (select 1 from translations t where t.id = target and t.person_id = auth.uid() and kind = 'sentence')
  and not exists (select 1 from ratings r where r.translation_id = target and r.person_id = auth.uid() and kind = 'sentence')
);
create policy "read decisions" on decisions for select using (is_board());

-- The sync job uses a separate database role with read access to decided
-- rows and the people table (handles, credit names, GitHub names; no email),
-- and update access to decisions.exported_in only.
