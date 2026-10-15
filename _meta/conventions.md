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
- No spaces at the start or end of a cell, and no double spaces.
- Apostrophes are straight (`'`), never curly (`’`).
- An empty cell means "not known yet".
- Several values in one cell are separated by `; ` (semicolon, space), for example `house; home`.

Schemas live in `_meta/schema/` in [Frictionless Table Schema](https://specs.frictionlessdata.io/table-schema/) format. `_meta/schema/registry.json` says which schema applies to which file.

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
| `translated_by` | Who wrote the translations: `machine` for machine drafts, otherwise GitHub usernames separated by `; `. Required whenever `en`, `nl` or `es` is filled. When you correct a machine draft, replace `machine` with your username. |
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

## Files and names

- Folder and file names are lowercase kebab-case, ASCII only, no spaces. Letter folders (`A`–`Z`) and source ids are the only uppercase names.
- Generated files (`dist/`, letter `README.md` progress pages) are never edited by hand.
