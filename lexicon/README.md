# lexicon/

The words of Aruban Papiamento and the small reference tables built around them. All files are TSV and follow [`_meta/conventions.md`](../_meta/conventions.md).

## What lives here

| Folder | File(s) | Content | Status |
|---|---|---|---|
| `words/A` … `words/Z` | `words.tsv` | Every headword of the official AB 2018 no. 68 word list, with English, Dutch and Spanish columns | 16,218 words; machine-drafted EN/NL/ES for the 3,000 most frequent |
| `numbers/` | `cardinals.tsv`, `ordinals.tsv`, `fractions.tsv`, `multiples.tsv`, `times.tsv`, `examples.tsv` | How numbers and clock times are written (AB §10.1, §11.8; Morfologia §9) | 159 rows |
| `calendar/` | `days.tsv`, `months.tsv`, `holidays.tsv` | Days, months, public holidays | days and months done; holidays need an official source |
| `barbarismos/` | `barbarismos.tsv` | Forms to avoid and the Aruban form to use instead | 41 rows |
| `variants/` | `curacao-aruba.tsv` | Curaçao spelling mapped to Aruban spelling | 372 attested pairs |
| `loanwords/` | `loanwords.tsv` | Loanwords, their origin and accepted Aruban form (AB §12) | 315 rows from AB 2018 §12 |
| `names/` | `names.tsv` | The proper names of the AB 2018 word list: continents, countries, regions, islands, places, waters, demonyms, peoples, languages, religious names, holidays, titles, planets, zodiac signs, institutions (AB §9.3) | 380 rows, `draft`; each points to its headword in `words/` |
| `closed-classes/` | `articles.tsv`, `pronouns.tsv`, `particles.tsv`, `verbs.tsv`, `conjunctions.tsv`, `prepositions.tsv` | Articles, pronouns, tense/aspect particles, modal and other dependent verbs, conjunctions, prepositions (Morfologia ch. 4, 6–8, 10) | 181 rows, `draft` |
| `verb-forms/` | `verb-forms.tsv` | Gerunds and participles that Morfologia (§6.6) or the AB 2018 word list prints, each linked to its base verb | 1,921 rows, `draft` |

The schema for each table is in [`_meta/schema/`](../_meta/schema/); [`registry.json`](../_meta/schema/registry.json) maps files to schemas.

## How to add or fix something

1. Open the file on GitHub and use the pencil icon, or use one of the issue forms. Spreadsheets are fine for reading, but saving from one can break ñ, page ranges and quotes; see [Editing a table in the browser](../CONTRIBUTING.md#editing-a-table-in-the-browser).
2. Keep the columns exactly as they are. One row per entry.
3. Fill `source` and `page` from the PDF you checked. Without them, the row stays `draft`.
4. Leave `status` as `draft`. A review-board member changes it to `reviewed`.
5. Run `python3 tools/validate.py`, or let the pull request run it for you.

## Rules that matter most here

- Aruban spelling only. Curaçao forms go in `variants/` and nowhere else.
- One row per sense the source lists. Homographs get separate rows.
- Translations are separated by `; `.
- Never paste from copyrighted dictionaries, Glosbe or websites.
