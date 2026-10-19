-- Contribution tool: access-rule test. Run it in the Supabase SQL Editor after
-- 001_contribute.sql (README.md, step 6).
--
-- It creates three test people inside a transaction, tries everything the
-- rules must allow or refuse, and rolls it all back: nothing is kept.
-- Each check prints PASS in the Messages panel. The first failure stops the
-- script with an error that starts with FAIL.

begin;

-- Three test sign-ins. The .invalid addresses can never receive mail.
insert into auth.users (id, aud, role, email, created_at, updated_at)
values ('00000000-0000-4000-8000-00000000000a', 'authenticated', 'authenticated', 'rls-test-a@example.invalid', now(), now()),
       ('00000000-0000-4000-8000-00000000000b', 'authenticated', 'authenticated', 'rls-test-b@example.invalid', now(), now()),
       ('00000000-0000-4000-8000-00000000000c', 'authenticated', 'authenticated', 'rls-test-c@example.invalid', now(), now());

-- ---------------------------------------------------------------- anonymous visitor (publishable key, not signed in)
set local role anon;
set local request.jwt.claims = '{"role": "anon"}';

do $$ begin
  begin perform 1 from public.answers limit 1;
        raise exception 'FAIL: anonymous visitor can read answers';
  exception when insufficient_privilege then raise notice 'PASS: anonymous visitor cannot read answers'; end;
  begin perform 1 from public.profiles limit 1;
        raise exception 'FAIL: anonymous visitor can read profiles';
  exception when insufficient_privilege then raise notice 'PASS: anonymous visitor cannot read profiles'; end;
  begin perform 1 from public.translations limit 1;
        raise exception 'FAIL: anonymous visitor can read sentences';
  exception when insufficient_privilege then raise notice 'PASS: anonymous visitor cannot read sentences'; end;
  begin perform 1 from auth.users limit 1;
        raise exception 'FAIL: anonymous visitor can read auth.users (emails)';
  exception when insufficient_privilege then raise notice 'PASS: anonymous visitor cannot read auth.users (emails)'; end;
  begin perform public.queue_state();
        raise exception 'FAIL: anonymous visitor can call queue_state';
  exception when insufficient_privilege then raise notice 'PASS: anonymous visitor cannot call the app functions'; end;
  begin insert into public.answers (kind, ref, person_id, body) values ('review', 'pap-000001', '00000000-0000-4000-8000-00000000000a', '{}');
        raise exception 'FAIL: anonymous visitor can write an answer';
  exception when insufficient_privilege then raise notice 'PASS: anonymous visitor cannot write'; end;
end $$;

-- ---------------------------------------------------------------- person A
set local role authenticated;
set local request.jwt.claims = '{"sub": "00000000-0000-4000-8000-00000000000a", "role": "authenticated"}';

do $$
declare v_tr bigint;
begin
  perform public.create_profile('Test Teacher A', true, 'Test school', 'teacher', 'tool-2026-10');
  insert into public.answers (kind, ref, body) values ('review', 'pap-000001', '{"en": {"verdict": "correct"}}');
  insert into public.translations (prompt_ref, text) values ('prm-000001', 'test sentence a') returning id into v_tr;
  perform set_config('rls_test.tr_a', v_tr::text, true);
  raise notice 'PASS: A created a profile, an answer and a sentence';

  begin perform 1 from auth.users limit 1;
        raise exception 'FAIL: a signed-in person can read auth.users (emails)';
  exception when insufficient_privilege then raise notice 'PASS: a signed-in person cannot read auth.users (emails)'; end;
  begin perform 1 from public.reserved_handles limit 1;
        raise exception 'FAIL: reserved_handles is readable';
  exception when insufficient_privilege then raise notice 'PASS: reserved_handles is not readable'; end;
  begin update public.profiles set role = 'maintainer' where id = auth.uid();
        raise exception 'FAIL: A can make themselves a maintainer';
  exception when insufficient_privilege then raise notice 'PASS: A cannot change their own role'; end;
  begin update public.profiles set handle = 'victorgomesrt-rgb' where id = auth.uid();
        raise exception 'FAIL: A can take another handle';
  exception when insufficient_privilege then raise notice 'PASS: A cannot change their handle'; end;
  begin insert into public.answers (kind, ref, body) values ('review', 'pap-000001', '{}');
        raise exception 'FAIL: A can answer the same word twice';
  exception when unique_violation then raise notice 'PASS: A cannot answer the same word twice'; end;
  begin insert into public.answers (kind, ref, person_id, body) values ('review', 'pap-000002', '00000000-0000-4000-8000-00000000000b', '{}');
        raise exception 'FAIL: A can write an answer in B''s name';
  exception when insufficient_privilege or foreign_key_violation then raise notice 'PASS: A cannot write in someone else''s name'; end;
end $$;

-- ---------------------------------------------------------------- person B
set local request.jwt.claims = '{"sub": "00000000-0000-4000-8000-00000000000b", "role": "authenticated"}';

do $$
declare v_tr_a bigint := current_setting('rls_test.tr_a')::bigint; v_own bigint; v_n int;
begin
  perform public.create_profile('Test Teacher B', false, '', 'linguist', 'tool-2026-10');

  select count(*) into v_n from public.answers;
  if v_n <> 0 then raise exception 'FAIL: B can see A''s answers (%)', v_n; end if;
  raise notice 'PASS: B cannot see A''s answers';
  select count(*) into v_n from public.translations;
  if v_n <> 0 then raise exception 'FAIL: B can see A''s sentences directly'; end if;
  select count(*) into v_n from public.profiles;
  if v_n <> 1 then raise exception 'FAIL: B can see other profiles (%)', v_n; end if;
  raise notice 'PASS: B sees only their own sentences and profile';

  if (public.queue_state() -> 'review_closed') @> '["pap-000001"]' then
    raise exception 'FAIL: pap-000001 is closed for B after one answer';
  end if;
  insert into public.answers (kind, ref, body) values ('review', 'pap-000001', '{"en": {"verdict": "correct"}}');
  raise notice 'PASS: B gives the second answer on pap-000001';

  select count(*) into v_n from public.rate_queue(20) q where q.id = v_tr_a;
  if v_n <> 1 then raise exception 'FAIL: A''s sentence is not offered to B for rating'; end if;
  raise notice 'PASS: A''s sentence is offered to B for rating, without its author';

  insert into public.ratings (translation_id, verdict) values (v_tr_a, 'good');
  raise notice 'PASS: B rates A''s sentence';
  begin insert into public.ratings (translation_id, verdict) values (v_tr_a, 'fix');
        raise exception 'FAIL: B can rate the same sentence twice';
  exception when unique_violation then raise notice 'PASS: B cannot rate the same sentence twice'; end;

  insert into public.translations (prompt_ref, text) values ('prm-000002', 'test sentence b') returning id into v_own;
  perform set_config('rls_test.tr_b', v_own::text, true);
  begin insert into public.ratings (translation_id, verdict) values (v_own, 'good');
        raise exception 'FAIL: B can rate their own sentence';
  exception when insufficient_privilege then raise notice 'PASS: B cannot rate their own sentence'; end;

  begin insert into public.decisions (kind, word_ref, outcome, value) values ('review', 'pap-000001', 'reviewed', '{}');
        raise exception 'FAIL: a contributor can decide';
  exception when insufficient_privilege then raise notice 'PASS: a contributor cannot decide'; end;

  begin perform 1 from public.decisions limit 1;
        if exists (select 1 from public.decisions) then raise exception 'FAIL: a contributor can read decisions'; end if;
        raise notice 'PASS: a contributor reads no decisions';
  exception when insufficient_privilege then raise notice 'PASS: a contributor reads no decisions'; end;
end $$;

-- ---------------------------------------------------------------- A rates B's sentence with a correction
set local request.jwt.claims = '{"sub": "00000000-0000-4000-8000-00000000000a", "role": "authenticated"}';

do $$
declare v_tr_b bigint := current_setting('rls_test.tr_b')::bigint; v_n int;
begin
  perform public.rate_sentence(v_tr_b, 'fix', 'test correction a', '[]', '');
  select count(*) into v_n from public.translations where fix_of = v_tr_b;
  if v_n <> 1 then raise exception 'FAIL: the correction was not saved with the rating'; end if;
  raise notice 'PASS: A rates B''s sentence and saves a correction in one step';
  begin perform public.rate_sentence(v_tr_b, 'fix', 'test correction a2', '[]', '');
        raise exception 'FAIL: A can rate the same sentence twice';
  exception when unique_violation then null; end;
  select count(*) into v_n from public.translations where fix_of = v_tr_b;
  if v_n <> 1 then raise exception 'FAIL: a refused rating kept its correction'; end if;
  raise notice 'PASS: a refused rating keeps no correction';
end $$;

-- ---------------------------------------------------------------- person C: third answer refused
set local request.jwt.claims = '{"sub": "00000000-0000-4000-8000-00000000000c", "role": "authenticated"}';

do $$ begin
  perform public.create_profile('Test Teacher C', true, '', 'teacher', 'tool-2026-10');
  if not ((public.queue_state() -> 'review_closed') @> '["pap-000001"]') then
    raise exception 'FAIL: pap-000001 still open for C after two answers';
  end if;
  begin insert into public.answers (kind, ref, body) values ('review', 'pap-000001', '{}');
        raise exception 'FAIL: a third answer was accepted';
  exception when raise_exception then raise notice 'PASS: a third answer on the same word is refused'; end;
end $$;

-- ---------------------------------------------------------------- A becomes a maintainer: the board's work while it has fewer than two members
reset role;
update public.profiles set role = 'maintainer', github = 'rls-test-a' where id = '00000000-0000-4000-8000-00000000000a';
set local role authenticated;
set local request.jwt.claims = '{"sub": "00000000-0000-4000-8000-00000000000a", "role": "authenticated"}';

do $$
declare v_n int;
begin
  if not (public.queue_state() ->> 'board')::boolean then raise exception 'FAIL: a maintainer cannot do the board''s work while the board is empty'; end if;
  select count(*) into v_n from public.answers where ref = 'pap-000001';
  if v_n <> 2 then raise exception 'FAIL: a maintainer does not see both answers while the board is empty (%)', v_n; end if;
  raise notice 'PASS: while the board has fewer than two members, a maintainer does its work';
end $$;

-- ---------------------------------------------------------------- C and B join the board (as a maintainer would, in the SQL Editor)
reset role;
update public.profiles set role = 'board', github = 'rls-test-c' where id = '00000000-0000-4000-8000-00000000000c';
update public.profiles set role = 'board' where id = '00000000-0000-4000-8000-00000000000b';
set local role authenticated;
set local request.jwt.claims = '{"sub": "00000000-0000-4000-8000-00000000000c", "role": "authenticated"}';

do $$
declare v_tr_a bigint := current_setting('rls_test.tr_a')::bigint; v_n int;
begin
  select count(*) into v_n from public.answers where ref = 'pap-000001';
  if v_n <> 2 then raise exception 'FAIL: the board does not see both answers (%)', v_n; end if;
  if (public.queue_state() ->> 'board_open')::int < 2 then raise exception 'FAIL: board_open does not count the open items'; end if;
  raise notice 'PASS: board member C sees both answers and the open items';

  insert into public.decisions (kind, word_ref, outcome, value) values ('review', 'pap-000001', 'reviewed', '{"en": {"value": "x", "from": "machine"}}');
  insert into public.decisions (kind, translation_id, outcome, value) values ('sentence', v_tr_a, 'reviewed', '{"text": "test sentence a"}');
  raise notice 'PASS: C decides a word and a sentence C did not take part in';

  begin update public.decisions set exported_in = 'https://example.invalid' where word_ref = 'pap-000001';
        if exists (select 1 from public.decisions where exported_in is not null) then raise exception 'FAIL: the board can mark decisions exported'; end if;
        raise notice 'PASS: only the sync job marks decisions exported';
  exception when insufficient_privilege then raise notice 'PASS: only the sync job marks decisions exported'; end;
end $$;

-- With two board members, the maintainer is back to being a contributor:
set local request.jwt.claims = '{"sub": "00000000-0000-4000-8000-00000000000a", "role": "authenticated"}';
do $$
declare v_n int;
begin
  if (public.queue_state() ->> 'board')::boolean then raise exception 'FAIL: a maintainer still does the board''s work after the board has two members'; end if;
  select count(*) into v_n from public.answers where ref = 'pap-000001';
  if v_n <> 1 then raise exception 'FAIL: a maintainer still reads other people''s answers (%)', v_n; end if;
  begin insert into public.decisions (kind, word_ref, outcome) values ('translate', 'pap-000004', 'disputed');
        raise exception 'FAIL: a maintainer can still decide';
  exception when insufficient_privilege then null; end;
  raise notice 'PASS: once the board has two members, a maintainer no longer decides';
end $$;

-- B is now on the board but answered pap-000003, and rated A's sentence:
set local request.jwt.claims = '{"sub": "00000000-0000-4000-8000-00000000000b", "role": "authenticated"}';
do $$ begin
  insert into public.answers (kind, ref, body) values ('translate', 'pap-000003', '{}');
  begin insert into public.decisions (kind, word_ref, outcome) values ('translate', 'pap-000003', 'disputed');
        raise exception 'FAIL: a board member can decide a word they answered';
  exception when insufficient_privilege then raise notice 'PASS: a board member cannot decide a word they answered'; end;
end $$;

do $$ begin raise notice 'All access-rule checks passed. Rolling back: nothing was kept.'; end $$;

rollback;
