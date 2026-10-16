<h1 align="center">
  <img src=".github/assets/banner.webp" alt="Papiamento: open data for Aruban Papiamento" width="100%">
</h1>

<p align="center">
  <a href="https://github.com/ARUBAGOV33/papiamento/actions/workflows/gauntlet.yml"><img alt="Gauntlet" src="https://github.com/ARUBAGOV33/papiamento/actions/workflows/gauntlet.yml/badge.svg"></a>
  <a href="https://github.com/ARUBAGOV33/papiamento/releases"><img alt="Latest release" src="https://img.shields.io/github/v/release/ARUBAGOV33/papiamento?label=release&color=1f6fb2"></a>
  <a href="LICENSE-DATA"><img alt="Data licence: CC BY 4.0" src="https://img.shields.io/badge/data-CC%20BY%204.0-1f6fb2"></a>
  <a href="LICENSE"><img alt="Code licence: Apache-2.0" src="https://img.shields.io/badge/code-Apache--2.0-1f6fb2"></a>
  <img alt="Language: Aruban Papiamento (pap-AW)" src="https://img.shields.io/badge/language-pap--AW-f9d616">
</p>

<!-- PAP-INTRO: written with AI, every word checked against the AB 2018 list; approved by the maintainer (@victorgomesrt-rgb) on 2026-10-16. -->
> **Papiamento:** Aki bo ta haya un coleccion habri di dato riba Papiamento di Aruba: palabra, regla di ortografia y gramatica, number y mas. Maestro, investigado, gobierno, compania y sistema di inteligencia artificial por uza e dato aki pa skirbi Papiamento corecto. Tur dato ta bini di e fuentenan oficial: e Afkondigingsblad 2018 no. 68 y e bukinan di Departamento di Enseñansa. Bo por yuda: corigi un traduccion, propone un palabra of reporta un eror.

## What this is

This repository is an open, citable reference dataset for **Aruban Papiamento**: the language as it is written in Aruba, in the etymological spelling set out in the AB 2018 no. 68 law and its official word list.

It holds:

- every headword of the AB 2018 word list, with English, Dutch and Spanish translations;
- numbers, days and months, loanwords, names and other closed word lists;
- barbarismos (borrowed forms to avoid) with the Aruban form to use instead;
- a map from Curaçao spellings to Aruban spellings;
- spelling and grammar rules, in plain words and in a machine-readable form;
- test sets for checking tools and models.

Every row says which source it comes from and on which printed page. Everything is plain text (tab-separated files) that opens in a spreadsheet, a text editor or any programming language.

It is written for:

- **teachers and linguists** who want a single, checkable reference;
- **government bodies** that publish in Papiamento;
- **companies** building spell checkers, keyboards, translation or speech tools;
- **people training AI models** who need clean, labelled Aruban data.

## Why an Aruban dataset

Papiamento is written in two standards:

| | Aruba | Curaçao and Bonaire |
|---|---|---|
| Name | Papiamento | Papiamentu |
| Spelling | Etymological (follows the origin of the word) | Phonological (follows the sound) |
| Example | cas, educacion | kas, edukashon |
| Language tag | `pap-AW` | `pap-CW` |

Both are correct in their own place. But most Papiamento text online uses the Curaçao standard, and both standards share one language code, `pap`. Models and spell checkers trained on that text learn Curaçao spelling and then use it for Aruba.

This dataset keeps the two apart. Canonical columns hold Aruban Papiamento only. Curaçao forms appear in one place, `lexicon/variants/curacao-aruba.tsv`, mapped to the Aruban form.

## What's inside

```
_meta/            Conventions, schemas, invariants, known facts, allowlists
_templates/       Starter files: word row, grammar rule, source card, errata row
lexicon/
  words/A-Z/      words.tsv per letter: every AB 2018 headword with EN, NL, ES
  numbers/        Cardinals, ordinals, fractions and clock times
  calendar/       Days, months and public holidays
  barbarismos/    Forms to avoid, with the Aruban form to use instead
  variants/       Curaçao spelling mapped to Aruban spelling
  loanwords/      Loanwords, their origin and the accepted Aruban form
  names/          Places, institutions, demonyms
  closed-classes/ Pronouns, articles, prepositions, conjunctions, tense markers
grammar/          Rules in plain language, one file per rule: orthography,
                  morphology, syntax, prepositions, style
rules/            Machine-readable checker rules, each with its own tests
corpus/           Aruban text we may redistribute, with a manifest
eval/             Test sets for the writing auditor and for AI models
sources/          Source registry (sources.tsv), source cards, shareable PDFs,
                  errata and permission records
release/          Template of the Hugging Face dataset card
tools/            The validator and build scripts
tests/            Tests for the validator
CLAUDE.md         Routing notes for AI agents
AGENTS.md         Points other AI agents to CLAUDE.md
```

Every folder has a `README.md` that says what lives there and how to add to it.

Start with [`_meta/conventions.md`](_meta/conventions.md). It explains the file format, ids, status values and source citations that every table follows. [`_meta/invariants.md`](_meta/invariants.md) lists the spelling and grammar rules that are not up for debate.

## Project status

Version 0.1.0 is the first release. See [CHANGELOG.md](CHANGELOG.md).

<!-- REPO-PROGRESS:START -->
<!-- Generated by tools/build_pages.py from the data. Do not edit by hand. -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/progress-dark.svg">
  <img alt="Progress: 16,218 words; 18% with English, 18% with Dutch, 18% with Spanish; 0% reviewed by the board; 49 of 80 flaggable grammar rules have a machine check." src=".github/assets/progress-light.svg" width="100%">
</picture>

| Table | Rows | Reviewed by the board |
|---|---:|---:|
| [Words](lexicon/words/) (AB 2018 word list) | 16,218 | 0 |
| Numbers | 159 | 0 |
| Days and months | 19 | 0 |
| Barbarismos | 42 | 0 |
| Curaçao → Aruba spelling pairs | 372 | 0 |
| Loanwords | 315 | 0 |
| [Grammar rules](grammar/) | 192 | 0 |
| [Machine checker rules](rules/) | 49 | |
<!-- REPO-PROGRESS:END -->

- Every headword of the AB 2018 word list is in `lexicon/words/A`–`Z`, checked against the printed law and the Papiamento.aw list. The most frequent words have machine-drafted English, Dutch and Spanish translations, marked `translated_by = machine` until a person reviews them. [Progress per letter](lexicon/words/README.md).
- Names, closed word classes, public holidays, the corpus and the test sets are still empty.
- The review board is being recruited. Until it checks a row, that row stays `draft`.
- The chart and table above are rebuilt from the data after every change.

## How to use it

### Teachers and linguists

1. Open a letter folder, for example [`lexicon/words/`](lexicon/words/), then a letter, then `words.tsv`. GitHub shows the file as a table you can search.
2. To work with it in Excel or Google Sheets, use the **Download raw file** button above the table, then open the file in your spreadsheet. If Excel asks for the file origin or encoding, choose **UTF-8**, or letters like ñ will show up wrong.
3. Check the `status` column. Only `reviewed` rows have been checked by the review board.

Found a mistake? See [How to contribute](#how-to-contribute). You do not need to know any programming.

### Developers and AI trainers

All tables are UTF-8 TSV files with a header row, one tab between cells, no quoting. An empty cell means "not known yet". Several values in one cell are separated by `; `.

Each row has a `status`:

| Status | Meaning |
|---|---|
| `draft` | Entered by a person or a machine; not yet checked by the review board. |
| `reviewed` | A review-board member checked it against the source page. `reviewed_by` names them. |
| `disputed` | Reviewers disagree or sources conflict. See `notes` and `sources/errata.tsv`. |
| `deprecated` | Kept for history; no longer valid. |

**If you want only verified data, keep the rows where `status == reviewed`.** Machine-made content, including AI translations, is always `draft`. In word files, a `translated_by` that includes `machine` marks translations a machine drafted; filter on it to leave them out entirely.

Reading the files in Python, with no dependencies:

```python
import csv
from pathlib import Path

rows = []
for path in sorted(Path("lexicon/words").glob("*/words.tsv")):
    with path.open(encoding="utf-8", newline="") as f:
        rows += csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)

reviewed = [r for r in rows if r["status"] == "reviewed"]
```

If you use pandas, turn off its missing-value guessing. Otherwise it reads real words such as `nan` as "not a number":

```python
pd.read_csv(path, sep="\t", dtype=str, quoting=3, keep_default_na=False, na_filter=False)
```

Please keep Aruban (`pap-AW`) and Curaçao (`pap-CW`) data separate and labelled in anything you build.

**Do not train on `eval/`.** It holds test sets for measuring tools and models. [`eval/README.md`](eval/README.md) gives a canary string you can search for, to check that your training data does not contain them.

Each release also ships the tables as JSON Lines files, with a dataset card and `rule_pack.json` for writing checkers. They are attached to the [GitHub release](https://github.com/ARUBAGOV33/papiamento/releases) and published on Hugging Face, and Zenodo gives each version a DOI. The Hugging Face and DOI links are added here once version 0.1.0 is published. To build the same files yourself, run `python3 tools/build_dist.py`; they land in `dist/`.

## How to contribute

Teachers, linguists and other speakers are the most valuable contributors. You can:

1. fix or add a translation;
2. report a wrong word or spelling;
3. propose a rule;
4. add a test case for the writing auditor (the auditor is coming soon).

Each can be done through a simple form, with no code. See [CONTRIBUTING.md](CONTRIBUTING.md).

Every pull request runs the validator ("the gauntlet") through GitHub Actions. You can run it yourself with `python3 tools/validate.py` (Python 3.9 or newer, no extra packages). It checks:

| Gate | Checks |
|---|---|
| G0 Source trace | Every source id exists in `sources/sources.tsv`; reviewed rows have a source and a page; PDFs and permissions are recorded |
| G1 Format | UTF-8, tabs, line endings, header, sort order, no stray spaces or curly apostrophes |
| G2 Schema | Required values, allowed values, patterns, uniqueness |
| G3 Orthography | Aruban spelling, such as no accents and the right letter folder; warnings for Curaçao spellings |
| G4 Integrity | Ids unique across all tables; references between tables |
| G5 Known facts | Rulings that must never regress |

Details are in [`tools/README.md`](tools/README.md).

## Sources and source of truth

The source PDFs are the source of truth:

- **AB 2018 no. 68**: the law published in Aruba's official gazette in 2018, with its spelling rules and official word list.
- Books by the **Departamento di Enseñansa**: Ortografia (2009), Vocabulario (2009), Morfologia (2010), Sintaxis (2015), and Preposicion y Interheccion (2016).
- Other sources listed in [`sources/sources.tsv`](sources/sources.tsv).

How this works in practice:

- Every row cites a source id and the page number **as printed** in that source. Each source card in `sources/cards/` records the offset between printed and PDF page numbers, so anyone can open the exact page.
- OCR text, scraped data and older files are working copies. When a working copy disagrees with the PDF, the PDF wins.
- When two PDFs disagree, or a PDF contains a typo, the case goes into [`sources/errata.tsv`](sources/errata.tsv) and the review board decides. Nobody picks a winner silently.
- Nothing is copied from copyrighted dictionaries, websites, Glosbe or newspapers.

## Licences

| What | Where | Licence | File |
|---|---|---|---|
| Code | `tools/`, `tests/`, `.github/` | Apache-2.0 | [LICENSE](LICENSE) |
| Data and documentation | Everything else we author: `lexicon/`, `grammar/`, `rules/`, `corpus/`, `eval/`, `_meta/`, `_templates/`, and the cards and tables in `sources/` | CC BY 4.0 | [LICENSE-DATA](LICENSE-DATA) |
| Source PDFs | `sources/pdf/` | Each file keeps its own terms, recorded in `sources/sources.tsv` | |
| Voice sentences and recordings (planned) | | CC0 | |

The licences cover what this project's contributors wrote. Text reproduced from a source keeps that source's terms: see `sources/sources.tsv`, and `corpus/manifest.tsv` for corpus files.

The AB 2018 law is public domain. The Departamento di Enseñansa books are republished with permission from the Departamento di Enseñansa, granted through the Minister of Education and Innovation. The permission records are in `sources/permissions/`.

To attribute the data, write: "Papiamento Open Data contributors, https://github.com/ARUBAGOV33/papiamento, CC BY 4.0".

## How to cite

Citation details are in [CITATION.cff](CITATION.cff). On GitHub, use the **Cite this repository** button in the right-hand sidebar to get APA or BibTeX.

Until the Zenodo DOI is added here:

> Papiamento Open Data contributors. *Papiamento: open data for Aruban Papiamento* [Data set]. https://github.com/ARUBAGOV33/papiamento

Once a version has a Zenodo DOI, cite the DOI of the version you used. If you rely on a specific word or rule, also cite the source and page given in that row.

## Governance

The project is run by its maintainers, [@ARUBAGOV33](https://github.com/ARUBAGOV33) and [@victorgomesrt-rgb](https://github.com/victorgomesrt-rgb), and a review board of Aruban teachers and linguists. The board is being recruited. Until it has at least two members, the maintainers do its work.

Changes to language content need an approving review from a code owner. Only review-board members can mark a row `reviewed`. See [GOVERNANCE.md](GOVERNANCE.md) for roles, approvals, disputes and releases.

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Acknowledgements

- The **Departamento di Enseñansa** and the **Ministry of Education and Innovation** of Aruba, for permission to republish the Departamento di Enseñansa books.
- The authors and editors of the source books and of the AB 2018 word list, whose work this dataset is built on.
- **Vadria Innovation Labs**, for supporting the project.
- Everyone who reports a mistake, adds a translation or reviews a row.
