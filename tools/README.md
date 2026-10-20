# tools

## validate.py (the gauntlet)

Checks every data file in the repo against `_meta/conventions.md` and the schemas in `_meta/schema/`. Standard library only, Python 3.9 or newer.

```sh
python3 tools/validate.py            # human report, grouped by gate
python3 tools/validate.py --json     # machine-readable report
python3 tools/validate.py --strict   # warnings count as errors
python3 tools/validate.py --root PATH
```

Each finding is printed as `path:line: [GATE] SEVERITY message`, followed by a summary with error and warning counts per gate and how many known facts were checked or are still pending (with their ids).

Only files that match a glob in `_meta/schema/registry.json` are checked, plus `rules/rules.jsonl`, the grammar files and every PDF in the repo. Every table's glob must match at least one file (a file with only the header is enough), so a typo in a glob or a moved folder cannot drop a table. A table that may have no file yet gets `"optional": true` in the registry.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | No errors (warnings allowed) |
| 1 | At least one error (with `--strict`, any warning too) |
| 2 | Bad command line |

### Gates

| Gate | Checks | Severity |
|---|---|---|
| G0 Source trace | `source` is an id in `sources/sources.tsv`; `reviewed` rows have `source` and `page` | error |
| | Non-reviewed row with no source, or with a source but no page ("untraced"); `sources/sources.tsv` missing | warning |
| | Every PDF in `sources/pdf/` is referenced by exactly one sources row; no PDF anywhere else in the repo (hidden folders other than `.github` are skipped); rows with a `pdf` have a shareable `licence_tier`; `permission` rows have a `permission_ref`; `pdf` and `card` paths exist | error |
| G1 Format | Every registry table has a file and `rules/rules.jsonl` exists; UTF-8, NFC, LF only, final newline, no blank lines, header equals the schema, right number of cells, no leading/trailing/double spaces, no curly apostrophes, no hidden or line-breaking characters (control and zero-width characters, U+2028, no-break and other non-ASCII spaces), rows sorted by `sort_by` (case-insensitive) | error |
| | Cell wrapped in `"` quotes | warning |
| G2 Schema | `required`, `enum`, `pattern` (full match), `unique` within the file; `reviewed_by` set when `status` is `reviewed`; `at_most` pairs (an audit's `errors` never above its `sample_size`) | error |
| | The schemas themselves: no unknown top-level, field or constraint keys (only `required`, `enum`, `pattern`, `unique` are checked), and every `x-papiamento` key is known and names fields of the table. A typo would otherwise switch a check off. | error |
| G3 Orthography | In `aruban_text` columns: accented or non-Aruban characters unless the word is in `_meta/allowlists/accented-loans.txt`; word in the wrong letter folder | error |
| | Curaçao markers (`-shon`, `k` before a/o/u, `ku`/`kos`/`kon`/`ki`), skipped for rows sourced from `AB2018` | warning |
| G4 Integrity | `id` unique across all tables; `unique_together` across all files of a table; `word_refs` (`names.word_id` is an id in `lexicon/words/` whose lemma is the row's `name`); `folder_refs` (each `; `-separated id is in the named file in the same folder: a pair's prompt, a name's `related` names) | error |
| | `lexicon_refs` values that are not a lemma in `lexicon/words/` (skipped while there are no word files); `rule_refs` values (`barbarismos.rule_id`) that are not the id of a grammar file. `RULE_LEX_*` ids are row-level, the row itself is the rule, so they need no grammar file. | warning |
| G5 Known facts | Each row of `_meta/known-facts.tsv` holds for the matching data rows (deprecated rows and empty cells are ignored, and the fact is then pending). A fact on one row (`where` = `id=...`) is an error when that row's cell is empty or the row is deprecated, so a correction cannot be switched off silently. | error |
| | A fact whose `where` matches no row at all (a typo, or a fact recorded before its row) | warning |
| G5 Machine rules | Each rule in `rules/rules.jsonl` has a grammar file, compiles, catches its `match` tests, leaves its `no_match` tests alone and gives the expected `fix` output; tests are printed in the grammar file. No rule flags a `## Correct` example of any grammar file, its own included, unless the rule lists it in `allow_correct_hits`. | error |

G5 runs every function in `G5_CHECKS`; add rule tests there.

## contribute/ (prototype)

The contribution tool's clickable prototype for teachers and linguists (board card P2-09): checking machine translations, translating words and translating sentences, with live checks from `rules/`, `lexicon/barbarismos/` and `lexicon/variants/`. It runs from a local file and sends nothing anywhere. See [contribute/README.md](contribute/README.md) and the design in [contribute/DESIGN.md](contribute/DESIGN.md).

## build_pages.py (progress pages)

Rebuilds the generated progress pages from the data: the page of each letter in `lexicon/words/`, the table in `lexicon/words/README.md`, the progress chart `.github/assets/progress-light.svg` and `progress-dark.svg`, and the table between the `REPO-PROGRESS` markers in `README.md`. Standard library only. The same data always gives the same pages, byte for byte.

```sh
python3 tools/build_pages.py           # rewrite the pages
python3 tools/build_pages.py --check   # list pages that are out of date, write nothing
```

You don't have to run it: after every merge, the "Refresh progress pages" workflow runs it on `main` and commits the result. In a pull request the check only prints a notice.

### Measured quality

Row counts show how much has been added, not how much of it is right. The error rates come from random audits logged in [`_meta/audits.tsv`](../_meta/audits.tsv) (see the Audits section of [`_meta/conventions.md`](../_meta/conventions.md)):

- The README table has a **Measured error rate** column. For each table it shows the latest audit (by date, then id): the share of sampled rows that were wrong and the sample, with the 95% Wilson score interval and the date in small print under it, so the lines stay short on a phone. A table without an audit says "not audited yet". An audit of `translations` is shown under it in the Words row. An audit done only by `machine` says "checked by machine", and the note under the table explains it.
- Once any audit is logged, the chart gets a **Quality** section: one row per audited table, with a dot for the error rate and a band for its 95% interval. The scale runs from 0 to 25%, or to 50% or 100% if an interval reaches past that.
- Rows that the gauntlet rejects (for example `errors` greater than `sample_size`) are skipped.
- The **Milestones** line at the top of the block comes from the hand-maintained [`_meta/milestones.tsv`](../_meta/milestones.tsv): one entry per phase, P0 to P4, with its status.

Not yet: **frequency-weighted reviewed coverage**, "of every 100 words in real Aruban text, how many are reviewed entries". It needs a word-frequency list that may be published here, and the maintainer has not chosen one yet. See the TODO in `build_pages.py`; do not add frequency data until that is decided.

## build_dist.py (release files)

Builds what a release ships into `dist/`, which is never committed. Standard library only. It stops before writing anything if a table, the grammar rules or the machine rules have no rows (a table marked `"optional": true` in the registry may be empty).

```sh
python3 tools/build_dist.py                    # version from CITATION.cff
python3 tools/build_dist.py --version 0.2.0    # another version number
python3 tools/build_dist.py --check            # build into a temporary folder and discard it (CI)
```

| File | Content |
|---|---|
| `<table>.jsonl` | One JSON object per row for each table in `_meta/schema/registry.json`. Multi-value cells (`alt`, `en`, `nl`, `es`, `translated_by`, `reviewed_by`, `right`, `authors`) become lists. |
| `grammar.jsonl` | One object per grammar file: front matter, the rule text and the example lists. |
| `rules.jsonl` | The machine rules, with severity, status, source and page from the grammar file. |
| `rule_pack.json` | Machine rules, barbarismos and Curaçao-to-Aruba pairs in one file, for a writing checker. |
| `README.md` | The Hugging Face dataset card, filled in from `release/dataset-card.md`. |
| `RELEASE_NOTES.md` | Rows per table and status, then the version's section of `CHANGELOG.md`. |
| `manifest.json` | Counts, and the size and SHA-256 of every other file. |

The same input always gives byte-identical output. See [RELEASING.md](../RELEASING.md) for how a release is published.

## add_prompts.py (a batch of prompts for the parallel sentences)

Adds English or Spanish prompts from a text file (`lang|topic|text`, one per line) to `corpus/parallel/prompts.tsv`, or to `eval/parallel/prompts.tsv` for the held-out 15% (`int(sha256(id), 16) % 100 < 15`). It gives each prompt the next free id and refuses prompts that break the rules (1 to 14 words, no digits, no abbreviations, no characters Common Voice rejects) or are already in either table. Standard library only.

```sh
python3 tools/add_prompts.py batch.txt --batch prompts-2 --author machine --check   # report only
python3 tools/add_prompts.py batch.txt --batch prompts-2 --author machine
```

## word_frequency.py (which words to translate first)

Ranks the AB 2018 headwords by how often they occur in text the repo publishes: the shareable source PDFs in `sources/pdf/` (not the word lists AB2018 and VOC2009, which print every headword once; AB2018's orthography annex is the text of ORT2009, which is counted), blended with the Aruban sentences in `corpus/parallel/pairs.tsv` once there are any. The held-out `eval/` sentences are not used. Chosen by the maintainer on 2026-10-18; counts from private text are never published.

```sh
python3 tools/word_frequency.py --untranslated --out word-frequency.tsv
python3 tools/word_frequency.py --no-pdf      # sentences only
```

Output columns: `id`, `lemma`, `pdf_count`, `sentence_count`, `score` (rate per million words; the average of the PDF and sentence rates once there are sentences), `translated`. Reading the PDFs needs PyMuPDF (`pip install pymupdf`), like `import_ab2018.py`. The output is not committed: the contribution tool regenerates it to order its "Translate words" queue.

## apply_contributions.py (contribution tool → data files)

Brings the review board's decisions from the contribution tool's database (Supabase, see `tools/contribute/supabase/`) into the data files:

- **word decisions** go into the `en`/`nl`/`es`, `translated_by`, `status`, `reviewed_by` and `notes` cells of `lexicon/words/<L>/words.tsv`;
- **sentence decisions** become new rows in `corpus/parallel/pairs.tsv`, or `eval/parallel/pairs.tsv` for held-out prompts;
- **every person it credits** gets a row in `_meta/contributors.tsv` (no email).

A row becomes `reviewed` only when a board member or maintainer with a GitHub username decided it; otherwise it stays `draft`. It skips and lists, without writing:

- a word already reviewed in the repo;
- a translate decision on a word that has a translation by now;
- a sentence with characters Aruban spelling does not allow;
- a handle that belongs to someone else.

Standard library only.

```sh
python3 tools/apply_contributions.py fetch --out snapshot.json          # needs SUPABASE_URL and SUPABASE_SECRET_KEY
python3 tools/apply_contributions.py apply --snapshot snapshot.json --dry-run
python3 tools/apply_contributions.py apply --snapshot snapshot.json --summary pr-body.md --ids ids.json
python3 tools/apply_contributions.py mark-exported --ids ids.json --pr-url https://github.com/ARUBAGOV33/papiamento/pull/N
```

The **Contribution sync** workflow (`.github/workflows/contribute-sync.yml`) runs it weekly, or from the Actions tab (dry run by default):

1. It fetches the decisions, writes them, rebuilds the progress pages and runs the gauntlet and the tests.
2. It opens **one** pull request through the papiamento-sync GitHub App, so the gauntlet runs on it.
3. Only then does it mark the decisions as exported.

It does nothing while an earlier sync pull request is still open, and it never merges.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

`tests/fixtures/valid/` is a small repo that passes. Every other folder in `tests/fixtures/` holds only the files that differ from it, so each case breaks exactly one thing. The tests copy the real `_meta/` into each fixture, so they always run against the current schemas. The live known facts are the exception: they name rows the small repo does not have, so `tests/fixtures/valid/_meta/known-facts.tsv` holds a few facts that match its rows.
