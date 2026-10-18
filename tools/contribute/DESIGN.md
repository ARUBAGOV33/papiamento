# Contribution tool: design

Board card **P2-09**. Status: **decided by the maintainer on 2026-10-18** (§5). Step 1, the tables, the contributors list and the validator changes, is in [#20](https://github.com/ARUBAGOV33/papiamento/pull/20). Nothing has been deployed and no accounts were made. The clickable prototype is in this folder; see [README.md](README.md) to open it.

## 1. Summary

Aruban teachers and linguists need one simple website where they can do three things, without a GitHub account:

1. **Check translations.** Check the machine-drafted English, Dutch and Spanish for a word against the printed AB 2018 page.
2. **Translate words.** Add English, Dutch and Spanish for AB 2018 words that have no translation yet.
3. **Translate sentences.** Write short everyday English or Spanish sentences in Aruban Papiamento. This builds the parallel corpus (card P3-06).

Every item gets two independent answers. A review-board member confirms them when they agree and decides when they differ. Only then does a sync job write the result to a pull request. A board member approves that pull request on GitHub, as GOVERNANCE.md requires.

**Decisions** (the maintainer, 2026-10-18: "a yes b yes c yes d yes e reproducible")

| Decision | What was decided |
|---|---|
| (a) Licence for contributed sentences | **CC0 1.0** for sentences and prompts. Word translations stay **CC BY 4.0** like the rest of the data. Contributors are still credited by name. |
| (b) Where prompts come from | **Written for the project** (CC0), in themed batches that follow Common Voice's sentence rules. Tatoeba's **CC0 export** maybe later, and only with the maintainer's approval of the download. No FLORES. |
| (c) Hosting | **Static site on GitHub Pages + Supabase**, in a project **separate from Skirbi**. It opens pull requests through a small **GitHub App** so the gauntlet runs on them. Setup checklist: §11. |
| (d) Data model | Tables `corpus/parallel/prompts.tsv` and `pairs.tsv`, the same pair in `eval/parallel/` for a **15 % held-out split by prompt**, and `_meta/contributors.tsv` with no emails. Both convention changes accepted. Schemas in `_meta/schema/` ([#20](https://github.com/ARUBAGOV33/papiamento/pull/20)). |
| (e) Frequency order for "Translate words" | **Reproducible:** `tools/word_frequency.py` counts the repo's own shareable PDFs, blended with words from contributed sentences as they arrive. Ranks from the private corpus are **never published**. |
| Look and feel | Phone-first, one item per screen with a feedback sheet (Duolingo's pattern, calm styling), every screen grounded in a Mobbin reference. §8 lists them, with the states for loading, success and errors. |

## 2. Who uses it

| Person | Needs | Account |
|---|---|---|
| Teacher or linguist (contributor) | Short tasks on a phone or laptop, plain language, no files, credit by name | Email sign-in code. **No GitHub.** |
| Review-board member | See both answers side by side, confirm or decide, approve the resulting pull request | Email sign-in in the tool, plus a **GitHub account** (GOVERNANCE.md: `reviewed_by` must name a pull request author or approver) |
| Maintainer | Load items, run the sync job, merge pull requests | GitHub, plus admin on the database |

## 3. The three modes

### 3.1 Check translations

- **Queue:** rows with `translated_by = machine` (2,918 today). The 168 rows whose note says the machine was unsure go first.
- **Screen:**
  - the headword, its `alt`, `pos` and `tag`;
  - a **crop of the printed AB 2018 word-list page** with the entry highlighted (PDF page = printed page + 47, from `sources/cards/AB2018.md`), and a link to the whole page;
  - for each of English, Dutch and Spanish: the machine draft and the answers **Correct / Wrong / Not sure**. **Wrong** opens a box for the right translation.
- **Rules:** all three languages need an answer. "Not sure" is a valid answer, and it does not count towards agreement.
- **Crops:** they are pre-rendered by `build_sample.py`. Phones get a single-column crop, because four columns are unreadable at 375 px.

### 3.2 Translate words

- **Queue:** rows with no `en`, `nl` or `es` (13,294 today), in frequency order (see §5(e)).
- **Screen:** the same word card and crop, then three empty boxes, with a hint that follows `_meta/conventions.md`:
  - at most three senses, separated by `; `;
  - English verbs start with "to".
- **"I don't know this word"** is an answer too. It tells the board the word is hard.
- **Soft checks while typing** (they never block): more than three senses; an English verb without "to"; commas used instead of `;`.

### 3.3 Translate sentences

- **Queue:** prompts (3 to 12 words, English or Spanish). The ones with the fewest translations come first, and a teacher never sees a prompt again once they have answered it.
- **No machine draft is ever shown.** A draft would anchor the teacher and turn the result into machine text. The tool also prefills nothing in Papiamento and shows no example sentences.
- **Several valid translations:** "Save and write another way to say it" keeps the same prompt open. Other teachers' translations of that prompt stay hidden, so every answer is independent.
- **Rate sentences:** a second teacher sees someone else's sentence, with the prompt and the checker's flags, and answers **Good** or **Needs a fix**. A fix is a new sentence linked to the original (`fix_of`), and it goes through rating too. Nobody rates their own sentence.

### 3.4 Live checks while typing (sentences and fixes)

[`checker.js`](checker.js) runs entirely in the browser on the repo's own data, built into `data/checks.js`:

| Check | Source | Shown as |
|---|---|---|
| 49 machine rules, with the severity from the grammar file | `rules/rules.jsonl` (the patterns are JavaScript-compatible) | The rule's message, its id, and a **Use "…"** button when the rule has a replacement |
| Barbarismos (familia, hay, lunes …) | `lexicon/barbarismos/barbarismos.tsv` | "Not Aruban Papiamento. Write: famia", plus the reason. If the wrong form is itself an AB headword (en, mayo, todo, eigenlijk), it shows as a softer "Check this word". |
| Curaçao spellings (372 pairs) | `lexicon/variants/curacao-aruba.tsv` | "Curaçao spelling. Aruban spelling: amigo", with a button. Skipped for AB headwords, as the validator does. |
| Accent marks | rule `RULE_ORT_ACCENT_001` and `_meta/allowlists/accented-loans.txt` | The unaccented form is offered **only when the AB list has it** |
| Words not in the AB 2018 list | `lexicon/words/` (16,168 forms; the `-nan` plural is accepted) | A dotted underline only. It can be switched off. Names are fine. |

- **Nothing blocks saving.** The checks can be wrong (the bug hunt found 4 false alarms in 33,481 sentences).
- When a teacher keeps a flagged word, the tool stores it in `flags_kept`. The board sees it, and the project gets a running measure of checker precision on new text.
- `test_checker.mjs` runs the checker against every rule test, every barbarismo and every Curaçao pair: 808 checks, all passing.

## 4. Quality workflow (all modes)

```
contributor A ─┐                          agree ──► board member confirms ─┐
               ├─► 2 independent answers ─┤                                ├─► sync job ─► pull request ─► board member approves on GitHub ─► merge
contributor B ─┘                          differ ─► board member decides ──┘
```

### Agreement rules

| Mode | Two answers agree when | Otherwise |
|---|---|---|
| Check translations (per language) | Both say Correct; or both say Wrong with the same fix. Senses are compared as sets, ignoring case and spacing. | The board picks the draft, one of the fixes, or writes its own. "Not sure" answers leave the language at "not enough answers". |
| Translate words (per language) | Both give the same set of senses, or both leave it empty | The board picks or writes |
| Sentences (per sentence) | The author and at least one other teacher rate it Good | Any "Needs a fix": the board picks the original, a fix, or writes its own |

### Rules the tool enforces

- An item stops collecting answers after two.
- A board member can't decide on an item they answered, wrote or rated.
- The board can also choose **Mark as disputed**. The row then goes to the pull request as `disputed`, with the decision id in `notes`, following GOVERNANCE.md "Disputes".

### How a decision becomes repo data

This matches the existing conventions.

- **Word confirmed as drafted:**
  - `translated_by` stays `machine`;
  - `status` becomes `reviewed`;
  - `reviewed_by` is the board member's GitHub name.
- **Word corrected or newly translated:**
  - `translated_by` lists the contributors' handles: everyone who gave the chosen value is credited;
  - `machine` stays for any language that kept the draft;
  - `notes` says which language changed.
- **Sentence:** a row in the new `pairs.tsv` (§5(d)), with `translated_by` (the author), `checked_by` (the raters) and `reviewed_by` (the board).

### Credit and consent

At first sign-in a contributor gives:

- the name to credit (or chooses not to be named);
- their role;
- consent to two licences in plain words: word translations under CC BY 4.0, and sentences under CC0, if (a) is accepted.

Credit then appears in four places:

- the handle in the data rows;
- `_meta/contributors.tsv`;
- the release notes;
- the Zenodo record's contributors.

Email addresses are used only for sign-in and are never committed.

The prototype implements everything in this section, on one device. "Switch person" simulates several teachers and a board member, and the Export screen shows the exact TSV rows a pull request would contain.

## 5. Decisions for the maintainer

### (a) Licence for contributed sentences

| | CC0 1.0 | CC BY 4.0 |
|---|---|---|
| Common Voice | **Required.** Sentences must be CC0 or public domain ([playbook](https://common-voice.github.io/community-playbook/sub_pages/text.html)). `pap-AW` "Papiamento (Aruba)" is registered on Common Voice but not yet open for contribution ([API](https://commonvoice.mozilla.org/api/v1/languages), read 2026-10-16). | Can't go to Common Voice |
| TTS and recordings | Free to record and redistribute | Attribution has to travel with every derived corpus |
| Matches the rest of the repo | No. LICENSE-DATA needs one exception paragraph for `corpus/parallel/` and `eval/parallel/`. | Yes |
| Credit | Not a legal condition, but the project still credits by name (handles in rows, contributors list, release notes) | A legal condition |
| Can change later | CC0 text can always be included in a CC BY release | Moving to CC0 later needs every contributor's consent again |

**Recommendation: CC0 1.0 for sentences and prompts, decided before collection starts.**

**Decided on 2026-10-18: CC0 1.0.** The exception is in LICENSE-DATA ([#20](https://github.com/ARUBAGOV33/papiamento/pull/20)).

- Word translations stay CC BY 4.0.
- The consent screen must say plainly that CC0 means anyone may use the sentence without naming the writer, and that the project will name them anyway.

### (b) Where the English and Spanish prompts come from

| Option | Licence | Fit | Notes |
|---|---|---|---|
| **Written for the project** | CC0 (ours) | Everyday Aruban life: home, school, shop, health, weather, government counter, bus, beach. Length and wording are under our control. | Maintainers draft batches of about 300. EN/ES may be machine-drafted (marked `machine`; they aren't Papiamento) and a maintainer checks them. Follow Common Voice's rules: 1–14 words, no digits, no abbreviations ([validator](https://raw.githubusercontent.com/common-voice/sentence-collector/main/server/lib/validation/languages/en.js)). |
| Tatoeba, **CC0 export only** | CC0 1.0 | Short everyday sentences in both languages | A separate weekly "Sentences (CC0)" export exists ([downloads](https://tatoeba.org/en/downloads)). **Needs your OK to download.** |
| Tatoeba, main export | CC BY 2.0 FR ([terms](https://tatoeba.org/en/terms_of_use)) | Large | Tatoeba treats a translation as a derivative work, and translations of CC BY sentences cannot be CC0 ([wiki](https://en.wiki.tatoeba.org/articles/show/cc0-contributions)). That would block (a). **Avoid.** |
| FLORES-200 / FLORES+ | CC BY-SA 4.0 | Wikipedia-style, not everyday | It is an evaluation benchmark; the FLORES+ card says it "should not be used as training data" ([card](https://huggingface.co/datasets/openlanguagedata/flores_plus)), and it already lists `pap`. Translating it here would contaminate it. **Avoid.** |

**Recommendation: write the prompts for the project.**

**Decided on 2026-10-18: prompts written for the project.** Tatoeba's CC0 export may come later, only after the maintainer approves the download.

- Twelve sample prompts are in [`prompts.tsv`](prompts.tsv), marked `written-for-prototype`. Some deliberately tempt a barbarismo (Spanish *mucho*, *en*, *de la*, *domingo*) to show the checks.
- Add Tatoeba's CC0 export later, if a larger pool is needed and you approve the download.

### (c) Hosting

| | **A. Static site + Supabase** | B. Static site + GitHub App as the store | C. Google Sheet / Forms + sync bot | D. Hosted Weblate |
|---|---|---|---|---|
| **Cost** | $0 on the free plan: 500 MB database, 50,000 monthly users, 2 free projects per owner ([pricing](https://supabase.com/pricing)). Free projects **pause after 1 week without activity** ([docs](https://supabase.com/docs/guides/platform/going-into-prod)). Pro from $25/month. GitHub Pages is free for public repos. | $0 (static site + a small serverless function on a free tier) | $0. Sheets API quota is 300 requests/minute; Google says charges for going over are planned later in 2026 ([limits](https://developers.google.com/workspace/sheets/api/limits)). | Gratis "Libre" plan for public libre projects; whether a CC data repo qualifies is **unconfirmed**. Otherwise about €39–47/month ([hosting](https://weblate.org/en/hosting/)). |
| **Privacy** | Your choice of region: EU (Frankfurt, Paris…) or Americas (N. Virginia, São Paulo); no Caribbean region ([regions](https://supabase.com/docs/guides/platform/regions)). DPA published. Row-level security keeps answers blind and emails private. | Anything in a public repo is public: names, and answers the second teacher could read. That breaks independence unless a private repo is the store. | Google holds the data. Anyone with edit access to the sheet can change answers. | EU-hosted ([hosting](https://weblate.org/en/hosting/)) |
| **Sign-in for teachers** | Email code or magic link, no password ([docs](https://supabase.com/docs/guides/auth/auth-email-passwordless)). The built-in mailer only reaches project members, so **custom SMTP** is needed ([docs](https://supabase.com/docs/guides/auth/auth-smtp)). | Needs its own login (email codes) or none (spam) | None (weak identity, so "two different people" can't be enforced) or a Google account | A Weblate account |
| **Decisions → pull request** | A weekly GitHub Action reads board decisions, writes TSV rows (`tools/apply_contributions.py`, to be written), runs `build_pages.py` and the gauntlet, and opens a pull request. | The app opens the pull request directly | An Action reads the sheet with a service-account key and opens the pull request | Weblate's GitHub app pushes a branch and opens pull requests ([docs](https://docs.weblate.org/en/latest/admin/code-hosting.html)). Our 14-column `words.tsv` isn't a Weblate format, so a converter is needed both ways. |
| **Fits the three modes?** | All three: crops, blind double answers, several translations per prompt, live checks, board queue | Yes, but blindness and privacy are hard | Mode 2 only. A form can't run the 49 rules and the lexicon checks, or keep answers blind. | Modes 1–2 fit well: suggestion voting with 2 votes, an Approved state, screenshots per string, machine translation can be switched off ([workflows](https://docs.weblate.org/en/latest/workflows.html)). Mode 3 does not fit: one translation per string, no repo checks (custom checks need self-hosting). |
| **What the ARUBAGOV33 admin sets up** | 1. A Supabase project, owned by the project's email, separate from Skirbi. Note that the 2 free projects are counted across every organisation you administer. 2. Run [`proposal/supabase-schema.sql`](proposal/supabase-schema.sql). 3. Email sign-in with SMTP (an email-sending account). 4. GitHub Pages. 5. Repository secrets for the sync job. 6. A small GitHub App installed on the repo to open pull requests. | Create and install a GitHub App; host the function and its private key (another account); a private store repo | A Google account and Cloud project, a service account, the sheet shared with it, and a key as a repo secret | A Weblate account, the Libre-plan application, Weblate's GitHub app installed, components configured, crops uploaded |

**Recommendation: A, Supabase plus a static site on GitHub Pages.**

**Decided on 2026-10-18: option A**, with a Supabase project separate from Skirbi. The maintainer sets up the accounts himself; the checklist is in §11.

- It is the only option that does all three modes, keeps answers blind and keeps emails private.
- You already run Supabase for Skirbi. Use a separate project so dataset contributors and Skirbi users never share a database.
- The prototype's front end carries over almost unchanged: swap `localStorage` for Supabase calls.

**Two traps to plan for:**

- **The gauntlet would not run on bot pull requests.** Pull requests opened with Actions' built-in `GITHUB_TOKEN` don't trigger other workflows ([docs](https://docs.github.com/en/actions/using-workflows/triggering-a-workflow)). So the sync job should open them with a **GitHub App** token.
  - The alternative is the repo setting "Allow GitHub Actions to create and approve pull requests", which only an admin can change, plus manual re-runs.
  - The job must also run `tools/build_pages.py`. Otherwise the stale progress pages fail the unit tests (bug hunt M6).
- **Free-plan pausing.** Whether a weekly sync query counts as activity is unconfirmed. If pausing bites, move to Pro ($25/month).

**If you want something running this month:** Weblate's Libre plan can cover modes 1–2 while mode 3 waits for option A. But that means two tools and a converter, so I'd rather build A once.

### (d) Data model

**Decided on 2026-10-18: this model, with both convention changes below.** The schemas, empty tables, `_meta/contributors.tsv` and validator checks are in [#20](https://github.com/ARUBAGOV33/papiamento/pull/20).

| File | Rows | Key columns |
|---|---|---|
| `corpus/parallel/prompts.tsv` (`_meta/schema/parallel-prompts.schema.json`) | English/Spanish prompts | `id` (`prm-000001`), `lang`, `text`, `topic`, `origin` (`written` / `tatoeba-cc0`), `origin_ref`, `author`, `batch`, `licence`, `status`, `reviewed_by`, `notes` |
| `corpus/parallel/pairs.tsv` (`_meta/schema/parallel-pairs.schema.json`) | Papiamento sentences, several per prompt | `id` (`par-000001`), `prompt_id`, `pap` (gets the Aruban spelling checks), `translated_by`, `checked_by`, `fix_of`, `flags_kept`, `batch`, `licence`, `status`, `reviewed_by`, `notes` |
| `eval/parallel/prompts.tsv`, `eval/parallel/pairs.tsv` | The held-out split, same schemas | — |
| `_meta/contributors.tsv` (`_meta/schema/contributors.schema.json`) | Everyone credited | `handle`, `credit_name`, `github`, `role`, `licence_words`, `licence_sentences`, `consent`, `joined`, `notes`. **No email.** |

**Held-out share:**

- 15 % of **prompts**, chosen by a deterministic hash of the prompt id (`sha256(id) mod 100 < 15`) when the prompt is created, before anyone translates it.
- Every translation of a held-out prompt goes to `eval/parallel/`. Alternative translations of the same sentence therefore never straddle the split.
- Held-out sentences are **never sent to Common Voice**: its text ends up in training corpora.
- `eval/README.md`'s canary and "never train on this" already cover the folder.

**Words need no new columns.** Contributor handles fit the existing `translated_by` / `reviewed_by` pattern. The validator checks two things:

- every handle is in `_meta/contributors.tsv` (`contributor_refs`, [#20](https://github.com/ARUBAGOV33/papiamento/pull/20));
- `reviewed_by` never holds `machine` (since #19).

It also checks that a pair's prompt is in the same folder (`folder_refs`), so a training pair can never point at a held-out prompt.

**Two convention changes, accepted on 2026-10-18** and written into `_meta/conventions.md` in #20:

1. Contributed sentences have no printed source page. The parallel tables have no `source`/`page` columns; `translated_by` (or `author`) plus a `batch` column is their provenance.
2. `reviewed_by` stays GitHub usernames, as GOVERNANCE.md requires. Board members need GitHub accounts; contributors don't.

The tool's own working database is sketched in [`proposal/supabase-schema.sql`](proposal/supabase-schema.sql). Its row-level security policies are what enforce:

- blind answers;
- no self-rating;
- no deciding on your own item.

### (e) Where frequency ranks come from

The 2,918 machine drafts were chosen by frequency in a private Aruban text corpus (commit `cac2e2e`). That corpus can't be published, so the order it produces can't be reproduced by anyone else.

For the 13,141 single-word rows still without a translation, I measured the publishable alternative in this repo. I counted the PDFs already in `sources/pdf/`: the AB 2018 law and annex (without the word list), MOR2010, ORT2009, PRE2016 and SIN2015, 72,000 tokens in all.

- **1,362** of the untranslated words appear at all.
- Only **18** appear five times or more.
- Several top hits are Dutch words the books quote (*van*, *het*).

The signal is weak.

| Option | Publishable | Signal |
|---|---|---|
| 1. Publish **only the rank number** from the private corpus, never its text | Your call: the ranks are statistics, but nobody can re-derive them | Strong |
| 2. Count the repo's PDFs, plus the public-domain PEN2019 and HIM2019 and more laws once added (`tools/word_frequency.py`, reproducible) | Yes | Weak; formal register |
| 3. Count the words teachers use in the contributed sentences (mode 3) | Yes (CC0) | Everyday register; grows over time |
| 4. No frequency: base words before their derived forms (-ando, -cion), by AB order | Yes | Structural only |

**Recommendation: 2 now, blended with 3 as sentences come in. Use 1 only if you are comfortable publishing a rank derived from text that can't be shared.**

**Decided on 2026-10-18: the reproducible option (2 blended with 3).** Ranks from the private corpus are never published. `tools/word_frequency.py` ([#20](https://github.com/ARUBAGOV33/papiamento/pull/20)) does it:

- **What it counts:** the shareable PDFs in `sources/pdf/`.
- **What it leaves out:**
  - VOC2009 and the AB 2018 word list, because they print every headword once;
  - AB 2018's orthography annex, because it is the text of ORT2009, which is already counted.
- **Scoring:** the PDF rate is averaged with the rate in `corpus/parallel/pairs.tsv` once there are sentences.
- **First run:** 1,539 untranslated headwords occur at least once.

The prototype's "Translate words" order uses the same PDFs.

## 6. Privacy, safety and copyright

- **Personal data:**
  - stored: name, email (sign-in only), role, and the answers;
  - published: the credit name and handle only;
  - the consent text is versioned and its version recorded.
  - A contributor can ask to be un-named. Contributions already released under CC0 or CC BY can't be recalled, and the consent text says so.
  - Check with the Ministry which data-protection rules apply to a government-related project.
- **Abuse:**
  - email sign-in plus per-account limits;
  - maintainers can disable an account;
  - nothing is published without a board decision and a reviewed pull request.
- **Copyright:**
  - Prompts are ours (CC0) or CC0 from Tatoeba.
  - The consent text asks teachers to write their own sentences, not to copy from books or websites (CONTRIBUTING.md rule 4).
  - Page crops come from the AB 2018 law, which is public domain.
- **Machine content:**
  - The tool never shows machine Papiamento.
  - Machine EN/NL/ES drafts are shown only in "Check translations", labelled "Machine draft", and stay `machine` in `translated_by` unless a person changes them.

## 7. Interface text

- English is the default.
- Papiamento is a **machine draft for teacher review**:
  - the language switch says "Papiamento (draft)";
  - a banner on every screen says a teacher must check the text;
  - every row in [`ui-strings.tsv`](ui-strings.tsv) has `pap_status = draft`.
- `build_sample.py` checks the Papiamento column and fails the build if:
  - any word in it is not an AB 2018 headword (allowed exceptions are listed, such as *browser*, *JSON* and the past marker *a*);
  - any rule, barbarismo or Curaçao form fires on it;
  - a vowel-final verb is followed by a bare pronoun `e`. It must be contracted (`uz'e`, AB 2018 annex §10.1 point 1, p. 33) or the pronoun dropped (`controla`). The maintainer corrected three such cases in the first draft, and the repo's rules don't catch the full form.
- That checks spelling only. **Grammar and wording need a teacher.**

## 8. UX and visual design

The interaction model is Duolingo's lesson pattern without its cartoon look:

- one item per screen;
- a close button and a thin progress bar at the top;
- a full-width primary button at the bottom;
- a feedback sheet that slides up after each answer.

The audience is teachers, linguists and a ministry, so the look is calm: high contrast, few colours, no mascots, no confetti. The app is phone-first, because many teachers and the maintainer work from a phone. From 900 px a sidebar replaces the tab bar, word tasks split into two columns, and the board becomes a list with a detail pane.

### References (Mobbin)

Each screen is grounded in a well-designed app. References marked † were passed on by the coordinating session; the others were examined in this session.

| Screen | What we took | References |
|---|---|---|
| Task flow (all modes) | Close, progress bar, one item, primary button, bottom feedback sheet with Continue | Duolingo [completing a lesson](https://mobbin.com/flows/40841c36-1296-4b96-95a1-1e1c60c64b83)†; Duolingo [incorrect answer sheet](https://mobbin.com/screens/999d36c0-e831-4345-94e1-896367f1d7fe) |
| Live spelling check | The sheet shows the wrong form struck through next to the right one (*amigu → amigo*) and offers "Use the suggestions" or "Keep as written" | Duolingo [complete the translation](https://mobbin.com/screens/dd4176cc-8b60-49d2-bfa6-7f5f659dd262) ("Pay attention to the accents") |
| Translate (phone) | Soft source card, a big text box, the hint under the input, a full-width check button | Babbel [inline input](https://mobbin.com/screens/fd9a34b9-ceb8-475d-b9f6-842312902258)†; Speak [source card and Check](https://mobbin.com/screens/d7165128-090f-4ebf-9e00-2edf29c9e6c5)† |
| Translate (laptop) | Source and page crop on the left, "Write in …" fields on the right | Etsy [languages and translations](https://mobbin.com/screens/3a3422a5-b3ce-4ace-8cc3-f8dc4ef57336); Ditto [string list with status](https://mobbin.com/screens/9000cc65-c691-443f-a730-9e1dd5adefec) |
| Sign-in | Email, then "Check your email" with six code boxes, a step counter, a fallback to change the address, no password | Shop [verify your email](https://mobbin.com/screens/f42ad150-2336-45f5-b7bd-d66f7c9f0cd5); Woolworths [step 2 of 2](https://mobbin.com/screens/c8b61ab0-b2fe-4abf-991d-fe2efe2c29c3); Taco Bell [one-time code](https://mobbin.com/screens/0f74bb48-0a88-408f-8647-ff00dfe6e6b5); Ro [magic link sent](https://mobbin.com/screens/a59b4355-5200-4e30-9f3f-c69c183f731d)†; Mesh [check your email](https://mobbin.com/screens/5d96cd3e-af3f-4eb5-b0a7-d19cc4a7989b)† |
| Onboarding | One topic per step, role as icon tiles, large inputs, the primary button pinned at the bottom, licence consent as two plain cards | Airtasker [onboarding](https://mobbin.com/flows/93cebe6f-786f-412f-99b1-ca941bd2119d); Replika [onboarding](https://mobbin.com/flows/19470dcc-dbd6-48ae-a945-f708e3a1b3d2); LinkedIn [volunteer preferences](https://mobbin.com/flows/c8d64c4f-9cc7-40a6-8844-ed05486938c6) |
| Home | A calm daily-goal card (ring, this week, days in a row) above a list of ways to help, each row with a count and a chevron | Coursera [daily goals](https://mobbin.com/screens/40087b17-c119-400c-8c7a-d84d50969b19); Quizlet [progress rows](https://mobbin.com/screens/439e68be-eb63-4fb8-985a-ab27b24e3ff2); Headway [streak and weekly stats](https://mobbin.com/screens/e069ee13-99bd-49bd-8d19-4cf8efbf466b). Left out: full-screen streak celebrations such as Babbel's [streak calendar](https://mobbin.com/screens/9a4520f9-45cc-4473-bacb-410dabe093c8), too game-like for this audience. |
| End of a queue | Check icon, one sentence, three stat tiles (answered today, waiting for a second answer, confirmed by the board), Back to home | Mimo [lesson complete](https://mobbin.com/screens/b96677c5-4f73-40ff-8dee-2bda19aed27e); Withings [all missions done](https://mobbin.com/screens/c52f7e0f-41e5-4e12-96d9-84b1b420f7f9) |
| Review board | "To decide / Decided" tabs, a list with status badges, a detail pane, Dispute and Save in a sticky footer | Reddit [mod queue](https://mobbin.com/screens/9e81dbcf-db79-45ef-8347-08e81e1b5b77); Airwallex [pending your approval](https://mobbin.com/screens/89c96631-be20-4176-be78-d24175e013ed); Calendly [list and detail](https://mobbin.com/screens/23888dde-e7ac-41d6-834c-fd316809d84a) |
| Offline | An inline banner that says what still works, not a dead end | Alta [network offline](https://mobbin.com/screens/2b00c4b9-d2a6-4a6a-9d95-2aba49348be1); Qantas [you're not connected](https://mobbin.com/screens/18f77caf-19d5-4199-98b4-a36f34096d23) |
| Credits | "Your contributions" as a list of counts; the board and contributors listed by name, alphabetical, not ranked | Google Maps [number of contributions](https://mobbin.com/screens/550534f8-b745-4442-98f1-29caf9fa7da2); X [moderators and members](https://mobbin.com/screens/278f2d6c-fd9c-4995-864c-77f4eea11450). Left out: ranked leaderboards such as Believe's [ranked list](https://mobbin.com/screens/13cba083-8369-4098-8800-253c652932e6). Volunteers should not compete. |

### Visual system

- **Colour:**
  - Aruba blue `#1663b8` for primary actions and progress;
  - navy `#0b3c78` for the goal card and language codes;
  - yellow `#f9d616` as an accent only (the goal ring, the prototype banner, the draft chip), never for text on white.
- **States:**
  - green for "correct" and success;
  - red for "wrong" and errors;
  - amber for warnings and checks.
- **Dark mode** follows the system setting.
- **Type:** the system font on a fixed scale (12.5, 14, 16, 18, 20, 24, 28, 34).
  - Weights are 400, 600 and 700, with tighter letter-spacing on large headings and tabular numbers for counts.
  - Inputs use 16 px text, so iPhones don't zoom in.
- **Sizes:**
  - touch targets are 48 px on phones and 44 px with a mouse;
  - buttons have 12 px corners, 16 px semibold text and a 20 px horizontal padding;
  - cards have 18 px corners.
- **Imagery:** the welcome screen uses a text-free slice of the README banner. That banner is Higgsfield artwork made for the repo (`.github/assets/README.md`), so the app matches the repository, and no new image was generated. Page crops are the only other images. They come from the public-domain AB 2018 law.

### Motion

Motion follows Emil Kowalski's rules:

- **Durations:** UI motion stays under about 300 ms, except the feedback sheet's 340 ms entrance.
- **Easing:** custom curves only: `cubic-bezier(0.23, 1, 0.32, 1)` for entering, and the iOS drawer curve for the sheet.
- **Exits** are faster than entrances: the sheet leaves in 200 ms.
- **Presses:** buttons and choice tiles scale to 0.97–0.98.
- **Hover** effects apply only on devices with a fine pointer.
- **What animates:** only `transform` and `opacity`.
- **Frequent actions don't animate:** moving to the next word, typing, switching tabs.
- **Rare moments may:** the end-of-queue check icon pops in.
- **Reduce motion:** with the system setting on, movement is replaced by fades and the shimmer stops.

### States

| State | How it shows |
|---|---|
| Loading | The pressed button keeps its width, shows a fast spinner and "Saving… / Sending… / Checking…", and is disabled until the answer is accepted, so nothing is sent twice. Page crops show a shimmer placeholder until they load. |
| Success | The bottom feedback sheet ("Saved. Thank you!" plus what happens next). Small confirmations (download, import, undo, back online) use a toast that pauses while the tab is hidden. |
| Field errors | A red border, an icon and a message under the field, read out by screen readers. The field takes focus and the error clears as soon as the person types. Primary buttons stay disabled until a task is complete, with a one-line hint saying what is missing. |
| Save failed | A red sheet: "Couldn't save. Your answer is still here." with Try again and Cancel. Nothing is stored until the save succeeds. |
| Offline | A banner on every screen. In the real tool, answers queue on the device and are sent when the connection returns. |
| Storage blocked | A banner asks the person to export before closing the page (private mode, full disk). |
| Image failed | A plain note with a link to the whole PDF page. |
| Empty | An icon, one sentence and one action, for example "No sentences to rate yet". |
| Data missing | A full-page message saying how to rebuild the sample. |

The prototype has no server. A **"Prototype: connection"** switch on the Account page (Normal / Slow / Failing) slows down or fails every save, so the loading and error states can be tried.

## 9. What the prototype does and doesn't do

**Does:**

- **All three modes**, plus rating and the board screen, the agreement rules and the conflict-of-interest rule.
- **Live checks** while typing.
- **Consent and credit**: the consent screen, contributor handles, credit for everyone who gave the chosen value.
- **Export and import**: JSON export and import, and a preview of the TSV rows a pull request would contain.
- **Language and layout**: English and a draft Papiamento interface, phone and laptop layouts, dark mode.
- **Onboarding**: four steps, with a mock email-code sign-in that sends nothing and stores no address.
- **States**: every state in §8, with a switch to simulate a slow or failing connection.

**Doesn't:**

- no server, real sign-in or email: "Switch person" (Account) simulates several people on one device;
- only 8 + 8 sample words and 12 sample prompts;
- the pull-request preview is illustrative (`par-NEW` ids);
- no Common Voice export.

## 10. Next steps

1. **Schema PR: [#20](https://github.com/ARUBAGOV33/papiamento/pull/20).**
   - The new tables and `_meta/contributors.tsv`.
   - The conventions and LICENSE-DATA as decided in (a) and (d).
   - The validator's handle and folder checks.
   - `tools/word_frequency.py`.
   - It is language governance, so it needs the maintainer's approval.
2. **Prompts, batch 1.**
   - About 300 prompts written for the project with the 15 % held out, machine-drafted and marked `author = machine`.
   - It opens as a pull request after #20 merges, because it needs those schemas.
3. **Tool v1 (option A).**
   - First the maintainer sets up the accounts (§11).
   - Then: Supabase schema and email sign-in, GitHub Pages, the sync job and `tools/apply_contributions.py`, and the GitHub App for pull requests.
   - Pilot with 3–5 teachers and the first board members.
4. **Common Voice (P2-04).** Export reviewed, CC0, non-held-out sentences that meet its rules.

## 11. Setup checklist for the ARUBAGOV33 account (option A)

The maintainer does these steps himself: Claude never creates accounts and never sees passwords, keys or other secrets. Menu paths come from each provider's documentation as read on 2026-10-18. Labels marked **(check)** could not be confirmed there and may be worded slightly differently on screen.

Do them in this order. Each step names what to write down. Where a step says "public", the value goes into the website. Where it says "secret", the value goes only into a GitHub secret (D2), never into a file, a chat or an email.

### A. Supabase project, separate from Skirbi

1. Go to <https://supabase.com/dashboard> and sign in with the **project's own email address**, not the account Skirbi uses. Supabase counts its two free projects across every organisation an account administers, so a separate account keeps Skirbi's free slot safe and the two databases apart.
2. Create an organisation for the project, then a **New project** **(check: the organisation picker at the top left)**:
   - **Name:** `papiamento-contribute`.
   - **Database password:** generated, and kept in a password manager.
   - **Region:** East US (North Virginia), the general region closest to Aruba.
   - **Plan:** Free.
3. **Authentication → Sign In / Providers → Email:**
   - Leave Email enabled. Email one-time codes are on by default.
   - Set **Email OTP expiration** to 3600 seconds.
   - Leave "Allow new users to sign up" on, because teachers sign up with their first code.
4. **Authentication → Email Templates → "Magic link or OTP":** leave it for now. The tool v1 pull request will give the text to paste, which shows the 6-digit code with `{{ .Token }}`.
5. **Authentication → URL Configuration:** Site URL = `https://arubagov33.github.io/papiamento/`, and add the same address under Redirect URLs.
6. **Settings → API Keys** (or the project's **Connect** dialog), write down:
   - the **Project URL** (public);
   - the **publishable key**, `sb_publishable_…` (public);
   - the **secret key**, `sb_secret_…` (**secret**).
7. Later, when the tool v1 pull request is ready: **SQL Editor** (left sidebar) → New query → paste the migration file from that pull request → Run. The current [`proposal/supabase-schema.sql`](proposal/supabase-schema.sql) is a sketch; don't run it.

### B. Email sending account (Brevo, free)

Supabase's built-in mailer only reaches the project's own team, so teachers' codes need an SMTP account.

1. Create a Brevo account at <https://www.brevo.com> with the project's email address.
2. **Settings → Senders, Domains, IPs → Senders → Add a sender:**
   - **From name:** `Papiamento contributions`;
   - **From email:** the project address.
   - Confirm it with the 6-digit code Brevo sends there.
   - Without a domain of our own, Brevo may send from an `@brevosend.com` address and address-book domains such as gmail.com can't be authenticated. If the project gets a domain later, authenticate it under **Domains** on the same page.
3. **Settings → SMTP & API → SMTP tab**, write down:
   - the server: `smtp-relay.brevo.com`, port `587`;
   - the **login**;
   - a new **SMTP key** (**secret**; an SMTP key, not an API key) **(check: button label)**.
   - The free plan sends about 300 emails a day **(check: on Brevo's pricing page)**.
4. Back in Supabase: **Authentication → SMTP Settings** → enable custom SMTP:
   - host, port, username (the login) and password (the SMTP key) from step 3;
   - sender email and sender name from step 2.
5. Supabase: **Authentication → Rate Limits**. Emails per hour start at 30 with custom SMTP. Raise it to about 100 before a workshop where many teachers sign up at once.

(Resend is the alternative, with 100 emails a day free, but it needs our own domain.)

### C. GitHub App that opens the sync pull requests

A pull request opened with Actions' own token does not trigger the gauntlet. One opened by a GitHub App does.

1. Signed in to GitHub as **ARUBAGOV33**: profile picture → **Settings → Developer settings → GitHub Apps → New GitHub App**.
2. Fill in the form:
   - **GitHub App name:** `papiamento-sync` (any unique name under 34 characters);
   - **Homepage URL:** `https://github.com/ARUBAGOV33/papiamento`;
   - **Webhook:** untick **Active**.
3. **Repository permissions**; leave everything else at No access:
   - **Contents:** Read and write;
   - **Pull requests:** Read and write;
   - **Metadata:** Read-only.
4. **Where can this GitHub App be installed?** Only on this account → **Create GitHub App**.
5. On the app's page, write down the **Client ID** (public). Under **Private keys**, generate a private key; it downloads a `.pem` file (**secret**).
6. **Install App** → **Install** next to ARUBAGOV33 → **Only select repositories** → `ARUBAGOV33/papiamento` → **Install**.

### D. Repository settings (ARUBAGOV33/papiamento)

1. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
2. **Settings → Secrets and variables → Actions:**
   - **Variables** tab → New repository variable, three times **(check: tab name)**:
     - `SYNC_APP_CLIENT_ID` = the app's Client ID (C5);
     - `SUPABASE_URL` = the Project URL (A6);
     - `SUPABASE_PUBLISHABLE_KEY` = the publishable key (A6).
   - **Secrets** tab → **New repository secret**, twice:
     - `SYNC_APP_PRIVATE_KEY` = the whole contents of the `.pem` file (C5);
     - `SUPABASE_SECRET_KEY` = the secret key (A6).
   - Then delete the downloaded `.pem` file.
3. **Settings → Actions → General → Workflow permissions:** leave "Allow GitHub Actions to create and approve pull requests" **off**. The GitHub App opens the pull requests, and nothing should approve them automatically.
4. Branch protection stays as it is. Every sync pull request waits for a maintainer's or board member's review, and the person named in `reviewed_by` approves it.

### E. When it's done

Tell Claude which **names** you created: the variables and secrets in D2, plus the app name. Never send the values. The tool v1 workflow reads them by those names.
