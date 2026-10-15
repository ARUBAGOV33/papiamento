# Changelog

All notable changes to this dataset are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See [GOVERNANCE.md](GOVERNANCE.md#releases) for what counts as a major, minor or patch change.

## [Unreleased]

The import of every headword in the AB 2018 word list into `lexicon/words/A-Z/words.tsv` is in progress. Translations start as `draft`.

### Added

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
