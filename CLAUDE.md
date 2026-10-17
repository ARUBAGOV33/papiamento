# CLAUDE.md — agent router

You are in **ARUBAGOV33/papiamento**, the open reference dataset for **Aruban** Papiamento (`pap-AW`). It is not Curaçao Papiamentu. Load only what your task needs.

## Always

- Read [`_meta/invariants.md`](_meta/invariants.md) before writing or checking any Papiamento text.
- The source PDFs are the source of truth. Cite `source` + printed `page` for every row you add. If you can't find the page, leave the row `draft` and say so.
- Never set `status` to `reviewed`. Only a human review-board member does that.
- Machine-made content (yours included) is always `draft`.
- Curaçao spellings go only in `lexicon/variants/curacao-aruba.tsv`.
- When you quote a wrong form, put the correct form next to it.
- Run `python3 tools/validate.py` before finishing. Zero errors.
- When your change makes progress (new rows or tables, rows reviewed, a release), update "Project status" in `README.md` in the same pull request. Run `python3 tools/build_pages.py` for the generated chart, table and "still empty" line, and edit the hand-written lines under them if they no longer hold.

## What to load for each task

| Task | Load | Do not load |
|---|---|---|
| Write or check Aruban text | `_meta/invariants.md`, `lexicon/barbarismos/`, `lexicon/numbers/`, `lexicon/calendar/` | `eval/`, `lexicon/variants/` (except to convert Curaçao text) |
| Add or fix a word or translation | `_meta/conventions.md` (Words section), the one letter file `lexicon/words/<L>/words.tsv`, `sources/cards/<ID>.md` for its source | other letter files |
| Add a source | `sources/README.md`, `_templates/source-card.md`, `_meta/schema/sources.schema.json` | `sources/pdf/` contents |
| Write or fix a grammar rule | `grammar/README.md`, the topic folder, the cited source card | `eval/` answers |
| Convert Curaçao text to Aruban | `lexicon/variants/curacao-aruba.tsv`, `_meta/invariants.md` | — |
| Change the validator | `tools/README.md`, `_meta/schema/`, `tests/` | data files beyond test fixtures |
| Build evaluation sets | `eval/README.md` | — (and never train on `eval/`) |
| Log a source typo | `sources/errata.tsv`, the source card | — |
| Log an audit (random sample checked against the PDFs) | `_meta/conventions.md` (Audits section), `_templates/audit-row.tsv`, `_meta/audits.tsv` | — |
| Prepare a release | `RELEASING.md`, `CHANGELOG.md`, `CITATION.cff`, `release/dataset-card.md` | data files |

## Where things live

| Path | What |
|---|---|
| `_meta/` | conventions, schemas, invariants, known facts, allowlists, audit log |
| `_templates/` | starter files for each contribution type |
| `lexicon/` | words A–Z, numbers, calendar, barbarismos, variants, loanwords, names |
| `grammar/` | rules in plain language, one small file per rule |
| `rules/` | machine-readable checker rules and their tests |
| `corpus/` | redistributable Aruban text with a manifest |
| `eval/` | test sets for the writing auditor (do not train on them) |
| `sources/` | source registry, cards, shareable PDFs, errata, permissions |
| `release/` | template of the Hugging Face dataset card |
| `tools/` | validator and build scripts |

Every folder's `README.md` is its contract: what lives there, the format, and how to add to it.
