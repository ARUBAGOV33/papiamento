-- Contribution tool, database (Supabase / Postgres). Migration 001.
--
-- Paste the whole file into the Supabase SQL Editor once and press Run
-- (see README.md in this folder). It is safe to run on the empty project
-- "papiamento-contribute"; it stops with an error if the tables already exist.
--
-- What the access rules (row-level security, RLS) guarantee, for anyone using
-- the public (publishable) key, signed in or not:
--   * Without signing in, nothing can be read or written.
--   * Email addresses live only in Supabase's auth.users, which the API does
--     not expose. No table in this file has an email column.
--   * Blind answers: a contributor reads only their own answers, sentences and
--     ratings. Other people's work is visible only to the review board, plus the
--     sentences offered for rating (rate_queue), without their authors.
--   * Two independent answers per word: a third answer is refused, and so is a
--     second answer from the same person.
--   * Nobody rates their own sentence, rates one twice, or rates after the
--     board has decided.
--   * Only board members and maintainers decide, never on an item they
--     answered, wrote or rated. Maintainers do the board's work until the
--     board has two members (GOVERNANCE.md).
--   * Contributors cannot make themselves board members or maintainers, change
--     their handle or claim a GitHub name: those columns are not writable
--     through the API. A maintainer sets them in the SQL Editor (README.md).
--   * Only the sync job, with the secret key, marks decisions as exported.
--
-- Items (words and prompts) are not stored here: they come from the repo, by
-- id (pap-000123, prm-000045). Answers point at those ids.

begin;

-- ---------------------------------------------------------------- tables

create table public.profiles (
  id               uuid primary key references auth.users (id) on delete cascade,
  handle           text not null unique check (handle ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  credit_name      text not null default '' check (char_length(credit_name) <= 120),
  credit           boolean not null default true,          -- show credit_name in credits
  role             text not null default 'contributor' check (role in ('contributor', 'board', 'maintainer')),
  github           text check (github is null or github ~ '^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$'),
  occupation       text not null default 'teacher' check (occupation in ('teacher', 'linguist', 'other')),
  school           text not null default '' check (char_length(school) <= 160),
  consent_version  text not null check (consent_version ~ '^tool-[0-9]{4}-[0-9]{2}$'),
  licence_words    text not null default 'CC-BY-4.0' check (licence_words = 'CC-BY-4.0'),
  licence_sentences text not null default 'CC0-1.0' check (licence_sentences = 'CC0-1.0'),
  created_at       timestamptz not null default now()
);
comment on table public.profiles is 'One row per contributor. No email: that stays in auth.users.';

-- Handles already used in the repo (_meta/contributors.tsv) and words that
-- must not become handles. create_profile never hands these out.
create table public.reserved_handles (
  handle text primary key,
  note   text not null default ''
);
insert into public.reserved_handles (handle, note) values
  ('arubagov33', 'maintainer in _meta/contributors.tsv'),
  ('victorgomesrt-rgb', 'maintainer in _meta/contributors.tsv'),
  ('machine', 'means machine-made in the data'),
  ('board', 'means the review board in the tool'),
  ('unknown', 'reserved');

-- Answers on words: check a machine translation (review) or translate a word.
create table public.answers (
  id          bigint generated always as identity primary key,
  kind        text not null check (kind in ('review', 'translate')),
  ref         text not null check (ref ~ '^pap-[0-9]{6}$'),
  person_id   uuid not null default auth.uid() references public.profiles (id) on delete cascade,
  body        jsonb not null check (jsonb_typeof(body) = 'object' and octet_length(body::text) <= 4000),
  comment     text not null default '' check (char_length(comment) <= 1000),
  created_at  timestamptz not null default now(),
  unique (kind, ref, person_id)
);

-- Aruban Papiamento sentences written for a prompt. Several per prompt.
create table public.translations (
  id          bigint generated always as identity primary key,
  prompt_ref  text not null check (prompt_ref ~ '^prm-[0-9]{6}$'),
  person_id   uuid not null default auth.uid() references public.profiles (id) on delete cascade,
  text        text not null check (char_length(btrim(text)) between 1 and 400),
  flags_kept  jsonb not null default '[]' check (jsonb_typeof(flags_kept) = 'array' and octet_length(flags_kept::text) <= 4000),
  fix_of      bigint references public.translations (id) on delete set null,
  created_at  timestamptz not null default now()
);

-- A second teacher's rating of someone else's sentence.
create table public.ratings (
  id                  bigint generated always as identity primary key,
  translation_id      bigint not null references public.translations (id) on delete cascade,
  person_id           uuid not null default auth.uid() references public.profiles (id) on delete cascade,
  verdict             text not null check (verdict in ('good', 'fix')),
  fix_translation_id  bigint references public.translations (id) on delete set null,
  comment             text not null default '' check (char_length(comment) <= 1000),
  created_at          timestamptz not null default now(),
  unique (translation_id, person_id)
);

-- A review-board decision on a word (review, translate) or a sentence.
create table public.decisions (
  id              bigint generated always as identity primary key,
  kind            text not null check (kind in ('review', 'translate', 'sentence')),
  word_ref        text check (word_ref ~ '^pap-[0-9]{6}$'),
  translation_id  bigint references public.translations (id) on delete cascade,
  board_id        uuid not null default auth.uid() references public.profiles (id),
  outcome         text not null check (outcome in ('reviewed', 'disputed')),
  value           jsonb check (value is null or (jsonb_typeof(value) = 'object' and octet_length(value::text) <= 6000)),
  note            text not null default '' check (char_length(note) <= 1000),
  created_at      timestamptz not null default now(),
  exported_in     text,              -- pull request URL, set by the sync job
  exported_at     timestamptz,
  check ((kind in ('review', 'translate') and word_ref is not null and translation_id is null)
      or (kind = 'sentence' and translation_id is not null and word_ref is null))
);
create unique index decisions_one_per_word on public.decisions (kind, word_ref) where word_ref is not null;
create unique index decisions_one_per_sentence on public.decisions (translation_id) where translation_id is not null;

create index answers_ref on public.answers (kind, ref);
create index answers_person on public.answers (person_id);
create index translations_prompt on public.translations (prompt_ref);
create index translations_person on public.translations (person_id);
create index ratings_translation on public.ratings (translation_id);
create index ratings_person on public.ratings (person_id);
create index decisions_board on public.decisions (board_id);

-- ---------------------------------------------------------------- helpers
-- In a schema the API does not expose. Security definer, so the access rules
-- can count rows the caller may not read; each returns only a yes/no or a count.

create schema contribute_private;

-- Board members decide. Maintainers do the board's work only while the board
-- has fewer than two members (GOVERNANCE.md).
create function contribute_private.is_board() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid()
      and (role = 'board'
           or (role = 'maintainer' and (select count(*) from public.profiles where role = 'board') < 2)))
$$;

-- The prompt a sentence translates; lets rate_sentence check a correction
-- without showing the caller anyone else's row.
create function contribute_private.translation_prompt(p_translation bigint) returns text
language sql stable security definer set search_path = public as $$
  select prompt_ref from public.translations where id = p_translation
$$;

create function contribute_private.has_profile() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = auth.uid())
$$;

create function contribute_private.word_decided(p_kind text, p_ref text) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.decisions where kind = p_kind and word_ref = p_ref)
$$;

create function contribute_private.sentence_decided(p_translation bigint) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.decisions where translation_id = p_translation)
$$;

create function contribute_private.translation_owner(p_translation bigint) returns uuid
language sql stable security definer set search_path = public as $$
  select person_id from public.translations where id = p_translation
$$;

-- True when the person took part in the item, so they may not decide it.
create function contribute_private.involved_word(p_kind text, p_ref text, p_person uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.answers where kind = p_kind and ref = p_ref and person_id = p_person)
$$;

create function contribute_private.involved_sentence(p_translation bigint, p_person uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.translations where id = p_translation and person_id = p_person)
      or exists (select 1 from public.ratings where translation_id = p_translation and person_id = p_person)
$$;

grant usage on schema contribute_private to authenticated;

-- ---------------------------------------------------------------- limits enforced by triggers
-- Counted under a lock, so two people answering at the same moment cannot
-- both become the second answer.

create function contribute_private.check_answer() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform pg_advisory_xact_lock(hashtext('answer:' || new.kind || ':' || new.ref));
  if (select count(*) from public.answers where kind = new.kind and ref = new.ref) >= 2 then
    raise exception 'This word already has two answers.' using errcode = 'P0001', hint = 'full';
  end if;
  if contribute_private.word_decided(new.kind, new.ref) then
    raise exception 'The review board has already decided this word.' using errcode = 'P0001', hint = 'decided';
  end if;
  return new;
end $$;
create trigger answers_limit before insert on public.answers for each row execute function contribute_private.check_answer();

create function contribute_private.check_rating() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  perform pg_advisory_xact_lock(hashtext('rating:' || new.translation_id));
  if (select count(*) from public.ratings where translation_id = new.translation_id) >= 2 then
    raise exception 'This sentence already has two ratings.' using errcode = 'P0001', hint = 'full';
  end if;
  if contribute_private.sentence_decided(new.translation_id) then
    raise exception 'The review board has already decided this sentence.' using errcode = 'P0001', hint = 'decided';
  end if;
  return new;
end $$;
create trigger ratings_limit before insert on public.ratings for each row execute function contribute_private.check_rating();

-- ---------------------------------------------------------------- row-level security

alter table public.profiles         enable row level security;
alter table public.reserved_handles enable row level security;   -- no policies: not readable through the API
alter table public.answers          enable row level security;
alter table public.translations     enable row level security;
alter table public.ratings          enable row level security;
alter table public.decisions        enable row level security;

create policy "read own profile, board reads all" on public.profiles
  for select to authenticated using (id = auth.uid() or contribute_private.is_board());
create policy "edit own profile" on public.profiles
  for update to authenticated using (id = auth.uid()) with check (id = auth.uid());
-- Profiles are created through create_profile() only.

create policy "write own answers" on public.answers
  for insert to authenticated with check (person_id = auth.uid() and contribute_private.has_profile());
create policy "read own answers, board reads all" on public.answers
  for select to authenticated using (person_id = auth.uid() or contribute_private.is_board());

create policy "write own sentences" on public.translations
  for insert to authenticated with check (
    person_id = auth.uid() and contribute_private.has_profile()
    and (fix_of is null or contribute_private.translation_owner(fix_of) <> auth.uid()));
create policy "read own sentences, board reads all" on public.translations
  for select to authenticated using (person_id = auth.uid() or contribute_private.is_board());

create policy "rate other people's sentences" on public.ratings
  for insert to authenticated with check (
    person_id = auth.uid() and contribute_private.has_profile()
    and contribute_private.translation_owner(translation_id) <> auth.uid()
    and (fix_translation_id is null or contribute_private.translation_owner(fix_translation_id) = auth.uid()));
create policy "read own ratings, board reads all" on public.ratings
  for select to authenticated using (person_id = auth.uid() or contribute_private.is_board());

create policy "board decides items it did not take part in" on public.decisions
  for insert to authenticated with check (
    board_id = auth.uid() and contribute_private.is_board()
    and exported_in is null and exported_at is null
    and case when kind = 'sentence' then not contribute_private.involved_sentence(translation_id, auth.uid())
             else not contribute_private.involved_word(kind, word_ref, auth.uid()) end);
create policy "board reads decisions" on public.decisions
  for select to authenticated using (contribute_private.is_board());
create policy "board undoes its own unexported decisions" on public.decisions
  for delete to authenticated using (board_id = auth.uid() and contribute_private.is_board() and exported_in is null);

-- ---------------------------------------------------------------- functions the app calls (RPC)

-- Create the signed-in person's profile with a unique handle made from the name.
create function public.create_profile(p_name text, p_credit boolean, p_school text, p_occupation text, p_consent_version text)
returns public.profiles
language plpgsql security definer set search_path = public as $$
declare
  v_uid uuid := auth.uid();
  v_row public.profiles;
  v_base text;
  v_handle text;
  v_n int := 1;
begin
  if v_uid is null then
    raise exception 'Sign in first.' using errcode = '28000';
  end if;
  select * into v_row from public.profiles where id = v_uid;
  if found then
    return v_row;
  end if;
  if coalesce(btrim(p_name), '') = '' then
    raise exception 'A name is required.' using errcode = '22023';
  end if;
  v_base := lower(translate(btrim(p_name),
    'áàâäãåāéèêëēíìîïīóòôöõøōúùûüūñçýÿÁÀÂÄÃÅĀÉÈÊËĒÍÌÎÏĪÓÒÔÖÕØŌÚÙÛÜŪÑÇÝ',
    'aaaaaaaeeeeeiiiiiooooooouuuuuncyyAAAAAAAEEEEEIIIIIOOOOOOOUUUUUNCY'));
  v_base := btrim(regexp_replace(v_base, '[^a-z0-9]+', '-', 'g'), '-');
  v_base := btrim(left(v_base, 40), '-');
  if v_base = '' then
    v_base := 'contributor';
  end if;
  v_handle := v_base;
  while exists (select 1 from public.profiles where handle = v_handle)
     or exists (select 1 from public.reserved_handles where handle = v_handle) loop
    v_n := v_n + 1;
    v_handle := v_base || '-' || v_n;
  end loop;
  insert into public.profiles (id, handle, credit_name, credit, school, occupation, consent_version)
  values (v_uid, v_handle, left(btrim(p_name), 120), coalesce(p_credit, true),
          left(coalesce(btrim(p_school), ''), 160), coalesce(p_occupation, 'teacher'), p_consent_version)
  returning * into v_row;
  return v_row;
end $$;

-- What is still open for the signed-in person, as ids and counts only: never
-- the content or the authors of other people's answers.
create function public.queue_state()
returns jsonb
language sql stable security definer set search_path = public as $$
  select case when auth.uid() is null then null else jsonb_build_object(
    'review_closed', coalesce((
      select jsonb_agg(ref order by ref) from (
        select ref from public.answers where kind = 'review' group by ref having count(*) >= 2
        union select ref from public.answers where kind = 'review' and person_id = auth.uid()
        union select word_ref from public.decisions where kind = 'review') s), '[]'::jsonb),
    'translate_closed', coalesce((
      select jsonb_agg(ref order by ref) from (
        select ref from public.answers where kind = 'translate' group by ref having count(*) >= 2
        union select ref from public.answers where kind = 'translate' and person_id = auth.uid()
        union select word_ref from public.decisions where kind = 'translate') s), '[]'::jsonb),
    'prompts', coalesce((
      select jsonb_agg(jsonb_build_object('ref', p.prompt_ref, 'n', p.n, 'mine', p.mine, 'rated', p.rated) order by p.prompt_ref)
      from (
        select t.prompt_ref,
               count(*) as n,
               count(*) filter (where t.person_id = auth.uid()) as mine,
               bool_or(exists (select 1 from public.ratings r where r.translation_id = t.id and r.person_id = auth.uid())) as rated
        from public.translations t
        group by t.prompt_ref) p), '[]'::jsonb),
    'rate_open', (
      select count(*) from public.translations t
      where t.person_id <> auth.uid()
        and (select count(*) from public.ratings r where r.translation_id = t.id) < 2
        and not exists (select 1 from public.ratings r where r.translation_id = t.id and r.person_id = auth.uid())
        and not exists (select 1 from public.decisions d where d.translation_id = t.id)),
    'my_waiting', (
      (select count(*) from public.answers a
       where a.person_id = auth.uid()
         and (select count(*) from public.answers o where o.kind = a.kind and o.ref = a.ref) < 2
         and not exists (select 1 from public.decisions d where d.kind = a.kind and d.word_ref = a.ref))
      + (select count(*) from public.translations t
         where t.person_id = auth.uid()
           and not exists (select 1 from public.ratings r where r.translation_id = t.id)
           and not exists (select 1 from public.decisions d where d.translation_id = t.id))),
    'my_confirmed', (
      (select count(*) from public.answers a
       where a.person_id = auth.uid()
         and exists (select 1 from public.decisions d where d.kind = a.kind and d.word_ref = a.ref and d.outcome = 'reviewed'))
      + (select count(*) from public.translations t
         where t.person_id = auth.uid()
           and exists (select 1 from public.decisions d where d.translation_id = t.id and d.outcome = 'reviewed'))),
    'board', contribute_private.is_board(),
    'board_open', case when contribute_private.is_board() then (
      (select count(*) from (
         select kind, ref from public.answers group by kind, ref having count(*) >= 2
         except select kind, word_ref from public.decisions where word_ref is not null) w)
      + (select count(*) from public.translations t
         where exists (select 1 from public.ratings r where r.translation_id = t.id)
           and not exists (select 1 from public.decisions d where d.translation_id = t.id)))
      else 0 end
  ) end
$$;

-- Sentences the signed-in person may rate: other people's, not yet rated by
-- them, with fewer than two ratings and no decision. Prompts they have
-- translated themselves come first. No author is returned.
create function public.rate_queue(p_limit int default 20)
returns table (id bigint, prompt_ref text, text text, flags_kept jsonb)
language sql stable security definer set search_path = public as $$
  select t.id, t.prompt_ref, t.text, t.flags_kept
  from public.translations t
  where auth.uid() is not null
    and t.person_id <> auth.uid()
    and (select count(*) from public.ratings r where r.translation_id = t.id) < 2
    and not exists (select 1 from public.ratings r where r.translation_id = t.id and r.person_id = auth.uid())
    and not exists (select 1 from public.decisions d where d.translation_id = t.id)
  order by exists (select 1 from public.translations m where m.prompt_ref = t.prompt_ref and m.person_id = auth.uid()) desc,
           t.created_at, t.id
  limit greatest(1, least(coalesce(p_limit, 20), 100))
$$;

-- Rate a sentence, with an optional corrected version, in one step: if the
-- rating is refused (two ratings already, or the board has decided), the
-- correction is not kept either. Runs with the caller's own rights, so every
-- access rule above still applies.
create function public.rate_sentence(p_translation bigint, p_verdict text, p_fix_text text default null,
                                     p_fix_flags jsonb default '[]', p_comment text default '')
returns bigint
language plpgsql security invoker set search_path = public as $$
declare
  v_prompt text := contribute_private.translation_prompt(p_translation);
  v_fix bigint;
  v_rating bigint;
begin
  if v_prompt is null then
    raise exception 'This sentence does not exist.' using errcode = 'P0002';
  end if;
  if p_verdict = 'fix' then
    if coalesce(btrim(p_fix_text), '') = '' then
      raise exception 'A correction needs a sentence.' using errcode = '22023';
    end if;
    insert into public.translations (prompt_ref, text, flags_kept, fix_of)
    values (v_prompt, btrim(p_fix_text), coalesce(p_fix_flags, '[]'::jsonb), p_translation)
    returning id into v_fix;
  end if;
  insert into public.ratings (translation_id, verdict, fix_translation_id, comment)
  values (p_translation, p_verdict, v_fix, coalesce(p_comment, ''))
  returning id into v_rating;
  return v_rating;
end $$;

-- The credits page: names of people who agreed to be named, handles for the
-- others, and how many contributions each made. No email, no school.
create function public.credits()
returns table (name text, handle text, role text, contributions bigint)
language sql stable security definer set search_path = public as $$
  select case when p.credit and p.credit_name <> '' then p.credit_name else p.handle end,
         p.handle, p.role,
         (select count(*) from public.answers a where a.person_id = p.id)
       + (select count(*) from public.translations t where t.person_id = p.id)
       + (select count(*) from public.ratings r where r.person_id = p.id)
       + (select count(*) from public.decisions d where d.board_id = p.id)
  from public.profiles p
  where auth.uid() is not null
  order by 1
$$;

-- ---------------------------------------------------------------- privileges
-- Supabase grants every new table and function to anon and authenticated by
-- default. Take that back and grant only what the app needs; RLS then
-- decides which rows.

revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke all on all functions in schema public from anon, authenticated, public;
revoke all on all functions in schema contribute_private from anon, authenticated, public;

grant select on public.profiles to authenticated;
grant update (credit_name, credit, school, occupation) on public.profiles to authenticated;
grant select, insert on public.answers, public.translations, public.ratings to authenticated;
grant select, insert, delete on public.decisions to authenticated;
grant usage on all sequences in schema public to authenticated;

grant execute on function public.create_profile(text, boolean, text, text, text) to authenticated;
grant execute on function public.queue_state() to authenticated;
grant execute on function public.rate_queue(int) to authenticated;
grant execute on function public.credits() to authenticated;
grant execute on function public.rate_sentence(bigint, text, text, jsonb, text) to authenticated;
grant execute on all functions in schema contribute_private to authenticated;

-- Keep future objects locked down by default too.
alter default privileges in schema public revoke all on tables from anon, authenticated;
alter default privileges in schema public revoke all on functions from anon, authenticated, public;
alter default privileges in schema public revoke all on sequences from anon, authenticated;

commit;
