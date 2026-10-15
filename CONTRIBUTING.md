# Contributing

This guide is written for teachers and linguists first. You do not need to know any programming to help. Most help arrives through simple forms.

If you are a developer, skip to [The developer route](#the-developer-route).

## Five rules that apply to everything

1. **Aruban Papiamento only.** Canonical columns hold the Aruban standard (`pap-AW`). Curaçao spellings go only in `lexicon/variants/curacao-aruba.tsv`. See [Aruban spelling basics](#aruban-spelling-basics).
2. **Every row needs a source and a page.** The source is an id from [`sources/sources.tsv`](sources/sources.tsv), such as `AB2018`. The page is the number printed on the page, such as `38` or `38-39`. Use lowercase roman numerals for front matter, such as `iv`.
3. **New and changed rows are `draft`.** Only review-board members set `reviewed`. See [Status rules](#status-rules).
4. **Never paste from copyrighted dictionaries, websites, Glosbe or newspapers.** Write in your own words, or use a source listed in `sources/sources.tsv`. See [Copyright](#copyright).
5. **What you send is published openly.** Data and documentation are published under [CC BY 4.0](LICENSE-DATA); code under [Apache-2.0](LICENSE). By contributing, you confirm you wrote the content yourself or that it comes from an allowed source.

## Four ways to help

Each way has two routes:

- **The form route.** Fill in a form on GitHub. No files to edit. A maintainer turns your report into a change and credits you. You need a free GitHub account.
- **The browser route.** Edit the table yourself in GitHub's web editor and open a pull request. The steps are in [Editing a table in the browser](#editing-a-table-in-the-browser).

### 1. Fix or add a translation

Every word in `lexicon/words/<LETTER>/words.tsv` has an `en` (English), `nl` (Dutch) and `es` (Spanish) column. Many are empty or are machine-made drafts.

- **Form:** [Add or fix a translation](https://github.com/ARUBAGOV33/papiamento/issues/new?template=add-translation.yml).
- **Browser:** open the word's letter file (a word starting with `ñ` is in `N`), find the row, and fill in or correct the `en`, `nl` or `es` cell.

Tips:

- Separate different meanings with a semicolon and a space: `house; home`.
- Translate the Aruban meaning, not the meaning of a similar Spanish or Dutch word.
- Leave `source` and `page` as they are. They say where the Aruban word is printed.
- If you are not sure, say so in `notes` or in the form.

### 2. Report a wrong word or spelling

A word can be misspelled, mistranslated, have the wrong part of speech, use a Curaçao spelling in an Aruban column, or not be a real word at all.

- **Form:** [Report a wrong word or spelling](https://github.com/ARUBAGOV33/papiamento/issues/new?template=wrong-word.yml).
- **Browser:** correct the cell and give the source and page that shows the correct form, in the commit message or the pull request.

If the sources themselves disagree, or a source contains a typo, do not pick a winner. Set the row to `disputed` and add a row to [`sources/errata.tsv`](sources/errata.tsv), starting from [`_templates/errata-row.tsv`](_templates/errata-row.tsv). The review board decides. See [GOVERNANCE.md](GOVERNANCE.md#disputes).

### 3. Propose a rule

Rules describe spelling, word forms, sentence structure, prepositions, word choice and style. Each rule exists twice: in plain words in `grammar/` (one small file per rule), and as a machine-readable checker rule in `rules/`.

- **Form:** [Propose a rule](https://github.com/ARUBAGOV33/papiamento/issues/new?template=propose-rule.yml). Describe the rule in plain words and give correct and incorrect examples. A maintainer turns it into a rule file.
- **Browser:** copy [`_templates/rule.md`](_templates/rule.md) into the matching topic folder in `grammar/` (orthography, morphology, syntax, prepositions or style) and fill it in. Keep `status: draft`. [`grammar/README.md`](grammar/README.md) explains the file name and layout. A maintainer writes the machine-readable version in `rules/`.

### 4. Add a test case for the writing auditor

The writing auditor is coming soon. It will check Aruban Papiamento text against the rules in `rules/`. Test cases tell it what it must catch and what it must leave alone.

- **Form:** [Report an auditor mistake or add a test case](https://github.com/ARUBAGOV33/papiamento/issues/new?template=auditor-mistake.yml). You can use it now, before the auditor is available: give a text with a mistake it should catch, or a correct text it should leave alone.
- **Browser:** test sets live in `eval/`. Their file format is still being set up. Until it is published in [`eval/README.md`](eval/README.md), please use the form.

A test case counts only after a review-board member has checked the expected answer. Do not put names, addresses or other personal details in test texts. Test texts are published.

## Editing a table in the browser

1. Sign in to GitHub.
2. Open the file, for example `lexicon/words/F/words.tsv`. GitHub shows it as a table.
3. Click the pencil icon (**Edit this file**). GitHub makes your own copy of the repository (a fork) for you.
4. Find the row. Click inside the editor and press Ctrl+F (Cmd+F on a Mac) to search.
5. Make your change. While you edit:
   - **Keep the tabs.** Cells are separated by a single tab character. Do not delete tabs and do not replace them with spaces. Click inside a cell and type.
   - **Do not add or remove columns.** Do not change the first line (the header).
   - **Do not change the `id`.**
   - **If you wrote or corrected a translation, put your GitHub username in `translated_by`** (replacing `machine` if it was there).
   - **Set `status` to `draft`** and leave `reviewed_by` empty. If the row was `reviewed`, change it back to `draft` and empty `reviewed_by`: the board checks it again.
   - **Do not delete a row.** To retire a row, set its status to `deprecated` and explain why in `notes`.
   - If you need to type a tab, first check that the editor's indent setting (above the text) says **Tabs**, not Spaces.
6. Click **Commit changes**. Describe what you changed and why, with the source and page. Then click **Propose changes** and **Create pull request**.
7. The validator ("the gauntlet") runs on your pull request. On your first pull request, a maintainer may need to start it for you. A green check means the file is well formed. A red cross means something needs fixing: click **Details** to see the line. Fix it by editing the file again in your pull request, or ask for help in a comment. A maintainer can fix it with you.

Every commit needs a sign-off (see [Sign-off](#sign-off-developer-certificate-of-origin)). When you commit in the browser, GitHub adds it for you.

**About spreadsheets.** Excel, Numbers and Google Sheets are good for reading the tables and working out your changes. But saving a file back from a spreadsheet can silently turn page ranges into dates, break letters like ñ, or add quotes. The safest way to send changes is a form or the GitHub editor. If you do save from a spreadsheet, save as tab-separated text in UTF-8; the gauntlet will point out anything that broke.

**Adding a new row.** Copy the example row in [`_templates/word-row.tsv`](_templates/word-row.tsv) (the row, not the header), put it in its place in alphabetical order, and replace every value. A maintainer can assign the `id` if you are unsure.

## Status rules

| Status | Meaning | Who sets it |
|---|---|---|
| `draft` | Not yet checked by the review board. | Anyone. All new and changed rows start here. |
| `reviewed` | A review-board member checked the row against the source page. | Review-board members only. They add their GitHub username to `reviewed_by`. |
| `disputed` | Reviewers disagree, or sources conflict. | Anyone, with an explanation in `notes` and a row in `sources/errata.tsv`. |
| `deprecated` | Kept for history; no longer valid. | Anyone, with an explanation in `notes`. The board confirms. |

- Machine-made content is always `draft`. This includes AI translations, OCR output and anything a script produced. Say in your pull request how it was made.
- Nothing becomes `reviewed` automatically.
- A `reviewed` row must have a `source`, a `page` and at least one name in `reviewed_by`. Several names are separated by `; `.
- Until the review board has at least two members, the maintainers do its work. See [GOVERNANCE.md](GOVERNANCE.md).

## Aruban spelling basics

Aruban Papiamento uses an etymological spelling: words are written according to their origin. The main points:

- The language is **Papiamento**, with a capital P and ending in -o.
- **No accent marks**, except **ñ** and a short list of loanwords the AB 2018 list prints with accents ([`_meta/allowlists/accented-loans.txt`](_meta/allowlists/accented-loans.txt)). Write `educacion`, `mas`.
- The ending pronounced /-shon/ is written **-cion**: `educacion`, `nacion`.
- **c** before a, o, u; **k** before e, i: `cas`, `cumpra`, `kere`. Dutch loans keep their k: `kabel`, `kantoor`.
- A word-final i-sound after a vowel is written **y**: `bay`, `hoy`, `ley`.
- The plural ending is **-nan** only: `casnan`.
- Days and months are **lowercase**: `dialuna`, `januari`.
- Numbers 11 to 99 are **one word**: `bintitres` (23). Seven is `shete`; five is `cinco`.
- Spanish forms that are not Aruban Papiamento are barbarismos: write `famia`, not `familia`; `tur`, not `todo`.

The full list, with sources, is in [`_meta/invariants.md`](_meta/invariants.md). The validator checks several of these rules on every change.

Curaçao and Bonaire use a different standard, Papiamentu, with different spelling (`kas`, `edukashon`). It is not wrong in its own place, but it does not belong in Aruban columns.

## Copyright

- **Never copy** from copyrighted dictionaries, websites, Glosbe, newspapers, or other people's books. This also applies to AI output that reproduces such text.
- Facts, such as how a word is spelled and on which page a source prints it, can be cited from any source in `sources/sources.tsv`.
- Text, such as definitions, explanations and example sentences, must be your own words or come from a source whose licence allows it.
- Want to add a new source? Open an issue with its title, author, year and licence. The maintainers add it to `sources/sources.tsv` and record what may be shared.

## The developer route

You need Git and Python 3.9 or newer. The validator has no other dependencies.

```sh
# 1. Fork and clone
gh repo fork ARUBAGOV33/papiamento --clone    # or fork on github.com, then git clone your fork
cd papiamento

# 2. Branch
git switch -c fix-en-translations-letter-f

# 3. Edit, then run the gauntlet
python3 tools/validate.py

# 4. Commit with sign-off
git add lexicon/words/F/words.tsv
git commit -s -m "lexicon/F: add EN translations (AB2018)"

# 5. Push and open a pull request
git push -u origin fix-en-translations-letter-f
gh pr create
```

Before you open the pull request:

- Read [`_meta/conventions.md`](_meta/conventions.md). It defines the file format, ids, sort order and status values.
- Run `python3 tools/validate.py` and make sure it passes. It runs the same gates (G0 to G5) as GitHub Actions.
- Ids are never reused or renumbered. A new row gets the next free id. The gauntlet catches duplicates.
- Keep rows in the sort order the conventions describe.
- Do not edit generated files (`dist/`, letter `README.md` progress pages) by hand.
- Change the validator and `_meta/conventions.md` together when a rule changes.
- AI agents: start with `CLAUDE.md` or `AGENTS.md`.

### Sign-off (Developer Certificate of Origin)

Every commit must be signed off. A sign-off is a line at the end of the commit message:

```
Signed-off-by: Your Name <your-email@example.com>
```

`git commit -s` adds it for you. By signing off, you certify the [Developer Certificate of Origin](https://developercertificate.org/): that you wrote the contribution, or have the right to submit it under the project's licences.

Forgot the sign-off? Fix the last commit with `git commit --amend -s --no-edit`, or every commit on your branch with `git rebase --signoff main`, then `git push --force-with-lease`.

## Getting help

Ask in an issue or in your pull request. Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md). How changes are approved is described in [GOVERNANCE.md](GOVERNANCE.md).
