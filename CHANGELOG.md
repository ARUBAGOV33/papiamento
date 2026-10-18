# Changelog

All notable changes to this dataset are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See [GOVERNANCE.md](GOVERNANCE.md#releases) for what counts as a major, minor or patch change.

## [Unreleased]

### Added

- `_meta/audits.tsv`, a log of random audits of each table against the source PDFs, with its schema, a template (`_templates/audit-row.tsv`) and conventions. It holds the six audits of the 2026-10 bug hunt (done by AI checker agents): 2 wrong machine translations out of 60, and no errors in samples of words (200), numbers (30), Curaçao-to-Aruba pairs (40), loanwords (40) and grammar files (20). The README progress table has a new "Measured error rate" column: the latest audit of each table with a 95% Wilson interval, or "not audited yet". The chart has a new Quality section. The validator checks that an audit's `errors` is never greater than its `sample_size`.
- `_meta/milestones.tsv`: the project phases P0 to P4 and where each stands, shown on one line above the README progress chart.
- `sources/errata.tsv`: err-0019 to err-0022, where Morfologia (pp. 42, 44, 57) and Sintaxis (p. 119) use lo a, against the ruling that lo and a never combine. The maintainer kept the ruling (2026-10-17). err-0023 (open, `draft`): Morfologia p. 39 and Sintaxis p. 31 allow ta with gusta, against the modal ruling.
- `tools/contribute/`: a clickable prototype of the contribution tool (board card P2-09) and its design, `DESIGN.md`, with the maintainer's decisions of 2026-10-18 and the account setup checklist. Teachers and linguists check machine translations next to the printed AB 2018 page, translate words, and write everyday sentences in Aruban Papiamento with live checks from `rules/`, `lexicon/barbarismos/` and `lexicon/variants/`. It runs from a local file and stores answers only in the browser. Its Papiamento interface text is a draft for teacher review.

### Changed

- Version 0.1.0 is published on Hugging Face (https://huggingface.co/datasets/ARUBAGOV33/papiamento); the README links it.
- Version 0.1.0 is archived on Zenodo: README (badge, Project status, How to cite), `CITATION.cff` and the dataset card give the DOIs, 10.5281/zenodo.23427109 for 0.1.0 and 10.5281/zenodo.23427108 for all versions.
- Every rule that rested on a maintainer ruling was checked against the source pages, and the maintainer decided each one (2026-10-17):
  - Locative en becomes den (a closed or limited place) or na (a place in general), depending on the meaning (Preposicion y Interheccion pp. 6, 15). Barbarismo bar-0007 now gives `den; na`, and RULE_PRE_EN_001 flags en cas without an automatic fix.
  - RULE_MOR_GERUND_PREFIRIENDO no longer flags prefarando, a form from the old rule pack that no page prints.
  - `_meta/invariants.md` now follows the law on two spelling points. The -sion nouns of AB 2018 §5 (pp. 17–18) are an exception to -cion, and rooi, trei and fei (§3.2, p. 8) are exceptions to word-final y. The example hoy, which is not in the AB 2018 word list, is replaced.
  - The collective-noun invariant cites Stilistica (PDF p. 4) instead of a bare ruling, with the page's own example.
  - Barbarismo bar-0009 (del) now points to RULE_PRE_DE_001.
- The validator closes gaps that let wrong or missing data pass with CI green (found in the 2026-10 bug hunt; the maintainer chose each policy):
  - A registry table whose glob matches no file is an error, unless the registry marks it `"optional": true`. So is a missing `rules/rules.jsonl`, and `tools/test_rules.mjs` now fails without it. `build_dist.py` refuses to build a release in which a table, the grammar rules or the machine rules have no rows, and `build_pages.py` reads its table globs from the registry.
  - A machine rule may not flag any `## Correct` example, including those in its own grammar file (error). A rule lists deliberate exceptions in `allow_correct_hits`.
  - A known fact whose `where` matches no row is a warning. A fact on one row (`id=...`) is an error when that row's cell is emptied or the row is deprecated. The report lists the ids of pending facts.
  - `barbarismos.rule_id` must be the id of a grammar file, unless it is a row-level `RULE_LEX_*` id (warning). RULE_PRN_USTED_001 (bar-0005, bar-0006) is reported until it gets a grammar file or a `RULE_LEX_` id.
  - Rows with no source get an "untraced" warning. A PDF outside `sources/pdf/`, a hidden or line-breaking character in a cell (zero-width, U+2028, no-break space, control characters), and an unknown schema, constraint or `x-papiamento` key are errors.

## [0.1.0] - 2026-10-16

First public release. 16,218 words, 159 numbers, 19 calendar terms, 42 barbarismos, 372 Curaçao-to-Aruba pairs, 315 loanwords, 192 grammar rules and 49 machine rules. Every data row is `draft`: the review board has not reviewed any yet. The 16 errata are `reviewed` (decided by the maintainer).

### Added

- `lexicon/words/A`–`Z`: all 16,218 headwords of the AB 2018 no. 68 word list, with alternative forms, the law's own labels, part of speech where the law gives it, and the printed page. Every row is `draft`; 6 rows are `disputed` because the law appears to contain a typo (`sources/errata.tsv`, err-0003 to err-0008). Translations are empty except two confirmed by the maintainer.
- `sources/pdf/AB2018.pdf`: the official law, from the archive.org copy uploaded by Biblioteca Nacional Aruba.
- `tools/import_ab2018.py` and `tools/import_ab2018_overrides.tsv`: how the word list was rebuilt from the PDF, and every correction made during review.
- `tools/build_pages.py`: generated progress page in each letter folder; CI checks they are up to date.
- English, Dutch and Spanish drafts for the 3,000 most frequent words (2,924 rows filled; 91 left empty on purpose). Drafted by one model, checked cell by cell by a second, disagreements settled by a third; no dictionaries, websites or Glosbe. 170 rows the drafting model rated uncertain carry a note asking reviewers to check them first.
- `translated_by` column in word files: `machine` for machine drafts, otherwise GitHub usernames. The validator requires it whenever a translation is filled.
- Translation conventions in `_meta/conventions.md`.
- `lexicon/numbers/`: cardinals 0-99, 100, 1,000, 1,000,000 and 1,000,000,000 (`biyon`, ruled to mean 10^9) from the AB 2018 word list; ordinals, fractions and multiples from Morfologia §9.3; clock times and worked examples from AB 2018 §10.1.3 and §11.8. 159 rows with English, Dutch and Spanish.
- `lexicon/calendar/days.tsv` and `months.tsv`: the 7 days and 12 months, lowercase, from AB 2018 §9.6 and the word list. Public holidays wait for an official source.
- Number kind `multiple` in the numbers schema.
- All 33 known facts are now checked against data (none pending), including the new rulings never = `nunca` and billion = `biyon`.
- `lexicon/barbarismos/barbarismos.tsv`: 41 forms to avoid with the Aruban form to use: Spanish day and month names, familia, hay, todos, muchos, usted(es), en, de la/del/de los/de las, siete (maintainer rulings, with the correct form cited in AB 2018); tevreden and eigenlijk (Stilistica); four wrong gerund forms (Morfologia p. 48, AB 2018). Rows where the AB 2018 list itself contains the "wrong" form (todo, eigenlijk) are marked disputed with an errata entry.
- `lexicon/variants/curacao-aruba.tsv`: 372 Curaçao → Aruba spelling pairs. Each Curaçao form is printed on the cited page of a Curaçao-spelled source; each Aruban form is an AB 2018 headword. Checked pair by pair for false friends and non-standard spellings.
- `sources/errata.tsv`: err-0009 to err-0013. Morfologia p. 48 lists durmiendo, podiendo and prefiriendo as gerunds, against maintainer rulings (the AB 2018 list has drumiendo); Stilistica vs AB 2018 on eigenlijk; the ruling on todo vs AB 2018.
- `lexicon/loanwords/loanwords.tsv`: 315 loanwords from AB 2018 §12 (gazette pp. 41-44): Spanish words written in a set form, words keeping final z, -eza/-anza nouns; Dutch, English and French words kept in their original spelling or respelled, the two-option pairs, the sch table, special spellings and words derived from brand names; Italian, Latin and German words. Two checkers verified every row against the page images. The language of origin for §12.2 words is assigned by the editors, since the law groups Dutch, English and French.
- `sources/errata.tsv`: err-0014 to err-0016, where §12 and the law's own word list disagree. Decided by the maintainer: dagvaard, osterizer in lowercase, and both schuin and scuins (new loanword row).
- Loanword origins `it`, `la` and `de` in the schema.
- `grammar/`: 192 spelling and grammar rules rebuilt from the source PDFs (AB 2018 orthography annex, Morfologia, Preposicion y Interheccion, Sintaxis, Stilistica), one file per rule with source and printed page. Papiamento examples are quoted verbatim from the page; none were written by a machine. Eight writer agents and eight independent checkers verified every rule against the page image (33 corrections). Of the 222 old rule-pack rules, 30 are not files: duplicates merged into another rule, or statements no page supports (listed in `grammar/README.md`).
- Validator gate for grammar rule files (front matter, source and page, file name, required section), with tests.
- Source `RUL2026` for rules that rest on a maintainer ruling rather than a printed page.
- `rules/rules.jsonl`: 49 machine-readable checker rules (31 orthography, 9 morphology, 4 prepositions, 3 from maintainer rulings, 1 syntax, 1 style), 30 of them with an automatic fix. Every test sentence is printed in the linked grammar file or is a documented mechanical change of a printed example. Four writer agents and four independent checkers built them; the checkers judged precision on about 10,000 real Aruban sentences (no false alarms in their samples apart from foreign-language words in the no-accent rule). 31 flaggable grammar rules have no pattern because a regex cannot check them reliably; `rules/README.md` lists them with the reason.
- Validator gate G5 tests every machine rule against its grammar file; `tools/test_rules.mjs` runs the same tests in JavaScript (the Skirbi checker's engine) in CI. Patterns may not use `\b` or `\w`, which misfire next to ñ in JavaScript.
- `tools/build_dist.py`: builds the release files into `dist/` (never committed): one JSON Lines file per table, the grammar rules as JSON Lines, `rule_pack.json` for a writing checker (machine rules, barbarismos and Curaçao-to-Aruba pairs), the Hugging Face dataset card from `release/dataset-card.md`, a manifest with row counts and SHA-256 checksums, and release notes with the rows per table and status. CI checks that the build works.
- README banner, badges and a progress chart. The chart (`.github/assets/progress-*.svg`) and the table under it are rebuilt from the data by `tools/build_pages.py`, and a workflow refreshes them on `main` after every merge.
- "How this dataset was made" in the README, the Zenodo record and the dataset card: which parts were made with AI models, how they were checked, and why AI models are not listed as authors.
- Partner credit for Vadria Innovation Labs in the README, the Zenodo record and the dataset card, and a Partners section in `GOVERNANCE.md`.
- Release setup: `.zenodo.json` so that Zenodo archives each GitHub release with a DOI, and a release workflow that attaches the release files to the GitHub release and publishes them to Hugging Face. `RELEASING.md` gives the steps.
- Repository skeleton (version 0).
- `_meta/`: conventions for every data file, table schemas and the schema registry, Aruban spelling and grammar invariants, known facts checked on every change, and the allowlist of accented loanwords.
- `_templates/`: empty tables with the correct header row.
- Folder layout for `lexicon/`, `grammar/`, `rules/`, `corpus/` and `eval/`.
- `sources/`: source registry, source cards, errata table and permission records.
- `tools/validate.py`: the validator ("the gauntlet"), with gates G0 (source trace), G1 (format), G2 (schema), G3 (orthography), G4 (integrity) and G5 (known facts), and a GitHub Actions workflow that runs it on every pull request.
- `CLAUDE.md` and `AGENTS.md`: routing notes for AI agents.
- Community files: README, contributing guide, governance, code of conduct, citation metadata, issue forms, pull request template and code owners.
- Licences: Apache-2.0 for code (`LICENSE`) and CC BY 4.0 for data and documentation (`LICENSE-DATA`).

### Changed

- Maintainer decisions on all open errata (2026-10-16); err-0003 to err-0013 are now `reviewed`:
  - Six typos in the AB 2018 word list are corrected in the data (`bongo`, `cinematografo`, `computarisando`, `computerisando`; alternatives `coregimento` and `lisimbein`). Each row notes what the law prints, and a known fact guards each correction.
  - `drumiendo` confirmed over Morfologia's `durmiendo` (new barbarismo row); `por` and `prefera` have no gerund, against Morfologia p. 48.
  - `eigenlijk` is a valid word but should be avoided in careful writing; `todo` only in fixed expressions such as `en todo caso`, otherwise `tur`.
  - `hamas` also means "never".
- Removed the machine translation of `skit` ("sketch"): the law lists it among words from Dutch sch-.
- Known facts now wait while the checked cell is empty, since an empty cell means "not known yet".

[Unreleased]: https://github.com/ARUBAGOV33/papiamento/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ARUBAGOV33/papiamento/releases/tag/v0.1.0
