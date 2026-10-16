# Changelog

All notable changes to this dataset are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See [GOVERNANCE.md](GOVERNANCE.md#releases) for what counts as a major, minor or patch change.

## [Unreleased]

### Added

- `rules/rules.jsonl`: 49 machine-readable checker rules (31 orthography, 9 morphology, 4 prepositions, 3 from maintainer rulings, 1 syntax, 1 style), 30 of them with an automatic fix. Every test sentence is printed in the linked grammar file or is a documented mechanical change of a printed example. Four writer agents and four independent checkers built them; the checkers judged precision on about 10,000 real Aruban sentences (no false alarms in their samples apart from foreign-language words in the no-accent rule). 31 flaggable grammar rules have no pattern because a regex cannot check them reliably; `rules/README.md` lists them with the reason.
- Validator gate G5 tests every machine rule against its grammar file; `tools/test_rules.mjs` runs the same tests in JavaScript (the Skirbi checker's engine) in CI. Patterns may not use `\b` or `\w`, which misfire next to ñ in JavaScript.

### Added

- `grammar/`: 192 spelling and grammar rules rebuilt from the source PDFs (AB 2018 orthography annex, Morfologia, Preposicion y Interheccion, Sintaxis, Stilistica), one file per rule with source and printed page. Papiamento examples are quoted verbatim from the page; none were written by a machine. Eight writer agents and eight independent checkers verified every rule against the page image (33 corrections). Of the 222 old rule-pack rules, 30 are not files: duplicates merged into another rule, or statements no page supports (listed in `grammar/README.md`).
- Validator gate for grammar rule files (front matter, source and page, file name, required section), with tests.
- Source `RUL2026` for rules that rest on a maintainer ruling rather than a printed page.

### Added

- `lexicon/loanwords/loanwords.tsv`: 315 loanwords from AB 2018 §12 (gazette pp. 41-44): Spanish words written in a set form, words keeping final z, -eza/-anza nouns; Dutch, English and French words kept in their original spelling or respelled, the two-option pairs, the sch table, special spellings and words derived from brand names; Italian, Latin and German words. Two checkers verified every row against the page images. The language of origin for §12.2 words is assigned by the editors, since the law groups Dutch, English and French.
- `sources/errata.tsv`: err-0014 to err-0016, where §12 and the law's own word list disagree. Decided by the maintainer: dagvaard, osterizer in lowercase, and both schuin and scuins (new loanword row).
- Loanword origins `it`, `la` and `de` in the schema.

### Changed

- Removed the machine translation of `skit` ("sketch"): the law lists it among words from Dutch sch-.

### Changed

- Maintainer decisions on all open errata (2026-10-16); err-0003 to err-0013 are now `reviewed`:
  - Six typos in the AB 2018 word list are corrected in the data (`bongo`, `cinematografo`, `computarisando`, `computerisando`; alternatives `coregimento` and `lisimbein`). Each row notes what the law prints, and a known fact guards each correction.
  - `drumiendo` confirmed over Morfologia's `durmiendo` (new barbarismo row); `por` and `prefera` have no gerund, against Morfologia p. 48.
  - `eigenlijk` is a valid word but should be avoided in careful writing; `todo` only in fixed expressions such as `en todo caso`, otherwise `tur`.
  - `hamas` also means "never".

### Added

- `lexicon/barbarismos/barbarismos.tsv`: 41 forms to avoid with the Aruban form to use: Spanish day and month names, familia, hay, todos, muchos, usted(es), en, de la/del/de los/de las, siete (maintainer rulings, with the correct form cited in AB 2018); tevreden and eigenlijk (Stilistica); four wrong gerund forms (Morfologia p. 48, AB 2018). Rows where the AB 2018 list itself contains the "wrong" form (todo, eigenlijk) are marked disputed with an errata entry.
- `lexicon/variants/curacao-aruba.tsv`: 372 Curaçao → Aruba spelling pairs. Each Curaçao form is printed on the cited page of a Curaçao-spelled source; each Aruban form is an AB 2018 headword. Checked pair by pair for false friends and non-standard spellings.
- `sources/errata.tsv`: err-0009 to err-0013. Morfologia p. 48 lists durmiendo, podiendo and prefiriendo as gerunds, against maintainer rulings (the AB 2018 list has drumiendo); Stilistica vs AB 2018 on eigenlijk; the ruling on todo vs AB 2018.

### Added

- `lexicon/numbers/`: cardinals 0-99, 100, 1,000, 1,000,000 and 1,000,000,000 (`biyon`, ruled to mean 10^9) from the AB 2018 word list; ordinals, fractions and multiples from Morfologia §9.3; clock times and worked examples from AB 2018 §10.1.3 and §11.8. 159 rows with English, Dutch and Spanish.
- `lexicon/calendar/days.tsv` and `months.tsv`: the 7 days and 12 months, lowercase, from AB 2018 §9.6 and the word list. Public holidays wait for an official source.
- All 33 known facts are now checked against data (none pending), including the new rulings never = `nunca` and billion = `biyon`.
- Number kind `multiple` in the numbers schema.

### Added

- English, Dutch and Spanish drafts for the 3,000 most frequent words (2,924 rows filled; 91 left empty on purpose). Drafted by one model, checked cell by cell by a second, disagreements settled by a third; no dictionaries, websites or Glosbe. 170 rows the drafting model rated uncertain carry a note asking reviewers to check them first.
- `translated_by` column in word files: `machine` for machine drafts, otherwise GitHub usernames. The validator requires it whenever a translation is filled.
- Translation conventions in `_meta/conventions.md`.

### Added

- `lexicon/words/A`–`Z`: all 16,218 headwords of the AB 2018 no. 68 word list, with alternative forms, the law's own labels, part of speech where the law gives it, and the printed page. Every row is `draft`; 6 rows are `disputed` because the law appears to contain a typo (`sources/errata.tsv`, err-0003 to err-0008). Translations are empty except two confirmed by the maintainer.
- `sources/pdf/AB2018.pdf`: the official law, from the archive.org copy uploaded by Biblioteca Nacional Aruba.
- `tools/import_ab2018.py` and `tools/import_ab2018_overrides.tsv`: how the word list was rebuilt from the PDF, and every correction made during review.
- `tools/build_pages.py`: generated progress page in each letter folder; CI checks they are up to date.

### Changed

- Known facts now wait while the checked cell is empty, since an empty cell means "not known yet".

- Repository skeleton (version 0).
- `_meta/`: conventions for every data file, table schemas and the schema registry, Aruban spelling and grammar invariants, known facts checked on every change, and the allowlist of accented loanwords.
- `_templates/`: empty tables with the correct header row.
- Folder layout for `lexicon/`, `grammar/`, `rules/`, `corpus/` and `eval/`.
- `sources/`: source registry, source cards, errata table and permission records.
- `tools/validate.py`: the validator ("the gauntlet"), with gates G0 (source trace), G1 (format), G2 (schema), G3 (orthography), G4 (integrity) and G5 (known facts), and a GitHub Actions workflow that runs it on every pull request.
- `CLAUDE.md` and `AGENTS.md`: routing notes for AI agents.
- Community files: README, contributing guide, governance, code of conduct, citation metadata, issue forms, pull request template and code owners.
- Licences: Apache-2.0 for code (`LICENSE`) and CC BY 4.0 for data and documentation (`LICENSE-DATA`).

[Unreleased]: https://github.com/ARUBAGOV33/papiamento/commits/main
