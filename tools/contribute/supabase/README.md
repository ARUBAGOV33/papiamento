# tools/contribute/supabase/

The contribution tool's database, in the Supabase project `papiamento-contribute`, which is separate from Skirbi. The repository stays the source of truth: this database only holds work in progress (answers, sentences, ratings and board decisions) until the sync job turns decisions into a pull request.

| File | What |
|---|---|
| `001_contribute.sql` | The migration: tables, access rules (row-level security), the functions the app calls, and privileges. Paste it into the SQL Editor once. |
| `rls-test.sql` | Tries every access rule as three test people and as an anonymous visitor, then rolls everything back. |
| `email-template.html` | The sign-in email that shows the 6-digit code. |
| `check_anon_access.mjs` | Proves from outside that the public key alone reads and writes nothing. The **Contribution security check** workflow runs it. |

## What the access rules guarantee

- **Not signed in:** nothing can be read or written with the public key.
- **Email addresses** stay in Supabase's `auth.users`, which the API does not expose. No table here has an email column.
- **Blind answers:**
  - A contributor reads only their own answers, sentences and ratings.
  - The sentences offered for rating come without their authors.
  - The review board reads everything (no emails).
- **Two answers per word:** a third answer is refused, and so is a second answer from the same person. The check runs under a lock, so it holds even when two people answer at the same moment.
- **Rating:** nobody rates their own sentence, rates one twice, or rates after the board has decided.
- **Deciding:**
  - Only board members and maintainers decide.
  - They never decide an item they answered, wrote or rated.
  - Maintainers do the board's work only while the board has fewer than two members (GOVERNANCE.md). The database checks this itself: when a second board member is added, maintainers stop deciding.
- **Protected columns:** contributors cannot change their role, handle or GitHub name. Those columns aren't writable through the API, so only a maintainer can set them, in the SQL Editor.
- **Exporting:** only the sync job, with the secret key, marks decisions as exported.

## Set it up (once)

In the Supabase dashboard of `papiamento-contribute`:

1. **Run the migration.**
   - **SQL Editor** → New query → paste the whole of [`001_contribute.sql`](001_contribute.sql) → **Run**.
   - It should finish with "Success. No rows returned".
   - It runs in a transaction, so on any error nothing is created.
2. **Paste the sign-in email.**
   - **Authentication → Email Templates → "Magic link or OTP"**:
     - Subject: `Your sign-in code for Papiamento contributions`;
     - Body: everything in [`email-template.html`](email-template.html) below the comment.
   - Do the same in **"Confirm signup"**: a first-time sign-in may use that template.
3. **Check the code settings.**
   - **Authentication → Sign In / Providers → Email:** Email OTP expiration is 3600, as you set in DESIGN.md §11.
   - If the page shows an **Email OTP length**, it must be **6**: the app has six boxes.
4. **Sign in once.** Open the tool at <https://arubagov33.github.io/papiamento/> (after the site pull request is merged and deployed), sign in with your own email and finish the profile step. This creates your profile as a contributor.
5. **Make yourself a maintainer.** Back in the **SQL Editor**, run the query below, with your own email address between the quotes. The address isn't a secret, and it stays in your SQL Editor.

   ```sql
   update public.profiles
   set role = 'maintainer', github = 'victorgomesrt-rgb', handle = 'victorgomesrt-rgb'
   where id = (select id from auth.users where email = 'your-address@example.com');

   select handle, role, github from public.profiles;
   ```

   - The second query should show `victorgomesrt-rgb | maintainer | victorgomesrt-rgb`.
   - Reload the tool: the **Review board** appears.
   - As a maintainer you do the board's work while the board has fewer than two members. If you later join the board yourself, set `role = 'board'` instead: then you keep deciding after the board grows.
6. **Run the access-rule test.**
   - SQL Editor → New query → paste [`rls-test.sql`](rls-test.sql) → **Run**.
   - The **Messages** panel lists the PASS lines and ends with "All access-rule checks passed. Rolling back: nothing was kept."
   - A line starting with FAIL means a rule is broken: don't open the tool to teachers, and report the line.
   - If the very first statement fails with a permission error on `auth.users`, your project doesn't let the SQL Editor create test users. Then test with two real sign-ins in the app instead.
7. **Run the outside check.** GitHub → **Actions → Contribution security check → Run workflow**. Every line should be PASS.

## Adding a board member

When someone joins the review board (GOVERNANCE.md, "Joining the review board"), they sign in to the tool once. Then a maintainer runs this in the SQL Editor, with their handle (shown on their Account page) and their GitHub username:

```sql
update public.profiles set role = 'board', github = 'their-github-username' where handle = 'their-handle';
```

Add them to `_meta/contributors.tsv` with role `board`. The sync job does this when it first exports one of their decisions.

When the second board member is added, maintainers with `role = 'maintainer'` stop seeing the review board in the tool, as GOVERNANCE.md says.

## Removing someone

Go to **Authentication → Users → … → Delete user**. That deletes their profile, answers, sentences and ratings in this database. Anything already merged into the repository stays there, under its licence.

## Changing the database later

Add a new numbered file (`002_….sql`) and never edit `001` after it has been run. Re-run `rls-test.sql` after every change.
