# Contribution tool: design proposal

Board card **P2-09**. Status: **proposal for the maintainer**. Nothing has been deployed, no accounts were made, and no data in the repository was changed. The clickable prototype is in this folder; see [README.md](README.md) to open it.

## 1. Summary

Aruban teachers and linguists need one simple website where they can do three things, without a GitHub account:

1. **Check translations.** Check the machine-drafted English, Dutch and Spanish for a word against the printed AB 2018 page.
2. **Translate words.** Add English, Dutch and Spanish for AB 2018 words that have no translation yet.
3. **Translate sentences.** Write short everyday English or Spanish sentences in Aruban Papiamento. This builds the parallel corpus (card P3-06).

Every item gets two independent answers. A review-board member confirms them when they agree and decides when they differ. Only then does a sync job write the result to a pull request. A board member approves that pull request on GitHub, as GOVERNANCE.md requires.

**Recommendations at a glance**

| Decision | Recommendation |
|---|---|
| (a) Licence for contributed sentences | **CC0 1.0** for sentences and prompts. Word translations stay **CC BY 4.0** like the rest of the data. Contributors are still credited by name. |
| (b) Where prompts come from | **Written for the project** (CC0), in themed batches that follow Common Voice's sentence rules. Later, optionally, Tatoeba's **CC0 export only** (needs your OK to download). No FLORES. |
| (c) Hosting | **Static site on GitHub Pages + Supabase** (a new project, separate from Skirbi). It opens pull requests through a small **GitHub App** so the gauntlet runs on them. |
| (d) Data model | New tables `corpus/parallel/prompts.tsv` and `pairs.tsv`, the same pair in `eval/parallel/` for a **15 % held-out split by prompt**, and `_meta/contributors.tsv`. Draft schemas are in [`proposal/`](proposal/). |
| (e) Frequency order for "Translate words" | **Your decision.** See §5(e). The repo's own PDFs give a weak signal; the private corpus is strong but can't be published. |

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

Draft schemas in the style of `_meta/schema/` are in [`proposal/`](proposal/). They are not wired into the validator, and `_meta/schema/` is untouched.

| File | Rows | Key columns |
|---|---|---|
| `corpus/parallel/prompts.tsv` ([schema](proposal/parallel-prompts.schema.json)) | English/Spanish prompts | `id` (`prm-000001`), `lang`, `text`, `topic`, `origin` (`written` / `tatoeba-cc0`), `origin_ref`, `author`, `licence`, `status`, `reviewed_by`, `notes` |
| `corpus/parallel/pairs.tsv` ([schema](proposal/parallel-pairs.schema.json)) | Papiamento sentences, several per prompt | `id` (`par-000001`), `prompt_id`, `pap` (gets the Aruban spelling checks), `translated_by`, `checked_by`, `fix_of`, `flags_kept`, `licence`, `status`, `reviewed_by`, `notes` |
| `eval/parallel/prompts.tsv`, `eval/parallel/pairs.tsv` | The held-out split, same schemas | — |
| `_meta/contributors.tsv` ([schema](proposal/contributors.schema.json)) | Everyone credited | `handle`, `credit_name`, `github`, `role`, `licence_words`, `licence_sentences`, `consent_version`, `joined`, `notes`. **No email.** |

**Held-out share:**

- 15 % of **prompts**, chosen by a deterministic hash of the prompt id (`sha256(id) mod 100 < 15`) when the prompt is created, before anyone translates it.
- Every translation of a held-out prompt goes to `eval/parallel/`. Alternative translations of the same sentence therefore never straddle the split.
- Held-out sentences are **never sent to Common Voice**: its text ends up in training corpora.
- `eval/README.md`'s canary and "never train on this" already cover the folder.

**Words need no new columns.** Contributor handles fit the existing `translated_by` / `reviewed_by` pattern. A later validator change should do two things:

- check every handle against `_meta/contributors.tsv`;
- reject `machine` in `reviewed_by` (bug hunt M2).

**Two convention changes to decide** (they are proposals, not done):

1. Contributed sentences have no printed source page. The pair tables therefore have no `source`/`page` columns; `translated_by` plus the batch id in `notes` is their provenance. `_meta/conventions.md` would need that exception.
2. `reviewed_by` stays GitHub usernames, as GOVERNANCE.md requires. Board members need GitHub accounts; contributors don't.

The tool's own working database is sketched in [`proposal/supabase-schema.sql`](proposal/supabase-schema.sql). Its row-level security policies are what enforce:

- blind answers;
- no self-rating;
- no deciding on your own item.

### (e) Where frequency ranks come from (question for you)

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

**Recommendation: 2 now, blended with 3 as sentences come in. Use 1 only if you are comfortable publishing a rank derived from text that can't be shared.** The prototype uses option 2 as a labelled stand-in.

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

## 8. What the prototype does and doesn't do

**Does:**

- **All three modes**, plus rating and the board screen, the agreement rules and the conflict-of-interest rule.
- **Live checks** while typing.
- **Consent and credit**: the consent screen, contributor handles, credit for everyone who gave the chosen value.
- **Export and import**: JSON export and import, and a preview of the TSV rows a pull request would contain.
- **Language and layout**: English and a draft Papiamento interface, phone layout and dark mode.

**Doesn't:**

- no server, sign-in or email: "Switch person" simulates several people on one device;
- only 8 + 8 sample words and 12 sample prompts;
- the frequency order is a stand-in;
- the pull-request preview is illustrative (`par-NEW` ids);
- no Common Voice export.

## 9. Proposed next steps (after your decisions)

1. **Schema PR.**
   - Add the new tables and `_meta/contributors.tsv`.
   - Change the conventions and LICENSE-DATA as decided in (a) and (d).
   - Teach the validator about handles.
   - Language content, so it needs board approval.
2. **Prompts, batch 1.** About 300 written prompts with the 15 % held out, checked by a maintainer.
3. **Tool v1 (option A).**
   - Supabase project and schema, email sign-in, GitHub Pages.
   - The sync job and `tools/apply_contributions.py`.
   - The GitHub App for pull requests.
   - Pilot with 3–5 teachers and the first board members.
4. **Common Voice (P2-04).** Export reviewed, CC0, non-held-out sentences that meet its rules.
