# tools

## validate.py (the gauntlet)

Checks every data file in the repo against `_meta/conventions.md` and the schemas in `_meta/schema/`. Standard library only, Python 3.9 or newer.

```sh
python3 tools/validate.py            # human report, grouped by gate
python3 tools/validate.py --json     # machine-readable report
python3 tools/validate.py --strict   # warnings count as errors
python3 tools/validate.py --root PATH
```

Each finding is printed as `path:line: [GATE] SEVERITY message`, followed by a summary with error and warning counts per gate and how many known facts were checked or are still pending.

Only files that match a glob in `_meta/schema/registry.json` are checked, plus the PDFs in `sources/pdf/`.

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
| | Non-reviewed row with a source but no page ("untraced"); `sources/sources.tsv` missing | warning |
| | Every PDF in `sources/pdf/` is referenced by exactly one sources row; rows with a `pdf` have a shareable `licence_tier`; `permission` rows have a `permission_ref`; `pdf` and `card` paths exist | error |
| G1 Format | UTF-8, NFC, LF only, final newline, no blank lines, header equals the schema, right number of cells, no leading/trailing/double spaces, no curly apostrophes, rows sorted by `sort_by` (case-insensitive) | error |
| | Cell wrapped in `"` quotes | warning |
| G2 Schema | `required`, `enum`, `pattern` (full match), `unique` within the file; `reviewed_by` set when `status` is `reviewed`; `at_most` pairs (an audit's `errors` never above its `sample_size`) | error |
| G3 Orthography | In `aruban_text` columns: accented or non-Aruban characters unless the word is in `_meta/allowlists/accented-loans.txt`; word in the wrong letter folder | error |
| | Curaçao markers (`-shon`, `k` before a/o/u, `ku`/`kos`/`kon`/`ki`), skipped for rows sourced from `AB2018` | warning |
| G4 Integrity | `id` unique across all tables; `unique_together` across all files of a table | error |
| | `lexicon_refs` values that are not a lemma in `lexicon/words/` (skipped while there are no word files) | warning |
| G5 Known facts | Each row of `_meta/known-facts.tsv` holds for the matching data rows (deprecated rows are ignored). Facts with no matching row yet are counted as pending, not reported. | error |

G5 runs every function in `G5_CHECKS`; add rule tests there.

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

Builds what a release ships into `dist/`, which is never committed. Standard library only.

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

## Tests

```sh
python3 -m unittest discover -s tests -v
```

`tests/fixtures/valid/` is a small repo that passes. Every other folder in `tests/fixtures/` holds only the files that differ from it, so each case breaks exactly one thing. The tests copy the real `_meta/` into each fixture, so they always run against the current schemas.
