# Conventions

How every data file in this repo is written. The validator (`tools/validate.py`) enforces these rules. When this file and the validator disagree, fix one of them in the same change.

## Source of truth

The source PDFs are the source of truth: the AB 2018 no. 68 law, Ortografia 2009, Vocabulario 2009, Morfologia, Sintaxis, Preposicion y Interheccion, and the other books listed in `sources/sources.tsv`.

- Every row cites a `source` (an id from `sources/sources.tsv`) and a `page`.
- OCR text, scraped data and older JSON files are working copies only. When a working copy disagrees with the PDF, the PDF wins.
- When two PDFs disagree, or a PDF contains an obvious typo, do not pick a winner silently. Add a row to `sources/errata.tsv` and let the review board decide.

## File format

All tables are TSV files:

- UTF-8, Unicode NFC, LF line endings, a final newline.
- First line is the header, with exactly the columns in the table's schema, in that order.
- Columns are separated by a single tab. Cells never contain tabs or line breaks, and are never quoted.
- Cells hold only visible characters and plain spaces: no control or zero-width characters, no line or paragraph separators (U+2028, U+2029), no no-break spaces.
- No spaces at the start or end of a cell, and no double spaces.
- Apostrophes are straight (`'`), never curly (`’`).
- An empty cell means "not known yet".
- Several values in one cell are separated by `; ` (semicolon, space), for example `house; home`.

Schemas live in `_meta/schema/` in [Frictionless Table Schema](https://specs.frictionlessdata.io/table-schema/) format. `_meta/schema/registry.json` says which schema applies to which file. Each table's glob must match at least one file (a file with only the header is enough); a table that may have no file yet is marked `"optional": true`.

## Ids

Ids are assigned once, never reused and never renumbered. A word that moves to another letter folder keeps its id.

| Table | Id pattern | Example |
|---|---|---|
| Words | `pap-` + 6 digits | `pap-000412` |
| Numbers | `num-` + 4 digits | `num-0007` |
| Calendar | `cal-` + 4 digits | `cal-0001` |
| Barbarismos | `bar-` + 4 digits | `bar-0001` |
| Curaçao–Aruba variants | `var-` + 4 digits | `var-0001` |
| Loanwords | `loan-` + 4 digits | `loan-0001` |
| Errata | `err-` + 4 digits | `err-0001` |
| Audits | `aud-` + 4 digits | `aud-0001` |
| Sources | short code + year | `AB2018`, `MOR2010` |
| Rules | `RULE_<DOMAIN>_<NAME>` | `RULE_ORT_ACCENT_001` |

Rule ids keep the names already used by the Skirbi checker, so the auditor and this repo stay in sync.

## Status

Every data row has a `status`:

| Status | Meaning |
|---|---|
| `draft` | Entered by a machine or a contributor, not yet checked by the review board. |
| `reviewed` | A review-board member checked the row against the source. `reviewed_by` must name them. |
| `disputed` | Reviewers disagree, or sources conflict. Explain in `notes` and link the errata row. |
| `deprecated` | Kept for history; no longer valid. Explain in `notes`. |

Machine-made content is always `draft`. Nothing becomes `reviewed` automatically. Anyone training a model can filter to `status == reviewed`.

`reviewed_by` holds GitHub usernames, separated by `; `.

## Source and page

- `source`: an id from `sources/sources.tsv`, for example `AB2018`.
- `page`: the page number **as printed** on the page, for example `38` or `38-39`. Use lowercase roman numerals for front matter (`iv`). Each source card records the offset between printed pages and PDF page numbers, so a reviewer can jump straight to the page.
- A `reviewed` row must have both.
- **AB 2018 page numbers restart** in each part of the law: the law itself, the orthography annex (same numbering as ORT2009) and the word list (pages 1–72, same as VOC2009). For words, `page` is the word-list page. For rules, also give the section (e.g. §11.8) so the page is unambiguous.

## Words (`lexicon/words/<LETTER>/words.tsv`)

| Column | Content |
|---|---|
| `id` | Stable id, `pap-000001`. |
| `lemma` | The headword exactly as the source prints it. Proper nouns keep their capital. |
| `alt` | Alternative forms the source gives in brackets, e.g. `cuatro` for `cuater [cuatro]`. |
| `pos` | Part of speech, from the list below. Empty when unknown. |
| `tag` | The source's own label in parentheses, copied verbatim, e.g. `s.`, `pisca`, `- la pena`. |
| `en`, `nl`, `es` | Translations. Several senses separated by `; `. |
| `translated_by` | Who wrote the translations: `machine` for machine drafts, otherwise GitHub usernames separated by `; `. Required whenever `en`, `nl` or `es` is filled. When you correct a machine draft, replace `machine` with your username; when you confirm only one language, keep both, e.g. `victorgomesrt-rgb; machine`, and say which in `notes`. |
| `status`, `reviewed_by`, `source`, `page`, `notes` | As above. |

- **Letter folders:** a word goes in the folder of its first letter, uppercased, with the accent removed. Words starting with `ñ` go in `N`, as in the AB list.
- **Homographs:** one row per entry the source lists. `bale (s.)` and `bale (- la pena)` are two rows. Lemma + pos + tag must be unique.
- **Sort order:** by lemma (case-insensitive), then pos, tag and id.

### Translations

- Translate the **Aruban** meaning. Many Papiamento words look like Spanish, Dutch or English words with a different meaning: `hopi` is "a lot", not "Hopi"; `cinco` is "five".
- At most three senses per language, most common first, separated by `; `.
- Verbs: English with "to" (`bay` → `to go`); Dutch and Spanish in the infinitive (`gaan`, `ir`).
- Nouns in the singular; Spanish adjectives in the masculine singular.
- Grammatical words get a short description in parentheses when no single word fits, e.g. `(present tense marker)`.
- Proper nouns: the usual name in each language.
- Use the source's labels: `(pisca)` means a fish, `(mata)` a plant, `(mus.)` music.
- **Leave the cell empty when unsure.** An empty cell is better than a wrong one.

### Part-of-speech values

The first four are the abbreviations the AB list itself uses.

| Value | Meaning |
|---|---|
| `s.` | sustantivo |
| `v.` | verbo |
| `adh.` | adhetivo |
| `adv.` | adverbio |
| `num.` | numeral |
| `pron.` | pronomber |
| `prep.` | preposicion |
| `conh.` | conhuncion |
| `interh.` | interheccion |
| `art.` | articulo |
| `expr.` | expresion |
| `abr.` | abreviatura |

## Spelling checks on Aruban text

These checks apply to Aruban text columns (`lemma`, `alt`, `pap`, `right`, `aruba`):

- **Allowed characters only:** ASCII letters, `ñ`/`Ñ`, digits, apostrophe, hyphen, period and space. Any other character, including accented vowels (á é í ó ú à è ì ò ù â ê ô û ë ï ü), is an error, except in the loanwords listed in `_meta/allowlists/accented-loans.txt`.
- **Curaçao markers** (`-shon` endings, `k` before a/o/u, the words `ku`, `kos`, `kon`, `ki`) are a warning, not an error, because the AB list contains legitimate words with them (`cashon`, `shon`, `kabel`, `kantoor`). The warning is skipped for rows whose `source` is `AB2018`.
- **Loanwords** (`lexicon/loanwords/`) keep the spelling AB §12 allows for their language of origin, so their `lemma` is not spelling-checked.

## Variants

Canonical columns hold Aruban Papiamento (`pap-AW`) only. Curaçao spellings (`pap-CW`) appear only in `lexicon/variants/curacao-aruba.tsv`, as a mapping to the Aruban form.

## Audits (`_meta/audits.tsv`)

An audit measures how many rows of a table are wrong. Take a random sample of the table, check each sampled row against the page image of its cited source, and count the rows that are wrong. One row in `_meta/audits.tsv` records one audit of one table. The README progress table shows each table's latest audit as its measured error rate, with a 95% Wilson interval.

| Column | Content |
|---|---|
| `id` | Stable id, `aud-0001`. |
| `date` | The day the audit finished, `YYYY-MM-DD`. |
| `table` | What was audited: `words`, `numbers`, `calendar`, `barbarismos`, `variants`, `loanwords`, `grammar` (the files in `grammar/`), `rules` (the machine rules in `rules/rules.jsonl`), or `translations` (the `en`, `nl` and `es` cells of word rows). |
| `sample_size` | How many rows were checked. |
| `errors` | How many of them were wrong. Never more than `sample_size`. |
| `method` | How the sample was drawn, with the seed if a program drew it, and what counted as an error. |
| `auditor` | GitHub usernames of the people who checked the sample, separated by `; `. `machine` when software or an AI model did the checking; both when a person re-checked the machine's findings, e.g. `victorgomesrt-rgb; machine`. |
| `notes` | Rows that were doubtful but not counted, the errata or fixes the audit led to, a link to the full report. |

- **Only log an audit that was carried out.** Never estimate or copy a number from somewhere else. "Not audited yet" is better than a guess.
- **Random means random.** Draw the sample with a program and a stated seed (for example Python `random.sample` with seed 2026), or by a stated rule such as every 50th row. Rows picked by hand, or rows already known to be wrong, measure nothing. If how a sample was drawn was not recorded, as in the 2026-10 bug hunt, say so in `method`.
- **The page is the judge.** Check the rendered page image of the cited source page, not an OCR or text layer.
- **An error** is a row with at least one cell that disagrees with the page. For `translations`, which no source page prints, it is a sense that is not the Aruban meaning or breaks the translation conventions above. Say in `method` if you counted differently, for example "only the lemma, alt and tag cells". Doubtful rows go in `notes`, not in `errors`.
- **Fix what you find in a separate change.** The audit row keeps the number found at the time; later fixes do not change it. The next audit measures the table again.
- **Rows are never edited or deleted**, except to fix a typo in the log itself. Old audits stay as the history of the table's quality.
- Audit rows have no `status`: they record a measurement, not language content.

## Milestones (`_meta/milestones.tsv`)

One row per project phase, as on the project board: `P0` Foundation to `P4` Speech and AI. The README shows them on one line above the progress chart. Maintainers edit this file by hand when a phase changes.

| Column | Content |
|---|---|
| `id` | The phase, `P0` to `P9`. Rows are sorted by it. |
| `title` | Its short name, e.g. `Clean data`. |
| `status` | `done`, `in-progress`, `next` or `not-started`. |
| `left` | What is still to do, separated by `; `. A phase can be `done` with a few small items left. |
| `notes` | Anything else, e.g. the release that closed it. |

## Files and names

- Folder and file names are lowercase kebab-case, ASCII only, no spaces. Letter folders (`A`–`Z`) and source ids are the only uppercase names.
- Generated files (`dist/`, letter `README.md` progress pages) are never edited by hand.
