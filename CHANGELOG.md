# Changelog

All notable changes to this dataset are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See [GOVERNANCE.md](GOVERNANCE.md#releases) for what counts as a major, minor or patch change.

## [Unreleased]

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
