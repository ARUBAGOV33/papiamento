# Changelog

All notable changes to this dataset are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See [GOVERNANCE.md](GOVERNANCE.md#releases) for what counts as a major, minor or patch change.

## [Unreleased]

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
