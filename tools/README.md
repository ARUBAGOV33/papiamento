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
| G2 Schema | `required`, `enum`, `pattern` (full match), `unique` within the file; `reviewed_by` set when `status` is `reviewed` | error |
| G3 Orthography | In `aruban_text` columns: accented or non-Aruban characters unless the word is in `_meta/allowlists/accented-loans.txt`; word in the wrong letter folder | error |
| | Curaçao markers (`-shon`, `k` before a/o/u, `ku`/`kos`/`kon`/`ki`), skipped for rows sourced from `AB2018` | warning |
| G4 Integrity | `id` unique across all tables; `unique_together` across all files of a table | error |
| | `lexicon_refs` values that are not a lemma in `lexicon/words/` (skipped while there are no word files) | warning |
| G5 Known facts | Each row of `_meta/known-facts.tsv` holds for the matching data rows (deprecated rows are ignored). Facts with no matching row yet are counted as pending, not reported. | error |

G5 runs every function in `G5_CHECKS`; add rule tests there.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

`tests/fixtures/valid/` is a small repo that passes. Every other folder in `tests/fixtures/` holds only the files that differ from it, so each case breaks exactly one thing. The tests copy the real `_meta/` into each fixture, so they always run against the current schemas.
